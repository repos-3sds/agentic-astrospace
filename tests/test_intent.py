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


# Revised after independent review of the first version (which picked
# retrospective whenever both cues appeared, on the theory that "did" is
# the more specific signal). That collapsed a genuinely two-part question
# into a single tense and fed it to a *blocking* verifier invariant
# (verifier.py) that then discarded a correct answer to the future half.
# "mixed" is the honest classification: both halves are real, so the
# retrospective-only invariant does not apply (checked via an exact
# `== "retrospective"` match — "mixed" intentionally excluded).
@pytest.mark.parametrize("question", [
    "When did retirement happen, and will my next chapter be different?",
    "I did start my career in 2001 - when will I get a promotion?",
    "Why did my last job end, and when will I find a new one?",
    "What happened in my last relationship, and when will I find love again?",
])
def test_mixed_retrospective_and_future_cues_is_not_pure_retrospective(question):
    """Found by independent review: collapsing a two-part question to a
    single tense fed a blocking invariant the wrong signal. A question
    with a real future half must never classify as pure 'retrospective' —
    that would suppress a legitimate future answer."""
    assert detect_tense(question) == "mixed"
