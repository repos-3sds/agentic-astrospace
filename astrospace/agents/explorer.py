"""The exploring step of the tool-using Ask (ASK_ENGINE=agent, see
agents/ask_engine.py).

Before the domain specialist writes its structured answer, this agent reads
the question and the fixed domain bundle, then works through the read-only
chart tools in agents/ask_tools.py. It writes nothing the reader sees. Its
tool results go into the bundle as `explored`, where the specialist reads them
and may cite their refs, and the verifier checks every citation against
exactly those refs.

The first test (2026-10-28, a career question) showed what a free hand gets
wrong: it stopped after two of five rounds, never saw that the career planet
was debilitated, and read a transit rule backwards. So coverage is no longer
left to the model:

- Code runs the core look-ups for the life area before the model starts
  (AREA_PLAN: every planet's dignity and strength, the area's houses from the
  Lagna, the Moon and the Sun, its D-chart, the Jaimini karakas, the dasha
  down to the sub-sub period, transits, Ashtakavarga, the area's rules).
- The model then explores further and must finish by calling submit_findings
  with a verdict (holds / partly / fails / reverses) for every A and B rule it
  was shown. Code refuses the submission, naming what is missing, until it is
  complete, and the round budget leaves room for that.
- Only rules judged holds or partly become citable (verifier.explored_refs);
  a rule that fails or reverses reaches the specialist as a warning.

Safety, scope, the dosha rule and the checker stay in code, untouched.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Callable

from pydantic import BaseModel, ConfigDict

from .ask_tools import TOOL_SPECS, ChartTools, summarize_call
from .base import BaseAstroAgent, compact_json
from .style import PLAIN_INDIAN_ENGLISH

log = logging.getLogger(__name__)

# Tool rounds per question kind (agents/scope.py), after the core look-ups
# code has already run. Practitioner readers get two more, capped at eight.
ROUNDS_BY_KIND = {"today": 3, "narrow": 4, "explain": 5, "broad": 6}
MAX_ROUNDS = 8

VERDICTS = ("holds", "partly", "fails", "reverses")

# What every reading in a life area is checked from: its houses (counted from
# the Lagna, the Moon and the Sun), its divisional chart, and its karakas.
AREA_PLAN: dict[str, dict] = {
    "career": {"houses": [10, 6, 2, 11], "varga": "D10", "karakas": "Sun, Saturn, Mercury, Jupiter; Amatyakaraka"},
    "wealth": {"houses": [2, 11, 5, 9], "varga": "D2", "karakas": "Jupiter, Venus; 2nd and 11th lords"},
    "marriage": {"houses": [7, 2, 8, 12], "varga": "D9", "karakas": "Venus (Jupiter for a woman's husband); Darakaraka, Upapada"},
    "children": {"houses": [5, 9], "varga": "D7", "karakas": "Jupiter; Putrakaraka"},
    "education": {"houses": [4, 5, 9, 2], "varga": "D24", "karakas": "Mercury, Jupiter"},
    "family_property": {"houses": [4, 2, 11], "varga": "D4", "karakas": "Mars (land), Moon (mother), Venus (vehicles)"},
    "health": {"houses": [1, 6, 8], "varga": "D30", "karakas": "Sun (vitality), Moon (mind); Lagna lord"},
    "foreign": {"houses": [12, 9, 3, 7], "varga": "D9", "karakas": "Rahu, Moon; 12th and 9th lords"},
    "litigation": {"houses": [6, 8, 12], "varga": "D30", "karakas": "Mars, Saturn; 6th lord"},
    "spirituality": {"houses": [9, 12, 5], "varga": "D20", "karakas": "Jupiter, Ketu; Atmakaraka, Karakamsha"},
    "personality": {"houses": [1], "varga": "D9", "karakas": "Lagna lord, Moon, Sun; Atmakaraka"},
}
_DEFAULT_PLAN = {"houses": [1], "varga": "D9", "karakas": "Lagna lord, Moon"}

SUBMIT_SPEC = {
    "name": "submit_findings",
    "description": "Finish. Give a verdict for every A and B rule you were shown, the reader's own life facts, and your findings. Refused until complete.",
    "input_schema": {
        "type": "object",
        "properties": {
            "rule_verdicts": {"type": "array", "items": {"type": "object", "properties": {
                "id": {"type": "string", "description": "pattern:XXX-NN"},
                "verdict": {"type": "string", "enum": list(VERDICTS)},
                "why": {"type": "string", "description": "The chart facts, with their tool refs."},
            }, "required": ["id", "verdict", "why"]}},
            "reader_facts": {"type": "array", "items": {"type": "string"},
                             "description": "What the reader has told Siddha about their life that bears on this question (empty if none)."},
            "findings": {"type": "array", "items": {"type": "string"},
                         "description": "Short lines, each ending with the [ref] it rests on."},
            "timing": {"type": "string", "description": "For when-questions: the windows, down to the sub-sub period, and what supports or blocks each."},
            "personality_in_period": {"type": "string", "description": "How this person's nature meets the running periods and transits."},
            "guidance": {"type": "object", "properties": {
                "take_care": {"type": "array", "items": {"type": "string"}},
                "consider": {"type": "array", "items": {"type": "string"}},
                "avoid": {"type": "array", "items": {"type": "string"}},
                "do": {"type": "array", "items": {"type": "string"}}}},
            "remedies": {"type": "array", "items": {"type": "object", "properties": {
                "mantra_id": {"type": "string"}, "why_for_this_reader": {"type": "string"}},
                "required": ["mantra_id", "why_for_this_reader"]},
                "description": "1-2 from the remedies look-up."},
        },
        "required": ["rule_verdicts", "reader_facts", "findings"],
    },
}

_SYSTEM = """You are the research step of Siddha, a Vedic astrology app. Work like a careful,
senior astrologer who reads a chart from every side before saying anything.

