"""Deterministic verifier — the only gate between a generated `StructuredReading`
and persistence. No second model call: regex and set-membership checks only,
per the agreed v1 scope (an LLM-based verifier is explicitly deferred until
this proves insufficient).

Returns a list of violation strings; empty means the reading passes. The
orchestrator (`astrospace/agents/orchestrator.py`) is what enforces "no DB
write before a pass" and the one-repair-attempt cap — this module only
judges, it never retries or persists.
"""
from __future__ import annotations

import re

from .safety import dosha_overclaim_kind, prohibited_verdict
from .schema import StructuredReading

# Candidate invariant from the tense/life-stage finding
# (docs/ask_context_engine_multi_agent_architecture_2026-08-07.md, "Update
# 2026-08-09" requirement 4): a retrospective question ("when did X start")
# answered with an invented future timeline is a trust violation, same
# category as a prohibited verdict or a dosha overclaim. Deterministic and
# narrow by design — a 4-digit year past `as_of`, or an explicit
# future-tense construction, in a reading whose *question* was retrospective.
# This does not (and cannot, without a second model call) catch every
# tense mismatch; it catches the exact repro shape that motivated it.
_FUTURE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_FUTURE_PHRASE_RE = re.compile(
    r"\b(?:will (?:start|begin|happen|occur|arrive)|is coming|upcoming|"
    r"in the (?:coming|next) \d+)\b"
)


def _tense_conflict(text: str, as_of_year: int) -> bool:
    for match in _FUTURE_YEAR_RE.finditer(text):
        if int(match.group(0)) > as_of_year:
            return True
    return bool(_FUTURE_PHRASE_RE.search(text.casefold()))


# A technical_basis[].source is allowed to name a bundle *section* directly
# (not every claim traces to a citation — a house placement is itself
# evidence) as long as that section actually exists in the bundle handed to
# the agent. Citation-shaped sources are checked against the bundle's real
# references/source_passages instead — see `_valid_sources`.
_BUNDLE_SECTION_NAMES = {
    "houses", "karakas", "vargas", "yogas", "doshas",
    "dasha_relevance", "gochara", "jaimini_karakas", "arudhas",
}


def _valid_sources(bundle: dict) -> set[str]:
    ref_ids = {ref["ref_id"] for ref in bundle.get("references", []) if ref.get("ref_id")}
    chunk_ids = {p["chunk_id"] for p in bundle.get("source_passages", []) if p.get("chunk_id")}
    return _BUNDLE_SECTION_NAMES | ref_ids | chunk_ids


def verify(reading: StructuredReading, bundle: dict, routed_domain: str,
          question_tense: str = "unspecified") -> list[str]:
    violations: list[str] = []

    if bundle.get("domain") and bundle["domain"] != routed_domain:
        violations.append(
            f"bundle domain {bundle.get('domain')!r} does not match routed domain {routed_domain!r}"
        )

    if question_tense == "retrospective":
        as_of = (bundle.get("profile_facts") or {}).get("as_of", "")
        as_of_year = int(as_of[:4]) if as_of[:4].isdigit() else 9999
        for text in (reading.interpretation, reading.summary_and_assurance):
            if _tense_conflict(text, as_of_year):
                violations.append(
                    "retrospective question answered with an invented future "
                    f"timeline: {text!r}"
                )

    valid_sources = _valid_sources(bundle)
    for item in reading.technical_basis:
        if item.source not in valid_sources:
            violations.append(
                f"technical_basis source {item.source!r} does not resolve to the bundle's "
                "references, source_passages, or a known bundle section"
            )

    text_to_check = [reading.interpretation, reading.summary_and_assurance] + [
        item.reading for item in reading.technical_basis
    ]
    for text in text_to_check:
        crossed = prohibited_verdict(text)
        if crossed:
            violations.append(f"prohibited verdict ({crossed}) in: {text!r}")
        dosha_crossed = dosha_overclaim_kind(text)
        if dosha_crossed:
            violations.append(f"dosha overclaim in: {text!r}")

    return violations
