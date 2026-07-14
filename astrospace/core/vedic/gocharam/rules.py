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
    principle: str
    plain_when_active: str
    plain_when_inactive: str


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
        principle="Saturn in 12th, 1st, or 2nd from natal Moon is treated as a long pressure cycle.",
        plain_when_active=(
            "This is a slow responsibility period. It can feel like life is asking for maturity, patience, discipline, "
            "and cleaner choices rather than quick wins."
        ),
        plain_when_inactive="Sade Sati is not the main Gocharam background right now.",
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
        principle="Saturn in the 8th from natal Moon is treated as a caution period.",
        plain_when_active=(
            "This can bring heavier inner pressure, delays, health sensitivity, or sudden responsibilities. "
            "It is a period for caution, repair, and avoiding avoidable risks."
        ),
        plain_when_inactive="Ashtama Shani is not active from the Moon.",
    ),
    GocharaRuleDefinition(
        id="gochara_kantaka_shani",
        name="Kantaka Shani / Dhaiya",
        planet="Saturn",
        anchor="moon",
        active_houses=frozenset({4}),
        severity="medium",
        tone="challenging",
        source_status="south_indian_common_practice",
        principle="Saturn in the 4th from natal Moon is treated as domestic, emotional, and stability pressure.",
        plain_when_active=(
            "Home, emotional comfort, property, mother-related matters, or peace of mind may need more patience. "
            "This is not a panic signal; it asks for steadiness and fewer impulsive moves."
        ),
        plain_when_inactive="Kantaka Shani is not active from the Moon.",
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
        principle="Jupiter in 2, 5, 7, 9, or 11 from natal Moon is treated as supportive.",
        plain_when_active=(
            "This gives a more helpful background for guidance, learning, recovery, family support, planning, and growth. "
            "It does not remove all problems, but it can make support easier to access."
        ),
        plain_when_inactive="Jupiter is not in a major supportive house from the Moon.",
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
        principle="Jupiter in 2, 5, 7, 9, or 11 from Lagna is used as a practical-life cross-check.",
        plain_when_active=(
            "This supports visible progress, better advice, practical opportunities, agreements, education, and recovery. "
            "It is especially useful when the Moon-based reading is mixed."
        ),
        plain_when_inactive="Jupiter is not giving a major Lagna-based support signal.",
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
        principle="Rahu in sensitive houses from Moon is treated as a volatility marker.",
        plain_when_active=(
            "Rahu can amplify urgency, confusion, desire, experimentation, or sudden changes. "
            "This is a good time to double-check decisions that feel emotionally charged."
        ),
        plain_when_inactive="Rahu is not in one of the sensitive Moon houses tracked by this module.",
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
        principle="Ketu in sensitive houses from Moon is treated as detachment, uncertainty, or separation pressure.",
        plain_when_active=(
            "Ketu can create distance, doubt, spiritual focus, or loss of interest in ordinary outcomes. "
            "This is useful for simplification, but not ideal for decisions made from confusion."
        ),
        plain_when_inactive="Ketu is not in one of the sensitive Moon houses tracked by this module.",
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
        principle="Mars in pressure houses from Moon is treated as a short heat, conflict, or urgency trigger.",
        plain_when_active=(
            "Mars can make the period sharper, faster, and more reactive. "
            "Use it for action and courage, but watch anger, haste, injuries, and conflict."
        ),
        plain_when_inactive="Mars is not in a major pressure house from the Moon.",
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