QUESTION: {question}
Life area: {domain_name} ({domain}). Question kind: {kind}. Today is {as_of}.

WHAT THE READER HAS TOLD SIDDHA BEFORE (their own words, from other chats on this profile):
{history}

ALREADY LOOKED UP FOR YOU (in the first message): every planet's dignity and strength, the
{houses} houses from the Lagna and from the Moon and the Sun, the {varga}, the Jaimini karakas,
the birth stars (nakshatras) of the Lagna and every planet, the dasha running now with the next
three years of sub-sub periods, transits, Ashtakavarga, yogas and doshas, this chart's remedy
plan, and the classical rules for this area. Read all of it before calling anything.

Work through every point of view before you finish:
1. DIGNITY FIRST. For each planet that matters here (house lords, karakas: {karakas}),
   note exaltation, debilitation, own sign, combustion, retrogression and Shadbala band. A
   debilitated or combust key planet changes the reading; never skip it. Check neecha-bhanga.
2. THREE LAGNAS. Judge the area's houses from the Lagna, the Moon and the Sun. Where they
   agree the result is firm; where they differ, say so.
3. HOUSE, LORD, KARAKA, VARGA. The house, where its lord sits and how strong it is, the
   karaka, and the same house and lord in the {varga}. Use Ashtakavarga bindus as weight
   (28+ supportive).
4. JAIMINI. The relevant chara karaka and arudha (e.g. Amatyakaraka for work, Darakaraka and
   Upapada for marriage).
5. TIMING. Mahadasha, antardasha AND pratyantardasha (sub-sub period) windows, with which
   house each lord rules and occupies. Then transits counted from the Moon AND the Lagna, with
   bindus. Read transit rules exactly as written: in the classics Jupiter in the 10th from the
   Moon is a strain, not a boost.
6. NAKSHATRAS. Read the stars of the Lagna, the Moon and each key lord: star lord, deity,
   symbol, gana. Apply the Moon's classical star traits scaled by the Moon's strength. Use the
   deity's story to colour HOW the result shows (e.g. Chitra's Vishwakarma: craft, design,
   making). Note whose star each dasha lord sits in; the star lord's house shades that period.
   Story-based colour is practice: say so. It adds texture; it never overrides houses or dashas.
7. RULES. For EVERY A and B rule shown, decide: holds, partly, fails (conditions not met), or
   reverses (the chart shows the opposite). Use C and H rules only as supporting colour and
   say they are practice.
8. THE READER'S LIFE. Use what they have told Siddha. If they say they have never worked, the
   answer must start from that, not assume a career already running. Record their facts as
   they said them; never add dates or details they did not give.
9. PERSONALITY x PERIOD. Tie the person's nature (Lagna and its lord, Moon and its star,
   Atmakaraka) to what the running maha, antar and sub-sub lords and today's transits stir in
   that nature. Say how this person in particular will feel and act in this period.
