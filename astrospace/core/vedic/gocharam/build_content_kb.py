"""Build the reviewed Gocharam content library.

The classical layer is deliberately small and auditable: the favourable-house
and vedha table lives in ``rules.py``. Every one of the 108 baseline records
generated here is composed, not hand-typed per placement, from three kinds of
ingredient that are each separately labelled:

1. The classical favourable/unfavourable verdict (Phaladeepika ch.26,
   ``source_status: "classical_table"`` — unchanged, verified against the
   source).
2. Computed facts: the houses this planet classically aspects from this
   transit position (BPHS ch.3 graha-drishti rule, via
   ``rules.special_aspect_houses``) and, for the handful of houses with a
   genuinely well-established South Indian name (Sade Sati, Ashtama Shani,
   Ardhashtama Shani, Ashtama Guru, Upachaya strength for malefics), that
   name. These are geometry/convention, not opinion, and are the same for
   every planet-house pair — never hand-typed, never drifting.
3. Editorial synthesis: a short authored "voice" paragraph per planet (nine
   of these, not 108) describing that planet's classical transit
   temperament, combined with the house's own significations.

None of this pretends to be a verbatim classical translation — every record
carries ``content_status: "ai_authored_pending_astrologer_review"`` at the KB
level until a human astrologer review pass (tracked in
``docs/gocharam_engine_checklist.md``) clears it.
"""

from __future__ import annotations

import json
from pathlib import Path

from .rules import CLASSICAL_GOCHARA_VEDHA, special_aspect_houses

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")

SOURCE_ID = "phaladeepika_26_south_indian"
NODE_SOURCE_ID = "south_indian_node_analogy"
ASPECT_SOURCE_ID = "bphs_3_drishti_and_dignity"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ── Per-house data (Sanskrit bhava name, plain theme, short label) ──────────

BHAVA_NAMES = {
    1: "Tanu Bhava", 2: "Dhana Bhava", 3: "Sahaja Bhava", 4: "Sukha Bhava",
    5: "Putra Bhava", 6: "Ari Bhava", 7: "Kalatra Bhava", 8: "Randhra Bhava",
    9: "Dharma Bhava", 10: "Karma Bhava", 11: "Labha Bhava", 12: "Vyaya Bhava",
}

HOUSE_THEMES = {
    1: "body, identity and immediate direction",
    2: "resources, speech, food and family continuity",
    3: "effort, courage, skills and short journeys",
    4: "home, emotional foundations, property and care",
    5: "learning, creativity, counsel and children",
    6: "workload, service, disputes, health routines and obstacles",
    7: "partnerships, agreements and public interaction",
    8: "shared resources, vulnerability, repair and discontinuity",
    9: "teachers, ethics, belief, study and long journeys",
    10: "work, responsibility, reputation and visible contribution",
    11: "gains, networks, fulfilment and longer-term aims",
    12: "expense, rest, retreat, release and distant places",
}

HOUSE_SHORT_LABEL = {
    1: "self", 2: "wealth", 3: "courage", 4: "home", 5: "creativity",
    6: "health", 7: "partnerships", 8: "transformation", 9: "luck",
    10: "career", 11: "gains", 12: "losses",
}


# ── Per-planet authored voice (nine paragraphs, reused across all 12 houses
# of that planet — this, not a bigger template, is the actual authoring
# surface; every house then gets differentiated automatically by its own
# computed aspect houses and any named effect it carries). ──────────────────

