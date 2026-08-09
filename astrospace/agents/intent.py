"""Cheap heuristic intent tagging — server-computed, never model-generated.

v1 only: regex pattern matching, no LLM call. Intent is a descriptive tag on
the response envelope (helps the agent's `acknowledgment` read naturally,
helps analytics), it never gates or overrides domain routing — a question
that's both "daily_guidance"-shaped and clearly career-shaped still answers
via career. See `astrospace/agents/orchestrator.py`.
"""
from __future__ import annotations

import re
from typing import Literal

from .schema import AskIntent

QuestionTense = Literal["retrospective", "current_state", "future", "mixed", "unspecified"]

# Order matters: earlier entries win on overlap. daily_guidance's temporal
# cues are checked first because they're the most specific and would
# otherwise be swallowed by "timing" ("today" is a timing word too, but a
# much more specific one). comparison is checked last — "between"/"or" are
# the weakest, most false-positive-prone signals of the set.
_INTENT_PATTERNS: tuple[tuple[AskIntent, tuple[str, ...]], ...] = (
    ("daily_guidance", (
        r"\btoday\b", r"\btomorrow\b", r"\bthis week\b", r"\btonight\b",
    )),
    ("timing", (
        r"\bwhen\b", r"\bwhich month\b", r"\bwhich year\b", r"\bthis year\b",
        r"\bsoon\b", r"\bwhat date\b", r"\bwhat period\b", r"\bhow long until\b",
    )),
    ("remedy", (
        r"\bremed(?:y|ies)\b", r"\bmantra\b", r"\bwhat should i do\b",
        r"\bpractice\b", r"\bpuja\b", r"\bvrata\b",
    )),
    ("suitability", (
        r"\bshould i\b", r"\bis it good\b", r"\bis this good\b",
        r"\bright for me\b", r"\bsuitable\b", r"\bgood idea\b",
    )),
    ("explanation", (
        r"\bwhat does\b", r"\bmeaning of\b", r"\bexplain\b", r"\bwhy\b",
        r"\bwhat is\b",
    )),
    ("comparison", (
        r"\bcompare\b", r"\bversus\b", r"\bvs\.?\b", r"\bbetter option\b",
    )),
)


def detect_intent(question: str) -> AskIntent:
    normalized = " ".join(question.casefold().split())
    for intent, patterns in _INTENT_PATTERNS:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return intent
    return "general_guidance"


# Orthogonal to AskIntent, not a replacement for it: "timing" intent covers
# both "when did X start" and "when will X happen" today (that collapse is
# exactly the gap this fixes — see docs/ask_context_engine_multi_agent_
# architecture_2026-08-07.md, "Update 2026-08-09"). A non-timing question
# ("why did I get that promotion") can carry tense too, so this is a
# separate, additional classification, not a timing sub-bucket.
#
# 2026-08-09, revised after independent review of the first version: that
# version picked retrospective over future whenever both cues appeared
# anywhere in the question, on the reasoning that "did" auxiliaries are the
# more specific signal. That's true for classifying which cue is "stronger",
# but it's the wrong call once tense feeds a *blocking* verifier invariant
# (see verifier.py) — a genuinely two-part question like "When did
# retirement happen, and will my next chapter be different?" has a real
# future half that deserves a real future answer, and silently downgrading
# it to "retrospective" caused the verifier to discard a correct answer.
# `mixed` is a third, explicit outcome for exactly this case: both cues
# present, so the verifier's retrospective-only invariant does not apply at
# all (checked via `tense == "retrospective"`, an exact-match — "mixed"
# intentionally does not qualify).
_RETROSPECTIVE_PATTERNS = (
    r"\bwhen did\b", r"\bwhy did\b", r"\bhow did\b", r"\bwhat happened\b",
    r"\bhas already\b", r"\balready happened\b", r"\bwhen was\b",
    r"\bdid\b.{0,25}\b(?:start|happen|occur|begin|end)\b",
    r"\bused to\b", r"\bin the past\b", r"\bhow long ago\b",
)
_FUTURE_PATTERNS = (
    r"\bwhen will\b", r"\bwill i\b", r"\bwill my\b", r"\bwill this\b",
    r"\bgoing to\b", r"\bhow soon\b", r"\bwhen can i expect\b",
    r"\bwhen would\b", r"\bhow long until\b", r"\bwhat's coming\b",
    r"\bwhats coming\b",
)
_CURRENT_STATE_PATTERNS = (
    r"\bright now\b", r"\bcurrently\b", r"\bat the moment\b", r"\bthese days\b",
)


def detect_tense(question: str) -> QuestionTense:
    """Server-computed, same discipline as `detect_intent()` — a cheap
    heuristic tag, never inferred by the model. `unspecified` is the honest
    default: most questions ("what does the 7th house mean") carry no tense
    signal at all, and guessing one would be worse than admitting there
    isn't one."""
    normalized = " ".join(question.casefold().split())
    is_retrospective = any(re.search(p, normalized) for p in _RETROSPECTIVE_PATTERNS)
    is_future = any(re.search(p, normalized) for p in _FUTURE_PATTERNS)
    if is_retrospective and is_future:
        return "mixed"
    if is_retrospective:
        return "retrospective"
    if is_future:
        return "future"
    if any(re.search(p, normalized) for p in _CURRENT_STATE_PATTERNS):
        return "current_state"
    return "unspecified"
