"""Governed Profile Context Ledger vocabulary and deterministic projection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
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


# ── Logical preflight ────────────────────────────────────────────────────
#
# Phase 2 of the Profile Context Ledger (docs/profile_context_ledger_
# architecture_2026-08-14.md): logical constraints from reader-confirmed
# life facts must be established BEFORE astrological reasoning, the same
# discipline `detect_tense()`/the retrospective-timeline verifier invariant
# already apply to tense alone (astrospace/agents/intent.py,
# astrospace/agents/verifier.py). This is a superset of that mechanism, not
# a second one — see docs/ask_context_engine_multi_agent_architecture_
# 2026-08-07.md's "Update 2026-08-09" for the incident this generalizes.
#
# Deterministic and rule-based throughout, same style as `logical_constraints`
# above: no model call, no inference, one `if key == X and value == Y` row
# per governed fact. Adding a new blocked/required frame means adding a row
# here, never teaching the model to derive one itself.

@dataclass(frozen=True)
class LogicalPreflight:
    """Server-computed constraints the domain agent's prompt receives BEFORE
    the astrological context bundle (domain_agent.py's `_BASE_SYSTEM`), and
    the verifier checks the answer against afterward (verifier.py's
    `verify()`). Every field is a tuple of short, stable string codes/notes
    — never free text the model could echo back as if it were its own
    reasoning."""
    blocked_frames: tuple[str, ...] = ()
    required_frames: tuple[str, ...] = ()
    context_notes: tuple[str, ...] = ()
    missing_or_conflicting_context: tuple[str, ...] = ()
    applicable_fact_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "blocked_frames": list(self.blocked_frames),
            "required_frames": list(self.required_frames),
            "context_notes": list(self.context_notes),
            "missing_or_conflicting_context": list(self.missing_or_conflicting_context),
            "applicable_fact_refs": list(self.applicable_fact_refs),
        }


# Conservative, narrow patterns — false negatives (missing a real mismatch)
# are far cheaper here than false positives (blocking a legitimate late-life
# first job or a plausible pregnancy question). Age thresholds are wide
# margins around clear biological/social implausibility, not clinical
# fertility cutoffs — this is a plausibility guard, not a medical claim.
_FIRST_JOB_RE = re.compile(
    r"\bfirst job\b|\bfirst career\b|\bstart(?:ing)? my career\b|\bentry.level\b|"
    r"\bland my first\b|\bbegin(?:ning)? my career\b",
    re.IGNORECASE,
)
_PREGNANCY_RE = re.compile(
    r"\b(?:have|having|conceive|conceiving)\b.{0,20}\b(?:baby|babies|child|children|kids)\b|"
    r"\bpregnan\w*\b|\bstart(?:ing)? a family\b",
    re.IGNORECASE,
)
_FIRST_MARRIAGE_RE = re.compile(
    r"\bwhen will i (?:get married|marry)\b|\bfind (?:my )?(?:husband|wife|spouse)\b|"
    r"\bwill i (?:ever )?(?:get married|marry)\b",
    re.IGNORECASE,
)
_WILL_HAVE_CHILDREN_RE = re.compile(
    r"\bwill i (?:ever )?have (?:a |any )?(?:child|children|kids|baby)\b|"
    r"\bam i going to have (?:a |any )?(?:child|children|kids|baby)\b|"
    r"\bwill i become a parent\b",
    re.IGNORECASE,
)

_IMPLAUSIBLE_FIRST_JOB_AGE = 70
_IMPLAUSIBLE_PREGNANCY_AGE = 55


def _active_fact(
    projection_facts: list[dict], key: str,
    contradicted_keys: frozenset[str] = frozenset(),
) -> dict | None:
    # A key with more than one simultaneously-active value (the reader has
    # an unresolved `married` AND `single` fact, say) must never be picked
    # from arbitrarily — whichever happened to be first in `projection_facts`
    # would silently become policy, driven by DB insertion order rather than
    # any real resolution. `contradicted_keys` (from the projection's own
    # `contradictions` list, the same list that already drives its
    # `context_confirmation_needed` status) makes this key inert here: no
    # blocked/required frame, no ref, until the reader resolves it.
    if key in contradicted_keys:
        return None
    for fact in projection_facts:
        if fact.get("key") == key and fact.get("status") == "active":
            return fact
    return None


def build_logical_preflight(
    *, profile_facts: dict, projection_facts: list[dict],
    tense: str, question: str, domain: str,
    contradictions: tuple[str, ...] = (),
) -> LogicalPreflight:
    """`profile_facts` is the assembler's own deterministic block
    (age_years/birth_year/as_of — astrospace/context/assembler.py's
    `_profile_facts`). `projection_facts` is the frozen ledger projection's
    `facts` list (each already carrying a `ref: "profile_fact:<id>@<rev>"`
    string) for THIS profile, already domain-filtered and current-as-of by
    the caller — see `FrozenProfileContextProjection` in
    `astrospace/db/crud_profile_context.py`. This function does no I/O and
    reads no mutable state; called once per Ask turn against an already-
    frozen snapshot.

    `contradictions` is the projection's own `contradictions` field (fact
    keys with more than one simultaneously-active value) — kept as a
    separate explicit parameter rather than re-derived from
    `projection_facts` so this stays the same one contradiction check the
    projection builder already performs, not a second one that could drift
    out of sync with it."""
    blocked: list[str] = []
    required: list[str] = []
    notes: list[str] = []
    missing_or_conflicting: list[str] = []
    refs: list[str] = []
    contradicted_keys = frozenset(contradictions)
    for key in sorted(contradicted_keys):
        missing_or_conflicting.append(
            f"The ledger has more than one active value for {key!r} — an unresolved "
            "contradiction. No blocked or required framing is derived from it until the "
            "reader confirms a single value."
        )

    employment = _active_fact(projection_facts, "employment_status", contradicted_keys)
    if employment and employment["value"].get("code") == "retired" and domain in ("career", "wealth"):
        blocked.append("future_first_career_inception")
        required.append("retrospective_or_legacy_or_purpose_career_framing")
        notes.append(
            "The reader is retired. Treat career questions as retrospective, legacy, "
            "consulting, purpose, or post-retirement activity unless re-employment is explicit "
            "in the question itself."
        )
        refs.append(employment["ref"])

    relationship = _active_fact(projection_facts, "relationship_status", contradicted_keys)
    if relationship and relationship["value"].get("code") == "married" and domain == "marriage":
        if tense != "retrospective":
            blocked.append("first_marriage_framing")
            notes.append(
                "The reader is married. Do not frame future relationship timing as a first "
                "marriage — answer about their existing marriage, remarriage-shaped questions "
                "only if the question itself raises that, or explicitly historical timing."
            )
        refs.append(relationship["ref"])

    children = _active_fact(projection_facts, "has_children", contradicted_keys)
    if children and children["value"].get("value") is True and domain in ("children", "wealth", "marriage"):
        required.append("existing_children_context")
        notes.append(
            "The reader has children. Interpret relevant fifth-house periods through their "
            "existing children, caregiving, or creative legacy where the question invites it — "
            "do not frame the chart as pointing toward becoming a parent for the first time."
        )
        refs.append(children["ref"])
        if _WILL_HAVE_CHILDREN_RE.search(question or ""):
            blocked.append("future_first_child_framing")
            notes.append(
                "The reader already has children. Do not answer 'will I have children' as if "
                "asking whether they will become a parent for the first time — the confirmed fact "
                "above already answers that; if the question is really about an additional child, "
                "acknowledge the existing one(s) first."
            )
            missing_or_conflicting.append(
                "The question asks whether the reader will have children, but the ledger has an "
                "active confirmed has_children=true fact."
            )

    health = _active_fact(projection_facts, "current_health_constraint", contradicted_keys)
    if health and domain == "health":
        blocked.append("medical_prognosis_or_recovery_guarantee")
        notes.append(
            "The reader has disclosed a current health constraint. Do not diagnose, prescribe, "
            "predict a medical outcome, or guarantee recovery — describe supportive astrological "
            "tendencies only, and route anything resembling a medical judgment to a qualified "
            "professional."
        )
        refs.append(health["ref"])

    age_years = profile_facts.get("age_years")
    if isinstance(age_years, (int, float)):
        if _FIRST_JOB_RE.search(question or "") and age_years >= _IMPLAUSIBLE_FIRST_JOB_AGE:
            blocked.append("first_job_entry_framing")
            notes.append(
                f"The reader is approximately {age_years:.0f} years old. A literal first-ever "
                "job at this age is biologically/socially implausible — if the question is "
                "really about a career change or new venture, answer that instead."
            )
        if _PREGNANCY_RE.search(question or "") and age_years >= _IMPLAUSIBLE_PREGNANCY_AGE:
            blocked.append("biological_pregnancy_framing")
            notes.append(
                f"The reader is approximately {age_years:.0f} years old, well past the age "
                "range this question's biological-pregnancy framing would be plausible for. "
                "Do not predict a pregnancy; if children/family legacy is the real question, "
                "answer that instead."
            )

    # A married reader asking a first-marriage-shaped question, or a
    # disputed/contradictory fact, is exactly the case Phase 1's ledger
    # already refuses to resolve silently (see get_profile_context's own
    # `context_confirmation_needed` status) — surfaced here too, since the
    # preflight is a second consumer of the same projection.
    if relationship and relationship["value"].get("code") == "married" and _FIRST_MARRIAGE_RE.search(question or ""):
        missing_or_conflicting.append(
            "The question asks about a first marriage, but the ledger has an active "
            "confirmed married relationship_status fact."
        )

    return LogicalPreflight(
        blocked_frames=tuple(dict.fromkeys(blocked)),
        required_frames=tuple(dict.fromkeys(required)),
        context_notes=tuple(dict.fromkeys(notes)),
        missing_or_conflicting_context=tuple(dict.fromkeys(missing_or_conflicting)),
        applicable_fact_refs=tuple(dict.fromkeys(refs)),
    )