PLANET_PROFILE = {
    "Sun": {
        "nature": "malefic",
        "voice": (
            "the Sun is a fast-moving malefic of authority, vitality and visible standing; it "
            "moves through a sign in about a month, so its effect on any one house is usually "
            "brief but sharply felt"
        ),
        "favourable_note": (
            "in the Upachaya-style houses the Sun's heat works for the native, burning through "
            "obstacles and building visible authority"
        ),
        "challenging_note": (
            "outside those houses its heat can show up as friction, ego clashes or short-lived "
            "strain on whatever the house governs"
        ),
    },
    "Moon": {
        "nature": "benefic",
        "voice": (
            "the Moon is the fastest-moving graha and the most emotionally exposed, governing "
            "mind, mother and daily comfort; it changes sign roughly every two and a quarter "
            "days, so no single house transit lasts long"
        ),
        "favourable_note": (
            "as a benefic it tends to nourish and steady whatever house it visits"
        ),
        "challenging_note": (
            "in its difficult houses from itself it can bring a felt restlessness or insecurity "
            "that is usually mild and passes quickly rather than a lasting affliction — the same "
            "configuration daily muhurta timing flags as Chandrashtama when it falls in the 8th"
        ),
    },
    "Mars": {
        "nature": "malefic",
        "voice": (
            "Mars is a fiery, assertive malefic of courage, initiative and decisive action, "
            "carrying a special aspect on the 4th and 8th houses in addition to the ordinary 7th"
        ),
        "favourable_note": (
            "in the Upachaya houses (3rd, 6th, 11th) its combative energy is classically "
            "considered strong, helping the native overcome rivals and obstacles"
        ),
        "challenging_note": (
            "elsewhere its assertive energy can surface as friction, accident-proneness or "
            "impulsive decisions in the house's affairs if left unchecked"
        ),
    },
    "Mercury": {
        "nature": "benefic",
        "voice": (
            "Mercury is an adaptive, quick-moving graha of intellect, communication and trade; "
            "it rarely stays long in a sign and rarely strays far from the Sun, so its transits "
            "tend to be brief and strongly coloured by whichever planets it is combining with"
        ),
        "favourable_note": (
            "in its favourable houses it sharpens analysis, negotiation and paperwork in the "
            "native's favour"
        ),
        "challenging_note": (
            "elsewhere it can bring miscommunication, second-guessing or scattered attention to "
            "the house's affairs rather than outright damage"
        ),
    },
    "Jupiter": {
        "nature": "benefic",
        "voice": (
            "Jupiter is the great benefic of wisdom, expansion and grace, carrying a special "
            "aspect on the 5th and 9th houses in addition to the 7th; its roughly year-long "
            "dwell in each sign makes it the most consequential slow benefic transit after Saturn"
        ),
        "favourable_note": (
            "in its favourable houses it expands and protects the significations strongly, "
            "often bringing the most auspicious results of any Gochara"
        ),
        "challenging_note": (
            "even outside its favourable houses Jupiter rarely does pure damage — the more "
            "usual reading is a slow-burning lesson, a hidden gain, or support that arrives "
            "later than expected"
        ),
    },
    "Venus": {
        "nature": "benefic",
        "voice": (
            "Venus is the benefic of comfort, relationship and resources, moving quickly enough "
            "that it rarely spends more than a few weeks in a sign; its favourable-house list is "
            "the largest of any planet in this table"
        ),
        "favourable_note": (
            "it tends to add ease, value or warmth to whatever the house governs"
        ),
        "challenging_note": (
            "in its few difficult houses the concern is usually indulgence, compromise or public "
            "scrutiny working against comfort rather than genuine hardship"
        ),
    },
    "Saturn": {
        "nature": "malefic",
        "voice": (
            "Saturn is the great teacher and disciplinarian of structure, delay and endurance, "
            "carrying a special aspect on the 3rd and 10th houses in addition to the 7th; its "
            "roughly two-and-a-half-year dwell in each sign is the slowest of the classical "
            "seven, which is why its transits are treated as the most consequential in this system"
        ),
        "favourable_note": (
            "in the Upachaya houses (3rd, 6th, 11th) Saturn is classically considered strong, "
            "rewarding sustained effort with durable, if slow, gains"
        ),
        "challenging_note": (
            "outside those houses its results are earned through restriction before release — "
            "natal Saturn's own strength and Ashtakavarga support usually decide whether that "
            "shows up as disciplined growth or prolonged hardship"
        ),
    },
    "Rahu": {
        "nature": "malefic",
        "voice": (
            "Rahu is a shadow planet of amplification, ambition and unconventional experience; "
            "South Indian practice reads its favourable houses like Saturn's by explicit "
            "convention, not an independently attested classical table"
        ),
        "favourable_note": (
            "in its favourable houses that amplification tends to inflate opportunity, appetite "
            "and visible progress well past ordinary expectations"
        ),
        "challenging_note": (
            "elsewhere the same amplifying tendency can inflate anxiety, obsession or "
            "overreach in the house's affairs"
        ),
    },
    "Ketu": {
        "nature": "malefic",
        "voice": (
            "Ketu is the other shadow planet, governing detachment, sudden endings and inward "
            "focus; it follows the same borrowed Saturn-style convention as Rahu for its "
            "favourable houses"
        ),
        "favourable_note": (
            "in its favourable houses that detachment tends to simplify and focus the house's "
            "affairs rather than expand them, which classically reads as support"
        ),
        "challenging_note": (
            "elsewhere it can bring an unlooked-for ending, loss or withdrawal in the house's "
            "affairs, often without an obvious external cause"
        ),
    },
}


