"""Cheap heuristic intent tagging — one case per intent, plus the fallback.
Server-computed, never model-generated; see astrospace/agents/intent.py."""
import pytest

from astrospace.agents.intent import detect_intent, detect_tense


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


# Codex's live-testing finding (docs/ask_context_engine_multi_agent_
# architecture_2026-08-07.md, "Update 2026-08-09"): the exact repro was a
# retired user asking "when did my career inception start and when did
# retirement happen?" and getting a future prediction back. detect_tense()
# is the fix's first piece — an orthogonal classification to detect_intent(),
# not a replacement, since both timing and non-timing questions carry tense.
@pytest.mark.parametrize(("question", "expected"), [
    ("When did my career inception start and when did retirement happen?", "retrospective"),
    ("Why did I get passed over for that promotion?", "retrospective"),
    ("What happened during my last Saturn dasha?", "retrospective"),
    ("How did my marriage come about?", "retrospective"),
    ("I used to work in finance, why did that change?", "retrospective"),
    ("When will I get married?", "future"),
    ("How soon will I see a promotion?", "future"),
    ("Is my career going to improve this year?", "future"),
    ("How am I doing in my career right now?", "current_state"),
    ("What does the 10th house mean for my career?", "unspecified"),
    ("Tell me about my chart", "unspecified"),
])
def test_detect_tense(question, expected):
    assert detect_tense(question) == expected


def test_detect_tense_case_insensitive():
    assert detect_tense("WHEN DID MY CAREER START") == "retrospective"


def test_retrospective_checked_before_future_on_mixed_cues():
    """A question naming a past event with 'happen' must not be pulled to
    'future' just because a later, unrelated clause about future timing
    exists — retrospective is checked first because 'when did' is the more
    specific, earlier signal in the actual repro question."""
    assert detect_tense(
        "When did retirement happen, and will my next chapter be different?"
    ) == "retrospective"