10. GUIDANCE. From all of the above, list what to TAKE CARE of, what to CONSIDER, what to AVOID
   and what to DO (implement), each tied to a planet, period or house with its ref.
11. REMEDIES. Pick 1-2 from the remedies look-up that fit this reader's situation best (the
   period lord, the stressed area, a flag) and say why in their terms. Never invent one.

Call more tools for anything still open (another house or view, a varga, a dasha_variant as a
cross-check, the classics). You have {rounds} rounds; you may call several tools per round.
Finish by calling submit_findings. It is refused until every A and B rule has a verdict.

Never predict death, illness, lawsuits or money outcomes as verdicts. A dosha is a flag, not a
verdict. Never invent a fact the tools did not return.

{style}"""


def _today(bundle: dict) -> date:
    try:
        return date.fromisoformat(str((bundle.get("profile_facts") or {}).get("as_of"))[:10])
    except ValueError:
        return date.today()


class _Findings(BaseModel):
    """Shape check for a forced submit_findings call; SUBMIT_SPEC is what
    the model is shown."""
    model_config = ConfigDict(extra="allow")
    rule_verdicts: list = []
    reader_facts: list = []
    findings: list = []


class ChartExplorer(BaseAstroAgent):
    tools = [*TOOL_SPECS, SUBMIT_SPEC]
    # submit_findings is a large call and Gemini's thinking shares this cap;
    # at 4096 the explorer's last turn came back empty (2026-10-28 A/B).
    max_output_tokens = 16384

    def __init__(self, tools: ChartTools, question: str, bundle: dict, question_kind: str = "broad",
                 experience_mode: str = "balanced", history: list[str] | None = None,
                 on_tool: Callable[[str, dict], None] | None = None, api_key: str | None = None):
        super().__init__(api_key)
        self.chart_tools = tools
        self.on_tool = on_tool
        self.domain = bundle.get("domain", "")
        self.plan = AREA_PLAN.get(self.domain, _DEFAULT_PLAN)
        self.today = _today(bundle)
        self.submitted: dict | None = None
        self.refusals = 0
        rounds = ROUNDS_BY_KIND.get(question_kind, 5)
        if experience_mode == "practitioner":
            rounds += 2
        self.max_tool_rounds = min(rounds, MAX_ROUNDS)
        said = [f"- {line}" for line in (history or []) if line.strip()][:12]
        self.system_prompt = _SYSTEM.format(
            question=question.strip()[:600],
            domain_name=bundle.get("domain_name", self.domain),
            domain=self.domain,
            kind=question_kind,
            as_of=self.today.isoformat(),
            history="\n".join(said) or "(nothing yet)",
            houses=", ".join(str(h) for h in self.plan["houses"]),
            varga=self.plan["varga"],
            karakas=self.plan["karakas"],
            rounds=self.max_tool_rounds,
            style=PLAIN_INDIAN_ENGLISH,
        )

    # Core look-ups -----------------------------------------------------------

    def core_calls(self) -> list[tuple[str, dict]]:
        calls: list[tuple[str, dict]] = [("chart_overview", {}), ("strengths", {})]
        for house in self.plan["houses"]:
            calls.append(("house", {"number": house}))
        primary = self.plan["houses"][0]
        calls += [("house", {"number": primary, "view": "moon"}),
                  ("house", {"number": primary, "view": "sun"}),
                  ("varga", {"division": self.plan["varga"]}),
                  ("jaimini", {}),
                  ("nakshatra", {}),
                  ("ashtakavarga", {}),
                  ("dasha_at", {}),
                  ("dasha_timeline", {"start": self.today.isoformat(),
                                      "end": self.today.replace(year=self.today.year + 3).isoformat()}),
                  ("transits", {}),
                  ("yogas_doshas", {}),
                  ("remedies", {})]
        if self.domain:
            calls.append(("classical_patterns", {"area": self.domain}))
        return calls

    def run_core(self) -> list[dict]:
        return [self._dispatch_tool(name, args) for name, args in self.core_calls()]

    # Tool dispatch ----------------------------------------------------------

    def _dispatch_tool(self, name: str, inputs: dict):
        if name == "submit_findings":
            return self._submit(inputs or {})
        if self.on_tool is not None:
            try:
                self.on_tool(name, inputs or {})
            except Exception:  # progress lines never cost the reader an answer
                log.exception("explorer progress callback failed")
        return self.chart_tools.call(name, inputs or {})

    def required_rules(self) -> set[str]:
        """Every A and B rule the model has been shown this turn."""
        out: set[str] = set()
        for call in self.chart_tools.calls:
            for row in (call.get("result") or {}).get("patterns") or []:
                if row.get("tier") in ("A", "B") and row.get("id"):
                    out.add(row["id"])
        return out

    def _submit(self, findings: dict) -> dict:
        judged = {
            row.get("id") for row in findings.get("rule_verdicts") or []
            if isinstance(row, dict) and row.get("verdict") in VERDICTS
        }
        missing = sorted(self.required_rules() - judged)
        if missing and self.refusals < 2:
            self.refusals += 1
            return {"accepted": False,
                    "missing_verdicts": missing,
                    "do": "Give a verdict (holds, partly, fails, reverses) for each missing rule, "
                          "then call submit_findings again with ALL verdicts."}
        self.submitted = findings
        return {"accepted": True, "do": "Done. Reply with the single word: done."}

    def _force_submit(self) -> None:
        """The loop ended without an accepted submit_findings (the model went
        quiet, ran out of rounds, or was refused twice): one more call that
        can only be submit_findings, over everything looked up so far."""
        looked_up = [{"ref": c.get("ref"), "result": c.get("result")} for c in self.chart_tools.calls]
        rules = sorted(self.required_rules())
        try:
            found = self.run_structured([{
                "role": "user",
                "content": "Everything looked up for this question:\n" + compact_json(looked_up)
                           + "\n\nNow call submit_findings. Give a verdict for each of these rules: "
                           + (", ".join(rules) or "(none)")
                           + ". Fill reader_facts from what the reader said before.",
            }], _Findings, tool_name="submit_findings", input_schema=SUBMIT_SPEC["input_schema"])
        except Exception:
            log.exception("explorer forced submit failed")
            return
        self.submitted = found.model_dump()

    # Run -------------------------------------------------------------------

    def explore(self) -> dict:
        """Run the core look-ups, then the tool loop. Returns {"notes",
        "explored", "passages", "verdicts", "reader_facts"} for the bundle;
        `explored` is every call with the result the model saw."""
        core = self.run_core()
        notes, _used = self.run_messages([{
            "role": "user",
            "content": "Core look-ups for this question (each has a ref you can cite):\n"
                       + compact_json(core)
                       + "\n\nWork through every point of view, call more tools for anything still "
                         "open, then call submit_findings.",
        }])
        if self.submitted is None:
            self._force_submit()
        found = self.submitted or {}
        verdicts = {
            row["id"]: {"verdict": row["verdict"], "why": str(row.get("why") or "")[:400]}
            for row in found.get("rule_verdicts") or []
            if isinstance(row, dict) and row.get("id") and row.get("verdict") in VERDICTS
        }
        lines = [*(found.get("findings") or [])]
        if found.get("timing"):
            lines.append(f"Timing: {found['timing']}")
        if found.get("personality_in_period"):
            lines.append(f"Personality in this period: {found['personality_in_period']}")
        for key, label in (("take_care", "Take care"), ("consider", "Consider"),
                           ("avoid", "Avoid"), ("do", "Do")):
            for item in (found.get("guidance") or {}).get(key) or []:
                lines.append(f"{label}: {item}")
        plan_ids = {row.get("mantra_id") for call in self.chart_tools.calls if call["tool"] == "remedies"
                    for row in (call.get("result") or {}).get("plan") or []}
        for row in (found.get("remedies") or [])[:2]:
            if isinstance(row, dict) and row.get("mantra_id") in plan_ids:
                lines.append(f"Remedy {row['mantra_id']}: {row.get('why_for_this_reader', '')}")
        if not lines and notes and notes.strip().lower() != "done":
            lines.append(notes.strip())
        return {
            "notes": "\n".join(str(line) for line in lines)[:5000],
            "explored": list(self.chart_tools.calls),
            "passages": list(self.chart_tools.passages),
            "verdicts": verdicts,
            "reader_facts": [str(f)[:300] for f in found.get("reader_facts") or []][:10],
            "submitted": self.submitted is not None,
        }


__all__ = ["AREA_PLAN", "ChartExplorer", "ROUNDS_BY_KIND", "summarize_call"]