# ── Named effects: the small set of genuinely well-established South Indian
# names for a specific planet-house combination. Nothing is invented here —
# entries not listed simply get the planet-voice + aspect composition above,
# which is already a substantial step beyond a bare favourable/unfavourable
# label. ─────────────────────────────────────────────────────────────────────

UPACHAYA_HOUSES = {3, 6, 11}

NAMED_EFFECTS: dict[tuple[str, int], str] = {
    ("Saturn", 12): "the first leg of Sade Sati",
    ("Saturn", 1): "the core, most keenly felt leg of Sade Sati",
    ("Saturn", 2): "the final leg of Sade Sati",
    ("Saturn", 8): "Ashtama Shani",
    ("Saturn", 4): "Ardhashtama Shani, also called Kantaka Shani",
    ("Jupiter", 8): "Ashtama Guru",
    ("Jupiter", 9): "Jupiter's own Bhagya transit, among the most auspicious Gochara positions",
    ("Moon", 8): "the configuration daily muhurta timing calls Chandrashtama",
}


def _named_effect(planet: str, house: int) -> str | None:
    direct = NAMED_EFFECTS.get((planet, house))
    if direct:
        return direct
    if planet in {"Sun", "Mars", "Saturn"} and house in UPACHAYA_HOUSES:
        return "an Upachaya house, traditionally strong ground for a malefic transit"
    return None


def _cap_first(text: str) -> str:
    """Uppercase only the first character — str.capitalize() also lowercases
    the rest of the string, which mangles proper nouns like "Saturn" or
    "Ashtakavarga" appearing mid-sentence."""
    return text[:1].upper() + text[1:] if text else text


def _aspect_sentence(planet: str, house: int) -> str:
    houses = special_aspect_houses(planet, house)
    ordinals = [ordinal(h) for h in houses]
    if len(ordinals) == 1:
        joined = f"the {ordinals[0]} house"
    else:
        joined = ", ".join(f"the {o}" for o in ordinals[:-1]) + f" and the {ordinals[-1]} houses"
    return f"From here it aspects {joined} from itself."


def _content(planet: str, house: int, favourable: bool) -> dict[str, str]:
    profile = PLANET_PROFILE[planet]
    theme = HOUSE_THEMES[house]
    short_label = HOUSE_SHORT_LABEL[house]
    bhava = BHAVA_NAMES[house]
    aspect_sentence = _aspect_sentence(planet, house)
    named_effect = _named_effect(planet, house)
    status_word = "supportive" if favourable else "demanding"
    verdict_word = "favourable" if favourable else "unfavourable"
    note = profile["favourable_note"] if favourable else profile["challenging_note"]

    guided = (
        f"A {status_word} period for {short_label}. {_cap_first(note)}."
        + (f" This is {named_effect}." if named_effect else "")
    )

    balanced = (
        f"{planet} is transiting the {ordinal(house)} house from the natal Moon ({bhava}), "
        f"touching {theme}. In this table {planet}'s "
        f"{verdict_word} houses make this a {status_word} placement: {note}. {aspect_sentence} "
        + (f"This is classically read as {named_effect}. " if named_effect else "")
        + "Vedha, Ashtakavarga, retrograde motion and the active dasha can all modify how "
        "strongly this plays out."
    )

    practitioner = (
        f"Gochara of {planet} in the {ordinal(house)} house from Janma Chandra ({bhava}). "
        f"Base verdict is {verdict_word} per the classical favourable-house table (Phaladeepika "
        f"ch.26 for the seven visible grahas; Rahu/Ketu by explicit South-Indian convention). "
        f"{_cap_first(profile['voice'])}. {aspect_sentence} "
        + (f"This placement is classically named: {named_effect}. " if named_effect else "")
        + "Resolve BAV/SAV, kakshya, station/retrograde state, natal contacts and dasha "
        "concordance separately before judging intensity — this record is the base verdict, "
        "not the final effective read."
    )

    return {
        "guided_summary": guided,
        "balanced_context": balanced,
        "practitioner_deep_dive": practitioner,
    }


