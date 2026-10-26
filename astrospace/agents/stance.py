"""Spots a reader pushing back, so the reading holds its ground.

2026-10-26: a tester asked Ask which car colour suited his chart. It said
white and cream, then "Pewter Olive is not recommended", then, once he wrote
"we liked Magma Red", ranked red 9/10 first and called every option "Positive
Impact" — using the same Jupiter placement it had just used for white. The
prompt's rules E-G (domain_agent.py) say earlier answers are commitments and
a reader's liking is not chart evidence. This module makes the rule concrete
for the one turn where it matters most: when the question itself carries a
preference, a doubt, someone else's verdict or plain pressure, the agent gets
a short note naming that, on top of the standing rules.

Deterministic and deliberately simple: a phrase list, not a model call. A
miss costs nothing (the standing rules still apply); a false match only
reminds the agent to answer honestly, which it should do anyway.
"""
from __future__ import annotations

import re

# Order matters only for which note a question with several signals gets;
# the notes all end in the same instruction.
_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("authority", re.compile(
        r"\b(my|our|another|other|a|the) (astrologer|pandit|panditji|guruji|jyotish\w*|"
        r"priest|swamiji)\b|"
        r"\b(my|our) (mother|mom|mum|amma|father|dad|nanna|family|wife|husband|friend)s? "
        r"(says|said|told|thinks|feels)\b|"
        r"\b(another|other|different) (app|website|reading|chart)\b|"
        r"\b(someone|they|people|everyone) (says|said|told me)\b", re.I)),
    ("doubt", re.compile(
        r"\bare you (sure|certain|confident)\b|\breally\s*\?|\byou(?:'re| are) wrong\b|"
        r"\bthat(?:'s| is) (wrong|not right|incorrect)\b|\bcheck (it )?again\b|"
        r"\b(re-?check|double[- ]check|reconsider|think again)\b|"
        r"\bbut (you|earlier you) said\b|\bconfirm (it|this|again)\b", re.I)),
    ("preference", re.compile(
        # "Will I like my new job?" is a question, not a preference.
        r"(?<!will )(?<!would )(?<!do )(?<!did )(?<!should )(?<!can )(?<!could )"
        r"\b(i|we) (really |both |all )?(like|liked|love|loved|prefer|preferred)\b|"
        r"\b(i|we) (really )?(want|wanted) (the|this|that|it|a|an) |"
        r"\b(i|we)(?: have| had|'ve)?(?: already)? (chosen|chose|decided|bought|booked|"
        r"paid for|picked|finali[sz]ed)\b|"
        r"\b(my|our) (favourite|favorite|choice|preference)\b|"
        r"\bbut i like\b", re.I)),
    ("pressure", re.compile(
        r"\bjust (say|tell me) (it'?s|it is|yes|ok|okay|fine|good)\b|"
        r"\bplease (say|agree)\b|\bsay (yes|it'?s fine|it'?s good)\b|"
        r"\b(i|we) need you to (agree|say)\b", re.I)),
)

_NOTES = {
    "preference": "The reader has said what they like or have already chosen.",
    "doubt": "The reader is questioning or asking you to re-check an earlier answer.",
    "authority": "The reader is citing someone else's reading or opinion.",
    "pressure": "The reader is pressing you to approve something.",
}


def detect_pushback(question: str) -> str | None:
    """`preference`, `doubt`, `authority`, `pressure`, or None."""
    for kind, pattern in _PATTERNS:
        if pattern.search(question or ""):
            return kind
    return None


def stance_note(kind: str | None) -> str:
    """The prompt block for this turn, or "" when there is no pushback."""
    if kind not in _NOTES:
        return ""
    return (
        "\n── THIS TURN — hold your ground (rules E, F and G) ──\n"
        f"{_NOTES[kind]} That is not new evidence from the chart. Give exactly the "
        "judgement you would give if they had not said it, and keep every earlier answer "
        "in this conversation unless they gave you a genuinely new fact. If something they "
        "like does not suit the chart, say so plainly and kindly, say why, and say the "
        "choice is theirs. If a re-check confirms your earlier answer, say it is confirmed. "
        "If it shows you were wrong, say plainly what was wrong.\n"
    )
