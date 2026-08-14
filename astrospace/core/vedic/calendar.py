"""Calendar intelligence built from panchanga, dashas, and transits."""
from datetime import datetime, timedelta

from .dashas import vimshottari_dasha
from .nakshatra import nakshatra_of
from .panchanga_day import daily_panchanga, personal_panchanga
from .positions import sign_index
from .transits import transit_analysis

# Bumped when the calendar/festival assembly logic or dataset changes in a
# way that would make a previously cached response wrong — independent of
# any profile's own birth-data revision. See docs/reliable_native_core_
# architecture_2026-08-14.md's cache validity contract; consumed by
# /api/v1/vedic/{kundli_id}/calendar-intelligence.
CALENDAR_ENGINE_VERSION = "calendar-intelligence-1.0"
CALENDAR_DATASET_VERSION = "astrospace-calendar-2026.08.14"


def _event(date: str, category: str, title: str, detail: str,
           tone: str = "neutral", strength: int = 50, meta: dict | None = None) -> dict:
    return {
        "date": date,
        "category": category,
        "title": title,
        "detail": detail,
        "tone": tone,
        "strength": strength,
        "meta": meta or {},
    }


def _period_event_if_inside(period: dict | None, label: str,
                            start_dt: datetime, end_dt: datetime) -> list[dict]:
    if not period:
        return []
    rows = []
    for key, title in (("start", f"{label} starts"), ("end", f"{label} ends")):
        dt = datetime.fromisoformat(period[key])
        if start_dt.date() <= dt.date() <= end_dt.date():
            rows.append(_event(
                dt.date().isoformat(),
                "dasha",
                f"{period['lord']} {title}",
                f"{period['lord']} {label.lower()} {key}: {dt.date().isoformat()}",
                "neutral",
                68,
                {"lord": period["lord"], "period": label, "boundary": key},
            ))
    return rows


def _practitioner_day_detail(payload: dict) -> dict:
    """Full panchanga detail for practitioner-mode calendar day screens.

    The regular day summary is intentionally compact for month/list rendering.
    Practitioner mode needs the complete named windows and non-window rules
    (Disha Shool, Panchaka, Hora, Choghadiya, masa, etc.) so the UI should not
    have to render "Not returned" for facts already computed by daily_panchanga.
    """
    return {
        "sunrise": payload.get("sunrise"),
        "sunset": payload.get("sunset"),
        "next_sunrise": payload.get("next_sunrise"),
        "moonrise": payload.get("moonrise"),
        "moonset": payload.get("moonset"),
        "masa": payload.get("masa"),
        "samvatsara": payload.get("samvatsara"),
        "ritu": payload.get("ritu"),
        "ayana": payload.get("ayana"),
        "disha_shool": payload.get("disha_shool"),
        "panchaka": payload.get("panchaka"),
        "elements": payload.get("elements"),
        "windows": payload.get("windows") or {"auspicious": [], "inauspicious": []},
        "choghadiya": payload.get("choghadiya"),
        "horas": payload.get("horas"),
        "conventions": payload.get("_conventions"),
    }


