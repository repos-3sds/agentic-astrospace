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

from .safety import _negation_precedes, _normalize, dosha_overclaim_kind, prohibited_verdict
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
# references/source_passages instead — see `valid_sources`.
_BUNDLE_SECTION_NAMES = {
    "houses", "karakas", "vargas", "yogas", "doshas",
    "dasha_relevance", "gochara", "jaimini_karakas", "arudhas",
    "profile_facts", "profile_context",
    # `retrospect` and `timeline` are real top-level bundle sections
    # (assembler.py's `_retrospect()`/`build_timeline()`) that
    # `domain_agent.py`'s own prompt explicitly tells the model to read
    # dated boundaries from (rules 10 and 13) — they were simply missing
    # here, so a technical_basis item citing either failed verification
    # even though the underlying claim was legitimately bundle-grounded.
    "retrospect", "timeline",
}


def valid_sources(bundle: dict) -> set[str]:
    """Every source a `technical_basis` item may cite — one deterministic
    evidence-resolution boundary shared by KB citations and Profile Context
    Ledger facts (docs/profile_context_ledger_architecture_2026-08-14.md's
    "Unified evidence resolution against the frozen request bundle").

    Since 2026-08-18 the generation side consumes it too:
    `astrospace/agents/schema.py`'s `reading_tool_schema()` compiles this
    exact set into the tool's `source` enum, so the model cannot emit a
    citation this function would then reject. Public rather than private
    for that reason — one set, two consumers. Never fork a second copy of
    this logic for the schema; a constraint that disagrees with its checker
    is worse than no constraint, because it fails silently in whichever
    direction is looser.

    `profile_fact:<id>@<revision>` refs are checked against the FROZEN
    bundle's own `profile_context.facts[].ref` values only — never a live
    database re-read. A ref that is deleted, superseded, expired outside
    `as_of`, or belongs to a different profile is simply absent from that
    list (it was never included when the projection was built, see
    `astrospace/db/crud_profile_context.py`'s `build_profile_context_projection`),
    so citing it fails this membership check the same way an invented KB
    citation already does — no special-case detection needed."""
    ref_ids = {ref["ref_id"] for ref in bundle.get("references", []) if ref.get("ref_id")}
    chunk_ids = {p["chunk_id"] for p in bundle.get("source_passages", []) if p.get("chunk_id")}
    fact_refs = {
        f["ref"] for f in (bundle.get("profile_context") or {}).get("facts", [])
        if f.get("ref")
    }
    return _BUNDLE_SECTION_NAMES | ref_ids | chunk_ids | fact_refs


class Violation(str):
    """A violation that also knows how bad it is, and — since D2 — which
    `StructuredReading` field it lives in.

    A `str` subclass on purpose: every existing consumer treats violations as
    strings (`"; ".join(...)`, `== []`, formatting into the repair prompt) and
    keeps working untouched. Severity and field are both additive.

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

    `field` names the top-level `StructuredReading` field a fix belongs in
    (`"acknowledgment"`, `"technical_basis"`, `"interpretation"`,
    `"summary_and_assurance"`, `"guidance"`), or `None` when a violation
    isn't attributable to one field — a bundle/routed-domain mismatch, for
    instance, is an orchestration bug, not something regenerating any field
    of this reading would fix. `None` is also the safe default for a
    violation constructed without a field: the orchestrator's D2 repair
    path (`_agent_run_and_verify`) falls back to whole-object repair
    whenever any surviving violation's field is unknown, exactly the
    behaviour that existed before field attribution — this is additive,
    not a narrowing of what gets fixed.
    """

    severity: str = "safety"
    field: str | None = None

    def __new__(cls, text: str, severity: str = "safety", field: str | None = None):
        obj = super().__new__(cls, text)
        obj.severity = severity
        obj.field = field
        return obj


def safety_violations(violations: list[str]) -> list[str]:
    """The subset that must never ship. A plain `str` in the list counts as
    safety, so anything constructed outside this module fails closed."""
    return [v for v in violations if getattr(v, "severity", "safety") == "safety"]


def quality_violations(violations: list[str]) -> list[str]:
    return [v for v in violations if getattr(v, "severity", "safety") == "quality"]


