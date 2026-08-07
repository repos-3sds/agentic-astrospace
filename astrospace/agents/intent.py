"""Cheap heuristic intent tagging — server-computed, never model-generated.

v1 only: regex pattern matching, no LLM call. Intent is a descriptive tag on
the response envelope (helps the agent's `acknowledgment` read naturally,
helps analytics), it never gates or overrides domain routing — a question
that's both "daily_guidance"-shaped and clearly career-shaped still answers
via career. See `astrospace/agents/orchestrator.py`.
"""
from __future__ import annotations

import re

from .schema import AskIntent

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
