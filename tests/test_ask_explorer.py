"""The tool-using Ask (agents/ask_tools.py, agents/explorer.py), behind
ASK_ENGINE / ASK_AGENT_EMAILS (agents/ask_engine.py).

No model is reached: the exploring agent's tool loop is replaced by a fake
that calls the real tools on a real chart, and the specialist's answer is
stubbed. What is checked is the plumbing that keeps it grounded: every tool
answers on a real chart, the switch picks the right readers, the answer may
cite exactly the refs the tools returned, and a failed exploration falls back
to today's Ask.
"""
from unittest.mock import patch

import pytest

from astrospace.agents.ask_engine import uses_agent
from astrospace.agents.ask_tools import TOOL_SPECS, ChartTools, pattern_cards, summarize_call
from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.explorer import ChartExplorer
from astrospace.agents.orchestrator import AskOrchestrator
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.agents.scope import QuestionPlan
from astrospace.agents.verifier import _period_boundary_years, valid_sources
from astrospace.core.vedic.chart import VedicChart

QUESTION = "When will I get married, and will it be a happy marriage?"


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1993, 7, 20, 11, 28, "Rajahmundry", "IN")


def _reading(*sources: str) -> StructuredReading:
    return StructuredReading(
        acknowledgment="You asked about marriage.",
        technical_basis=[TechnicalBasisItem(factor=s, reading="Supports a steady marriage.", source=s)
                         for s in sources],
        interpretation="The 7th house looks steady and the coming years open the door.",
        summary_and_assurance="There is a calm base here.",
        guidance=Guidance(practical_actions=["Talk openly with family."]),
        confidence="medium",
    )


class TestTools:
    CALLS = {
        "chart_overview": {}, "house": {"number": 7}, "varga": {"division": "D9"},
        "dasha_at": {"date": "2027-01-01"}, "dasha_timeline": {"start": "2026-01-01", "end": "2030-01-01"},
        "dasha_variant": {"variant": "kshema"}, "transits": {}, "ashtakavarga": {"planet": "Venus"},
        "strengths": {}, "yogas_doshas": {}, "jaimini": {}, "favourable": {}, "panchang": {},
        "classical_patterns": {"area": "marriage"},
    }

    def test_every_tool_is_covered_here(self):
        assert {spec["name"] for spec in TOOL_SPECS} == set(self.CALLS) | {"classics"}

    @pytest.mark.parametrize("name", sorted(CALLS))
    def test_each_tool_answers_on_a_real_chart(self, chart, name):
        tools = ChartTools(chart)
        result = tools.call(name, self.CALLS[name])
        assert "error" not in result, result
        assert result["ref"].startswith(f"tool:{name}")
        assert len(str(result)) < 12_000, "tool results must stay small"
        assert tools.calls[-1]["result"] is result

    @pytest.mark.parametrize("variant", ["utpanna", "adhana", "d9_lagna", "tribhagi", "yogini", "chara"])
    def test_dasha_variants_are_marked_convention_dependent(self, chart, variant):
        result = ChartTools(chart).call("dasha_variant", {"variant": variant})
        assert "error" not in result, result
        assert result["is_convention_dependent"] is True and result["note"]

    def test_failures_reach_the_model_not_the_reader(self, chart):
        tools = ChartTools(chart)
        assert "error" in tools.call("house", {"number": 13})
        assert "error" in tools.call("no_such_tool", {})
        assert "error" in tools.call("classics", {"query": "7th lord"})  # no retriever here

    def test_patterns_come_from_the_book_with_tiers(self, chart):
        assert len(pattern_cards()) > 150
        result = ChartTools(chart).call("classical_patterns", {"area": "career"})
        tiers = [row["tier"] for row in result["patterns"]]
        assert tiers and tiers == sorted(tiers, key="ABCH".index)
        assert all(row["id"].startswith("pattern:") for row in result["patterns"])

    def test_progress_lines_are_plain(self):
        assert summarize_call("house", {"number": 7}) == "Looking at your 7th house…"
        assert summarize_call("house", {"number": 11}) == "Looking at your 11th house…"
        assert summarize_call("varga", {"division": "D9"}) == "Reading your D9 chart…"


class TestSwitch:
    def test_off_for_everyone_when_the_list_is_empty(self):
        assert not uses_agent("vikramadityavss@gmail.com")

    def test_owner_only_by_default(self, monkeypatch):
        monkeypatch.delenv("ASK_AGENT_EMAILS")
        assert uses_agent("VikramadityaVSS@gmail.com")
        assert not uses_agent("someone@example.com")
        assert not uses_agent(None)

    def test_listed_accounts_and_everyone(self, monkeypatch):
        monkeypatch.setenv("ASK_AGENT_EMAILS", "a@x.com, b@y.com")
        assert uses_agent("b@y.com") and not uses_agent("c@z.com")
        monkeypatch.setenv("ASK_ENGINE", "agent")
        assert uses_agent("c@z.com")


