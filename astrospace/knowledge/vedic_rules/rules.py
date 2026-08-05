from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent


@lru_cache(maxsize=1)
def rules_catalog() -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    for filename, kind in (("yogas.json", "yoga"), ("doshas.json", "dosha")):
        payload = json.loads((BASE / filename).read_text())
        for rule_id, rule in payload["rules"].items():
            # classical_name mirrors "name" here so /rules and /rules/{id}
            # (raw catalog entries) and enrich_rule_result's computed
            # results (which set their own instance-specific "name") expose
            # the same field for "the general classical term" consistently.
            catalog[rule_id] = {**rule, "id": rule_id, "kind": kind, "classical_name": rule["name"]}
    return catalog


def get_rule(rule_id: str) -> dict[str, Any]:
    return rules_catalog().get(rule_id, {
        "id": rule_id,
        "name": rule_id.replace("_", " ").title(),
        "classical_name": rule_id.replace("_", " ").title(),
        "status": "needs_review",
        "implementation": "unknown",
        "source_refs": [],
        "practitioner_explanation": "",
        "lay_explanation": "",
        "strength_rubric": "",
        "caveats": [],
        "notes": ["Rule metadata missing from AstroSpace Vedic rules KB."],
    })


def enrich_rule_result(rule_id: str, result: dict[str, Any]) -> dict[str, Any]:
    """Merge KB metadata into a computed yoga/dosha result.

    ``classical_name`` is deliberately distinct from any ``name`` the caller
    already set on ``result``: a grouped rule like Raja Yoga or Neecha Bhanga
    reports a per-instance name (e.g. "Raja Yoga: Sun-Moon"), while
    ``classical_name`` is always the general classical term from the KB — the
    thing a "Learn this Yoga" sheet should title itself with (US-PR-014).
    """
    rule = get_rule(rule_id)
    status = rule.get("status", "needs_review")
    return {
        **result,
        "rule_id": rule_id,
        "classical_name": rule.get("classical_name", rule_id.replace("_", " ").title()),
        "source_status": status,
        "implementation": rule.get("implementation", "unknown"),
        "source_refs": rule.get("source_refs", []),
        "practitioner_explanation": rule.get("practitioner_explanation", ""),
        "lay_explanation": rule.get("lay_explanation", ""),
        "strength_rubric": rule.get("strength_rubric", ""),
        "caveats": rule.get("caveats", []),
        "verified": status == "verified_common",
        "notes": [*rule.get("notes", []), *result.get("notes", [])],
    }
