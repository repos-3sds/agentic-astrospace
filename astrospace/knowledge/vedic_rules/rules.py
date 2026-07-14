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
            catalog[rule_id] = {**rule, "id": rule_id, "kind": kind}
    return catalog


def get_rule(rule_id: str) -> dict[str, Any]:
    return rules_catalog().get(rule_id, {
        "id": rule_id,
        "name": rule_id.replace("_", " ").title(),
        "status": "needs_review",
        "implementation": "unknown",
        "source_refs": [],
        "notes": ["Rule metadata missing from AstroSpace Vedic rules KB."],
    })


def enrich_rule_result(rule_id: str, result: dict[str, Any]) -> dict[str, Any]:
    rule = get_rule(rule_id)
    status = rule.get("status", "needs_review")
    return {
        **result,
        "rule_id": rule_id,
        "source_status": status,
        "implementation": rule.get("implementation", "unknown"),
        "source_refs": rule.get("source_refs", []),
        "verified": status == "verified_common",
        "notes": [*rule.get("notes", []), *result.get("notes", [])],
    }
