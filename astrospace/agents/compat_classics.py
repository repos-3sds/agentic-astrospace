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

Upapada and Navamsa (2026-10-21): the Upapada rules are BPHS ch.30 and
Uttara Kalamritam Kanda IV sl.39-40, the Navamsa rules BPHS ch.7 and
Phaladeepika IX.20 / XX.22. Only the parts about married happiness and the
partner's nature were stored. Both books spend most of these verses on the
loss of a wife, the number of wives, the wife's illnesses and children; none
of that was stored, and the harsh half of a verse that was stored is never a
trigger here except bphs30_4, which goes out softened through READ_AS. See
docs/marriage_kb_bphs_7th_house.md, "Upapada and Navamsa".
"""
from __future__ import annotations

from ..context.kb import get_knowledge_base
from ..core.vedic.constants import EXALTATION, SIGN_LORDS, SIGNS
from ..core.vedic.jaimini import arudha_pada_detail
from ..core.vedic.vargas import d9
from ..core.vedic.vimshopaka import dignity_in_varga
from ..core.vedic.yogas import _planet_aspects

STRONG = {"Exalted", "Moolatrikona", "Own", "Great Friend", "Friend"}
WEAK = {"Debilitated", "Enemy", "Great Enemy"}
DUSTHANAS = {6, 8, 12}
MALEFICS = ("Sun", "Mars", "Saturn", "Rahu", "Ketu")
# Natural benefics only (Uttara Kalamritam's note to IV.39), as yogas.py counts them.
BENEFICS = ("Jupiter", "Venus", "Mercury")
# Signs owned by the Sun, Mars and Saturn (BPHS 30.4's "malefic sign").
MALEFIC_SIGNS = {0, 4, 7, 9, 10}
BENEFIC_SIGNS = {1, 2, 5, 6, 8, 11}
# BPHS 30.6: the Sun is no malefic when exalted or in a friendly sign.
_SUN_NOT_MALEFIC = {"Exalted", "Moolatrikona", "Own", "Great Friend", "Friend"}

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
    "bphs30_4_upapada_malefic": "Read as: commitment asks for patience and steady effort from this person. Never as being without a partner, leaving, or a loss.",
    "bphs7_vimsopaka_varga_dignity": "When the planet is weak there, read as: this side of married life grows with effort rather than coming easily.",
    "bphs30_14_upapada_lord_exalted": "Speak of the partner's good upbringing and values; never rank families or castes.",
}


def _statements() -> dict[str, str]:
    return {ref.ref_id: ref.statement for ref in get_knowledge_base().retrieve(["marriage"], limit=100)}


def _aspected_by_jupiter(planets: dict, house: int) -> bool:
    jupiter = (planets.get("Jupiter") or {}).get("house")
    if not jupiter:
        return False
    # Jupiter's 5th, 7th and 9th aspects, and conjunction.
    return house in {jupiter, (jupiter + 3) % 12 + 1, (jupiter + 5) % 12 + 1, (jupiter + 7) % 12 + 1}


def _malefics(dignities: dict) -> set[str]:
    sun = (dignities.get("Sun") or {}).get("dignity")
    return {name for name in MALEFICS if name != "Sun" or sun not in _SUN_NOT_MALEFIC}


def _sign_influence(sign: int, signs: dict[str, int]) -> tuple[list[str], list[str]]:
    """Planets in a sign, and planets aspecting it (Parashari graha drishti)."""
    occupants = [name for name, at in signs.items() if at == sign]
    aspecting = [name for name, at in signs.items() if at != sign and _planet_aspects(name, at, sign)]
    return occupants, aspecting


def upapada_facts(lagna_sign: int, positions: dict, dignities: dict) -> dict:
    """The Upapada (arudha of the 12th), the 2nd from it, and the Darapada (A7).

    Convention: the 12th house for every rising sign, as BPHS 30.2 reads and
    as jaimini.py computes it. Santhanam's note prefers the 2nd house for an
    even rising sign, after some Jaimini commentaries; that variant is not used.
    """
    signs = {name: int(row["lon"] // 30) for name, row in positions.items()}
    malefics = _malefics(dignities)

    def describe(sign: int) -> dict:
        occupants, aspecting = _sign_influence(sign, signs)
        return {
            "sign": SIGNS[sign],
            "lord": SIGN_LORDS[sign],
            "planets_in_it": occupants,
            "aspected_by": aspecting,
            "benefic_in": [n for n in occupants if n in BENEFICS],
            "benefic_on": [n for n in occupants + aspecting if n in BENEFICS],
            "malefic_on": [n for n in occupants + aspecting if n in malefics],
            "_index": sign,
        }

    ul = arudha_pada_detail(12, lagna_sign, positions)["sign"]
    a7 = arudha_pada_detail(7, lagna_sign, positions)["sign"]
    lord = SIGN_LORDS[ul]
    return {
        "upapada": describe(ul),
        "second_from_upapada": describe((ul + 1) % 12),
        "darapada": describe(a7),
        "upapada_lord": {"planet": lord, "sign": SIGNS[signs[lord]],
                         "dignity": (dignities.get(lord) or {}).get("dignity")},
    }


def navamsa_facts(positions: dict, lagna_lon: float, seventh_lord: str,
                  conditions: dict | None = None) -> dict:
    """The Navamsa (D9) placements BPHS ch.7 reads for the spouse."""
    conditions = conditions or {}

    def place(name: str) -> dict:
        lon = positions[name]["lon"]
        sign = d9(lon)
        return {
            "planet": name,
            "sign": SIGNS[sign],
            "dignity": dignity_in_varga(name, "D9", positions),
            "vargottama": sign == int(lon // 30),
            "combust": bool(((conditions.get(name) or {}).get("combustion") or {}).get("active")),
        }

    planets = {name: place(name) for name in EXALTATION if name in positions}
    return {
        "seventh_sign": SIGNS[(d9(lagna_lon) + 6) % 12],
        "seventh_lord": planets[seventh_lord],
        "venus": planets["Venus"],
        "planets": planets,
    }


def _upapada_picks(facts: dict) -> list[tuple[str, str]]:
    ul, second, a7, lord = (facts["upapada"], facts["second_from_upapada"],
                            facts["darapada"], facts["upapada_lord"])
    picked: list[tuple[str, str]] = []
    where = f"Upapada in {ul['sign']}"
    if ul["benefic_on"]:
        picked.append(("bphs30_1_upapada_benefic", f"{where} with {', '.join(ul['benefic_on'])}"))
    if ul["benefic_in"]:
        picked.append(("uk4_39_upapada_benefic_character", f"{', '.join(ul['benefic_in'])} in the Upapada ({ul['sign']})"))
    strain = ul["malefic_on"] or ul["_index"] in MALEFIC_SIGNS
    if strain:
        because = f"{where}" + (f" with {', '.join(ul['malefic_on'])}" if ul["malefic_on"] else ", a sign of a malefic")
        if ul["benefic_on"]:
            picked.append(("bphs30_5_upapada_benefic_relief", f"{because}, eased by {', '.join(ul['benefic_on'])}"))
        else:
            picked.append(("bphs30_4_upapada_malefic", because))
    if second["_index"] in BENEFIC_SIGNS or second["benefic_on"]:
        because = f"2nd from the Upapada is {second['sign']}"
        if second["benefic_on"]:
            because += f" with {', '.join(second['benefic_on'])}"
        picked.append(("bphs30_7_second_from_upapada_benefic", because))
    if lord["dignity"] == "Exalted":
        picked.append(("bphs30_14_upapada_lord_exalted", f"Upapada lord {lord['planet']} exalted in {lord['sign']}"))
    if ul["benefic_on"] and a7["benefic_on"] and not ul["malefic_on"] and not a7["malefic_on"]:
        picked.append(("uk4_40_darapada_upapada_benefic",
                       f"benefics on both the Upapada ({ul['sign']}) and the Darapada ({a7['sign']})"))
    return picked


def _navamsa_picks(facts: dict, running: dict, seventh_lord: str, in_seventh: set[str]) -> list[tuple[str, str]]:
    lord, venus = facts["seventh_lord"], facts["venus"]
    picked: list[tuple[str, str]] = [(
        "bphs7_navamsa_for_spouse",
        f"Navamsa: 7th lord {seventh_lord} in {lord['sign']}, Venus in {venus['sign']}"
        + (f", 7th sign {facts['seventh_sign']}" if facts.get("seventh_sign") else ""),
    )]
    vargottama = [row["planet"] for row in (lord, venus) if row["vargottama"]]
    if vargottama:
        picked.append(("phal9_vargottama_own_house", f"{' and '.join(dict.fromkeys(vargottama))} vargottama"))
    graded = [f"{row['planet']} {row['dignity']} in the Navamsa" for row in (lord, venus)
              if row["dignity"] in STRONG or row["dignity"] in WEAK]
    if graded:
        picked.append(("bphs7_vimsopaka_varga_dignity", "; ".join(dict.fromkeys(graded))))
    marriage_lords = {seventh_lord, "Venus", *in_seventh}
    for level in ("mahadasha", "antardasha"):
        period = (running.get(level) or {}).get("lord")
        row = facts["planets"].get(period) or {}
        if period in marriage_lords and row.get("vargottama"):
            mixed = row["combust"] or row["dignity"] == "Debilitated"
            picked.append(("phal20_vargottama_dasha_favourable",
                           f"running {level} of {period}, vargottama and linked to marriage"
                           + ("; combust or debilitated, so mixed" if mixed else "")))
            break
    return picked


def classical_rules(planets: dict, dignities: dict, seventh_lord: str, manglik: dict,
                    running: dict, upapada: dict | None = None,
                    navamsa: dict | None = None) -> list[dict]:
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

    if upapada:
        picked.extend(_upapada_picks(upapada))
    if navamsa:
        picked.extend(_navamsa_picks(navamsa, running, seventh_lord, in_seventh))

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
