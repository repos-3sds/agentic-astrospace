"""South-Indian style Gocharam rule definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GocharaRuleDefinition:
    id: str
    name: str
    planet: str
    anchor: str
    active_houses: frozenset[int]
    severity: str
    tone: str
    source_status: str


RULE_DEFINITIONS = [
    GocharaRuleDefinition(
        id="gochara_sade_sati",
        name="Sade Sati",
        planet="Saturn",
        anchor="moon",
        active_houses=frozenset({12, 1, 2}),
        severity="high",
        tone="challenging",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_ashtama_shani",
        name="Ashtama Shani",
        planet="Saturn",
        anchor="moon",
        active_houses=frozenset({8}),
        severity="high",
        tone="challenging",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_kantaka_shani",
        name="Ardhashtama Shani (Kantaka Shani)",
        planet="Saturn",
        anchor="moon",
        active_houses=frozenset({4}),
        severity="medium",
        tone="challenging",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_guru_moon_support",
        name="Guru Bala from Moon",
        planet="Jupiter",
        anchor="moon",
        active_houses=frozenset({2, 5, 7, 9, 11}),
        severity="supportive",
        tone="supportive",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_guru_lagna_support",
        name="Guru Bala from Lagna",
        planet="Jupiter",
        anchor="lagna",
        active_houses=frozenset({2, 5, 7, 9, 11}),
        severity="supportive",
        tone="supportive",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_rahu_moon_caution",
        name="Rahu caution from Moon",
        planet="Rahu",
        anchor="moon",
        active_houses=frozenset({1, 5, 7, 8, 9, 12}),
        severity="medium",
        tone="challenging",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_ketu_moon_caution",
        name="Ketu caution from Moon",
        planet="Ketu",
        anchor="moon",
        active_houses=frozenset({1, 5, 7, 8, 9, 12}),
        severity="medium",
        tone="challenging",
        source_status="south_indian_common_practice",
    ),
    GocharaRuleDefinition(
        id="gochara_mars_moon_trigger",
        name="Mars trigger from Moon",
        planet="Mars",
        anchor="moon",
        active_houses=frozenset({1, 4, 7, 8, 12}),
        severity="medium",
        tone="challenging",
        source_status="south_indian_common_practice",
    ),
]


RULE_BY_ID = {rule.id: rule for rule in RULE_DEFINITIONS}


# ── Classical Moon-sign gochara with Vedha ───────────────────────────────────
#
# Standard favourable-house / vedha-sthana table as given in Phaladeepika
# (ch. 26) and followed in common South-Indian practice. Mapping is
# {favourable_house_from_natal_Moon: vedha_house}. A transit planet standing
# in a favourable house loses the promised good result when ANOTHER planet
# simultaneously transits the corresponding vedha house.
CLASSICAL_GOCHARA_VEDHA: dict[str, dict[int, int]] = {
    "Sun": {3: 9, 6: 12, 10: 4, 11: 5},
    "Moon": {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
    "Mars": {3: 12, 6: 9, 11: 5},
    "Mercury": {2: 5, 4: 3, 6: 9, 8: 1, 10: 8, 11: 12},
    "Jupiter": {2: 12, 5: 4, 7: 3, 9: 10, 11: 8},
    "Venus": {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 6, 12: 3},
    "Saturn": {3: 12, 6: 9, 11: 5},
    # The nodes are not covered by the classical table; the common convention
    # is to read them like Saturn (3, 6, 11 favourable with the same vedhas).
    "Rahu": {3: 12, 6: 9, 11: 5},
    "Ketu": {3: 12, 6: 9, 11: 5},
}

# Classical exceptions: no vedha operates between Sun and Saturn
# (father-son), nor between Moon and Mercury.
VEDHA_EXEMPT_PAIRS = {
    frozenset({"Sun", "Saturn"}),
    frozenset({"Moon", "Mercury"}),
}

_CLASSICAL_SOURCE_STATUS = {
    "Rahu": "convention_dependent",
    "Ketu": "convention_dependent",
}


# ── Special (graha) drishti: aspect houses from a transit position ──────────
#
# Every planet aspects the 7th house from itself. Mars, Jupiter and Saturn
# additionally carry classical "special" aspects (BPHS ch.3): Mars on the 4th
# and 8th, Jupiter on the 5th and 9th, Saturn on the 3rd and 10th. Expressed
# as offsets added to the occupied house (1-12, wrapping mod 12).
SPECIAL_ASPECT_OFFSETS: dict[str, tuple[int, ...]] = {
    "Mars": (3, 6, 7),
    "Jupiter": (4, 6, 8),
    "Saturn": (2, 6, 9),
}
DEFAULT_ASPECT_OFFSETS: tuple[int, ...] = (6,)


def special_aspect_houses(planet: str, house: int) -> list[int]:
    """Houses (1-12) aspected by ``planet`` occupying ``house`` (1-12)."""
    offsets = SPECIAL_ASPECT_OFFSETS.get(planet, DEFAULT_ASPECT_OFFSETS)
    return sorted({((house - 1 + offset) % 12) + 1 for offset in offsets})


def classical_gochara_status(houses_from_moon: dict[str, int]) -> dict[str, dict]:
    """Classical Moon-sign gochara verdict with vedha for each transit planet.

    ``houses_from_moon`` maps planet name -> house (1-12) counted from the
    natal Moon sign. Returns a per-planet dict:
    ``{house_from_moon, favourable, vedha: {obstructed, by, vedha_house},
    effective, source_status}``.
    """
    result: dict[str, dict] = {}
    for planet, house in houses_from_moon.items():
        table = CLASSICAL_GOCHARA_VEDHA.get(planet)
        if table is None:
            continue
        favourable = house in table
        vedha_house = table.get(house)
        obstructed_by = None
        if favourable:
            for other, other_house in houses_from_moon.items():
                if other == planet or other not in CLASSICAL_GOCHARA_VEDHA:
                    continue
                if frozenset({planet, other}) in VEDHA_EXEMPT_PAIRS:
                    continue
                if other_house == vedha_house:
                    obstructed_by = other
                    break
        obstructed = obstructed_by is not None
        if favourable:
            effective = "obstructed" if obstructed else "favourable"
        else:
            effective = "unfavourable"
        result[planet] = {
            "house_from_moon": house,
            "favourable": favourable,
            "vedha": {
                "obstructed": obstructed,
                "by": obstructed_by,
                "vedha_house": vedha_house,
            },
            "effective": effective,
            "source_status": _CLASSICAL_SOURCE_STATUS.get(planet, "classical"),
        }
    return result
