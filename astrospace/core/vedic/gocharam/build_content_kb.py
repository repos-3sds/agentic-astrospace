"""Build the reviewed Gocharam content library.

The classical layer is deliberately small and auditable: the favourable-house
and vedha table lives in ``rules.py``.  The 108 placement records generated
here never pretend that modern counselling language is a verbatim classical
translation.  Each record labels the classical verdict separately from the
editorial synthesis used by the product UI.
"""

from __future__ import annotations

import json
from pathlib import Path

from .rules import CLASSICAL_GOCHARA_VEDHA

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")

PLANET_DOMAINS = {
    "Sun": ("visibility, authority, vitality and purpose", "leadership or recognition"),
    "Moon": ("mood, responsiveness, care and daily rhythm", "emotional steadiness"),
    "Mars": ("effort, assertion, conflict and decisive action", "disciplined action"),
    "Mercury": ("analysis, communication, trade and coordination", "clear communication"),
    "Jupiter": ("learning, judgment, counsel and expansion", "wise growth"),
    "Venus": ("relationships, agreement, comfort and resources", "balanced relating"),
    "Saturn": ("duty, delay, endurance and structure", "patient restructuring"),
    "Rahu": ("amplification, appetite, novelty and uncertainty", "careful experimentation"),
    "Ketu": ("separation, simplification, scrutiny and inward focus", "intentional simplification"),
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

SOURCE_ID = "phaladeepika_26_south_indian"
NODE_SOURCE_ID = "south_indian_node_analogy"


def _content(planet: str, house: int, favourable: bool) -> dict[str, str]:
    domain, action = PLANET_DOMAINS[planet]
    theme = HOUSE_THEMES[house]
    status = "supportive" if favourable else "demanding"
    guided = (
        f"This is a {status} transit for {theme}. "
        f"Keep the focus on {action}; treat the indication as context, not a guaranteed event."
    )
    balanced = (
        f"{planet} is in house {house} from the natal Moon. In the configured Gocharam table "
        f"this placement is {status}. It connects {domain} with {theme}. "
        "Natal strength, vedha, Ashtakavarga and the active dasha can modify the result."
    )
    practitioner = (
        f"Transit {planet}: {house} from Janma Chandra; base verdict={status}. "
        f"Interpretive domains: {domain}; bhava field: {theme}. This is an editorial synthesis "
        "of the configured classical verdict, not a verbatim textual quotation. Resolve vedha, "
        "BAV/SAV, kakshya, station/retrograde state, natal contacts and dasha concordance separately."
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
        "rule_name": "Ardhashtama Shani",
        "content": {
            "guided_summary": "Home and emotional foundations may ask for steadier maintenance and clearer limits.",
            "balanced_context": "Saturn is fourth from the natal Moon, traditionally called Ardhashtama or Kantaka Shani.",
            "practitioner_deep_dive": "Ardhashtama Shani overlay active: Saturn=4 from Janma Chandra. Cross-check Lagna, fourth-house factors, BAV/SAV and dasha.",
        },
    },
]


def build() -> dict:
    rules = [_placement_rule(planet, house) for planet in PLANETS for house in range(1, 13)]
    rules.extend(SPECIAL_RULES)
    return {
        "schema_version": "gocharam.kb.v2",
        "library_version": "astrospace-gocharam-kb-2026.07.1",
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


def write(path: Path | None = None) -> Path:
    target = path or Path(__file__).with_name("content_kb.json")
    kb = build()
    validate(kb)
    target.write_text(json.dumps(kb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    print(write())
