"""Deterministic, evidence-bearing Gocharam interpretation composition."""

from __future__ import annotations

import json
from pathlib import Path

INTERPRETATION_SCHEMA_VERSION = "gocharam.interpretation.v3"

DOMAIN_DEFINITIONS = (
    {
        "id": "career",
        "title": "Career and visible work",
        "houses": {2, 6, 10, 11},
        "planets": {"Sun", "Mars", "Mercury", "Jupiter", "Saturn", "Rahu"},
        "theme": "responsibility, execution, reputation, gains and professional networks",
        "action": "Prioritize work that can be completed and verified; document important decisions.",
    },
    {
        "id": "money",
        "title": "Money and resources",
        "houses": {2, 5, 8, 11, 12},
        "planets": {"Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"},
        "theme": "income, savings, shared resources, speculation and expenditure",
        "action": "Use written numbers and buffers; avoid treating a transit as financial advice.",
    },
    {
        "id": "relationships",
        "title": "Relationships and family",
        "houses": {2, 4, 5, 7, 8, 11, 12},
        "planets": {"Moon", "Mars", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"},
        "theme": "partnership, family continuity, emotional availability and agreements",
        "action": "Clarify expectations directly and allow extra time where the evidence is mixed.",
    },
    {
        "id": "health_energy",
        "title": "Energy and daily care",
        "houses": {1, 6, 8, 12},
        "planets": {"Sun", "Moon", "Mars", "Saturn", "Rahu", "Ketu"},
        "theme": "energy, workload, recovery and sustainable routines",
        "action": "Protect sleep and routine; use qualified medical care for symptoms or decisions.",
    },
    {
        "id": "learning_travel",
        "title": "Learning, travel and growth",
        "houses": {3, 5, 9, 12},
        "planets": {"Sun", "Mercury", "Jupiter", "Rahu", "Ketu"},
        "theme": "study, mentors, communication, journeys and changes of perspective",
        "action": "Verify logistics and use supportive periods for structured learning or planning.",
    },
    {
        "id": "inner_life",
        "title": "Inner life and emotional balance",
        "houses": {1, 4, 8, 12},
        "planets": {"Moon", "Jupiter", "Saturn", "Rahu", "Ketu"},
        "theme": "emotional foundations, reflection, uncertainty, release and resilience",
        "action": "Make room for reflection without converting a symbolic indication into a diagnosis.",
    },
)


def load_knowledge_base() -> dict:
    path = Path(__file__).with_name("content_kb.json")
    if not path.exists():
        return {"rules": [], "sources": [], "library_version": "missing"}
    return json.loads(path.read_text(encoding="utf-8"))


class GocharamInferenceEngine:
    def __init__(self, kb_data: dict):
        self.kb = kb_data
        self.kb_rules = kb_data.get("rules", [])

    def resolve(
        self,
        gochara: dict,
        timeline: dict,
        dasha_context: dict | None = None,
    ) -> list[dict]:
        matched: list[dict] = []
        for rule in self.kb_rules:
            planet = rule.get("planet")
            planet_data = gochara.get("planets", {}).get(planet)
            if not planet_data or not self._matches(rule, planet_data):
                continue
            modifiers = self._modifiers(planet, planet_data, gochara, timeline, dasha_context)
            effective = self._effective_verdict(rule.get("base_verdict", "neutral"), modifiers)
            matched.append(
                {
                    "rule_id": rule.get("id"),
                    "kind": rule.get("kind", "special_overlay"),
                    "rule_name": rule.get("rule_name"),
                    "planet": planet,
                    "anchor": rule.get("anchor", "moon"),
                    "house": planet_data.get(f"house_from_{rule.get('anchor', 'moon')}"),
                    "category": rule.get("category"),
                    "duration": rule.get("duration"),
                    "base_verdict": rule.get("base_verdict"),
                    "effective_verdict": effective,
                    "source_id": rule.get("source_id"),
                    "source_status": rule.get("source_status"),
                    "claim_status": rule.get("claim_status"),
                    "content": dict(rule.get("content", {})),
                    "modifiers": modifiers,
                }
            )
        return matched

    @staticmethod
    def _matches(rule: dict, planet_data: dict) -> bool:
        anchor = rule.get("anchor", "moon")
        houses = rule.get("houses")
        if houses is not None and planet_data.get(f"house_from_{anchor}") not in houses:
            return False
        lord = rule.get("kakshya_lord")
        if lord and planet_data.get("kakshya", {}).get("lord") != lord:
            return False
        conjunction = rule.get("exact_natal_conjunction")
        return not conjunction or conjunction in planet_data.get("exact_natal_conjunctions", [])

    @staticmethod
    def _modifiers(
        planet: str,
        planet_data: dict,
        gochara: dict,
        timeline: dict,
        dasha_context: dict | None,
    ) -> list[dict]:
        modifiers: list[dict] = []
        status = gochara.get("classical_gochara", {}).get(planet, {})
        vedha = status.get("vedha", {})
        if vedha.get("obstructed"):
            modifiers.append(
                {
                    "type": "vedha",
                    "effect": "weakens_support",
                    "label": f"Obstructed by {vedha.get('by')} in house {vedha.get('vedha_house')}",
                    "evidence": vedha,
                }
            )

        av = gochara.get("ashtakavarga", {}).get("planets", {}).get(planet)
        if av:
            effect = {
                "strong": "strengthens",
                "average": "neutral",
                "weak": "weakens",
            }.get(av.get("bav_support"), "neutral")
            modifiers.append(
                {
                    "type": "ashtakavarga",
                    "effect": effect,
                    "label": f"{av.get('bindus')} BAV bindus · {av.get('sav')} SAV",
                    "evidence": {
                        "bindus": av.get("bindus"),
                        "bav_support": av.get("bav_support"),
                        "sav": av.get("sav"),
                        "sav_support": av.get("sav_support"),
                        "kakshya": av.get("kakshya"),
                    },
                }
            )

        if planet_data.get("retrograde"):
            modifiers.append(
                {
                    "type": "motion",
                    "effect": "review",
                    "label": "Retrograde: repeat, review or internalize the transit theme",
                    "evidence": {"retrograde": True, "speed": planet_data.get("speed")},
                }
            )

        contacts = planet_data.get("exact_natal_conjunctions", [])
        if contacts:
            modifiers.append(
                {
                    "type": "natal_contact",
                    "effect": "intensifies",
                    "label": "Within 1° of natal " + ", ".join(contacts),
                    "evidence": {"orb_limit_degrees": 1.0, "natal_planets": contacts},
                }
            )

        if dasha_context and planet.lower() in json.dumps(dasha_context, default=str).lower():
            modifiers.append(
                {
                    "type": "dasha_concordance",
                    "effect": "strengthens",
                    "label": f"{planet} is named in the active dasha context",
                    "evidence": dasha_context,
                }
            )

        active_window = next(
            (row for row in timeline.get("active_windows", []) if row.get("planet") == planet),
            None,
        )
        if active_window:
            modifiers.append(
                {
                    "type": "timing",
                    "effect": "active",
                    "label": f"Active {active_window.get('start_date') or 'before range'} to {active_window.get('end_date') or 'beyond range'}",
                    "evidence": {
                        "rule_id": active_window.get("rule_id"),
                        "start_date": active_window.get("start_date"),
                        "end_date": active_window.get("end_date"),
                    },
                }
            )
        return modifiers

    @staticmethod
    def _effective_verdict(base: str, modifiers: list[dict]) -> str:
        effects = {row["effect"] for row in modifiers}
        if base == "supportive" and ("weakens_support" in effects or "weakens" in effects):
            return "mixed"
        if base == "challenging" and "strengthens" in effects:
            return "mixed"
        return base


def _synthesis(rules: list[dict]) -> dict:
    baseline = [rule for rule in rules if rule["kind"] == "baseline_placement"]
    supportive = [rule for rule in baseline if rule["effective_verdict"] == "supportive"]
    challenging = [rule for rule in baseline if rule["effective_verdict"] == "challenging"]
    mixed = [rule for rule in baseline if rule["effective_verdict"] == "mixed"]
    if mixed or (supportive and challenging):
        tone = "mixed"
        headline = "The transit picture is mixed after strength and obstruction checks"
    elif supportive:
        tone = "supportive"
        headline = "The transit background is broadly supportive"
    elif challenging:
        tone = "challenging"
        headline = "The transit background calls for more care"
    else:
        tone = "neutral"
        headline = "The transit background is relatively even"
    strongest = (supportive + mixed + challenging)[:3]
    names = ", ".join(f"{row['planet']} in {row['house']}" for row in strongest)
    return {
        "tone": tone,
        "headline": headline,
        "counts": {
            "supportive": len(supportive),
            "mixed": len(mixed),
            "challenging": len(challenging),
        },
        "guided_summary": f"{headline}. Focus on one practical response at a time rather than treating any single transit as a guarantee.",
        "balanced_context": f"{headline}. The leading placement evidence is {names}. Open a planet for vedha, strength, motion and timing.",
        "practitioner_deep_dive": (
            f"Resolved {len(baseline)} baseline placements: {len(supportive)} supportive, "
            f"{len(mixed)} modified/mixed and {len(challenging)} challenging. "
            "This aggregate is descriptive; inspect every evidence-bearing modifier before judgment."
        ),
    }


def _tone_for(rules: list[dict]) -> str:
    verdicts = {rule["effective_verdict"] for rule in rules}
    if "mixed" in verdicts or ({"supportive", "challenging"} <= verdicts):
        return "mixed"
    if "challenging" in verdicts:
        return "challenging"
    if "supportive" in verdicts:
        return "supportive"
    return "neutral"


def _range_outlook(timeline: dict, planets: set[str] | None = None) -> dict:
    days = int(timeline.get("scan_days", 0))
    future = [
        event
        for event in timeline.get("next_365_days", [])
        if not planets or event.get("planet") in planets
    ]
    previous = [
        event
        for event in timeline.get("previous_365_days", [])
        if not planets or event.get("planet") in planets
    ]
    supportive = sum(event.get("tone") == "supportive" for event in future)
    challenging = sum(event.get("tone") in {"challenging", "hard"} for event in future)
    if supportive and challenging:
        tone = "mixed"
    elif challenging:
        tone = "challenging"
    elif supportive:
        tone = "supportive"
    else:
        tone = "neutral"
    if future:
        first = future[0]
        last = future[-1]
        title = f"{len(future)} named change{'s' if len(future) != 1 else ''} in the next {days} days"
        reading = (
            f"This {days}-day horizon begins with {first['title']} on {first['date']} "
            f"and extends through {last['title']} on {last['date']}. "
            f"It contains {supportive} supportive and {challenging} caution transition"
            f"{'s' if challenging != 1 else ''}."
        )
    else:
        title = f"Stable named-rule background for the next {days} days"
        reading = (
            f"No supported named Gocharam rule starts or ends inside this specific {days}-day horizon. "
            "The current placements and active windows still apply; shorter Moon movement, ingress, "
            "stations and exact aspects are outside this named-rule summary."
        )
    if previous:
        nearest_previous = previous[0]
        previous_title = f"{len(previous)} named change{'s' if len(previous) != 1 else ''} in the previous {days} days"
        previous_reading = (
            f"The nearest earlier transition is {nearest_previous['title']} on {nearest_previous['date']}. "
            f"The complete {days}-day backward scan contains {len(previous)} named change"
            f"{'s' if len(previous) != 1 else ''}."
        )
    else:
        previous_title = f"Stable named-rule background for the previous {days} days"
        previous_reading = (
            f"No supported named Gocharam rule started or ended in the previous {days} days. "
            "Use exact aspects, ingress and the dasha timeline to investigate shorter-lived changes."
        )
    return {
        "days": days,
        "event_count": len(future),
        "previous_event_count": len(previous),
        "supportive_count": supportive,
        "challenging_count": challenging,
        "tone": tone,
        "title": title,
        "reading": reading,
        "previous_title": previous_title,
        "previous_reading": previous_reading,
        "first_change": future[0] if future else None,
        "last_change": future[-1] if future else None,
        "highlights": future[:4],
        "previous_highlights": previous[:3],
    }


def _domain_readings(rules: list[dict], timeline: dict) -> list[dict]:
    baseline = [rule for rule in rules if rule["kind"] == "baseline_placement"]
    domains = []
    for definition in DOMAIN_DEFINITIONS:
        relevant = [
            rule
            for rule in baseline
            if rule["planet"] in definition["planets"] and rule["house"] in definition["houses"]
        ]
        if not relevant:
            relevant = [rule for rule in baseline if rule["planet"] in definition["planets"]][:3]
        supportive = [rule for rule in relevant if rule["effective_verdict"] == "supportive"]
        challenging = [rule for rule in relevant if rule["effective_verdict"] == "challenging"]
        mixed = [rule for rule in relevant if rule["effective_verdict"] == "mixed"]
        leading = sorted(
            relevant,
            key=lambda rule: (
                not any(mod["effect"] in {"intensifies", "strengthens", "weakens_support"} for mod in rule["modifiers"]),
                rule["planet"],
            ),
        )[:4]
        leading_text = ", ".join(
            f"{rule['planet']} in {rule['house']} ({rule['effective_verdict']})" for rule in leading
        )
        tone = _tone_for(relevant)
        if tone == "supportive":
            main_theme = f"Current evidence is comparatively supportive for {definition['theme']}."
        elif tone == "challenging":
            main_theme = f"Current evidence asks for more care around {definition['theme']}."
        elif tone == "mixed":
            main_theme = f"Support and pressure coexist around {definition['theme']}."
        else:
            main_theme = f"No strong directional verdict dominates {definition['theme']}."
        domains.append(
            {
                "id": definition["id"],
                "title": definition["title"],
                "tone": tone,
                "main_theme": main_theme,
                "rationale": (
                    f"This domain projection uses {len(relevant)} current placement witnesses: {leading_text}. "
                    "It retains each witness's base verdict and modifiers rather than assigning a new probability."
                ),
                "reading": (
                    f"{main_theme} {definition['action']} "
                    f"The current mix contains {len(supportive)} supportive, {len(mixed)} modified, "
                    f"and {len(challenging)} demanding witnesses."
                ),
                "strengths": [
                    rule["content"]["guided_summary"] for rule in supportive[:2]
                ],
                "challenges": [
                    rule["content"]["guided_summary"] for rule in (challenging + mixed)[:2]
                ],
                "actions": [definition["action"]],
                "leading_planets": [rule["planet"] for rule in leading],
                "evidence_ids": [f"rule.{rule['rule_id']}" for rule in relevant],
                "range_outlook": _range_outlook(timeline, definition["planets"]),
            }
        )
    return domains


def compose_gocharam_interpretation(
    gochara: dict,
    timeline: dict,
    dasha_context: dict | None = None,
) -> dict:
    kb = load_knowledge_base()
    matched = GocharamInferenceEngine(kb).resolve(gochara, timeline, dasha_context)
    evidence = [
        {
            "id": f"transit.{planet.lower()}",
            "type": "computed_transit",
            "planet": planet,
            "sign": row.get("sign"),
            "degree_in_sign": row.get("degree_in_sign"),
            "house_from_moon": row.get("house_from_moon"),
            "house_from_lagna": row.get("house_from_lagna"),
            "retrograde": row.get("retrograde"),
            "classical": gochara.get("classical_gochara", {}).get(planet),
        }
        for planet, row in gochara.get("planets", {}).items()
    ]
    evidence.extend(
        {
            "id": f"rule.{rule['rule_id']}",
            "type": "deterministic_rule",
            "rule_id": rule["rule_id"],
            "source_id": rule["source_id"],
            "base_verdict": rule["base_verdict"],
            "effective_verdict": rule["effective_verdict"],
        }
        for rule in matched
    )
    return {
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "library_version": kb.get("library_version"),
        "mode": "deterministic_cited_kb",
        "convention": kb.get("convention", {}),
        "sources": kb.get("sources", []),
        "methodology": {
            "calculation_rule": "Positions and rule activation come from the canonical Swiss-Ephemeris engine.",
            "interpretation_rule": "Classical verdicts and explicitly labelled editorial synthesis are composed deterministically; AI is not used at runtime.",
        },
        "synthesis": _synthesis(matched),
        "range_outlook": _range_outlook(timeline),
        "domains": _domain_readings(matched, timeline),
        "matched_rules": matched,
        "evidence": evidence,
    }