def calendar_intelligence(
    chart,
    start_dt: datetime,
    city: str,
    nation: str,
    lat: float,
    lng: float,
    tz_str: str,
    display_tz_str: str,
    days: int = 30,
    include_practitioner_detail: bool = False,
) -> dict:
    """Return a dated intelligence feed for the selected profile."""
    days = max(1, min(60, days))
    end_dt = start_dt + timedelta(days=days)
    moon_lon = chart.positions["Moon"]["lon"]
    janma_nak = nakshatra_of(moon_lon)
    janma_rashi = sign_index(moon_lon)

    dasha = vimshottari_dasha(moon_lon, chart.moment.dt_local, start_dt)
    transits = transit_analysis(
        chart.positions,
        chart.lagna_lon,
        start_dt,
        chart.ayanamsha,
        chart.node_type,
        dasha_context=dasha.get("current"),
    )

    events: list[dict] = []
    current = dasha["current"]
    active_parts = [
        current.get("mahadasha", {}).get("lord") if current.get("mahadasha") else None,
        current.get("antardasha", {}).get("lord") if current.get("antardasha") else None,
        current.get("pratyantardasha", {}).get("lord") if current.get("pratyantardasha") else None,
    ]
    active_label = " / ".join([p for p in active_parts if p])
    if active_label:
        events.append(_event(
            start_dt.date().isoformat(),
            "dasha",
            f"Active dasha: {active_label}",
            "Current Vimshottari period stack for this profile.",
            "neutral",
            82,
            {"path": active_label},
        ))

    events += _period_event_if_inside(current.get("mahadasha"), "Mahadasha", start_dt, end_dt)
    events += _period_event_if_inside(current.get("antardasha"), "Antardasha", start_dt, end_dt)
    events += _period_event_if_inside(current.get("pratyantardasha"), "Pratyantardasha", start_dt, end_dt)

    for rule in transits["gochara"]["active_rules"]:
        events.append(_event(
            start_dt.date().isoformat(),
            "transit",
            rule["name"],
            rule["trigger"],
            "supportive" if rule["severity"] == "supportive" else "challenging",
            92 if rule["severity"] == "high" else 78,
            {"planet": rule["planet"], "severity": rule["severity"]},
        ))

    if transits["strongest_aspect"]:
        aspect = transits["strongest_aspect"]
        events.append(_event(
            start_dt.date().isoformat(),
            "transit",
            f"{aspect['transit_planet']} {aspect['aspect'].lower()} natal {aspect['natal_planet']}",
            f"{aspect['transit_sign']} to {aspect['natal_sign']} · orb {aspect['orb']} deg.",
            aspect["tone"],
            aspect["strength"],
            {"aspect": aspect},
        ))

    for row in transits["timeline"]["next_30_days"]:
        events.append(_event(
            row["date"],
            "transit",
            row["title"],
            row["detail"],
            row["tone"],
            row["strength"],
            {"type": row["type"], "planet": row["planet"]},
        ))

    panchanga_days = []
    for offset in range(days + 1):
        day = start_dt + timedelta(days=offset)
        payload = daily_panchanga(
            day.year, day.month, day.day,
            city, nation, lat, lng, tz_str, display_tz_str,
        )
        personal = personal_panchanga(
            payload,
            janma_nakshatra_index=janma_nak["index"],
            janma_rashi_index=janma_rashi,
            ghatak_moon_sign=janma_rashi,
        )
        payload["personal"] = personal
        day_summary = {
            "date": payload["date"],
            "vara": payload["vara"]["name"],
            "tithi": payload["elements"]["tithi"][0]["name"],
            "nakshatra": payload["elements"]["nakshatra"][0]["name"],
            "moon_rashi": payload["moon_rashi_at_sunrise"],
            "tarabala": personal["tarabala"],
            "chandrabala": personal["chandrabala"],
            "auspicious_count": len(payload["windows"]["auspicious"]),
            "inauspicious_count": len(payload["windows"]["inauspicious"]),
            "windows": {
                "auspicious": payload["windows"]["auspicious"] if include_practitioner_detail else payload["windows"]["auspicious"][:3],
                "inauspicious": payload["windows"]["inauspicious"] if include_practitioner_detail else payload["windows"]["inauspicious"][:3],
            },
        }
        if include_practitioner_detail:
            day_summary.update({
                "gulika": payload.get("gulika"),
                "mandi": payload.get("mandi"),
                "practitioner_detail": _practitioner_day_detail(payload),
            })
        panchanga_days.append(day_summary)
        tone = "supportive" if personal["tarabala"]["favourable"] and personal["chandrabala"]["favourable"] else "challenging"
        strength = 74 if tone == "supportive" else 62
        events.append(_event(
            payload["date"],
            "panchanga",
            f"{payload['vara']['name']} · {payload['elements']['nakshatra'][0]['name']}",
            f"{payload['elements']['tithi'][0]['name']} tithi · Moon in {payload['moon_rashi_at_sunrise']}.",
            tone,
            strength,
            {
                "tarabala": personal["tarabala"]["tara"],
                "chandrabala_house": personal["chandrabala"]["house_from_rashi"],
            },
        ))

    events.sort(key=lambda row: (row["date"], -row["strength"], row["category"], row["title"]))
    by_date: dict[str, list[dict]] = {}
    for row in events:
        by_date.setdefault(row["date"], []).append(row)

    start_date = start_dt.date().isoformat()
    return {
        "system": "AstroSpace Calendar Intelligence",
        "engine_version": CALENDAR_ENGINE_VERSION,
        "dataset_version": CALENDAR_DATASET_VERSION,
        "profile": {"name": chart.name, "janma_nakshatra": janma_nak["name"]},
        "provenance": {
            **chart.provenance("calendar-intelligence"),
            "timezone": display_tz_str,
            "panchanga_place": {"city": city, "nation": nation, "timezone": tz_str},
            "confidence": {
                **chart.provenance("calendar-intelligence")["confidence"],
                "calendar_feed": "computed aggregation of dasha, panchanga, and transit signals",
            },
        },
        "start_date": start_date,
        "end_date": end_dt.date().isoformat(),
        "timezone": display_tz_str,
        "place": {"city": city, "nation": nation, "timezone": tz_str},
        "current": {
            "dasha": current,
            "strongest_transit": transits["strongest_aspect"],
            "active_rules": transits["gochara"]["active_rules"],
            "panchanga": next((p for p in panchanga_days if p["date"] == start_date), None),
        },
        "panchanga_days": panchanga_days,
        "events": events,
        "by_date": by_date,
        "notes": [
            "Calendar events are deterministic signals from panchanga, dasha, and transit engines.",
            "Saved readings and user validation can be attached to these dates next.",
        ],
    }
