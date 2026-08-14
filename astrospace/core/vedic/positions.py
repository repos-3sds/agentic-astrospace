"""
Sidereal position engine on Swiss Ephemeris (pyswisseph).

All longitudes returned are sidereal degrees [0, 360) unless suffixed
_tropical. Uses the Moshier analytical ephemeris (FLG_MOSEPH) so no
ephemeris data files are required — accuracy is well under 1 arcsecond
for our purposes.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

from .constants import SIGNS, SIGNS_SANSKRIT, SIGN_LORDS
from ..cities import lookup_city

AYANAMSHA_MODES = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
}

_SWE_BODIES = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
    "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS, "Saturn": swe.SATURN,
}

_BASE_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


class LocationError(ValueError):
    """Birth place could not be resolved to coordinates + timezone."""


@dataclass
class BirthMoment:
    """Resolved birth instant and place."""
    jd_ut: float
    dt_local: datetime
    dt_utc: datetime
    lat: float
    lng: float
    tz_str: str


def resolve_location(city: str = None, nation: str = "IN",
                     lat: float = None, lng: float = None,
                     tz_str: str = None) -> tuple[float, float, str]:
    if lat is not None and lng is not None and tz_str:
        return lat, lng, tz_str
    if city:
        geo = lookup_city(city, nation or "IN")
        if geo:
            return geo
    raise LocationError(
        f"Cannot resolve location for city={city!r}, nation={nation!r}. "
        "Provide explicit lat, lng and tz_str, or add the city to astrospace/core/cities.py."
    )


def birth_moment(year: int, month: int, day: int, hour: int, minute: int,
                 city: str = None, nation: str = "IN",
                 lat: float = None, lng: float = None,
                 tz_str: float = None, second: int = 0) -> BirthMoment:
    lat, lng, tz_str = resolve_location(city, nation, lat, lng, tz_str)
    dt_local = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo(tz_str))
    dt_utc = dt_local.astimezone(timezone.utc)
    jd_ut = swe.julday(
        dt_utc.year, dt_utc.month, dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )
    return BirthMoment(jd_ut=jd_ut, dt_local=dt_local, dt_utc=dt_utc,
                       lat=lat, lng=lng, tz_str=tz_str)


def _set_ayanamsha(ayanamsha: str) -> None:
    try:
        mode = AYANAMSHA_MODES[ayanamsha.lower()]
    except KeyError:
        raise ValueError(f"Unknown ayanamsha {ayanamsha!r}; options: {sorted(AYANAMSHA_MODES)}")
    swe.set_sid_mode(mode, 0, 0)


def ayanamsha_value(jd_ut: float, ayanamsha: str = "lahiri") -> float:
    _set_ayanamsha(ayanamsha)
    return swe.get_ayanamsa_ut(jd_ut)


def sidereal_positions(jd_ut: float, ayanamsha: str = "lahiri",
                       node_type: str = "mean") -> dict:
    """
    Sidereal longitudes for the 9 grahas.

    Returns {planet: {"lon": float, "speed": float, "retrograde": bool}}.
    Ketu is always Rahu + 180°. node_type: "mean" (traditional panchanga
    default) or "true".
    """
    _set_ayanamsha(ayanamsha)
    flags = _BASE_FLAGS | swe.FLG_SIDEREAL
    out = {}
    for name, body in _SWE_BODIES.items():
        (lon, _lat, _dist, spd, *_), _ = swe.calc_ut(jd_ut, body, flags)
        out[name] = {"lon": lon % 360.0, "speed": spd, "retrograde": spd < 0}

    node_body = swe.MEAN_NODE if node_type == "mean" else swe.TRUE_NODE
    (rahu_lon, _lat, _dist, rahu_spd, *_), _ = swe.calc_ut(jd_ut, node_body, flags)
    out["Rahu"] = {"lon": rahu_lon % 360.0, "speed": rahu_spd, "retrograde": True}
    out["Ketu"] = {"lon": (rahu_lon + 180.0) % 360.0, "speed": rahu_spd, "retrograde": True}
    return out


def tropical_sun(jd_ut: float) -> float:
    (lon, *_), _ = swe.calc_ut(jd_ut, swe.SUN, _BASE_FLAGS)
    return lon % 360.0


def sidereal_lagna(jd_ut: float, lat: float, lng: float,
                   ayanamsha: str = "lahiri") -> float:
    """Sidereal ascendant longitude. Houses are whole-sign from its sign."""
    _set_ayanamsha(ayanamsha)
    _cusps, ascmc = swe.houses_ex(jd_ut, lat, lng, b"W", swe.FLG_SIDEREAL)
    return ascmc[0] % 360.0


def sidereal_mc(jd_ut: float, lat: float, lng: float,
                ayanamsha: str = "lahiri") -> float:
    """Sidereal Midheaven (MC) longitude — the 10th-house bhava madhya
    anchor for the Sripati (Bhava Chalit) house system; see bhava_chalit.py.
    Whole-sign houses (the default everywhere else in this codebase) don't
    use MC at all — this exists only to feed that opt-in alternate system.
    """
    _set_ayanamsha(ayanamsha)
    _cusps, ascmc = swe.houses_ex(jd_ut, lat, lng, b"W", swe.FLG_SIDEREAL)
    return ascmc[1] % 360.0


def _sun_event(jd_ut_start: float, lat: float, lng: float, rsmi: int) -> float | None:
    try:
        res, tret = swe.rise_trans(
            jd_ut_start, swe.SUN, rsmi, (lng, lat, 0.0),
            0.0, 0.0, swe.FLG_MOSEPH,
        )
    except Exception:
        return None
    if res != 0:
        return None
    return tret[0]


def sunrise_jd(jd_ut_start: float, lat: float, lng: float) -> float | None:
    """Next sunrise (UT julian day) at or after jd_ut_start; None if circumpolar."""
    return _sun_event(jd_ut_start, lat, lng, swe.CALC_RISE)


def sunset_jd(jd_ut_start: float, lat: float, lng: float) -> float | None:
    """Next sunset (UT julian day) at or after jd_ut_start; None if circumpolar."""
    return _sun_event(jd_ut_start, lat, lng, swe.CALC_SET)


def day_span(year: int, month: int, day: int, lat: float, lng: float,
             tz_str: str) -> tuple[float, float, float] | None:
    """
    (sunrise, sunset, next_sunrise) UT julian days for a local calendar date.
    The Vedic day runs sunrise to next sunrise. None if circumpolar.
    """
    midnight_local = datetime(year, month, day, 0, 0, tzinfo=ZoneInfo(tz_str))
    midnight_utc = midnight_local.astimezone(timezone.utc)
    jd_start = swe.julday(
        midnight_utc.year, midnight_utc.month, midnight_utc.day,
        midnight_utc.hour + midnight_utc.minute / 60.0,
    )
    rise = sunrise_jd(jd_start, lat, lng)
    if rise is None:
        return None
    sets = sunset_jd(rise, lat, lng)
    next_rise = sunrise_jd(rise + 0.5, lat, lng)
    if sets is None or next_rise is None:
        return None
    return rise, sets, next_rise


def vedic_day_bounds(jd_ut: float, lat: float, lng: float) -> tuple[float, float] | None:
    """(sunrise, next_sunrise) UT julian days bounding the Vedic day that
    contains jd_ut: the last sunrise at or before jd_ut, through the
    following sunrise. None if circumpolar. Mirrors VedicChart's own
    birth-instant version (chart.py) but for an arbitrary moment, so a
    pre-sunrise request resolves to the still-current previous Vedic day
    rather than the civil calendar date."""
    rise = sunrise_jd(jd_ut - 1.5, lat, lng)
    if rise is None or rise > jd_ut:
        return None
    while True:
        nxt = sunrise_jd(rise + 0.01, lat, lng)
        if nxt is None:
            return None
        if nxt > jd_ut:
            return rise, nxt
        rise = nxt


def local_sunrise(moment: BirthMoment) -> datetime | None:
    """Sunrise (local tz) on the birth's local calendar date."""
    midnight_local = moment.dt_local.replace(hour=0, minute=0, second=0, microsecond=0)
    midnight_utc = midnight_local.astimezone(timezone.utc)
    jd_start = swe.julday(
        midnight_utc.year, midnight_utc.month, midnight_utc.day,
        midnight_utc.hour + midnight_utc.minute / 60.0,
    )
    jd_rise = sunrise_jd(jd_start, moment.lat, moment.lng)
    if jd_rise is None:
        return None
    return jd_to_local(jd_rise, moment.tz_str)


