"""Ask's `muhurta_search` section: real slots for "good time to..." questions."""
from datetime import date

import pytest

from astrospace.context.muhurta_search import is_muhurta_question, muhurta_section
from astrospace.core.vedic.chart import VedicChart


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test", 1991, 8, 14, 6, 12, "Vijayawada", "IN")


@pytest.mark.parametrize("question,expected", [
    ("When is a good time to take delivery of my new car?", True),
    ("Shubh muhurat for griha pravesh next week?", True),
    ("Best day for buying gold?", True),
    ("How will my career go?", False),
    ("Is my marriage going to be happy?", False),
])
def test_detects_muhurta_questions(question, expected):
    assert is_muhurta_question(question) is expected


def test_car_question_gets_vehicle_slots(chart):
    section = muhurta_section(chart, "Good time to take delivery of my car?", today=date(2026, 11, 1))
    assert section["purpose"] == "Buy or take delivery of a vehicle"
    assert section["slots"]
    assert all("09:00" <= s["from"] and s["to"] <= "19:00" for s in section["slots"])
    assert "Do not invent" in section["how_to_use"]


def test_other_questions_get_no_section(chart):
    assert muhurta_section(chart, "Tell me about my chart") is None


def test_refer_out_words_get_no_section(chart):
    assert muhurta_section(chart, "Auspicious time for my knee surgery?", today=date(2026, 11, 1)) is None


def test_section_is_citable_only_when_present():
    from astrospace.agents.verifier import valid_sources
    assert "muhurta_search" in valid_sources({"muhurta_search": {"slots": []}, "x": 1} | {"muhurta_search": {"slots": [1]}})
    assert "muhurta_search" not in valid_sources({})
