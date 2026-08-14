"""Governed Profile Context Ledger vocabulary and deterministic projection."""

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class FactSpec:
    category: str
    key: str
    sensitivity: str
    retention: str
    domains: frozenset[str]
    value_kind: str = "code"
    allowed_codes: frozenset[str] = frozenset()


def _spec(category: str, key: str, sensitivity: str, retention: str,
          domains: set[str], *, codes: set[str] | None = None,
          value_kind: str = "code") -> FactSpec:
    return FactSpec(
        category, key, sensitivity, retention, frozenset(domains), value_kind,
        frozenset(codes or set()),
    )


FACT_REGISTRY: dict[str, FactSpec] = {
    spec.key: spec for spec in (
        _spec("demographics", "preferred_name", "personal", "until_removed",
              set(), value_kind="text"),
        _spec("demographics", "pronouns", "personal", "until_removed", set(),
              value_kind="text"),
        _spec("demographics", "residence_country", "personal", "until_removed",
              {"foreign", "career", "family_property"}, value_kind="text"),
        _spec("life_stage", "employment_status", "personal", "until_removed",
              {"career", "wealth"},
              codes={"employed", "self_employed", "unemployed", "student", "retired"}),
        _spec("life_stage", "education_stage", "personal", "until_removed",
              {"education", "career"},
              codes={"school", "undergraduate", "postgraduate", "training", "completed"}),
        _spec("relationship", "relationship_status", "sensitive", "until_removed",
              {"marriage"},
              codes={"single", "partnered", "engaged", "married", "separated", "divorced", "widowed"}),
        _spec("relationship", "marriage_date", "sensitive", "until_removed",
              {"marriage"}, value_kind="date"),
        _spec("family", "has_children", "sensitive", "until_removed",
              {"children", "wealth"}, value_kind="boolean"),
        _spec("family", "child_count", "sensitive", "until_removed",
              {"children", "wealth"}, value_kind="integer"),
        _spec("family", "caregiving_role", "sensitive", "until_removed",
              {"children", "health", "career"}, value_kind="text"),
        _spec("career", "occupation", "personal", "until_removed",
              {"career", "wealth"}, value_kind="text"),
        _spec("career", "industry", "personal", "until_removed",
              {"career"}, value_kind="text"),
        _spec("health_context", "current_health_constraint", "highly_sensitive", "30_days",
              {"health"}, value_kind="text"),
        _spec("health_context", "recovery_period", "highly_sensitive", "30_days",
              {"health"}, value_kind="text"),
        _spec("location_history", "moved_to", "personal", "until_removed",
              {"foreign", "family_property"}, value_kind="text"),
        _spec("goals", "looking_for_work", "personal", "target_date",
              {"career", "wealth"}, value_kind="boolean"),
        _spec("goals", "planning_marriage", "sensitive", "target_date",
              {"marriage"}, value_kind="boolean"),
        _spec("goals", "study_goal", "personal", "target_date",
              {"education"}, value_kind="text"),
        _spec("preferences", "remedy_constraints", "sensitive", "until_removed",
              {"spirituality"}, value_kind="text"),
        _spec("preferences", "consultation_style", "personal", "until_removed",
              set(), codes={"guided", "balanced", "practitioner"}),
    )
}


def validate_fact_value(key: str, value: dict[str, Any]) -> FactSpec:
    spec = FACT_REGISTRY.get(key)
    if not spec:
        raise ValueError("Unsupported profile context key")
    if not isinstance(value, dict) or set(value) - {"code", "label", "text", "date", "value"}:
        raise ValueError("Fact value has unsupported fields")
    label = value.get("label")
    if label is not None and (not isinstance(label, str) or len(label.strip()) > 80):
        raise ValueError("Fact label must not exceed 80 characters")
    kind = spec.value_kind
    if kind == "code":
        code = value.get("code")
        if not isinstance(code, str) or (spec.allowed_codes and code not in spec.allowed_codes):
            raise ValueError("Fact code is not allowed")
    elif kind == "text":
        text = value.get("text")
        if not isinstance(text, str) or not text.strip() or len(text.strip()) > 240:
            raise ValueError("Fact text must be between 1 and 240 characters")
    elif kind == "date":
        try:
            date.fromisoformat(str(value.get("date")))
        except ValueError as exc:
            raise ValueError("Fact date must be ISO-8601") from exc
    elif kind == "boolean" and not isinstance(value.get("value"), bool):
        raise ValueError("Fact value must be boolean")
    elif kind == "integer":
        number = value.get("value")
        if isinstance(number, bool) or not isinstance(number, int) or number < 0 or number > 30:
            raise ValueError("Fact value must be an integer between 0 and 30")
    return spec


def fact_is_current(fact, as_of: date) -> bool:
    return (
        fact.status == "active"
        and (fact.valid_from is None or fact.valid_from <= as_of)
        and (fact.valid_to is None or fact.valid_to >= as_of)
    )


def relevant_to_domain(spec: FactSpec, domain: str | None) -> bool:
    return not domain or not spec.domains or domain in spec.domains


def logical_constraints(facts: list[dict]) -> list[str]:
    constraints: list[str] = []
    for fact in facts:
        key, value = fact["key"], fact["value"]
        if key == "employment_status" and value.get("code") == "retired":
            constraints.append(
                "The reader is retired. Treat career questions as retrospective, legacy, "
                "consulting, purpose, or post-retirement activity unless re-employment is explicit."
            )
        elif key == "relationship_status" and value.get("code") == "married":
            constraints.append(
                "The reader is married. Do not frame future relationship timing as a first marriage."
            )
        elif key == "has_children" and value.get("value") is True:
            constraints.append(
                "The reader has children. Distinguish existing children's milestones from future parenthood."
            )
        elif key == "current_health_constraint":
            constraints.append(
                "A reader-reported health constraint exists. Do not diagnose, prescribe, or guarantee recovery."
            )
    return constraints
