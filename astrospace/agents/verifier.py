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
# category as a prohibited verdict or a dosha overclaim.
#
# Revised after independent review of the first version, which had two real
# false-positive sources:
#
# 1. A flat "any year past as_of" check flags the bundle's *own* dasha
#    period boundaries — the currently-running mahadasha always ends in the
#    future (e.g. "Saturn mahadasha 2011 -> 2030"), and the prompt tells the
#    model to cite exactly that. `_period_boundary_years()` pulls the real
#    boundary years out of `bundle["dasha_relevance"]["chain"]` and excludes
#    them — a future year is only suspicious if it *isn't* one the bundle
#    itself handed the model.
# 2. `_FUTURE_PHRASE_RE` (removed) matched "will begin"/"upcoming" in
#    ordinary constructive closes, including ones explicitly *rejecting* a
#    future framing ("nothing about the upcoming years changes what already
#    happened in 2003"). Natural language has too many legitimate uses of
#    those words; the year check is the precise, well-grounded signal that
#    actually matches the reported bug (explicit invented years), so the
#    phrase heuristic is dropped rather than patched narrower and narrower.
_FUTURE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _period_boundary_years(bundle: dict) -> set[int]:
    years: set[int] = set()
    chain = (bundle.get("dasha_relevance") or {}).get("chain") or []
    for row in chain:
        for key in ("start", "end"):
            value = row.get(key)
            if isinstance(value, str) and value[:4].isdigit():
                years.add(int(value[:4]))
    return years


def _tense_conflict(text: str, as_of_year: int, safe_years: set[int]) -> bool:
    for match in _FUTURE_YEAR_RE.finditer(text):
        year = int(match.group(0))
        if year > as_of_year and year not in safe_years:
            return True
    return False


# A technical_basis[].source is allowed to name a bundle *section* directly
# (not every claim traces to a citation — a house placement is itself
# evidence) as long as that section actually exists in the bundle handed to
# the agent. Citation-shaped sources are checked against the bundle's real
# references/source_passages instead — see `_valid_sources`.
_BUNDLE_SECTION_NAMES = {
    "houses", "karakas", "vargas", "yogas", "doshas",
    "dasha_relevance", "gochara", "jaimini_karakas", "arudhas",
    "profile_facts",
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

    valid_sources = _valid_sources(bundle)
    for item in reading.technical_basis:
        if item.source not in valid_sources:
            violations.append(
                f"technical_basis source {item.source!r} does not resolve to the bundle's "
                "references, source_passages, or a known bundle section"
            )

    # Shared across every text-scanning check below — every field a model
    # can put free text into, not just the ones a first pass happened to
    # cover. Found by a second independent review: the first fix added
    # technical_basis and practical_actions but stopped there, leaving
    # acknowledgment, guidance.remedies (both practice and note), and
    # guidance.follow_up_questions completely unscanned by every check here
    # — including prohibited_verdict, so a death verdict placed in a remedy
    # note passed cleanly. That's CLAUDE.md non-negotiable #1 (no death/
    # longevity verdicts) and #4 (remedies never framed as fear leverage)
    # both landing in a field nothing was looking at.
    text_to_check = [reading.acknowledgment, reading.interpretation, reading.summary_and_assurance] + [
        item.reading for item in reading.technical_basis
    ] + list(reading.guidance.practical_actions) + list(reading.guidance.follow_up_questions) + [
        text for remedy in reading.guidance.remedies for text in (remedy.practice, remedy.note)
    ]

    for text in text_to_check:
        crossed = prohibited_verdict(text)
        if crossed:
            violations.append(f"prohibited verdict ({crossed}) in: {text!r}")
        dosha_crossed = dosha_overclaim_kind(text)
        if dosha_crossed:
            violations.append(f"dosha overclaim in: {text!r}")

    # "mixed" (both a retrospective and a future cue present in the same
    # question, e.g. "when did retirement happen, and what comes next?")
    # deliberately does not qualify here — only a pure retrospective
    # question triggers this; see intent.py's detect_tense() docstring for
    # why that split exists.
    if question_tense == "retrospective":
        profile_facts = bundle.get("profile_facts") or {}
        as_of = str(profile_facts.get("as_of") or "")
        as_of_year = int(as_of[:4]) if as_of[:4].isdigit() else 9999
        safe_years = _period_boundary_years(bundle)
        for text in text_to_check:
            if _tense_conflict(text, as_of_year, safe_years):
                violations.append(
                    "retrospective question answered with an invented future "
                    f"timeline: {text!r}"
                )

    return violations