def violation_fields(violations: list[str]) -> set[str | None]:
    """The set of `StructuredReading` top-level fields a violation list
    touches — `None` in the set means at least one violation isn't
    attributable to a single field, which the orchestrator's repair path
    reads as "fall back to whole-object repair, we don't know what's safe
    to leave alone." A plain `str` (constructed outside this module, or a
    violation predating field attribution) counts as unattributed for the
    same fail-closed reason `safety_violations` treats a plain `str` as
    safety-severity."""
    return {getattr(v, "field", None) for v in violations}


# ── Profile Context Ledger — logical preflight enforcement ────────────────
#
# Deterministic, regex-based, same discipline as every check above: no
# second model call, and every pattern here corresponds 1:1 to a
# `blocked_frames` code `astrospace/context/profile_context.py`'s
# `build_logical_preflight()` can emit. Adding a new blocked frame means
# adding both a row in that function AND a row here — the two are meant to
# be read together, not duplicated logic, since the preflight decides
# *when* a frame applies and this only detects whether the model's own
# text actually used it.
#
# Negation-aware, using the SAME shared check as safety.py's wealth/
# children/personality/health-outcome overclaim patterns
# (`_negation_precedes`/`_normalize`, imported above) — not a second
# heuristic. Round-1 of this file shipped without it on the (wrong)
# assumption these patterns were as clearly-positive as the marriage
# dosha-overclaim patterns that deliberately skip the check; in fact these
# are exactly the reassurance shape the negation check exists for — "This
# does not mean you will get married in this period" and "I cannot promise
# you will recover" both contain the bad phrase as a literal substring of a
# safe, hedged sentence, and a bare `.search()` rejected both, discarding a
# careful answer the agent is explicitly asked to produce. Safety severity
# throughout: a genuinely unhedged blocked frame is exactly the class of
# violation `safety_violations()` must never let ship, same as a prohibited
# verdict — the negation check only prevents flagging the sentences that
# exist specifically to rule the frame out.
_BLOCKED_FRAME_PATTERNS: dict[str, re.Pattern] = {
    "future_first_career_inception": re.compile(
        r"\byour career will begin\b|\byour career (?:is going to|will) start\b|"
        r"\bstart(?:ing)? your career\b|\bbegin(?:ning)? your career\b|"
        r"\byour first job\b|\bentering the workforce\b|"
        r"\byou will (?:begin|start) working\b",
        re.IGNORECASE,
    ),
    "first_marriage_framing": re.compile(
        r"\byou will (?:get married|marry)\b|\byour (?:future|upcoming) (?:marriage|wedding)\b|"
        r"\bfind (?:your |a )?(?:future )?(?:husband|wife|spouse)\b",
        re.IGNORECASE,
    ),
    "medical_prognosis_or_recovery_guarantee": re.compile(
        r"\byou will (?:recover|heal|be cured|make a full recovery)\b|"
        r"\bfull recovery is (?:certain|guaranteed|assured)\b|"
        r"\byour (?:illness|condition|surgery|recovery) will\b",
        re.IGNORECASE,
    ),
    "biological_pregnancy_framing": re.compile(
        r"\byou will (?:conceive|become pregnant|have a baby|have a child)\b|"
        r"\byour (?:future |upcoming )?pregnancy\b",
        re.IGNORECASE,
    ),
    "first_job_entry_framing": re.compile(
        r"\byour first job\b|\bentering the workforce\b|\bstart(?:ing)? your first career\b",
        re.IGNORECASE,
    ),
    "future_first_child_framing": re.compile(
        r"\byou will (?:have|become the parent of) (?:a |your first )?(?:child|baby|kids)\b|"
        r"\byou (?:will|are going to) become a parent\b",
        re.IGNORECASE,
    ),
}

# "Your chart reveals/shows..." immediately paired with language about a
# fact the reader already disclosed is exactly the discovery-not-report
# failure the prompt (domain_agent.py's `_format_profile_context_block`)
# explicitly forbids. A generous character window around the discovery
# phrase, not a same-sentence requirement — "Your chart reveals real
# strength here. As you know, since you're retired, this next phase..." is
# fine (the discovery phrase governs "real strength", not the retirement
# fact); "Your chart reveals that you are retired" is not, and both need
# the same window to be caught by the same check.
_DISCOVERY_PHRASE_RE = re.compile(
    r"\byour chart (?:reveals?|shows?|indicates?|tells? (?:us|me))\b|"
    r"\bthe (?:chart|stars|planets) (?:reveals?|shows?|indicates?)\b",
    re.IGNORECASE,
)

