"""Cheap heuristic intent tagging — one case per intent, plus the fallback.
Server-computed, never model-generated; see astrospace/agents/intent.py."""
import pytest

from astrospace.agents.intent import detect_intent


@pytest.mark.parametrize(("question", "expected"), [
    ("What should I focus on today?", "daily_guidance"),
    ("What is going on for me tomorrow?", "daily_guidance"),
    ("When will I get a promotion?", "timing"),
    ("Which month is strongest for a job change this year?", "timing"),
    ("What remedy should I do for this dosha?", "remedy"),
    ("Should I take this job offer?", "suitability"),
    ("Is this a good idea for my career?", "suitability"),
    ("What does the 10th house mean for my career?", "explanation"),
    ("Why is my Saturn period difficult?", "explanation"),
    ("Compare my D1 and D9 for this question", "comparison"),
    ("Tell me about my chart", "general_guidance"),
])
def test_detect_intent(question, expected):
    assert detect_intent(question) == expected


def test_daily_guidance_checked_before_timing():
    """'today' is a temporal cue that would also loosely match nothing in
    'timing', but the ordering must not let a genuinely daily-shaped
    question fall through to a domain-timing read."""
    assert detect_intent("What should I focus on today at work?") == "daily_guidance"


def test_case_insensitive():
    assert detect_intent("WHEN WILL I GET MARRIED") == "timing"
