"""
Daily panchanga orchestrator — the full "Today" payload for a date+place,
plus the personalized block (tarabala, chandrabala, ghatak alerts) that
relates the day to a specific person's janma nakshatra/rashi.
"""
from datetime import date as date_cls, datetime

from .constants import NAKSHATRAS, TITHI_GROUPS, VARA_NAMES, VARA_LORDS
from .positions import (
    resolve_location, day_span, jd_to_local, sidereal_positions, sign_index,
    sign_name,
)
from .nakshatra import nakshatra_of
from .kala import kala_windows, choghadiya, horas
from .masa import (
    amanta_masa, ayana, gulika_positions, moon_events_for_day, ritu,
    samvatsara,
)
from .moontimes import elements_for_day, varjya_windows, amrit_kalam_windows
from .ghatak import ghatak_of

TARABALA_NAMES = [
    "Janma", "Sampat", "Vipat", "Kshema", "Pratyari",
    "Sadhaka", "Vadha", "Mitra", "Parama Mitra",
]
TARABALA_GOOD = {"Sampat", "Kshema", "Sadhaka", "Mitra", "Parama Mitra"}
CHANDRABALA_GOOD = {1, 3, 6, 7, 10, 11}
CHANDRABALA_BAD = {4, 8, 12}

# Disha shool — direction to avoid travelling toward, by weekday.
DISHA_SHOOL = {
    "Monday": "East", "Saturday": "East",
    "Thursday": "South",
    "Sunday": "West", "Friday": "West",
    "Tuesday": "North", "Wednesday": "North",
}

# Panchaka nakshatras: Dhanishta..Revati. Classical rule starts from
# Dhanishta's SECOND half; we flag the whole nakshatra conservatively.
PANCHAKA_NAKSHATRA_IDX = {22, 23, 24, 25, 26}


def _bhadra_windows(karana_entries: list, rise: float, next_rise: float,
                    tz_str: str) -> list:
    """
    Vishti (Bhadra) karana spans overlapping the Vedic day, as inauspicious
    windows. Boundaries come from the karana entries' iso end times: each
    entry starts where the previous ended (sunrise for the first) and ends
    at its own upto, capped at next sunrise.
    """
    windows = []
    rise_dt = jd_to_local(rise, tz_str)
    next_rise_dt = jd_to_local(next_rise, tz_str)
    prev_end = rise_dt
    for entry in karana_entries:
        end_dt = datetime.fromisoformat(entry["upto_iso"])
        if entry["name"] == "Vishti":
            w_start = max(prev_end, rise_dt)
            w_end = min(end_dt, next_rise_dt)
            if w_end > w_start:
                windows.append({
                    "name": "Bhadra (Vishti Karana)",
                    "kind": "inauspicious",
                    "start": w_start.strftime("%H:%M"),
                    "end": w_end.strftime("%H:%M"),
                    "start_iso": w_start.isoformat(),
                    "end_iso": w_end.isoformat(),
                })
        prev_end = end_dt
    return windows