def _placement_rule(planet: str, house: int) -> dict:
    favourable = house in CLASSICAL_GOCHARA_VEDHA[planet]
    node = planet in {"Rahu", "Ketu"}
    return {
        "id": f"baseline_{planet.lower()}_moon_{house}",
        "kind": "baseline_placement",
        "planet": planet,
        "anchor": "moon",
        "houses": [house],
        "category": "baseline",
        "duration": "transit_sign",
        "base_verdict": "supportive" if favourable else "challenging",
        "source_id": NODE_SOURCE_ID if node else SOURCE_ID,
        "source_status": "convention_dependent" if node else "classical_table",
        "claim_status": "classical_verdict_with_editorial_synthesis",
        "rule_name": f"{planet} in house {house} from natal Moon",
        "computed_evidence": {
            "special_aspect_houses": special_aspect_houses(planet, house),
            "named_effect": _named_effect(planet, house),
            "source_id": ASPECT_SOURCE_ID,
        },
        "content": _content(planet, house, favourable),
    }


SPECIAL_RULES = [
    {
        "id": "special_sade_sati",
        "kind": "special_overlay",
        "planet": "Saturn",
        "anchor": "moon",
        "houses": [12, 1, 2],
        "category": "long_cycle",
        "duration": "long_term",
        "base_verdict": "challenging",
        "source_id": "south_indian_sade_sati",
        "source_status": "traditional_practice",
        "claim_status": "traditional_label_with_editorial_synthesis",
        "rule_name": "Sade Sati",
        "content": {
            "guided_summary": "A long responsibility cycle is active. Reduce avoidable pressure and favour patient, repeatable progress.",
            "balanced_context": "Saturn is transiting the 12th, 1st or 2nd from the natal Moon, the traditional Sade Sati span. Read the phase together with Saturn's natal condition and Ashtakavarga support.",
            "practitioner_deep_dive": "Sade Sati overlay active. Phase is determined by Saturn's house from Janma Chandra. Do not infer a fixed event: inspect BAV/SAV, kakshya, dasha concordance, natal Saturn and exact Moon contact.",
        },
    },
    {
        "id": "special_ashtama_shani",
        "kind": "special_overlay",
        "planet": "Saturn",
        "anchor": "moon",
        "houses": [8],
        "category": "long_cycle",
        "duration": "long_term",
        "base_verdict": "challenging",
        "source_id": "south_indian_saturn_specials",
        "source_status": "traditional_practice",
        "claim_status": "traditional_label_with_editorial_synthesis",
        "rule_name": "Ashtama Shani",
        "content": {
            "guided_summary": "A slower repair-oriented cycle is active. Leave margin for delays and avoid fear-based conclusions.",
            "balanced_context": "Saturn is eighth from the natal Moon, traditionally called Ashtama Shani. Emphasize maintenance, resilience and risk controls.",
            "practitioner_deep_dive": "Ashtama Shani overlay active: Saturn=8 from Janma Chandra. Weight by BAV/SAV, natal Saturn, dasha and exact contacts before judging intensity.",
        },
    },
    {
        "id": "special_ardhashtama_shani",
        "kind": "special_overlay",
        "planet": "Saturn",
        "anchor": "moon",
        "houses": [4],
        "category": "long_cycle",
        "duration": "long_term",
        "base_verdict": "challenging",
        "source_id": "south_indian_saturn_specials",
        "source_status": "traditional_practice",
        "claim_status": "traditional_label_with_editorial_synthesis",
        "rule_name": "Ardhashtama Shani (Kantaka Shani)",
        "content": {
            "guided_summary": "Home and emotional foundations may ask for steadier maintenance and clearer limits.",
            "balanced_context": "Saturn is fourth from the natal Moon, traditionally called Ardhashtama Shani or Kantaka Shani.",
            "practitioner_deep_dive": "Ardhashtama Shani (Kantaka Shani) overlay active: Saturn=4 from Janma Chandra. Cross-check Lagna, fourth-house factors, BAV/SAV and dasha.",
        },
    },
]


