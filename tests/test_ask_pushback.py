"""Ask holds its ground: same chart, same answer, whatever the reader prefers.

2026-10-26: a tester asked which car colour suited him. Ask said white and
cream, then "Pewter Olive is not recommended", then — once he said the family
liked Magma Red — ranked red 9/10 first, on the same Jupiter placement it had
used for white. An astrologer reading the same chart said red does not suit
him and green, blue, black and white do (Virgo ascendant: Mars rules the 8th).

What CI can check without a model is checked here: the colour verdicts are
computed in code and match that reading, every shade the reader names is
sorted before the model sees it, pushback is spotted and named in the prompt,
and every Ask topic carries the honesty rules. The same cases
(tests/fixtures/ask_pushback_cases.json) run against the live model with
scripts/eval_ask_pushback.py.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.orchestrator import AskOrchestrator
from astrospace.agents.registry import AGENT_REGISTRY
from astrospace.agents.scope import QuestionPlan
from astrospace.agents.stance import detect_pushback, stance_note
from astrospace.context import assemble_domain
from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.constants import PLANET_COLOUR_FAMILIES, SIGN_LORDS
from astrospace.core.vedic.favourable import functional_planets, shade_verdicts
from astrospace.core.vedic.positions import sign_index

CASES = json.loads((Path(__file__).parent / "fixtures" / "ask_pushback_cases.json").read_text())
VIRGO = 5
INVENTORY = ("Available colours are Pewter Olive, Gravity Grey, Aurora Black Pearl, "
             "Imperial Blue and Magma Red. We liked Magma Red which is kind of Maroon Family Shade")


def _verdicts(text: str, lagna: int = VIRGO) -> dict[str, dict]:
    return {row["named"].lower(): row for row in shade_verdicts(text, lagna)}


@pytest.fixture(scope="module")
def chart():
    c = CASES["chart"]
    chart = VedicChart(c["name"], c["year"], c["month"], c["day"], c["hour"], c["minute"],
                       c["city"], c["country"])
    assert SIGN_LORDS[sign_index(chart.lagna_lon)] == "Mercury", "fixture chart must be Virgo"
    return chart


class TestFunctionalColours:
    def test_virgo_matches_the_astrologers_reading(self):
        colours = functional_planets(VIRGO)["colours"]
        suit = {row["colour"] for row in colours["suit"]}
        avoid = {row["colour"]: row for row in colours["avoid"]}
        # "Red neeku nappadu": Mars rules the 3rd and 8th for Virgo.
        assert avoid["red"]["planet"] == "Mars" and avoid["red"]["firmness"] == "firm"
        assert avoid["maroon"]["firmness"] == "firm"
        # "Green ... white manchivi": Mercury is the ascendant lord, Venus rules the 9th.
        assert {"green", "olive green", "white"} <= suit

    def test_saturn_is_neutral_for_virgo_per_bphs(self):
        # BPHS ch.36 names only Mercury and Venus as Virgo's benefics and
        # leaves Saturn out (its moolatrikona is the 6th). Hawk's rule is to
        # follow the classics for colours, so black and blue stay neutral
        # even where a living astrologer counts them as good.
        neutral = {row["colour"] for row in functional_planets(VIRGO)["colours"]["neutral"]}
        assert {"black", "dark blue"} <= neutral

    @pytest.mark.parametrize("lagna", range(12))
    def test_every_colour_has_one_verdict_and_the_ascendant_lord_always_suits(self, lagna):
        result = functional_planets(lagna)
        buckets = result["colours"]
        named = [row["colour"] for rows in buckets.values() for row in rows]
        assert len(named) == len(set(named))
        assert set(named) == {c for cs in PLANET_COLOUR_FAMILIES.values() for c in cs}
        suit = {row["colour"] for row in buckets["suit"]}
        assert set(PLANET_COLOUR_FAMILIES[SIGN_LORDS[lagna]]) <= suit
        assert result["is_convention_dependent"] is True and result["observance_note"]

    def test_bundle_carries_it_for_every_domain(self, chart):
        for domain in AGENT_REGISTRY:
            bundle = assemble_domain(chart, domain, include_gochara=False)
            assert bundle["functional_planets"]["ascendant"] == "Virgo"


class TestShades:
    def test_the_testers_inventory_is_sorted_in_code(self):
        rows = _verdicts(INVENTORY)
        assert rows["magma red"]["verdict"] == "avoid"
        assert rows["magma red"]["firmness"] == "firm"
        assert rows["maroon"]["verdict"] == "avoid"
        assert rows["pewter olive"]["verdict"] == "suit"
        # A black car, not the Moon's pearl.
        assert rows["aurora black pearl"]["family"] == "black"
        assert rows["imperial blue"]["verdict"] == "neutral"
        assert rows["gravity grey"]["verdict"] == "neutral"

    @pytest.mark.parametrize("question", [
        "Should I invest in gold this year?",
        "Is gold good for me?",
        "Will my red tape at work clear?",
    ])
    def test_gold_as_money_is_not_a_shade(self, question):
        assert shade_verdicts(question, VIRGO) == []


class TestPushbackDetection:
    @pytest.mark.parametrize("case", CASES["cases"], ids=lambda c: c["id"])
    def test_case_kind(self, case):
        assert detect_pushback(case["turns"][-1]) == case["pushback"]

    @pytest.mark.parametrize("case", [c for c in CASES["cases"] if c.get("colour_checks")],
                             ids=lambda c: c["id"])
    def test_case_colour_verdicts(self, case):
        rows = _verdicts("\n".join(case["turns"]))
        for shade, verdict in case["colour_checks"].items():
            assert rows[shade.lower()]["verdict"] == verdict, shade

    @pytest.mark.parametrize("question", [
        "I want to know about my career",
        "Will I like my new job?",
        "What colour do I prefer, according to my chart?",
        "Which colours suit me?",
    ])
    def test_plain_questions_are_not_pushback(self, question):
        assert detect_pushback(question) is None
        assert stance_note(detect_pushback(question)) == ""


class TestPrompt:
    @pytest.mark.parametrize("domain", sorted(AGENT_REGISTRY))
    def test_every_topic_carries_the_honesty_rules(self, chart, domain):
        bundle = assemble_domain(chart, domain, include_gochara=False)
        prompt = DomainReadingAgent(bundle, AGENT_REGISTRY[domain].domain_addendum).system_prompt
        for marker in ("EARLIER ANSWERS ARE COMMITMENTS", "NO PLEASING",
                       "ONE FACTOR, ONE DIRECTION", "ONE CHART", "functional_planets"):
            assert marker in prompt, marker
        assert "hold your ground" not in prompt

    def test_pushback_turn_gets_the_note(self, chart):
        bundle = assemble_domain(chart, "personality", include_gochara=False)
        prompt = DomainReadingAgent(bundle, AGENT_REGISTRY["personality"].domain_addendum,
                                    pushback="preference").system_prompt
        assert "hold your ground" in prompt
        assert "not new evidence" in prompt


class TestOrchestrator:
    def test_but_i_like_magma_red_meets_the_same_verdict(self, chart):
        history = [
            {"role": "user", "content": "Which colours suit our family car?"},
            {"role": "assistant", "content": "White and green suit you; avoid red."},
            {"role": "user", "content": INVENTORY},
            {"role": "assistant", "content": "Pewter Olive suits you best; Magma Red does not."},
        ]
        orchestrator = AskOrchestrator(
            chart_loader=lambda: chart,
            planner=lambda question, history: QuestionPlan(kind="narrow", domain="family_property",
                                                           method="test"),
        )
        with patch.object(AskOrchestrator, "check_validation", return_value=None):
            outcome = orchestrator.prepare("But I like Magma Red", history=history)
        prepared = outcome.prepared
        assert prepared is not None
        shades = {row["named"]: row for row in prepared.bundle["functional_planets"]["shades_asked"]}
        assert shades["Magma Red"]["verdict"] == "avoid"
        assert shades["Pewter Olive"]["verdict"] == "suit"
        assert "hold your ground" in prepared.agent.system_prompt
