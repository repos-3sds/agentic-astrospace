"""Nakshatra and pada from sidereal longitude. 27 nakshatras x 4 padas."""
from .constants import NAKSHATRAS, NAKSHATRA_LORDS, NAKSHATRA_SPAN, PADA_SPAN


def nakshatra_of(lon: float) -> dict:
    """
    Nakshatra details for a sidereal longitude.

    Returns {"index": 0-26, "number": 1-27, "name", "lord", "pada": 1-4,
             "degree_in_nakshatra": float}.
    """
    lon = lon % 360.0
    # multiply before dividing: 360/27 is not exactly representable and
    # exact boundary longitudes (e.g. 240.0 = Moola 0°) would bucket low
    idx = min(int(lon * 27.0 / 360.0), 26)
    pada_global = min(int(lon * 108.0 / 360.0), 107)
    pada = pada_global % 4 + 1
    return {
        "index": idx,
        "number": idx + 1,
        "name": NAKSHATRAS[idx],
        "lord": NAKSHATRA_LORDS[idx],
        "pada": pada,
        "degree_in_nakshatra": lon - idx * NAKSHATRA_SPAN,
    }