def daily_panchanga(year: int, month: int, day: int,
                    city: str = None, nation: str = "IN",
                    lat: float = None, lng: float = None,
                    tz_str: str = None,
                    display_tz_str: str = None) -> dict:
    lat, lng, tz_str = resolve_location(city, nation, lat, lng, tz_str)
    display_tz_str = display_tz_str or tz_str
    span = day_span(year, month, day, lat, lng, tz_str)
    if span is None:
        raise ValueError("Sunrise/sunset undefined at this latitude/date (circumpolar).")
    rise, sets, next_rise = span

    vara_idx = (date_cls(year, month, day).weekday() + 1) % 7
    elements = elements_for_day(rise, next_rise, display_tz_str)
    windows = kala_windows(rise, sets, next_rise, vara_idx, display_tz_str)
    windows["inauspicious"] += varjya_windows(rise, next_rise, display_tz_str)
    windows["inauspicious"] += _bhadra_windows(elements["karana"], rise,
                                               next_rise, display_tz_str)
    windows["auspicious"] += amrit_kalam_windows(rise, next_rise, display_tz_str)
    windows["auspicious"].sort(key=lambda w: w["start_iso"])
    windows["inauspicious"].sort(key=lambda w: w["start_iso"])

    moon_at_rise = sidereal_positions(rise)["Moon"]["lon"]

    masa_info = amanta_masa(rise)
    moonrise_jd, moonset_jd = moon_events_for_day(rise, next_rise, lat, lng)
    day_nak_idx = elements["nakshatra"][0]["index"]

    return {
        "date": f"{year:04d}-{month:02d}-{day:02d}",
        "place": {
            "city": city,
            "lat": lat,
            "lng": lng,
            "timezone": display_tz_str,
            "calculation_timezone": tz_str,
        },
        "vara": {"name": VARA_NAMES[vara_idx], "lord": VARA_LORDS[vara_idx]},
        "sunrise": jd_to_local(rise, display_tz_str).strftime("%H:%M"),
        "sunset": jd_to_local(sets, display_tz_str).strftime("%H:%M"),
        "next_sunrise": jd_to_local(next_rise, display_tz_str).strftime("%H:%M"),
        "moon_rashi_at_sunrise": sign_name(sign_index(moon_at_rise)),
        "moonrise": (jd_to_local(moonrise_jd, display_tz_str).strftime("%H:%M")
                     if moonrise_jd is not None else None),
        "moonset": (jd_to_local(moonset_jd, display_tz_str).strftime("%H:%M")
                    if moonset_jd is not None else None),
        "masa": {
            "amanta": masa_info["name"],
            "purnimanta": masa_info["purnimanta_name"],
            "adhika": masa_info["adhika"],
            "paksha": masa_info["paksha"],
        },
        "samvatsara": samvatsara(rise),
        "ritu": ritu(masa_info["name_index"]),
        "ayana": ayana(rise),
        "disha_shool": DISHA_SHOOL[VARA_NAMES[vara_idx]],
        "panchaka": {
            "active": day_nak_idx in PANCHAKA_NAKSHATRA_IDX,
            "nakshatra": NAKSHATRAS[day_nak_idx],
            "note": ("Whole-Dhanishta flagged conservatively (classical rule "
                     "starts from its second half); type classification "
                     "convention-dependent; verify"),
        },
        "gulika": gulika_positions(rise, sets, next_rise, vara_idx, lat, lng,
                                   display_tz_str),
        "elements": elements,
        "windows": windows,
        "choghadiya": choghadiya(rise, sets, next_rise, vara_idx, display_tz_str),
        "horas": horas(rise, sets, next_rise, vara_idx, display_tz_str),
        "_conventions": {
            "day_definition": "sunrise to next sunrise",
            "verify_pending": ["durmuhurta table", "choghadiya tables",
                               "varjya/amrit ghati tables", "godhuli span",
                               "samvatsara reckoning", "panchaka type table",
                               "gulika start-vs-middle of Saturn part"],
        },
    }


def personal_panchanga(day_payload: dict, janma_nakshatra_index: int,
                       janma_rashi_index: int, ghatak_moon_sign: int = None) -> dict:
    """
    Personal indicators for a day. janma_* come from the person's kundli;
    ghatak_moon_sign is their Moon sign index for ghatak-chakra alerts.
    """
    today_nak_name = day_payload["elements"]["nakshatra"][0]["name"]
    today_nak_idx = NAKSHATRAS.index(today_nak_name)
    today_tithi_idx = day_payload["elements"]["tithi"][0]["index"]
    today_moon_sign = day_payload["moon_rashi_at_sunrise"]
    vara_name = day_payload["vara"]["name"]

    # Tarabala: count from janma nakshatra to today's, inclusive, cycle of 9
    count = (today_nak_idx - janma_nakshatra_index) % 27 % 9
    tara = TARABALA_NAMES[count]
    tarabala = {
        "tara": tara,
        "count": count + 1,
        "favourable": tara in TARABALA_GOOD,
        "note": "Janma tara — avoid major beginnings" if tara == "Janma" else None,
    }

    # Chandrabala: today's Moon sign counted from janma rashi
    today_moon_idx = [i for i in range(12) if sign_name(i) == today_moon_sign][0]
    house = (today_moon_idx - janma_rashi_index) % 12 + 1
    chandrabala = {
        "house_from_rashi": house,
        "favourable": house in CHANDRABALA_GOOD,
        "chandrashtama": house == 8,
    }

    # Ghatak alerts: does today match the person's ghatak indicators?
    alerts = []
    if ghatak_moon_sign is not None:
        g = ghatak_of(ghatak_moon_sign)
        tithi_number = today_tithi_idx % 15 + 1
        # Amanta masa name from the day payload (adhika prefix stripped for
        # comparison against the ghatak table's plain month names).
        today_masa = (day_payload.get("masa") or {}).get("amanta")
        today_masa_base = (today_masa.removeprefix("Adhika ")
                           if isinstance(today_masa, str) else None)
        checks = [
            ("month", today_masa_base == g["month"], g["month"]),
            ("day", vara_name == g["day"], g["day"]),
            ("nakshatra", today_nak_name == g["nakshatra"], g["nakshatra"]),
            ("tithi", tithi_number in TITHI_GROUPS[g["tithi_group"]], g["tithi"]),
            ("chandra", today_moon_sign == g["rashi"], g["rashi"]),
        ]
        alerts = [
            {"type": t, "matched": m, "ghatak_value": v}
            for t, m, v in checks
        ]

    return {"tarabala": tarabala, "chandrabala": chandrabala, "ghatak_alerts": alerts}