_FACT_KEY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "employment_status": ("retir", "employ", "career status", "job status"),
    "relationship_status": ("marri", "spouse", "divorce", "separat"),
    "has_children": ("child", "kids", " a parent", "parenthood"),
    # "illness"/"recovering" bare (not just "your illness"/"your recovery")
    # — found by D2's field-scoped repair: "recovering from an illness"
    # phrasing didn't match either possessive form, so this check silently
    # never fired for it. Whole-object repair had masked the gap, since a
    # DIFFERENT (coverage) violation on the same reading also triggered a
    # repair that happened to fix the discovery text as a side effect —
    # see tests/test_profile_context_ledger_phase2.py's
    # test_never_presents_disclosed_condition_as_a_chart_discovery.
    "current_health_constraint": ("health condition", "your condition",
                                  "your recovery", "your illness", "illness",
                                  "recovering", "diagnos"),
    "recovery_period": ("your recovery", "recovering", "your condition"),
}


def _blocked_frame_violations(reading: StructuredReading, bundle: dict) -> list[Violation]:
    preflight = ((bundle.get("profile_context") or {}).get("preflight") or {})
    blocked = preflight.get("blocked_frames") or []
    if not blocked:
        return []
    text_to_check = [
        ("interpretation", reading.interpretation),
        ("summary_and_assurance", reading.summary_and_assurance),
        ("acknowledgment", reading.acknowledgment),
    ] + [("technical_basis", item.reading) for item in reading.technical_basis]
    out: list[Violation] = []
    for frame in blocked:
        pattern = _BLOCKED_FRAME_PATTERNS.get(frame)
        if not pattern:
            continue
        for field, text in text_to_check:
            normalized = _normalize(text)
            unhedged = next(
                (match for match in pattern.finditer(normalized)
                 if not _negation_precedes(normalized, match.start())),
                None,
            )
            if unhedged:
                out.append(Violation(
                    f"blocked frame {frame!r} used in: {text!r} — the reader's own "
                    "confirmed profile context rules this framing out",
                    "safety", field,
                ))
                break
    return out


def _required_frame_shortfall(reading: StructuredReading, bundle: dict) -> list[Violation]:
    """Quality-severity, matching `verify_coverage`'s discipline exactly:
    a required frame's applicable fact never being cited is a worse
    reading, not a dangerous one — the reader isn't told anything false,
    the answer just failed to use context it had. Checked at the citation
    level (did the reading cite at least one of the facts driving a
    required frame), not by re-parsing prose for the framing itself, which
    would be far more false-positive-prone than a citation check."""
    preflight = ((bundle.get("profile_context") or {}).get("preflight") or {})
    required = preflight.get("required_frames") or []
    refs = preflight.get("applicable_fact_refs") or []
    if not required or not refs:
        return []
    cited = {item.source for item in reading.technical_basis}
    if cited & set(refs):
        return []
    return [Violation(
        "required framing "
        f"({', '.join(required)}) is established by the reader's own confirmed "
        "context, but none of the applicable facts "
        f"({', '.join(refs)}) were cited — the reading may have ignored it",
        "quality", "technical_basis",
    )]


def _discovery_violations(reading: StructuredReading, bundle: dict) -> list[Violation]:
    active_keys = {
        f["key"] for f in (bundle.get("profile_context") or {}).get("facts", [])
        if f.get("status") == "active"
    }
    if not active_keys:
        return []
    text_to_check = [
        ("interpretation", reading.interpretation),
        ("summary_and_assurance", reading.summary_and_assurance),
        ("acknowledgment", reading.acknowledgment),
    ] + [("technical_basis", item.reading) for item in reading.technical_basis]
    out: list[Violation] = []
    for field, text in text_to_check:
        for match in _DISCOVERY_PHRASE_RE.finditer(text):
            window = text[max(0, match.start() - 80): match.end() + 80].lower()
            for key in active_keys:
                if any(kw in window for kw in _FACT_KEY_KEYWORDS.get(key, ())):
                    out.append(Violation(
                        f"disclosed profile fact {key!r} presented as an astrological "
                        f"discovery in: {text!r}",
                        "safety", field,
                    ))
                    break
    return out


