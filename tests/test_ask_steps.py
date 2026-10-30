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


class TestReaderNotes:
    """Deep's own lines (Hawk, 2026-10-30): shown only when short, plain and
    clean; otherwise the fixed line for that look-up."""

    def test_plain_note_is_shown(self):
        from astrospace.agents.ask_tools import summarize_call
        line = summarize_call("house", {"number": 7, "reader_note": "Checking if Venus, your marriage planet, is strong."})
        assert line == "Checking if Venus, your marriage planet, is strong…"

    @pytest.mark.parametrize("note", [
        "Reading the BPHS rule for the 7th lord",
        "Counting Ashtakavarga bindus in the 7th",
        "Checking the D9 for Venus",
        "Checking the 7th for divorce",
        "Asking the AI model about Venus",
        "Checking <b>Venus</b>",
        "ok",
        "Checking a very long line that goes on and on about every single planet in the chart",
        None,
    ])
    def test_unsafe_or_odd_notes_fall_back(self, note):
        from astrospace.agents.ask_tools import summarize_call
        assert summarize_call("house", {"number": 7, "reader_note": note}) == \
            "Looking at your 7th house, marriage and partners…"

    def test_the_note_is_not_a_tool_argument(self, chart):
        from astrospace.agents.ask_tools import ChartTools
        tools = ChartTools(chart)
        with_note = tools.call("house", {"number": 7, "reader_note": "Checking your 7th house"})
        plain = tools.call("house", {"number": 7})
        assert "error" not in with_note and with_note["ref"] == plain["ref"]
        assert "reader_note" not in tools.calls[0]["args"]

    def test_every_tool_offers_the_note(self):
        from astrospace.agents.ask_tools import TOOL_SPECS
        assert all("reader_note" in spec["input_schema"]["properties"] for spec in TOOL_SPECS)
        assert all("reader_note" not in spec["input_schema"].get("required", []) for spec in TOOL_SPECS)
