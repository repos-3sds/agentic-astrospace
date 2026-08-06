"""Bhava Chalit — the Sripati cuspal house system, as an opt-in alternate
lens next to this codebase's default whole-sign houses.

T3.3, docs/backend_astro_depth_checklist_2026-08-06.md. **Whole-sign
houses stay the default everywhere** (``chart.py``'s
``"house_system": "whole-sign houses from sidereal lagna"``,
``positions.house_from_lagna()``, and every yoga/dosha/strength/dasha
calculation that uses it, are all unchanged by this module). This is
additive: a Practitioner can ask for the Sripati reading of the same
chart as a second, clearly-labeled lens, not a silent replacement.

The Sripati system (attributed to the 11th-century astronomer Śrīpati,
incorporated into later BPHS editions) computes house *midpoints* (bhava
madhya) first, then derives house *boundaries* (bhava sandhi) as the
midpoint between adjacent madhyas — the reverse of Placidus-style systems,
which compute boundaries directly and treat the arithmetic mid of a house
as secondary. Method (cross-checked via research 2026-08-06):

1. The 1st bhava madhya is the Lagna (Ascendant) longitude; the 10th is
   the sidereal Midheaven (MC). The 4th (IC) and 7th (Descendant) are
   their exact opposites (+180°).
2. Each of the four quadrants between consecutive angles (10→1, 1→4, 4→7,
   7→10, all read forward in zodiacal order) is trisected to give the two
   intermediate madhyas in that quadrant (11/12, 2/3, 5/6, 8/9).
3. Each house's boundary (sandhi) is the midpoint between its own madhya
   and the previous house's madhya.

Houses are NOT 30° wide in this system except on the (rare) day the
Ascendant-to-MC arcs happen to divide evenly — that unequal-width property
is the whole point of using it (see module docstring in
``strength.dignity_of`` for how whole-sign treats every house as exactly
one sign; Sripati explicitly does not).
"""
from __future__ import annotations

HOUSES = list(range(1, 13))


def _trisect(start: float, end: float) -> tuple[float, float]:
    """The two points trisecting the forward (zodiacal-direction) arc from
    start to end, closer-to-start first."""
    arc = (end - start) % 360.0
    step = arc / 3.0
    return (start + step) % 360.0, (start + 2 * step) % 360.0


def sripati_madhyas(lagna_lon: float, mc_lon: float) -> dict[int, float]:
    """The 12 bhava madhyas (house midpoints) for a Sripati chart."""
    lagna_lon %= 360.0
    mc_lon %= 360.0
    ic = (mc_lon + 180.0) % 360.0
    desc = (lagna_lon + 180.0) % 360.0

    m11, m12 = _trisect(mc_lon, lagna_lon)
    m2, m3 = _trisect(lagna_lon, ic)
    m5, m6 = _trisect(ic, desc)
    m8, m9 = _trisect(desc, mc_lon)

    return {
        1: lagna_lon, 2: m2, 3: m3, 4: ic, 5: m5, 6: m6,
        7: desc, 8: m8, 9: m9, 10: mc_lon, 11: m11, 12: m12,
    }


def sripati_cusps(lagna_lon: float, mc_lon: float) -> dict:
    """Bhava madhyas and the sandhi (boundary) longitude each house starts at.

    Returns ``{"madhyas": {1..12: lon}, "cusps": {1..12: lon},
    "widths": {1..12: degrees}}``. ``cusps[h]`` is where house h STARTS
    (the midpoint between madhya[h-1] and madhya[h]); a planet at longitude
    L is in house h when ``cusps[h] <= L < cusps[h+1]`` going forward
    (wrapping at house 12 → 1).
    """
    madhyas = sripati_madhyas(lagna_lon, mc_lon)
    cusps = {}
    for h in HOUSES:
        prev_h = 12 if h == 1 else h - 1
        arc = (madhyas[h] - madhyas[prev_h]) % 360.0
        cusps[h] = (madhyas[prev_h] + arc / 2.0) % 360.0
    widths = {}
    for h in HOUSES:
        next_h = 1 if h == 12 else h + 1
        widths[h] = (cusps[next_h] - cusps[h]) % 360.0
    return {"madhyas": madhyas, "cusps": cusps, "widths": widths}


def house_of(lon: float, cusps: dict[int, float]) -> int:
    """Which Sripati house (1-12) a longitude falls in, given ``cusps``
    from :func:`sripati_cusps`."""
    lon %= 360.0
    for h in HOUSES:
        next_h = 1 if h == 12 else h + 1
        arc = (cusps[next_h] - cusps[h]) % 360.0
        offset = (lon - cusps[h]) % 360.0
        if offset < arc:
            return h
    return 12  # unreachable given the 12 arcs partition the full circle


def bhava_chalit(lagna_lon: float, mc_lon: float, positions: dict) -> dict:
    """Full Sripati reading of a chart: madhyas, cusps, and each planet's
    Sripati house (alongside its longitude, for comparison against the
    whole-sign house the rest of the chart uses).
    """
    layout = sripati_cusps(lagna_lon, mc_lon)
    planets = {
        planet: {
            "longitude": data["lon"] % 360.0,
            "house": house_of(data["lon"], layout["cusps"]),
        }
        for planet, data in positions.items()
    }
    return {
        "system": "Sripati (Bhava Chalit)",
        "madhyas": layout["madhyas"],
        "cusps": layout["cusps"],
        "widths": layout["widths"],
        "planets": planets,
        "source_status": "convention_dependent",
        "notes": [
            "Opt-in alternate house lens — every other calculation in this "
            "codebase (yogas, doshas, strength, dashas) uses whole-sign "
            "houses and is unaffected by this reading.",
            "House widths are unequal by design (Sripati computes cuspal "
            "midpoints and boundaries, not equal 30-degree signs); a width "
            "far from 30 degrees is expected, not a bug.",
            "MC computed via Swiss Ephemeris's sidereal ascmc[1] (same "
            "ayanamsha path as the sidereal Lagna), not hand-derived.",
        ],
    }
