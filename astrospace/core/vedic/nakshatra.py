"""Nakshatra and pada from sidereal longitude. 27 nakshatras x 4 padas."""
from .constants import (
    GANA_BY_NAKSHATRA, NADI_BY_NAKSHATRA, NAKSHATRAS, NAKSHATRA_DEITY,
    NAKSHATRA_LORDS, NAKSHATRA_SPAN, NAKSHATRA_SYMBOL, PADA_SPAN,
    YONI_BY_NAKSHATRA,
)


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


def nakshatra_traits(index: int) -> dict:
    """The classical attribute set for a nakshatra, by 0-based index.

    Bare traditional facts only — deity, symbol, lord, and the three
    Ashtakoota temperament axes. Deliberately carries no interpretive prose:
    see NAKSHATRA_DEITY's comment in constants.py for why. Consumers are
    expected to interpret from these, not to be handed a conclusion.
    """
    return {
        "name": NAKSHATRAS[index],
        "lord": NAKSHATRA_LORDS[index],
        "deity": NAKSHATRA_DEITY[index],
        "symbol": NAKSHATRA_SYMBOL[index],
        "gana": GANA_BY_NAKSHATRA[index],
        "yoni": "{} ({})".format(*YONI_BY_NAKSHATRA[index]),
        "nadi": NADI_BY_NAKSHATRA[index],
    }