class TestVerifier:
    BUNDLE = {"explored": [
        {"ref": "tool:house(7)", "result": {"ref": "tool:house(7)", "sign": "Pisces"}},
        {"ref": "tool:classical_patterns(marriage)",
         "result": {"patterns": [{"id": "pattern:MAR-01", "tier": "A"}]}},
        {"ref": "tool:dasha_timeline(2026-01-01,2032-01-01)",
         "result": {"antardashas": [{"lord": "Rahu", "start": "2028-05-06", "end": "2031-05-07"}]}},
    ]}

    def test_explored_refs_and_patterns_are_citable(self):
        sources = valid_sources(self.BUNDLE)
        assert {"tool:house(7)", "pattern:MAR-01", "tool:classical_patterns(marriage)"} <= sources

    def test_nothing_extra_is_citable_without_exploring(self):
        assert not any(s.startswith(("tool:", "pattern:")) for s in valid_sources({}))

    def test_looked_up_period_years_count_as_real_boundaries(self):
        assert {2028, 2031} <= _period_boundary_years(self.BUNDLE)


def _fake_explore_loop(self, messages):
    self._dispatch_tool("classical_patterns", {"area": "marriage"})
    self._dispatch_tool("house", {"number": 7})
    self._dispatch_tool("dasha_timeline", {"start": "2026-01-01", "end": "2032-01-01"})
    return "- 7th lord Jupiter in the 1st [tool:house(7)]", ["classical_patterns", "house", "dasha_timeline"]


class TestOrchestrator:
    def _prepare(self, chart, explore: bool):
        orchestrator = AskOrchestrator(
            chart_loader=lambda: chart,
            planner=lambda question, history: QuestionPlan(kind="broad", domain="marriage", method="test"),
        )
        with patch.object(AskOrchestrator, "check_validation", return_value=None):
            outcome = orchestrator.prepare(QUESTION, explore=explore)
        assert outcome.prepared is not None
        return orchestrator, outcome.prepared

    def test_bundle_path_is_untouched_when_off(self, chart):
        _orch, prepared = self._prepare(chart, explore=False)
        assert prepared.explorer_factory is None and prepared.agent_factory is None

    def test_explores_then_answers_citing_what_it_looked_up(self, chart):
        orchestrator, prepared = self._prepare(chart, explore=True)
        seen_sources: list[set[str]] = []

        def answer(agent, messages):
            seen_sources.append(valid_sources(agent.bundle))
            assert "LOOKED UP FOR THIS QUESTION" in agent.system_prompt
            return _reading("tool:house(7)", "pattern:MAR-01", "houses")

        persisted = []
        with patch.object(ChartExplorer, "run_messages", _fake_explore_loop), \
                patch.object(DomainReadingAgent, "run_structured_reading", answer):
            events = list(orchestrator.run(prepared, [{"role": "user", "content": QUESTION}],
                                           persist=lambda r, s: persisted.append(s) or "t1"))

        labels = [e["label"] for e in events if e.get("stage") == "exploring"]
        assert labels == ["Checking the classical rules…", "Looking at your 7th house…",
                          "Checking your dasha periods…"]
        done = events[-1]
        assert done["status"] == "answered", done
        assert set(done["evidence_refs"]) == {"tool:house(7)", "pattern:MAR-01", "houses"}
        assert "explored" in done["context_used"]
        assert {"tool:house(7)", "pattern:MAR-01"} <= seen_sources[0]
        assert prepared.bundle["explorer_notes"].startswith("- 7th lord")
        assert persisted == ["answered"]

    def test_an_invented_tool_ref_is_still_rejected(self, chart):
        orchestrator, prepared = self._prepare(chart, explore=True)
        with patch.object(ChartExplorer, "run_messages", _fake_explore_loop), \
                patch.object(DomainReadingAgent, "run_structured_reading",
                             return_value=_reading("tool:house(5)")), \
                patch.object(DomainReadingAgent, "run_structured_repair",
                             side_effect=lambda m, f: _reading("tool:house(5)")):
            events = list(orchestrator.run(prepared, [{"role": "user", "content": QUESTION}],
                                           persist=lambda r, s: "t1"))
        assert events[-1]["status"] == "verification_failed"

    def test_failed_exploration_falls_back_to_todays_ask(self, chart):
        orchestrator, prepared = self._prepare(chart, explore=True)
        before = prepared.agent

        def broken(self, messages):
            raise RuntimeError("provider down")

        with patch.object(ChartExplorer, "run_messages", broken), \
                patch.object(DomainReadingAgent, "run_structured_reading", return_value=_reading("houses")):
            events = list(orchestrator.run(prepared, [{"role": "user", "content": QUESTION}],
                                           persist=lambda r, s: "t1"))
        assert events[-1]["status"] == "answered"
        assert prepared.agent is before and "explored" not in prepared.bundle

    def test_depth_follows_the_question(self, chart):
        tools = ChartTools(chart)
        assert ChartExplorer(tools, "q", {}, question_kind="today").max_tool_rounds == 2
        assert ChartExplorer(tools, "q", {}, question_kind="broad").max_tool_rounds == 5
        assert ChartExplorer(tools, "q", {}, question_kind="broad",
                             experience_mode="practitioner").max_tool_rounds == 6
