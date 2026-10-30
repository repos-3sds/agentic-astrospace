"""
Moon-transit timing engine — exact clock times for panchanga element
boundaries (tithi/nakshatra/yoga/karana "upto" times) and the
nakshatra-portion windows Varjya and Amrit Kalam.

Method: each element is a bucket of an angle that increases monotonically
with time (Moon−Sun elongation for tithi/karana, Moon longitude for
nakshatra, Moon+Sun for yoga; all move 10°–27°/day), so boundary crossings
are found by bisection on Swiss Ephemeris positions. Precision ~1 second.

Varjya/Amrit ghati tables: the nakshatra's full span is treated as 60
ghatis; the window starts at the tabled ghati and lasts 4 ghatis.
VERIFY both tables against DrikPanchang before treating as final.
"""
import swisseph as swe

from .constants import NAKSHATRAS, NAKSHATRA_SPAN
from .nakshatra import nakshatra_of
from .panchanga import tithi_of, yoga_of, karana_of
from .positions import jd_to_local, sidereal_positions, sign_name, sun_moon_sidereal

# ── angle functions ─────────────────────────────────────────────────────────

def _angles(jd: float) -> dict:
    sun, moon = sun_moon_sidereal(jd)
    return {
        "tithi": (moon - sun) % 360.0,
        "karana": (moon - sun) % 360.0,
        "nakshatra": moon,
        "yoga": (sun + moon) % 360.0,
        "rashi": moon,
    }

_STEPS = {"tithi": 12.0, "karana": 6.0, "nakshatra": NAKSHATRA_SPAN, "yoga": NAKSHATRA_SPAN,
          "rashi": 30.0}
_COUNTS = {"tithi": 30, "karana": 60, "nakshatra": 27, "yoga": 27, "rashi": 12}


def _index_at(jd: float, kind: str) -> int:
    a = _angles(jd)[kind]
    n = _COUNTS[kind]
    return min(int(a * n / 360.0), n - 1)


def _crossing(jd_lo: float, jd_hi: float, kind: str, target_index: int) -> float:
    """Bisect for the moment the element index first reaches target_index."""
    for _ in range(45):  # ~3 days / 2^45 → microsecond precision, cheap with Moshier
        mid = (jd_lo + jd_hi) / 2.0
        # handle wrap: compare cyclic index distance forward from current
        idx = _index_at(mid, kind)
        n = _COUNTS[kind]
        if (idx - target_index) % n < n // 2:
            jd_hi = mid
        else:
            jd_lo = mid
    return (jd_lo + jd_hi) / 2.0


def element_end(jd: float, kind: str) -> tuple[int, float]:
    """(current element index, UT jd when it ends). Search window 3 days."""
    idx = _index_at(jd, kind)
    n = _COUNTS[kind]
    return idx, _crossing(jd, jd + 3.0, kind, (idx + 1) % n)


def element_start(jd: float, kind: str) -> tuple[int, float]:
    """(current element index, UT jd when it began)."""
    idx = _index_at(jd, kind)
    lo, hi = jd - 3.0, jd
    # bisect for the moment idx was first reached (end of previous element)
    for _ in range(45):
        mid = (lo + hi) / 2.0
        if _index_at(mid, kind) == idx:
            hi = mid
        else:
            lo = mid
    return idx, (lo + hi) / 2.0


def elements_for_day(rise: float, next_rise: float, tz_str: str,
                     kinds: tuple = ("tithi", "nakshatra", "yoga", "karana")) -> dict:
    """
    Panchang-style element lists for a Vedic day (sunrise→next sunrise):
    the element prevailing at sunrise first, then successors that begin
    before next sunrise, each with its end time ("upto"). "rashi" (the
    Moon's sign) is not a panchang limb and is asked for on its own.
    """
    naming = {
        "tithi": lambda i, jd: tithi_of(*_sun_moon(jd))["display"],
        "nakshatra": lambda i, jd: NAKSHATRAS[i],
        "yoga": lambda i, jd: yoga_of(*_sun_moon(jd))["name"],
        "karana": lambda i, jd: karana_of(*_sun_moon(jd))["name"],
        "rashi": lambda i, jd: sign_name(i),
    }

    out = {}
    for kind in kinds:
        entries = []
        jd = rise
        for _ in range(6):  # karana can flip 3x per day; others 1-2x
            idx, end_jd = element_end(jd, kind)
            mid_jd = min(jd + 0.01, end_jd)  # sample inside the element for naming
            entries.append({
                "name": naming[kind](idx, mid_jd),
                "index": idx,
                "upto": jd_to_local(min(end_jd, next_rise), tz_str).strftime("%H:%M"),
                "upto_iso": jd_to_local(end_jd, tz_str).isoformat(),
                "spans_day_end": end_jd >= next_rise,
            })
            if end_jd >= next_rise:
                break
            jd = end_jd + 1e-5
        out[kind] = entries
    return out


def _sun_moon(jd: float) -> tuple[float, float]:
    pos = sidereal_positions(jd)
    return pos["Sun"]["lon"], pos["Moon"]["lon"]


