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

from .safety import dosha_overclaim_kind, prohibited_verdict
from .schema import StructuredReading

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


def verify(reading: StructuredReading, bundle: dict, routed_domain: str) -> list[str]:
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
