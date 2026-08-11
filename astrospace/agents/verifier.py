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

# A reading may name a varga either way; both satisfy the coverage check.
_VARGA_CLASSICAL_NAMES = {
    "D1": "rashi", "D2": "hora", "D3": "drekkana", "D4": "chaturthamsha",
    "D7": "saptamsa", "D9": "navamsa", "D10": "dashamsha", "D12": "dwadashamsha",
    "D16": "shodashamsha", "D20": "vimshamsha", "D24": "chaturvimshamsha",
    "D27": "bhamsha", "D30": "trimshamsha", "D40": "khavedamsha",
    "D45": "akshavedamsha", "D60": "shashtyamsha",
}

_KARAKA_LABELS = {
    "AK": "Atmakaraka", "AmK": "Amatyakaraka", "BK": "Bhratrikaraka",
    "MK": "Matrikaraka", "PK": "Putrakaraka", "PiK": "Pitrikaraka",
    "GK": "Gnatikaraka", "DK": "Darakaraka",
}


def _domain_spec(bundle: dict):
    """The taxonomy spec for the bundle's domain, or None.

    Imported lazily and failing soft on purpose: a taxonomy lookup problem
    must never be able to fail a reading that is otherwise fine, since every
    check built on it is quality-severity by design.
    """
    domain = bundle.get("domain")
    if not domain:
        return None
    try:
        from ..context.taxonomy import get_domain
        return get_domain(domain)
    except Exception:
        return None

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
#
# 3. (2026-08-10, independent review of the persona-depth/timing-precision
#    task) Same false-positive shape as #1, new source: once
#    `assembler.py`'s `_gochara_for_domain()` started carrying real
#    `start_date`/`end_date` per active transit rule, and `domain_agent.py`
#    started requiring the model to cite them for timing-shaped questions,
#    a genuinely bundle-grounded gochara year (e.g. "this transit runs
#    through 2027") could land in a retrospective-tense answer's
#    constructive close and get flagged as invented — it was never in
#    `dasha_relevance.chain`, the only section this function read from.
#    `_period_boundary_years()` now also pulls from
#    `gochara.active_rules[].start_date/end_date`, on the same principle as
#    #1: a future year is only suspicious if it isn't one the bundle itself
#    handed the model.
_FUTURE_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _period_boundary_years(bundle: dict) -> set[int]:
    years: set[int] = set()
    chain = (bundle.get("dasha_relevance") or {}).get("chain") or []
    for row in chain:
        for key in ("start", "end"):
            value = row.get(key)
            if isinstance(value, str) and value[:4].isdigit():
                years.add(int(value[:4]))
    gochara_rules = (bundle.get("gochara") or {}).get("active_rules") or []
    for row in gochara_rules:
        for key in ("start_date", "end_date"):
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


class Violation(str):
    """A violation that also knows how bad it is.

    A `str` subclass on purpose: every existing consumer treats violations as
    strings (`"; ".join(...)`, `== []`, formatting into the repair prompt) and
    keeps working untouched. Severity is additive.

    Two severities, and the distinction is about what happens when a repair
    attempt fails to clear it:

    - "safety"  — the reading is DISCARDED. A death verdict, an invented
                  citation, a fabricated timeline. Shipping it is worse than
                  shipping nothing, which is the current behaviour for every
                  violation and stays exactly as it is.
    - "quality" — the reading SHIPS, with the shortfall recorded. "You never
                  addressed the D10" is worth one repair attempt; it is not
                  worth throwing away an otherwise good consultation and
                  handing the reader an error instead. Before this split
                  existed, adding any coverage check would have meant exactly
                  that.
    """

    severity: str = "safety"

    def __new__(cls, text: str, severity: str = "safety"):
        obj = super().__new__(cls, text)
        obj.severity = severity
        return obj


def safety_violations(violations: list[str]) -> list[str]:
    """The subset that must never ship. A plain `str` in the list counts as
    safety, so anything constructed outside this module fails closed."""
    return [v for v in violations if getattr(v, "severity", "safety") == "safety"]


def quality_violations(violations: list[str]) -> list[str]:
    return [v for v in violations if getattr(v, "severity", "safety") == "quality"]


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


def verify_coverage(reading: StructuredReading, bundle: dict) -> list[Violation]:
    """The domain's own primary evidence must be addressed, or dismissed.

    A real career reading (2026-08-11) opened with the dasha chain, the 6th
    lord, two nakshatras and an argala — and never once mentioned the D10,
    which the taxonomy marks `tier: primary` for that domain and which the
    bundle carried the whole time. Also absent: A10, the career arudha, and
    the Amatyakaraka. The prose was excellent; the *selection* silently
    dropped the most career-specific chart available. A marriage reading that
    skipped D9 would be the same defect.

    Nothing enforced it, because the taxonomy declares what is primary and
    only the prompt asked for it — and a prompt rule is advisory. Rule 11's
    confirmation question was in the prompt too, and that reading skipped it.

    Naming a factor and dismissing it satisfies this: "the D10 adds nothing
    beyond what the D1 already shows" is a legitimate reading decision and a
    much better answer than silence. Only saying nothing at all fails.

    Quality severity throughout: a missed varga is worth one repair attempt,
    never worth discarding the consultation and handing the reader an error.
    """
    spec = _domain_spec(bundle)
    if spec is None:
        return []

    text_to_check = [
        reading.acknowledgment, reading.interpretation, reading.summary_and_assurance,
    ] + [item.reading for item in reading.technical_basis]

    haystack = " ".join(
        text_to_check
        + [item.factor for item in reading.technical_basis]
        + [item.source for item in reading.technical_basis]
    ).casefold()

    out: list[Violation] = []

    for varga in getattr(spec, "vargas_primary", ()) or ():
        # "D10" and the classical name both count — a reading is free to say
        # "dashamsha" and never write the code.
        names = {varga.casefold(), _VARGA_CLASSICAL_NAMES.get(varga, "").casefold()}
        if not any(n and n in haystack for n in names):
            out.append(Violation(
                f"the domain's primary divisional chart {varga} is never addressed — "
                f"cite it or say explicitly why it adds nothing here",
                "quality",
            ))

    for code in getattr(spec, "karakas_jaimini", ()) or ():
        row = (bundle.get("jaimini_karakas") or {}).get(code)
        if not row:
            continue
        label = _KARAKA_LABELS.get(code, code)
        if not any(t in haystack for t in (code.casefold(), label.casefold())):
            out.append(Violation(
                f"the domain's Jaimini karaka {code} ({label}, {row.get('planet')}) "
                "is never addressed",
                "quality",
            ))

    return out
