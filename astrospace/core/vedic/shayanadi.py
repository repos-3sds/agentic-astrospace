"""Shayanadi Avastha — a twelve-state planetary condition, distinct from the
Baladi avastha (strength.avastha_of) and Cheshta avastha
(strength.cheshta_avastha) already implemented in this codebase.

Formula, variable definitions and the 12-name ordering were cross-checked
2026-08-10 against three independent secondary sources (astrojyoti.com,
ganeshmitra.com via search snippet, jothishi.com) which all agree exactly on
the arithmetic and the name sequence. No primary BPHS verse was located in
this pass, so — same convention as Indu Lagna in special_lagnas.py — this
stays flagged source_status: convention_dependent rather than presented as
verbatim-primary-text.

This deliberately does NOT trust the worked examples/derivations that
appeared in a user-uploaded document earlier in this project's validation
pass: those examples' own shown arithmetic contradicted their stated
formula. The formula and ordering below come only from the three
independently-fetched web sources above, re-derived and hand-verified
against the worked example one of those sources gave:
  Sun in Hasta (nakshatra_serial=13), planet_serial=1, navamsha_number=6,
  Moon nakshatra_serial=25, ghatika=20, lagna_rashi_number=10
  -> (13*1*6) + 25 + 20 + 10 = 133 -> 133 % 12 = 1 -> Shayana. Matches.

    index = (nakshatra_serial * planet_serial * navamsha_number
             + moon_nakshatra_serial + ghatika + lagna_rashi_number) % 12
    (a zero remainder is treated as 12, the same convention used for Indu
    Lagna's sign count)

Where:
  nakshatra_serial      = 1..27, the planet's own nakshatra (nakshatra_of()'s
                           "number" field)
  planet_serial         = Sun=1 .. Saturn=7, Rahu=8, Ketu=9 — matches this
                           codebase's PLANETS order in constants.py exactly,
                           so no remapping is needed
  navamsha_number       = 1..9, which of the 9 navamsha divisions *within
                           the planet's own sign* it occupies (not the D9
                           sign index, which vargas.d9() already returns)
  moon_nakshatra_serial = 1..27, the Moon's (Janma) nakshatra
  ghatika                = whole ghatis elapsed since sunrise (1 ghati = 24
                           minutes), floored to an integer serial — reuses
                           the same ghatis_since_sunrise already computed
                           for Bhava/Hora/Ghati Lagna in special_lagnas.py
  lagna_rashi_number    = 1..12, Aries=1

Sources disagree on which of the 12 states are auspicious vs inauspicious
in effect, so this module reports the name/index only and leaves
interpretation to the domain agent — consistent with this project's
"raw KB, guardrails at the agent layer" convention.
"""
from .constants import PLANETS
from .nakshatra import nakshatra_of
from .positions import degree_in_sign

AVASTHA_NAMES = [
    "Shayana", "Upavesana", "Netrapani", "Prakashana", "Gamana", "Agamana",
    "Sabha", "Agama", "Bhojana", "Nrityalipsa", "Kautuka", "Nidra",
]

_PLANET_SERIAL = {planet: i + 1 for i, planet in enumerate(PLANETS)}


def _navamsha_number(lon: float) -> int:
    """1..9 — which navamsha division within the planet's own sign it falls in."""
    deg = degree_in_sign(lon)
    return min(int(deg * 9.0 / 30.0), 8) + 1


def shayanadi_avastha(planet: str, lon: float, moon_lon: float,
                       lagna_sign: int, ghatis_since_sunrise: float) -> dict:
    """Shayanadi avastha of one planet at the moment of birth.

    lon: the planet's own sidereal longitude. moon_lon: the Moon's sidereal
    longitude (for Janma Nakshatra). lagna_sign: 0-based rising sign index.
    ghatis_since_sunrise: from special_lagnas() (Bhava/Hora/Ghati Lagna
    already compute this for the same birth instant).
    """
    nak = nakshatra_of(lon)
    moon_nak = nakshatra_of(moon_lon)
    ghatika = int(ghatis_since_sunrise // 1.0)
    lagna_rashi_number = lagna_sign + 1

    raw = (nak["number"] * _PLANET_SERIAL[planet] * _navamsha_number(lon)
           + moon_nak["number"] + ghatika + lagna_rashi_number)
    remainder = raw % 12
    if remainder == 0:
        remainder = 12

    return {
        "name": AVASTHA_NAMES[remainder - 1],
        "index": remainder,
        "inputs": {
            "nakshatra_serial": nak["number"],
            "planet_serial": _PLANET_SERIAL[planet],
            "navamsha_number": _navamsha_number(lon),
            "moon_nakshatra_serial": moon_nak["number"],
            "ghatika": ghatika,
            "lagna_rashi_number": lagna_rashi_number,
        },
        "status": "implemented",
        "source_status": "convention_dependent",
        "rule": (
            "(nakshatra_serial x planet_serial x navamsha_number + "
            "moon_nakshatra_serial + ghatika + lagna_rashi_number) mod 12, "
            "a zero remainder treated as 12; cross-checked against three "
            "independent secondary sources, no primary BPHS verse located."
        ),
    }


def all_shayanadi_avasthas(positions: dict, lagna_sign: int,
                            ghatis_since_sunrise: float) -> dict:
    """Shayanadi avastha for every planet in `positions` (Rahu/Ketu included)."""
    moon_lon = positions["Moon"]["lon"]
    return {
        planet: shayanadi_avastha(planet, data["lon"], moon_lon, lagna_sign,
                                   ghatis_since_sunrise)
        for planet, data in positions.items()
    }