# ── Varjya and Amrit Kalam ──────────────────────────────────────────────────
# Start ghati (of 60 spanning the nakshatra) per nakshatra, duration 4 ghatis.
#
# T0.4 (docs/backend_astro_depth_checklist_2026-08-06.md) cross-check,
# 2026-08-06: independent research surfaced a published Varjya start-ghati
# list covering 18 of the 27 nakshatras (Ashwini, Krittika, Mrigashira,
# Ardra, Punarvasu, Pushya, Ashlesha, Magha, Purva Phalguni, Uttara
# Phalguni, Hasta, Chitra, Swati, Vishakha, Jyeshtha, Uttara Ashadha,
# Shatabhisha, Revati) — every one of those 18 values matched this table
# EXACTLY (e.g. Ashwini 50, Ashlesha 32, Jyeshtha 14). Zero discrepancies
# found. The remaining 9 nakshatras (Bharani, Rohini, Anuradha, Moola,
# Purva Ashadha, Shravana, Dhanishta, Purva Bhadrapada, Uttara Bhadrapada)
# and the entire Amrit Kalam table remain UNCONFIRMED against an
# independent source — upgrading the whole table to "verified" on the
# strength of a partial match would overclaim, so it stays VERIFY.
#
# 2026-10-28 audit against DrikPanchang day pages (Hyderabad, Kolkata,
# Singapore and others): Varjya now also confirmed for Rohini, Anuradha,
# Moola, Purva Ashadha, Shravana, Dhanishta and Purva Bhadrapada, and Moola's
# second Varjya at ghati 56 added. Amrit Kalam had two wrong entries,
# Mrigashira 26 -> 38 and Ardra 45 -> 35 (Drik: Singapore 2026-10-30 03:33,
# Kolkata 2026-10-30 21:58); confirmed for Ashwini, Krittika, Rohini,
# Mrigashira, Ardra, Punarvasu, Pushya, Magha, the Phalgunis, Hasta,
# Anuradha, Jyeshtha, Moola, both Ashadhas, Shravana and Purva Bhadrapada.
# The rest stay VERIFY: Drik refused further fetches that day.
VARJYA_START_GHATI = [
    50, 24, 30, 40, 14, 21, 30, 20, 32, 30, 20, 18, 21, 20,
    14, 14, 10, 14, 20, 24, 20, 10, 10, 18, 16, 24, 30,
]
AMRIT_START_GHATI = [
    42, 48, 54, 52, 38, 35, 54, 44, 56, 54, 44, 42, 45, 44,
    38, 38, 34, 38, 44, 48, 44, 34, 34, 42, 40, 48, 54,
]
# Moola carries a second Varjya at its 56th ghati, running to the
# nakshatra's end; DrikPanchang lists both (Hyderabad 2026-11-13).
VARJYA_EXTRA_START_GHATI = {NAKSHATRAS.index("Moola"): [56]}
_GHATI_DURATION = 4.0


def _nakshatra_portion_windows(rise: float, next_rise: float, tz_str: str,
                               table: list, name: str, kind: str,
                               extra: dict | None = None) -> list:
    """Windows at tabled ghati-fractions of each nakshatra overlapping the day."""
    windows = []
    # nakshatra prevailing at sunrise, plus any that begin before next sunrise
    idx, start_jd = element_start(rise, "nakshatra")
    jd = rise
    for _ in range(3):
        idx_now, end_jd = element_end(jd, "nakshatra")
        if jd == rise:
            _, start_jd = element_start(rise, "nakshatra")
        else:
            start_jd = jd
        span = end_jd - start_jd
        for ghati in [table[idx_now], *(extra or {}).get(idx_now, [])]:
            w_start = start_jd + span * (ghati / 60.0)
            w_end = w_start + span * (_GHATI_DURATION / 60.0)
            if w_end > rise and w_start < next_rise:  # overlaps the Vedic day
                windows.append({
                    "name": f"{name} ({NAKSHATRAS[idx_now]})",
                    "kind": kind,
                    "start": jd_to_local(w_start, tz_str).strftime("%H:%M"),
                    "end": jd_to_local(w_end, tz_str).strftime("%H:%M"),
                    "start_iso": jd_to_local(w_start, tz_str).isoformat(),
                    "end_iso": jd_to_local(w_end, tz_str).isoformat(),
                    "verified": False,
                })
        if end_jd >= next_rise:
            break
        jd = end_jd + 1e-5
    return windows


def varjya_windows(rise: float, next_rise: float, tz_str: str) -> list:
    return _nakshatra_portion_windows(rise, next_rise, tz_str,
                                      VARJYA_START_GHATI, "Varjya", "inauspicious",
                                      VARJYA_EXTRA_START_GHATI)


def amrit_kalam_windows(rise: float, next_rise: float, tz_str: str) -> list:
    return _nakshatra_portion_windows(rise, next_rise, tz_str,
                                      AMRIT_START_GHATI, "Amrit Kalam", "auspicious")
