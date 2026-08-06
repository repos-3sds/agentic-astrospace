"""
Lunar month (masa) engine — amanta/purnimanta month, adhika-masa detection,
samvatsara (60-year cycle), ritu, ayana, moonrise/moonset and Gulika/Mandi.

Conventions (all convention_dependent unless noted):
- Month boundaries: amanta — the month runs new moon to new moon
  (amavasya end). New-moon instants are found by bisection on the
  Moon−Sun elongation (moves 10.5°–14.5°/day, monotonic except the
  360°→0° wrap), same pattern as moontimes.py.
- Month name: from the sankranti (solar sidereal sign entry) that falls
  inside the month. Equivalently: with r = Sun's sidereal sign index at
  the month's STARTING new moon, name = LUNAR_MONTHS[(r + 1) % 12]
  (new moon with Sun in Pisces(11) starts Chaitra(0)). This same formula
  names an adhika month after the following regular month.
- Adhika masa: no sankranti between the two bounding new moons. The rare
  kshaya masa (two sankrantis in one month) is not specially named.
- Samvatsara: Shalivahana Shaka elapsed-year formula —
  shaka = gregorian_year − 78 (−79 before Chaitra Shukla Pratipada),
  index = (shaka + 11) % 60. Conventions differ (North-Indian Jovian
  vs. Southern luni-solar); source_status is "convention_dependent".
- Gulika: daytime (sunrise→sunset) in 8 equal parts, part lords in
  weekday order starting from the day's vara lord; Gulika rises at the
  START of Saturn's part (some traditions — Mandi — use the middle).
  Night lords start from the 5th weekday-lord from the vara's.
"""
import swisseph as swe

from .constants import LUNAR_MONTHS
from .positions import (
    degree_in_sign, jd_to_local, sidereal_lagna, sidereal_positions,
    sign_index, sign_name, to_dms, tropical_sun,
)

# Standard 60-name samvatsara cycle (Prabhava … Akshaya).
SAMVATSARA_NAMES = [
    "Prabhava", "Vibhava", "Shukla", "Pramoda", "Prajapati", "Angirasa",
    "Shrimukha", "Bhava", "Yuva", "Dhatri", "Ishvara", "Bahudhanya",
    "Pramathi", "Vikrama", "Vrisha", "Chitrabhanu", "Svabhanu", "Tarana",
    "Parthiva", "Vyaya", "Sarvajit", "Sarvadhari", "Virodhi", "Vikriti",
    "Khara", "Nandana", "Vijaya", "Jaya", "Manmatha", "Durmukha",
    "Hemalamba", "Vilambi", "Vikari", "Sharvari", "Plava", "Shubhakrit",
    "Shobhakrit", "Krodhi", "Vishvavasu", "Parabhava", "Plavanga", "Kilaka",
    "Saumya", "Sadharana", "Virodhikrit", "Paridhavi", "Pramadi", "Ananda",
    "Rakshasa", "Nala", "Pingala", "Kalayukti", "Siddharthi", "Raudra",
    "Durmati", "Dundubhi", "Rudhirodgari", "Raktakshi", "Krodhana", "Akshaya",
]

# Six ritus, two lunar months each, in LUNAR_MONTHS order from Chaitra.
RITUS = ["Vasanta", "Grishma", "Varsha", "Sharad", "Hemanta", "Shishira"]

# Weekday lord order used for Gulika part lords: Sun..Saturn.
_WEEKDAY_LORD_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]


# ── New-moon finder ──────────────────────────────────────────────────────────

def _elongation(jd: float) -> float:
    """Moon − Sun sidereal elongation [0, 360) (ayanamsha cancels)."""
    pos = sidereal_positions(jd)
    return (pos["Moon"]["lon"] - pos["Sun"]["lon"]) % 360.0


def _signed_elongation(jd: float) -> float:
    """Elongation mapped to (−180, 180]; ascends through 0 at new moon."""
    return ((_elongation(jd) + 180.0) % 360.0) - 180.0


def _refine_new_moon(jd_lo: float, jd_hi: float) -> float:
    """Bisect for the elongation 360°→0° crossing inside [jd_lo, jd_hi]."""
    for _ in range(60):  # 1 day / 2^60 — microsecond precision, cheap Moshier
        mid = (jd_lo + jd_hi) / 2.0
        if _signed_elongation(mid) < 0.0:
            jd_lo = mid
        else:
            jd_hi = mid
    return (jd_lo + jd_hi) / 2.0


