"""Which classical marriage rules apply to one person's chart.

The couple agent (compat_insight_agent.py) may interpret each person's
marriage picture only through the rules picked here. The rules themselves are
the marriage references already extracted from BPHS (ch.18, ch.24.73-84) and
Phaladeepika (Adhyaya X, XX) into context/references.json; see
docs/marriage_kb_bphs_7th_house.md and docs/phaladeepika_crosscheck.md for
what was read and what was excluded. Nothing here adds a rule: the code only
decides which stored rule a chart actually meets, so the model is never left
to recall a classical claim from memory.

Hawk (2026-10-20): ground the reading in the classics and standard rules, but
keep sources off the screen. So the picked rules travel to the model with
their ids and the reason they apply, and the reader only ever sees plain text.

The koota system itself is in none of the books we hold (it lives in Muhurta
Chintamani and Kalaprakashika); koota meanings come from the engine's own
standard-practice text in compatibility_guidance.py.
"""
from __future__ import annotations

from ..context.kb import get_knowledge_base

STRONG = {"Exalted", "Moolatrikona", "Own", "Great Friend", "Friend"}
WEAK = {"Debilitated", "Enemy", "Great Enemy"}
DUSTHANAS = {6, 8, 12}
MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")

# How a reader-facing line may carry a rule whose classical wording is harsh.
# The rule stays the rule; only its delivery is fixed here, once.
READ_AS = {
    "bphs18_2_seventh_lord_dusthana": "Read as: the marriage needs more conscious care and mutual support. Never mention the partner's health.",
    "bphs24_80_seventh_lord_in_eighth": "Read as: ease in the marriage comes through effort and patience, not by itself. Never as a lack or a loss.",
    "bphs18_16_malefic_on_seventh": "Read as: an area where friction can build, eased by patience and clear talk. Never as harm.",
    "phal10_malefic_seventh_harm": "Read as: an area where friction can build, eased by patience and clear talk. Never as harm.",
    "bphs18_18_moon_seventh_felicity": "Read as: moods can affect closeness; small daily care helps.",
    "bphs18_4_seventh_lord_strength": "When the lord is weak, read as: this person gives the marriage effort rather than finding it easy.",
    "phal10_strong_seventh_lord_marriage": "Speak of happiness in marriage only; leave children out.",
    "bphs_manglik_marriage_timing": "A flag to weigh with its cancellations, never a verdict.",
    "phal10_marriage_dasha_timing": "For a married couple, read as: a period that brings home and marriage to the front of life.",
}


def _statements() -> dict[str, str]:
    return {ref.ref_id: ref.statement for ref in get_knowledge_base().retrieve(["marriage"], limit=100)}


def _aspected_by_jupiter(planets: dict, house: int) -> bool:
    jupiter = (planets.get("Jupiter") or {}).get("house")
    if not jupiter:
        return False
    # Jupiter's 5th, 7th and 9th aspects, and conjunction.
    return house in {jupiter, (jupiter + 3) % 12 + 1, (jupiter + 5) % 12 + 1, (jupiter + 7) % 12 + 1}


def classical_rules(planets: dict, dignities: dict, seventh_lord: str, manglik: dict,
                    running: dict) -> list[dict]:
    """The stored rules this chart meets, each with why it applies."""
    statements = _statements()
    lord = planets.get(seventh_lord) or {}
    house, sign = lord.get("house"), lord.get("sign")
    dignity = (dignities.get(seventh_lord) or {}).get("dignity")
    venus = planets.get("Venus") or {}
    venus_dignity = (dignities.get("Venus") or {}).get("dignity")
    picked: list[tuple[str, str]] = [
        ("bphs_seventh_kalatra", f"7th lord {seventh_lord} in house {house}; Venus in {venus.get('sign')}"),
        ("bphs_venus_karaka_seventh", f"Venus in {venus.get('sign')}, house {venus.get('house')}, {venus_dignity}"),
    ]

    strong = dignity in STRONG and house not in DUSTHANAS
    weak = dignity in WEAK or house in DUSTHANAS
    if strong or weak:
        picked.append(("bphs18_4_seventh_lord_strength",
                       f"7th lord {seventh_lord} is {'strong' if strong else 'weak'} ({dignity}, house {house})"))
    if strong and _aspected_by_jupiter(planets, house):
        picked.append(("phal10_strong_seventh_lord_marriage", f"7th lord {seventh_lord} strong and in Jupiter's aspect"))

    if house in DUSTHANAS:
        picked.append(("bphs18_2_seventh_lord_dusthana", f"7th lord {seventh_lord} in house {house}"))
    if house == 7:
        picked.append(("bphs24_79_seventh_lord_in_seventh", f"7th lord {seventh_lord} in its own 7th house"))
    elif house == 8:
        picked.append(("bphs24_80_seventh_lord_in_eighth", f"7th lord {seventh_lord} in house 8"))
    elif house not in DUSTHANAS:
        picked.append(("bphs24_seventh_lord_is_also_gain", f"7th lord {seventh_lord} in house {house}"))

    # A 7th lord in its own house strengthens it (24.79), so it is never also
    # counted as a malefic sitting on the 7th.
    on_seventh = [name for name in MALEFICS
                  if name != seventh_lord and (planets.get(name) or {}).get("house") == 7]
    with_lord = [name for name in MALEFICS if name != seventh_lord and sign
                 and (planets.get(name) or {}).get("sign") == sign]
    if on_seventh or with_lord:
        because = "; ".join(filter(None, [
            f"{', '.join(on_seventh)} in the 7th house" if on_seventh else "",
            f"{', '.join(with_lord)} with the 7th lord" if with_lord else "",
        ]))
        picked.append(("bphs18_16_malefic_on_seventh", because))
        picked.append(("phal10_malefic_seventh_harm", because))

    if (planets.get("Moon") or {}).get("house") == 7 and (weak or on_seventh or with_lord):
        picked.append(("bphs18_18_moon_seventh_felicity", "Moon in the 7th with the 7th lord under strain"))

    if manglik.get("active"):
        picked.append(("bphs_manglik_marriage_timing", f"Manglik, net severity {manglik.get('net_severity')}"))

    in_seventh = {name for name, row in planets.items() if row.get("house") == 7}
    for level in ("mahadasha", "antardasha"):
        period = (running.get(level) or {}).get("lord")
        if period and (period == seventh_lord or period in in_seventh or period == "Venus"):
            picked.append(("phal10_marriage_dasha_timing", f"running {level} of {period}, linked to the 7th house or Venus"))
            if period == seventh_lord:
                picked.append(("bphs48_maraka_lords_also_signify_their_house", f"running {level} of the 7th lord {period}"))
                if strong:
                    picked.append(("phal20_maraka_lords_positive_dasha", f"running {level} of a strong 7th lord {period}"))
            break

    rules, seen = [], set()
    for ref_id, because in picked:
        if ref_id in seen or ref_id not in statements:
            continue
        seen.add(ref_id)
        rule = {"id": ref_id, "rule": statements[ref_id], "applies_because": because}
        if ref_id in READ_AS:
            rule["read_as"] = READ_AS[ref_id]
        rules.append(rule)
    return rules
