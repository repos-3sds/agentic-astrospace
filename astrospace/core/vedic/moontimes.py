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
from .positions import jd_to_local, sidereal_positions

# ── angle functions ─────────────────────────────────────────────────────────

def _angles(jd: float) -> dict:
    pos = sidereal_positions(jd)
    sun, moon = pos["Sun"]["lon"], pos["Moon"]["lon"]
    return {
        "tithi": (moon - sun) % 360.0,
        "karana": (moon - sun) % 360.0,
        "nakshatra": moon,
        "yoga": (sun + moon) % 360.0,
    }

_STEPS = {"tithi": 12.0, "karana": 6.0, "nakshatra": NAKSHATRA_SPAN, "yoga": NAKSHATRA_SPAN}
_COUNTS = {"tithi": 30, "karana": 60, "nakshatra": 27, "yoga": 27}


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


def elements_for_day(rise: float, next_rise: float, tz_str: str) -> dict:
    """
    Panchang-style element lists for a Vedic day (sunrise→next sunrise):
    the element prevailing at sunrise first, then successors that begin
    before next sunrise, each with its end time ("upto").
    """
    pos = sidereal_positions(rise)
    sun, moon = pos["Sun"]["lon"], pos["Moon"]["lon"]
    naming = {
        "tithi": lambda i, jd: tithi_of(*_sun_moon(jd))["display"],
        "nakshatra": lambda i, jd: NAKSHATRAS[i],
        "yoga": lambda i, jd: yoga_of(*_sun_moon(jd))["name"],
        "karana": lambda i, jd: karana_of(*_sun_moon(jd))["name"],
    }

    out = {}
    for kind in ("tithi", "nakshatra", "yoga", "karana"):
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
VARJYA_START_GHATI = [
    50, 24, 30, 40, 14, 21, 30, 20, 32, 30, 20, 18, 21, 20,
    14, 14, 10, 14, 20, 24, 20, 10, 10, 18, 16, 24, 30,
]
AMRIT_START_GHATI = [
    42, 48, 54, 52, 26, 45, 54, 44, 56, 54, 44, 42, 45, 44,
    38, 38, 34, 38, 44, 48, 44, 34, 34, 42, 40, 48, 54,
]
_GHATI_DURATION = 4.0


def _nakshatra_portion_windows(rise: float, next_rise: float, tz_str: str,
                               table: list, name: str, kind: str) -> list:
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
        w_start = start_jd + span * (table[idx_now] / 60.0)
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
                                      VARJYA_START_GHATI, "Varjya", "inauspicious")


def amrit_kalam_windows(rise: float, next_rise: float, tz_str: str) -> list:
    return _nakshatra_portion_windows(rise, next_rise, tz_str,
                                      AMRIT_START_GHATI, "Amrit Kalam", "auspicious")
