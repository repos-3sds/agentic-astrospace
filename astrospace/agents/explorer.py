"""The exploring step of the tool-using Ask (ASK_ENGINE=agent, see
agents/ask_engine.py).

Before the domain specialist writes its structured answer, this agent reads
the question and the fixed domain bundle, then calls the read-only chart
tools in agents/ask_tools.py for whatever else the question needs: another
house, a divisional chart, the dasha on a date, the classical rules for the
area. It writes nothing the reader sees. Its tool results go into the bundle
as `explored`, where the specialist reads them and may cite their refs, and
the verifier checks every citation against exactly those refs.

Depth follows the question: a quick "today" question gets two tool rounds, a
broad life question five. Safety, scope, the dosha rule and the checker stay
in code, untouched.
"""
from __future__ import annotations

import logging
from typing import Callable

from .ask_tools import TOOL_SPECS, ChartTools, summarize_call
from .base import BaseAstroAgent
from .style import PLAIN_INDIAN_ENGLISH

log = logging.getLogger(__name__)

# Tool rounds per question kind (agents/scope.py). Practitioner readers get
# one more, capped at the base loop's six.
ROUNDS_BY_KIND = {"today": 2, "narrow": 3, "explain": 4, "broad": 5}

# Bundle sections the explorer is told already exist, so it fetches what is
# missing rather than re-fetching what the specialist already has.
_SUMMARY_KEYS = ("houses", "karakas", "vargas", "dasha_relevance", "gochara", "yogas", "doshas",
                 "ashtakavarga", "strengths", "favourable", "panchang")

_SYSTEM = """You are the research step of Siddha, a Vedic astrology app. A reader asked:

QUESTION: {question}

Life area: {domain_name} ({domain}). Question kind: {kind}. Today is {as_of}.

A specialist will write the answer after you. It already has this fixed context for the area:
{already}

Your job: use the tools to look up anything ELSE this question needs, so the answer rests on
real chart facts, not guesses. Work like a careful astrologer:
1. Start with classical_patterns for the area. They are rules from the classics, graded A
   (two or more classics agree), B (one classic), C, H (practice or hypothesis).
2. Check the rules that matter for this question against THIS chart with the other tools
   (house, varga, dasha_at, dasha_timeline, ashtakavarga, strengths, transits, panchang ...).
   For "when" questions, look at the dasha timeline and transits. Cross-check timing with one
   dasha_variant only when it helps, and say it is a cross-check.
3. Do not fetch what the fixed context already has. Fetch only what changes the answer.
   You have {rounds} rounds of tool calls; you may call several tools in one round.

Then stop calling tools and write short findings, one per line, each ending with the ref of
the tool result it rests on in square brackets, e.g.
- 7th lord Jupiter sits in the 1st, neutral dignity [tool:house(7)]
- Rule MAR-01 holds in part: 7th lord not in 6/8/12 [pattern:MAR-01]
Say plainly where rules disagree or the chart is mixed. Never predict death, illness,
lawsuits or money outcomes as verdicts. A dosha is a flag, not a verdict. Never invent a fact
the tools did not return.

{style}"""


class ChartExplorer(BaseAstroAgent):
    tools = TOOL_SPECS

    def __init__(self, tools: ChartTools, question: str, bundle: dict, question_kind: str = "broad",
                 experience_mode: str = "balanced",
                 on_tool: Callable[[str, dict], None] | None = None, api_key: str | None = None):
        super().__init__(api_key)
        self.chart_tools = tools
        self.on_tool = on_tool
        rounds = ROUNDS_BY_KIND.get(question_kind, 4)
        if experience_mode == "practitioner":
            rounds += 1
        self.max_tool_rounds = min(rounds, 6)
        already = [key for key in _SUMMARY_KEYS if bundle.get(key)]
        self.system_prompt = _SYSTEM.format(
            question=question.strip()[:600],
            domain_name=bundle.get("domain_name", bundle.get("domain", "")),
            domain=bundle.get("domain", ""),
            kind=question_kind,
            as_of=(bundle.get("profile_facts") or {}).get("as_of", "today"),
            already=", ".join(already) or "very little",
            rounds=self.max_tool_rounds,
            style=PLAIN_INDIAN_ENGLISH,
        )

    def _dispatch_tool(self, name: str, inputs: dict):
        if self.on_tool is not None:
            try:
                self.on_tool(name, inputs or {})
            except Exception:  # progress lines never cost the reader an answer
                log.exception("explorer progress callback failed")
        return self.chart_tools.call(name, inputs or {})

    def explore(self) -> dict:
        """Run the tool loop. Returns {"notes", "explored", "passages"} for
        the bundle; `explored` is every call with the result the model saw."""
        notes, _used = self.run_messages([{
            "role": "user",
            "content": "Look up what this question needs, then write your findings.",
        }])
        return {
            "notes": (notes or "").strip()[:4000],
            "explored": list(self.chart_tools.calls),
            "passages": list(self.chart_tools.passages),
        }


__all__ = ["ChartExplorer", "ROUNDS_BY_KIND", "summarize_call"]
