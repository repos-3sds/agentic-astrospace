"""Ask's working steps (agents/ask_steps.py): every line names a lookup the
turn really made, in plain words, with no book or provider named."""
import pytest

from astrospace.agents.ask_steps import WRITING_STEP, bundle_steps, house_step, varga_step
from astrospace.context.assembler import assemble_domain
from astrospace.core.vedic.chart import VedicChart


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1993, 7, 20, 11, 28, "Rajahmundry", "IN")


def test_marriage_steps_name_the_real_lookups(chart):
    bundle = assemble_domain(chart, "marriage", question="When will I marry?")
    steps = bundle_steps(bundle)
    lords = [row["lord"] for row in bundle["dasha_relevance"]["chain"][:2]]
    assert steps[0] == "Reading your birth chart…"
    assert "Looking at your 7th house, marriage and partners…" in steps
    assert f"Checking your current period, {'–'.join(lords)}…" in steps
    assert "Reading your marriage chart…" in steps


def test_only_sections_present_become_steps():
    steps = bundle_steps({"houses": [{"house": 10, "tier": "primary"}, {"house": 6, "tier": "secondary"}]})
    assert steps == ["Reading your birth chart…", "Looking at your 10th house, career and name…"]


def test_no_jargon_books_or_providers(chart):
    bundle = assemble_domain(chart, "career", question="Will I get promoted?")
    text = " ".join([*bundle_steps(bundle), WRITING_STEP]).lower()
    for word in ("bphs", "parashara", "classic", "gemini", "openai", "claude", "karaka", "d10", "_"):
        assert word not in text


def test_unknown_house_and_chart_fall_back_plainly():
    assert house_step(13) == "Looking at your 13th house…"
    assert varga_step("D99") == "Reading a closer chart for this…"
