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
import re
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
EFFECTS = ("helps", "hurts", "mixed")

# Every point of view an astrologer reads before a verdict (owner, 2026-10-28:
# "analyse all angles first ... weigh combining each POV"), with the weight
# the explorer starts from; it may move a weight for this chart and says why.
ANGLES = {
    "lagna_houses": ("Houses and their lords from the Lagna", 4),
    "dignity_strength": ("Dignity and strength of the key planets and karakas", 4),
    "dasha": ("The running maha, antar and sub-sub periods", 4),
    "varga": ("The area's divisional chart and the D9", 3),
    "moon_sun_view": ("The same houses from the Moon and the Sun", 3),
    "yogas_doshas": ("Yogas and doshas touching the area", 3),
    "jaimini": ("Jaimini karakas and arudhas", 2),
    "transits": ("Transits now and in the window", 2),
    "ashtakavarga": ("Ashtakavarga bindus", 2),
    "nakshatra": ("Birth stars and their lords", 1),
}
# What a Guided reader sees for each angle in "How we weighed it".
ANGLE_PLAIN = {
    "lagna_houses": "Your birth chart for this area",
    "dignity_strength": "Strength of the planets that matter here",
    "dasha": "Your current time period",
    "varga": "The detailed chart for this area",
    "moon_sun_view": "Seen from your Moon and Sun",
    "yogas_doshas": "Special combinations in your chart",
    "jaimini": "Another classical way of reading",
    "transits": "Planets moving now",
    "ashtakavarga": "Planet support score",
    "nakshatra": "Your birth stars",
}
_REF = re.compile(r"tool:\w+(?:\([^)]*\))?|pattern:[A-Z]+-\d+")
_EMPTY_GROUP = re.compile(r"[\[(]\s*(?:[,;]\s*)*[\])]")
_EXTRA_COMMAS = re.compile(r"\s*([,;])(?:\s*[,;])+")


def _plain_why(text: str) -> str:
    """Drops tool and pattern refs from an angle's reason, then the empty
    brackets and runs of commas they leave behind."""
    text = _REF.sub("", text)
    text = _EMPTY_GROUP.sub("", text)
    text = _EXTRA_COMMAS.sub(r"\1", text)
    text = re.sub(r"\s+([,;.])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip(" ,;")


def weighing_view(angles: list[dict] | None, overall: dict | None) -> dict | None:
    """The reader-facing "How we weighed it" card: each angle's call and
    weight in a fixed order, its reason without internal refs, and the
    combined band."""
    by_key = {a.get("angle"): a for a in angles or [] if isinstance(a, dict) and a.get("angle") in ANGLES}
    if not by_key or not overall:
        return None
    rows = []
    for key, (label, default_weight) in ANGLES.items():
        row = by_key.get(key)
        if not row or row.get("call") not in ANGLE_CALLS:
            continue
        rows.append({
            "key": key, "label": label, "plain_label": ANGLE_PLAIN[key],
            "call": row["call"],
            "weight": max(1, min(5, int(row.get("weight") or default_weight))),
            "why": _plain_why(str(row.get("why") or ""))[:300],
        })
    return {"angles": rows, "overall": overall}


ANGLE_CALLS = {"good": 2, "moderate": 1, "neutral": 0, "mixed": 0, "weak": -1, "bad": -2}
# Weighted average of the calls -> the overall band the answer must follow.
BANDS = ((1.25, "good"), (0.5, "moderately good"), (-0.5, "mixed"), (-1.25, "weak, go carefully"))


def combine_angles(angles: list[dict]) -> dict | None:
    """The weighted call over every judged angle, computed here rather than
    left to the model so one strong-sounding number cannot decide alone."""
    rows = [a for a in angles or [] if isinstance(a, dict) and a.get("angle") in ANGLES
            and a.get("call") in ANGLE_CALLS]
    if not rows:
        return None
    total = sum(max(1, min(5, int(a.get("weight") or ANGLES[a["angle"]][1]))) for a in rows)
    score = sum(ANGLE_CALLS[a["call"]] * max(1, min(5, int(a.get("weight") or ANGLES[a["angle"]][1])))
                for a in rows) / total
    band = next((name for floor, name in BANDS if score >= floor), "unfavourable, avoid for now")
    return {"score": round(score, 2), "band": band}

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
# Earning questions are career AND money; the 2026-10-28 "Lilliput" trace
# shows the agent fetching the other set itself, a round late.
RELATED_AREAS = {"career": ("wealth",), "wealth": ("career",)}
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
                "effect": {"type": "string", "enum": list(EFFECTS),
                           "description": "For this question: helps, hurts or mixed."},
                "why": {"type": "string", "description": "The rule's condition, whether this chart meets it, with tool refs."},
            }, "required": ["id", "verdict", "effect", "why"]}},
            "angles": {"type": "array", "items": {"type": "object", "properties": {
                "angle": {"type": "string", "enum": list(ANGLES)},
                "call": {"type": "string", "enum": list(ANGLE_CALLS)},
                "weight": {"type": "integer", "minimum": 1, "maximum": 5,
                           "description": "How strong and relevant this angle is for THIS chart and question."},
                "why": {"type": "string", "description": "What this angle shows, with tool refs; why this weight."},
            }, "required": ["angle", "call", "weight", "why"]},
                "description": "Every angle, judged on its own before combining. Refused until all are present."},
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

=== HOW YOU MUST JUDGE (read this first, follow it every time) ===
A. Judge EVERY point of view before forming any view. No single fact, number or rule decides.
B. Weigh by influence. The running period, the house lords and the strength of the key planets
   matter most (weight 4). The divisional chart, the Moon and Sun views and the yogas come next
   (3). Jaimini, transits and Ashtakavarga support (2). The birth star colours (1).