def build() -> dict:
    rules = [_placement_rule(planet, house) for planet in PLANETS for house in range(1, 13)]
    rules.extend(SPECIAL_RULES)
    return {
        "schema_version": "gocharam.kb.v2",
        "library_version": "astrospace-gocharam-kb-2026.07.2",
        "content_status": "ai_authored_pending_astrologer_review",
        "convention": {
            "primary_anchor": "natal_moon",
            "ayanamsha": "runtime_setting",
            "node_treatment": "Rahu and Ketu use the Saturn favourable-house table by explicit South-Indian convention.",
            "safety": "Traditional indications are contextual and must not be presented as guaranteed medical, legal, financial, longevity or death predictions.",
        },
        "sources": [
            {
                "id": SOURCE_ID,
                "work": "Phaladeepika",
                "location": "chapter 26",
                "scope": "favourable houses and vedha table for seven visible grahas",
                "edition_status": "edition-neutral rule table; translation wording is not quoted",
            },
            {
                "id": NODE_SOURCE_ID,
                "work": "South-Indian applied Gocharam convention",
                "location": "configured project convention",
                "scope": "Rahu and Ketu treated like Saturn for favourable houses and vedha",
                "edition_status": "convention-dependent; not attributed to the Phaladeepika table",
            },
            {
                "id": "south_indian_sade_sati",
                "work": "South-Indian applied Gocharam convention",
                "location": "configured project convention",
                "scope": "Saturn in 12th, 1st and 2nd from natal Moon",
                "edition_status": "traditional label; product wording is editorial",
            },
            {
                "id": "south_indian_saturn_specials",
                "work": "South-Indian applied Gocharam convention",
                "location": "configured project convention",
                "scope": "Saturn in 4th and 8th from natal Moon",
                "edition_status": "traditional labels; product wording is editorial",
            },
            {
                "id": ASPECT_SOURCE_ID,
                "work": "Brihat Parashara Hora Shastra, ch.3 (dignity) and the standard graha-drishti rule",
                "location": "configured project convention",
                "scope": (
                    "Special aspect houses (Mars 4th/8th, Jupiter 5th/9th, Saturn 3rd/10th, all "
                    "planets' ordinary 7th) computed geometrically, not hand-typed; Upachaya "
                    "strength for malefics is a standard classical principle, not a specific "
                    "verse citation."
                ),
                "edition_status": "computed fact / well-established principle; not a verbatim quotation",
            },
        ],
        "rules": rules,
    }


def validate(kb: dict) -> None:
    rules = kb["rules"]
    baseline = [rule for rule in rules if rule["kind"] == "baseline_placement"]
    assert len(baseline) == 108
    ids = [rule["id"] for rule in rules]
    assert len(ids) == len(set(ids))
    source_ids = {source["id"] for source in kb["sources"]}
    assert all(rule["source_id"] in source_ids for rule in rules)
    for planet in PLANETS:
        houses = {rule["houses"][0] for rule in baseline if rule["planet"] == planet}
        assert houses == set(range(1, 13))
    assert all(rule["computed_evidence"]["special_aspect_houses"] for rule in baseline)


def write(path: Path | None = None) -> Path:
    target = path or Path(__file__).with_name("content_kb.json")
    kb = build()
    validate(kb)
    target.write_text(json.dumps(kb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_rich_content_snapshot()
    return target


def write_rich_content_snapshot(path: Path | None = None) -> Path:
    """Persist a flat {planet_house: content} snapshot for human diff review.

    This is generated output, not hand-authored input — kept as a committed,
    git-diffable artifact so a reviewer can see exactly what changed between
    library versions without diffing the full nested content_kb.json.
    """
    target = path or Path(__file__).with_name("rich_gocharam_content.json")
    snapshot = {
        f"{planet}_{house}": _content(planet, house, house in CLASSICAL_GOCHARA_VEDHA[planet])
        for planet in PLANETS
        for house in range(1, 13)
    }
    target.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    print(write())
