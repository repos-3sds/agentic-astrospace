"""Deep Ask's own cost ceiling (sweep 2026-10-29 S-1).

Deep runs the exploring agent, about five times Fast's model calls, at the
price of one question. Checked here: an account gets one Deep exploration at
a time and a daily allowance, after which the turn is today's Ask; an
exploration the reader stopped waiting for stops after the call in flight,
frees its slot only when it has really ended, and is still costed.
"""
import json
import logging
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from astrospace import ratelimit
from astrospace.agents import orchestrator as orch
from astrospace.agents.explorer import ExplorationStopped
from astrospace.api.ask_routes import _claim_deep


@pytest.fixture(autouse=True)
def _clean():
    ratelimit.reset()
    yield
    ratelimit.reset()


class TestDeepSlot:
    def test_one_at_a_time_per_account(self):
        release = ratelimit.deep_slot("a", now=0)
        assert release is not None
        assert ratelimit.deep_slot("a", now=1) is None
        assert ratelimit.deep_slot("b", now=1) is not None  # other accounts are separate
        release()
        release()  # twice is harmless
        assert ratelimit.deep_slot("a", now=100) is not None

    def test_a_busy_refusal_spends_no_allowance(self):
        hold = ratelimit.deep_slot("a", now=0)
        for t in range(1, 30):
            assert ratelimit.deep_slot("a", now=t) is None
        hold()
        assert ratelimit.deep_slot("a", now=100) is not None

    def test_daily_allowance(self):
        granted = 0
        for i in range(40):
            release = ratelimit.deep_slot("a", now=i * 61.0)
            if release:
                granted += 1
                release()
        assert granted == ratelimit.LIMITS["ask_deep"].per_day

    def test_a_slot_never_released_frees_itself(self):
        assert ratelimit.deep_slot("a", now=0) is not None
        assert ratelimit.deep_slot("a", now=60) is None
        assert ratelimit.deep_slot("a", now=ratelimit.DEEP_HOLD_MAX_S + 1) is not None


class TestClaimDeep:
    def test_busy_account_gets_todays_ask(self):
        first = SimpleNamespace(explorer_factory=object(), explore_release=None, deep_paused=False)
        _claim_deep(first, "a")
        assert first.explore_release is not None and not first.deep_paused

        second = SimpleNamespace(explorer_factory=object(), explore_release=None, deep_paused=False)
        _claim_deep(second, "a")
        assert second.explorer_factory is None and second.deep_paused

    def test_fast_questions_hold_nothing(self):
        fast = SimpleNamespace(explorer_factory=None, explore_release=None, deep_paused=False)
        _claim_deep(fast, "a")
        assert fast.explore_release is None and not fast.deep_paused


class _SlowExplorer:
    """Makes one timed "model call" per round until told to stop."""

    def __init__(self, stop, calls):
        self.stop, self.calls, self.usage_log = stop, calls, []

    def explore(self):
        for _ in range(50):
            time.sleep(0.05)
            self.calls.append(1)
            self.usage_log.append({"input_tokens": 10, "output_tokens": 5})
            if self.stop.is_set():
                raise ExplorationStopped("stopped")
        return {"explored": []}


def _prepared(calls, released):
    return SimpleNamespace(
        domain="career", intent="x", question_kind="broad",
        explorer_factory=lambda on_tool, stop: _SlowExplorer(stop, calls),
        explore_release=lambda: released.set(),
        explore_usage=[], usage={}, bundle={}, context_used=[],
    )


class TestAbandonedExploration:
    def test_a_timed_out_exploration_stops_frees_its_slot_and_is_costed(self, caplog):
        calls, released = [], threading.Event()
        prepared = _prepared(calls, released)
        with patch.object(orch, "EXPLORE_TIMEOUT_S", 0.2), \
                caplog.at_level(logging.INFO, logger="astrospace.ask.cost"):
            list(orch.AskOrchestrator._explore(None, prepared))
            assert released.wait(2), "the slot is freed once the worker ends"
        made = len(calls)
        time.sleep(0.2)
        assert len(calls) == made, "no model calls after it stopped"
        assert made < 10
        lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "astrospace.ask.cost"]
        abandoned = [line for line in lines if line["status"] == "explore_abandoned"]
        assert abandoned and abandoned[0]["calls"] == made

    def test_a_closed_stream_stops_the_exploration(self):
        calls, released = [], threading.Event()
        prepared = _prepared(calls, released)
        prepared.explorer_factory = lambda on_tool, stop: (on_tool("house", {"number": 7}),
                                                            _SlowExplorer(stop, calls))[1]
        events = orch.AskOrchestrator._explore(None, prepared)
        next(events)  # the first progress line reached the reader
        events.close()  # the reader went away
        assert released.wait(2)
        assert len(calls) < 10

    def test_a_turn_closed_before_exploring_frees_the_slot(self):
        released = threading.Event()
        prepared = SimpleNamespace(context_used=["chart"], bundle={}, deep_paused=False,
                                   explorer_factory=object(), explore_release=released.set)
        run = orch.AskOrchestrator.run(None, prepared, [], persist=lambda r, s: None)
        next(run)
        run.close()
        assert released.is_set()
