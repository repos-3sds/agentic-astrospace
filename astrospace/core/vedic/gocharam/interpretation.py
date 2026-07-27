"""Deterministic, KB-driven Gocharam interpretation composition.

The engine matches raw transit facts against a structured Content Knowledge Base (KB).
It never uses AI to evaluate astrology. It outputs structured JSON that the UI
uses to conditionally render text based on the user's Persona.
"""

from __future__ import annotations
import json
from pathlib import Path

INTERPRETATION_SCHEMA_VERSION = "gocharam.interpretation.v2"
INTERPRETATION_LIBRARY_VERSION = "astrospace-gocharam-kb-2026.07"


def load_knowledge_base() -> dict:
    kb_path = Path(__file__).parent / "content_kb.json"
    if not kb_path.exists():
        return {"rules": []}
    with kb_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class GocharamInferenceEngine:
    def __init__(self, kb_data: dict):
        self.kb_rules = kb_data.get("rules", [])

    def resolve(self, gochara: dict, timeline: dict, dasha_context: dict | None = None) -> list[dict]:
        """
        Step 1 (Fact Gathering) & Step 2 (Rule Matching): 
        Match calculated transits against KB conditions.
        """
        matched_results = []
        for rule in self.kb_rules:
            planet = rule.get("planet")
            
            # Fast fail if planet not in transit
            if not planet or planet not in gochara.get("planets", {}):
                continue
            
            planet_data = gochara["planets"][planet]
            # Match House
            houses = rule.get("houses")
            if houses is not None:
                anchor = rule.get("anchor", "moon")
                house_key = f"house_from_{anchor}"
                current_house = planet_data.get(house_key)
                if current_house not in houses:
                    continue
            
            # Match Kakshya
            kakshya_lord = rule.get("kakshya_lord")
            if kakshya_lord:
                if planet_data.get("kakshya", {}).get("lord") != kakshya_lord:
                    continue
            
            # Match Exact Natal Conjunction
            natal_conjunction = rule.get("exact_natal_conjunction")
            if natal_conjunction:
                if natal_conjunction not in planet_data.get("exact_natal_conjunctions", []):
                    continue
            
            # Match found! Step 3 (Resolution): Apply Mitigations/Aggravations
            content = dict(rule.get("content", {}))
            mitigations = rule.get("mitigations", [])
            
            for mitigation in mitigations:
                cond = mitigation.get("condition")
                
                # Check Ashtakavarga mitigation
                if cond == "ashtakavarga_strong":
                    av = self._get_av(planet, gochara)
                    if av and (av.get("bav_support") == "strong" or av.get("bindus", 0) >= 4):
                        content.update(mitigation.get("content", {}))
                
                # Check Vedha mitigation
                elif cond == "vedha_active":
                    status = gochara.get("classical_gochara", {}).get(planet, {})
                    if status.get("vedha", {}).get("obstructed"):
                        content.update(mitigation.get("content", {}))

            # Step 4 (Assembly): Build the payload
            matched_results.append({
                "rule_id": rule.get("id"),
                "rule_name": rule.get("rule_name"),
                "planet": planet,
                "category": rule.get("category"),
                "duration": rule.get("duration"),
                "content": content
            })
            
        return matched_results

    def _get_av(self, planet: str, gochara: dict) -> dict | None:
        """Helper to safely extract Ashtakavarga data for a planet."""
        row = gochara.get("ashtakavarga", {}).get("planets", {}).get(planet)
        if row:
            return row
        return next(
            (r.get("av_context") for r in gochara.get("rules", []) if r["planet"] == planet and r.get("av_context")),
            None,
        )


def compose_gocharam_interpretation(
    gochara: dict,
    timeline: dict,
    dasha_context: dict | None = None,
) -> dict:
    """
    Main entry point for building the final interpretation payload.
    Replaces the old string-heavy logic with the structured JSON output.
    """
    kb_data = load_knowledge_base()
    engine = GocharamInferenceEngine(kb_data)
    
    # 1. Get the structured text from the Content KB
    matched_rules = engine.resolve(gochara, timeline, dasha_context)
    
    # 2. Preserve the raw canonical evidence for the Professional Web App UI
    evidence = []
    for planet, row in gochara.get("planets", {}).items():
        evidence.append({
            "id": f"transit.{planet.lower()}",
            "type": "computed_transit",
            "planet": planet,
            "sign": row.get("sign"),
            "house_from_moon": row.get("house_from_moon"),
            "house_from_lagna": row.get("house_from_lagna"),
            "retrograde": row.get("retrograde"),
            "classical": gochara.get("classical_gochara", {}).get(planet),
        })

    for rule in gochara.get("rules", []):
        evidence.append({
            "id": f"rule.{rule.get('id')}",
            "type": "deterministic_rule",
            "rule_id": rule.get("id"),
            "active": rule.get("active"),
            "trigger": rule.get("trigger"),
            "source_status": rule.get("source_status"),
        })

    return {
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "library_version": INTERPRETATION_LIBRARY_VERSION,
        "mode": "deterministic_kb",
        "methodology": {
            "calculation_rule": "Planetary positions and rule activation come strictly from the canonical math engine.",
            "interpretation_rule": "Direct mapping to Content Knowledge Base. AI is not used for Gocharam generation.",
        },
        "matched_rules": matched_rules,
        "evidence": evidence,
    }