def new_moon_after(jd: float) -> float:
    """UT jd of the first new moon (elongation 0°) strictly after jd."""
    prev = _elongation(jd)
    t = jd
    for _ in range(32):  # lunation is ≤ 29.9 days
        t2 = t + 1.0
        cur = _elongation(t2)
        if cur < prev:  # wrapped past 360° inside (t, t2]
            return _refine_new_moon(t, t2)
        prev, t = cur, t2
    raise RuntimeError(f"No new moon found within 32 days after jd={jd}")


def new_moon_before(jd: float) -> float:
    """UT jd of the last new moon at or before jd."""
    prev = _elongation(jd)
    t = jd
    for _ in range(32):
        t2 = t - 1.0
        cur = _elongation(t2)
        if cur > prev:  # crossing inside (t2, t]
            return _refine_new_moon(t2, t)
        prev, t = cur, t2
    raise RuntimeError(f"No new moon found within 32 days before jd={jd}")


# ── Amanta month ─────────────────────────────────────────────────────────────

_EPS = 1e-4  # ~8.6 s inside the month, to sample the Sun clear of the bound


def _sun_sign_at(jd: float) -> int:
    return sign_index(sidereal_positions(jd)["Sun"]["lon"])


def amanta_masa(jd: float) -> dict:
    """
    The amanta lunar month containing jd (previous new moon → next new moon).

    Returns {name, name_index, adhika, paksha, month_start_jd, month_end_jd,
    purnimanta_name}. name_index is the index into LUNAR_MONTHS of the base
    name (without any "Adhika " prefix), usable for ritu().
    """
    start = new_moon_before(jd)
    end = new_moon_after(jd)

    r_start = _sun_sign_at(start + _EPS)
    r_end = _sun_sign_at(end - _EPS)
    adhika = r_start == r_end  # no sankranti between the bounding new moons

    name_index = (r_start + 1) % 12
    base_name = LUNAR_MONTHS[name_index]
    name = f"Adhika {base_name}" if adhika else base_name

    tithi_idx = min(int(_elongation(jd) // 12.0), 29)
    paksha = "Shukla" if tithi_idx < 15 else "Krishna"

    if paksha == "Shukla":
        purnimanta_name = name
    else:
        # Krishna paksha belongs to the NEXT amanta month under purnimanta
        # reckoning; use that month's base name (start-sign rule at `end`).
        purnimanta_name = LUNAR_MONTHS[(r_end + 1) % 12]

    return {
        "name": name,
        "name_index": name_index,
        "adhika": adhika,
        "paksha": paksha,
        "month_start_jd": start,
        "month_end_jd": end,
        "purnimanta_name": purnimanta_name,
    }


# ── Samvatsara / ritu / ayana ────────────────────────────────────────────────

def _chaitra_start_jd(year: int) -> float:
    """
    New moon that begins Chaitra of the given Gregorian year — the first
    new moon of the year with the Sun in sidereal Pisces. In an
    adhika-Chaitra year this is the adhika month's start (convention).
    """
    nm = new_moon_after(swe.julday(year, 2, 1, 0.0))
    for _ in range(4):
        if _sun_sign_at(nm + _EPS) == 11:  # Pisces
            return nm
        nm = new_moon_after(nm + 0.5)
    raise RuntimeError(f"Chaitra start not found for year {year}")


def samvatsara(jd: float) -> dict:
    """
    60-year samvatsara via the Shalivahana Shaka elapsed year:
    shaka = gregorian − 78, minus 1 before Chaitra Shukla Pratipada;
    index = (shaka + 11) % 60. Convention-dependent (Jovian vs luni-solar
    reckonings differ); do not treat as authoritative.
    """
    year = swe.revjul(jd)[0]
    shaka = year - 78 if jd >= _chaitra_start_jd(year) else year - 79
    idx = (shaka + 11) % 60
    return {
        "name": SAMVATSARA_NAMES[idx],
        "index": idx,
        "number": idx + 1,
        "shaka_year": shaka,
        "source_status": "convention_dependent",
    }


def ritu(month_index: int) -> str:
    """Ritu (season) for a LUNAR_MONTHS index: two months per ritu."""
    return RITUS[(month_index % 12) // 2]


def ayana(jd: float) -> str:
    """Uttarayana when the tropical Sun is in [270°,360°)∪[0°,90°)."""
    lon = tropical_sun(jd)
    return "Uttarayana" if (lon >= 270.0 or lon < 90.0) else "Dakshinayana"


# ── Moonrise / moonset ───────────────────────────────────────────────────────

def _moon_event(jd_ut_start: float, lat: float, lng: float, rsmi: int) -> float | None:
    try:
        res, tret = swe.rise_trans(
            jd_ut_start, swe.MOON, rsmi, (lng, lat, 0.0),
            0.0, 0.0, swe.FLG_MOSEPH,
        )
    except Exception:
        return None
    if res != 0:
        return None
    return tret[0]


def moon_events_for_day(rise: float, next_rise: float,
                        lat: float, lng: float) -> tuple[float | None, float | None]:
    """
    (moonrise_jd, moonset_jd): first moonrise and moonset after the day's
    sunrise. Either is None when it does not occur before the next sunrise
    (or at all — polar latitudes).
    """
    moonrise = _moon_event(rise, lat, lng, swe.CALC_RISE)
    moonset = _moon_event(rise, lat, lng, swe.CALC_SET)
    if moonrise is not None and moonrise >= next_rise:
        moonrise = None
    if moonset is not None and moonset >= next_rise:
        moonset = None
    return moonrise, moonset


# ── Gulika / Mandi ───────────────────────────────────────────────────────────

def _upagraha_block(start: float, end: float, first_lord_idx: int,
                    offset_fraction: float, lat: float, lng: float,
                    tz_str: str, ayanamsha: str) -> dict:
    """One day/night block of the 8-part Saturn-portion upagraha method.

    offset_fraction locates the instant WITHIN Saturn's 1/8 portion:
    0.0 = start of the portion (the Gulika convention this codebase
    defaults to), 0.5 = middle (the alternate "Mandi" convention — see
    T1.4, docs/backend_astro_depth_checklist_2026-08-06.md). Both read the
    same 8-part-day/lord-cycling structure; only this offset differs, per
    research confirming Gulika and Mandi disagree only on which point
    within Saturn's portion is taken, not on the underlying method.
    """
    part = (end - start) / 8.0
    saturn_part = (6 - first_lord_idx) % 7  # 0-based part ruled by Saturn
    instant = start + (saturn_part + offset_fraction) * part
    lon = sidereal_lagna(instant, lat, lng, ayanamsha)
    return {
        "start_jd": instant,
        "start_time": jd_to_local(instant, tz_str).strftime("%H:%M"),
        "longitude": lon,
        "sign": sign_name(sign_index(lon)),
        "dms": to_dms(degree_in_sign(lon)),
    }


def gulika_positions(rise: float, sets: float, next_rise: float,
                     vara_idx: int, lat: float, lng: float, tz_str: str,
                     ayanamsha: str = "lahiri") -> dict:
    """
    Day and night Gulika. Day: sunrise→sunset in 8 equal parts, part lords
    in weekday order (Sun..Saturn cycling) starting from the day's vara
    lord, 8th part lordless; Gulika rises at the START of Saturn's part.
    Night: sunset→next sunrise in 8 parts, lords starting from the 5th
    weekday-lord from the vara's ((vara_idx + 4) % 7). Gulika longitude is
    the sidereal ascendant at that instant. Note: Mandi conventions differ
    — some traditions take the MIDDLE of Saturn's portion; see
    mandi_positions() for that variant, computed side by side rather than
    silently substituted.
    """
    return {
        "day": _upagraha_block(rise, sets, vara_idx % 7, 0.0, lat, lng, tz_str, ayanamsha),
        "night": _upagraha_block(sets, next_rise, (vara_idx + 4) % 7, 0.0, lat, lng, tz_str, ayanamsha),
        "note": ("Gulika at the START of Saturn's part; some traditions "
                 "(Mandi) use the middle of the portion — convention-dependent."),
    }


def mandi_positions(rise: float, sets: float, next_rise: float,
                    vara_idx: int, lat: float, lng: float, tz_str: str,
                    ayanamsha: str = "lahiri") -> dict:
    """
    Mandi — the alternate reading of the same 8-part Saturn-portion
    upagraha method as gulika_positions(), taken at the MIDDLE of Saturn's
    portion instead of the start (see T1.4,
    docs/backend_astro_depth_checklist_2026-08-06.md). Shipped as a
    separate function rather than a silent flag flip on gulika_positions()
    so a caller that wants both conventions can show them side by side
    instead of one point quietly overwriting the other.
    """
    return {
        "day": _upagraha_block(rise, sets, vara_idx % 7, 0.5, lat, lng, tz_str, ayanamsha),
        "night": _upagraha_block(sets, next_rise, (vara_idx + 4) % 7, 0.5, lat, lng, tz_str, ayanamsha),
        "note": ("Mandi at the MIDDLE of Saturn's part — the same 8-part-day "
                 "method as Gulika, differing only in this offset; "
                 "convention-dependent, see gulika_positions()."),
    }