C. Ashtakavarga is a support, not a judge. Bindus confirm or soften what the lords and periods
   show; a low bindu count alone never makes the answer "no".
D. Judge the area's MAIN houses for this question. A weak supporting house (e.g. the 5th for
   work or earning) lowers a call one step at most.
E. Use the same yardstick every time (step 7b), so the same chart gets the same calls.
F. When the evidence inside an angle points both ways, the call is "mixed", not "weak".

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
   karaka, and the same house and lord in the {varga}. Ashtakavarga bindus support this
   (28+ supportive); they never override the lord and the period.
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
   reverses (the chart shows the opposite). In `why`, name the rule's condition and whether
   this chart meets it; a chart fact alone is not a test. Also give its `effect` for this
   question: helps, hurts or mixed. A rule about a weakness that holds HURTS; when it fails, the
   weakness is absent, which helps a little. A strength rule that fails helps nothing. Use C and H
   rules only as supporting colour and say they are practice.
7b. EVERY ANGLE, THEN WEIGH. Judge each angle on its own first: good, moderate, neutral,
   mixed, weak or bad, for this question. The angles and their starting weights (1-5):
{angles}
   Raise or lower a weight for this chart when an angle is unusually strong or weak here
   (e.g. a debilitated key lord, a very strong yoga) and say why. Submit ALL angles. Code
   combines them into one overall call; never let one angle or one number decide alone.
   Call each angle by the same yardstick every time, so the same chart gets the same calls:
   - Judge from the area's MAIN houses (the area's house list above). A weak supporting house
     (e.g. the 5th for a career question) pulls a call down one step at most; it never makes
     an angle weak or bad on its own when the main houses are strong.
   - Ashtakavarga: a main house at 28+ bindus is good, 25-27 moderate, 22-24 mixed, under 22
     weak. Call the angle by the main houses together, then adjust one step for the rest.
   - Strength: a key lord exalted or own sign is good; debilitated or deeply combust is weak,
     unless cancelled (neecha bhanga) - then moderate. Several key lords split: mixed.
   - Dasha: good when the running lords rule or aspect the main houses and are strong; mixed
     when one helps and one is weak.
8. THE READER'S LIFE. Use what they have told Siddha. If they say they have never worked, the
   answer must start from that, not assume a career already running. Record their facts as
   they said them; never add dates or details they did not give (no "faceless", no "another"
   when they did not say so).
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
            angles="\n".join(f"   - {key}: {label} (weight {w})" for key, (label, w) in ANGLES.items()),
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
                  # D9 is read for every question (dignity, Karakamsha, the
                  # 10th lord's navamsha); the model always fetched it itself,
                  # which cost a round.
                  *([("varga", {"division": "D9"})] if self.plan["varga"] != "D9" else []),
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
            for area in RELATED_AREAS.get(self.domain, ()):
                calls.append(("classical_patterns", {"area": area}))
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

    def _loop_done(self) -> bool:
        # An accepted submission is the result; the model's "done" turn
        # after it cost ~15 s and 1k tokens in the 2026-10-28 run.
        return self.submitted is not None

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
        seen_angles = {a.get("angle") for a in findings.get("angles") or [] if isinstance(a, dict)}
        missing_angles = sorted(set(ANGLES) - seen_angles)
        if (missing or missing_angles) and self.refusals < 2:
            self.refusals += 1
            return {"accepted": False,
                    "missing_verdicts": missing,
                    "missing_angles": missing_angles,
                    "do": "Give a verdict (holds, partly, fails, reverses) for each missing rule and a "
                          "call and weight for each missing angle, then call submit_findings again "
                          "with ALL verdicts and ALL angles."}
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
                           + ". Judge every angle (" + ", ".join(ANGLES) + ") with a call and weight. "
                           + "Fill reader_facts from what the reader said before.",
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
        notes, loop_failed = "", False
        try:
            notes, _used = self.run_messages([{
                "role": "user",
                "content": "Core look-ups for this question (each has a ref you can cite):\n"
                           + compact_json(core)
                           + "\n\nWork through every point of view, call more tools for anything still "
                             "open, then call submit_findings.",
            }])
        except Exception:
            # A provider error mid-loop (Gemini 504 DEADLINE_EXCEEDED twice in
            # the Lilliput re-run) used to throw away every look-up and the
            # weighing with it. Submit over what was gathered instead.
            log.exception("explorer tool loop failed; submitting over what was looked up")
            loop_failed = True
        if self.submitted is None:
            self._force_submit()
        if loop_failed and self.submitted is None:
            raise RuntimeError("explorer failed and could not submit")
        found = self.submitted or {}
        verdicts = {
            row["id"]: {"verdict": row["verdict"],
                        **({"effect": row["effect"]} if row.get("effect") in EFFECTS else {}),
                        "why": str(row.get("why") or "")[:400]}
            for row in found.get("rule_verdicts") or []
            if isinstance(row, dict) and row.get("id") and row.get("verdict") in VERDICTS
        }
        lines = [*(found.get("findings") or [])]
        overall = combine_angles(found.get("angles") or [])
        for row in found.get("angles") or []:
            if isinstance(row, dict) and row.get("angle") in ANGLES:
                lines.append(f"Angle {ANGLES[row['angle']][0]}: {row.get('call')} "
                             f"(weight {row.get('weight')}) - {row.get('why', '')}")
        if overall:
            lines.append(f"Overall, all angles weighed: {overall['band']} (score {overall['score']} "
                         "on a -2 to +2 scale)")
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
            "overall": overall,
            "weighing": weighing_view(found.get("angles"), overall),
        }


__all__ = ["AREA_PLAN", "ChartExplorer", "ROUNDS_BY_KIND", "summarize_call"]