def jd_to_local(jd_ut: float, tz_str: str) -> datetime:
    y, m, d, h = swe.revjul(jd_ut)
    hh = int(h)
    mm = int((h - hh) * 60)
    ss = int(round((((h - hh) * 60) - mm) * 60))
    if ss == 60:
        ss, mm = 0, mm + 1
    if mm == 60:
        mm, hh = 0, hh + 1
    dt_utc = datetime(y, m, d, min(hh, 23), mm, ss, tzinfo=timezone.utc)
    return dt_utc.astimezone(ZoneInfo(tz_str))


def local_mean_time(moment: BirthMoment) -> datetime:
    """LMT = UT + longitude/15 hours (east positive)."""
    return moment.dt_utc + timedelta(hours=moment.lng / 15.0)


def local_sidereal_time(jd_ut: float, lng: float) -> float:
    """Local sidereal time in hours [0, 24)."""
    gst = swe.sidtime(jd_ut)
    return (gst + lng / 15.0) % 24.0


def obliquity(jd_ut: float) -> float:
    (eps, *_), _ = swe.calc_ut(jd_ut, swe.ECL_NUT, _BASE_FLAGS)
    return eps


# ── Formatting / sign helpers ────────────────────────────────────────────────

def sign_index(lon: float) -> int:
    return int(lon % 360.0 // 30)


def degree_in_sign(lon: float) -> float:
    return lon % 30.0


def sign_name(idx: int) -> str:
    return SIGNS[idx % 12]


def sign_name_sanskrit(idx: int) -> str:
    return SIGNS_SANSKRIT[idx % 12]


def sign_lord(idx: int) -> str:
    return SIGN_LORDS[idx % 12]


def to_dms(deg: float) -> str:
    d = int(deg)
    m_f = (deg - d) * 60
    m = int(m_f)
    s = int(round((m_f - m) * 60))
    if s == 60:
        s, m = 0, m + 1
    if m == 60:
        m, d = 0, d + 1
    return f"{d}°{m:02d}'{s:02d}\""


def house_from_lagna(planet_sign: int, lagna_sign: int) -> int:
    """Whole-sign house (1..12) of a sign counted from the lagna sign."""
    return (planet_sign - lagna_sign) % 12 + 1