def verify(reading: StructuredReading, bundle: dict, routed_domain: str,
          question_tense: str = "unspecified") -> list[str]:
    violations: list[str] = []

    if bundle.get("domain") and bundle["domain"] != routed_domain:
        violations.append(
            f"bundle domain {bundle.get('domain')!r} does not match routed domain {routed_domain!r}"
        )

    allowed = valid_sources(bundle)
    for item in reading.technical_basis:
        if item.source not in allowed:
            violations.append(Violation(
                f"technical_basis source {item.source!r} does not resolve to the bundle's "
                "references, source_passages, or a known bundle section",
                "safety", "technical_basis",
            ))

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
    #
    # (field, text) pairs, not bare text — D2 needs to know which top-level
    # field a violation came from so a repair can regenerate only that
    # field. `guidance.practical_actions`/`follow_up_questions`/`remedies`
    # all live under the single `guidance` field on `StructuredReading`, so
    # they all attribute to `"guidance"`, not to their own sub-paths — the
    # repair schema (see schema.py's `repair_patch_schema`) regenerates
    # `guidance` as one object anyway, matching the model's own shape.
    text_to_check = [
        ("acknowledgment", reading.acknowledgment),
        ("interpretation", reading.interpretation),
        ("summary_and_assurance", reading.summary_and_assurance),
    ] + [
        ("technical_basis", item.reading) for item in reading.technical_basis
    ] + [
        ("guidance", text) for text in reading.guidance.practical_actions
    ] + [
        ("guidance", text) for text in reading.guidance.follow_up_questions
    ] + [
        ("guidance", text) for remedy in reading.guidance.remedies for text in (remedy.practice, remedy.note)
    ]

    for field, text in text_to_check:
        crossed = prohibited_verdict(text)
        if crossed:
            violations.append(Violation(f"prohibited verdict ({crossed}) in: {text!r}", "safety", field))
        dosha_crossed = dosha_overclaim_kind(text)
        if dosha_crossed == "health_outcome_overclaim":
            violations.append(Violation(f"health outcome overclaim in: {text!r}", "safety", field))
        elif dosha_crossed:
            violations.append(Violation(f"dosha overclaim in: {text!r}", "safety", field))

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
        for field, text in text_to_check:
            if _tense_conflict(text, as_of_year, safe_years):
                violations.append(Violation(
                    "retrospective question answered with an invented future "
                    f"timeline: {text!r}",
                    "safety", field,
                ))

    # Profile Context Ledger logical preflight (Phase 2) — safety severity,
    # same tier as prohibited_verdict/dosha_overclaim above: a blocked frame
    # or a disclosed fact handed back as a chart discovery is not a worse
    # reading, it is a trust violation, exactly like an invented citation.
    violations.extend(_blocked_frame_violations(reading, bundle))
    violations.extend(_discovery_violations(reading, bundle))

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
    # Independent of taxonomy — a required framing constraint applies
    # whenever the Profile Context Ledger preflight set one, regardless of
    # whether this domain has a registered taxonomy spec at all.
    out: list[Violation] = list(_required_frame_shortfall(reading, bundle))

    spec = _domain_spec(bundle)
    if spec is None:
        return out

    text_to_check = [
        reading.acknowledgment, reading.interpretation, reading.summary_and_assurance,
    ] + [item.reading for item in reading.technical_basis]

    haystack = " ".join(
        text_to_check
        + [item.factor for item in reading.technical_basis]
        + [item.source for item in reading.technical_basis]
    ).casefold()

    for varga in getattr(spec, "vargas_primary", ()) or ():
        # "D10" and the classical name both count — a reading is free to say
        # "dashamsha" and never write the code.
        names = {varga.casefold(), _VARGA_CLASSICAL_NAMES.get(varga, "").casefold()}
        if not any(n and n in haystack for n in names):
            out.append(Violation(
                f"the domain's primary divisional chart {varga} is never addressed — "
                f"cite it or say explicitly why it adds nothing here",
                "quality", "technical_basis",
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
                "quality", "technical_basis",
            ))

    return out
