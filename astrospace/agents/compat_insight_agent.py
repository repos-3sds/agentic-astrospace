"""Agent-written "About you two" section for the full compatibility report.

`compatibility_guidance.py` turns the Gun Milan rows into fixed lines, one set
per koota. Two couples with the same weak kootas read the same sentences, and
nothing outside the two Moon positions reaches the reader (Hawk, 2026-10-20:
"looks hardcoded, no personalized insights"). This agent keeps every score and
flag the engine computed and adds the parts of both charts the kootas never
look at: each person's 7th house and its lord, Venus, the rising sign, and the
period (dasha) each person is running now.

It is wording, not calculation: one structured model call, no tools, fed only
what the engine produced. The fixed guidance stays as the fallback, so a model
outage or a draft that crosses a boundary costs the reader nothing.

Grounding (Hawk, 2026-10-20: "ground with relevancy and accuracy based on
classics and standard rules", sources not shown on screen): each person's
marriage picture is read only through the BPHS and Phaladeepika rules that
compat_classics.py finds their chart actually meets, and each koota through
its standard meaning. The model names the rule ids it relied on in
``rules_used``, and an id it was not given sends the draft back.

Rules (design_principles.md §4 and §6, agents/style.py):

* Simple English for Indian readers, with no astrology terms on screen
  except planet names in the period line.
* No verdict on whether to marry or stay married. A dosha is a flag.
* No health, longevity, legal or money verdicts; practices are free.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

from pydantic import BaseModel, Field

from .base import BaseAstroAgent
from .compat_classics import classical_rules, navamsa_facts, upapada_facts
from .daily_brief_agent import card_jargon
from .period_agent import reading_boundary
from .style import PLAIN_INDIAN_ENGLISH
from ..core.vedic.compatibility_guidance import _FLAG_TEXT, _KOOTA_TEXT
from ..core.vedic.constants import SIGN_LORDS, SIGNS
from ..config import flag

# Bump when the prompt or schema changes, so saved sections are rewritten.
INSIGHT_VERSION = 3


def compat_insight_enabled() -> bool:
    """COMPAT_INSIGHT_AGENT=off falls back to the fixed guidance everywhere."""
    return flag("COMPAT_INSIGHT_AGENT")


class InsightItem(BaseModel):
    title: str = Field(description="2-6 plain everyday words, no astrology terms, no full stop.")
    detail: str = Field(description="One or two plain sentences, tied to a signal in the JSON.")


class CareItem(InsightItem):
    step: str = Field(description="One small thing the two of them can do together, this week.")


class PersonNote(BaseModel):
    name: str
    how_they_care: str = Field(description=(
        "Two plain sentences on how this person shows love and what they need, read through "
        "the classical rules given for them and their Venus and Moon. No astrology terms."))
    what_helps: str = Field(description="One plain sentence the partner can do for them.")


class CoupleInsight(BaseModel):
    headline: str = Field(description="This couple in 4-9 plain words, specific to them. No astrology terms.")
    summary: str = Field(description="Two or three plain sentences, at most 45 words, no astrology terms.")
    bond: list[InsightItem] = Field(min_length=2, max_length=3, description="What already works between them.")
    care: list[CareItem] = Field(min_length=1, max_length=3, description="Where a little effort helps, weakest first.")
    each: list[PersonNote] = Field(min_length=2, max_length=2)
    this_period: str = Field(description=(
        "Two or three plain sentences on the periods both are running now and what that "
        "means for the two of them, with the years the periods end."))
    rules_used: list[str] = Field(min_length=2, description=(
        "The ids of the classical rules (from each person's classical_rules) the lines above "
        "rely on. Only ids that were given. Not shown to the reader."))


SYSTEM = """You write the "About you two" section of a couple's compatibility
report in Siddha, a Vedic astrology app. The astrology is already computed for
both people and given to you as JSON. Your job is wording, not calculation.

Ground every line in the JSON:
- Use only the koota rows, safety checks, each person's rising sign, Moon,
  7th house (its sign, its lord and where the lord sits), planets in the 7th,
  Venus, Upapada (the sign read for commitment and the partner), Navamsa
  (the divisional chart read for married life), and the running periods.
  Never invent a placement, yoga, date or score.
- Interpret through the rules given, not from memory:
  * a koota through its `meaning` (standard matching practice);
  * each person's marriage picture only through their `classical_rules`.
    These are rules from the classical texts (BPHS, Phaladeepika, Uttara
    Kalamritam) that code
    has already found their chart meets, each with why it applies. Do not
    bring in any other classical rule, yoga or combination. The plain nature
    of a sign or planet (Venus for love and comfort, Mars for drive, a fire
    sign as direct) is standard and may be used.
  * When a rule has `read_as`, deliver it that way. A rule that does not fit
    the stage or adds nothing may be left out; never stretch one.
  * List the ids you relied on in rules_used. Never name a book, verse or
    rule on screen.
- What makes this personal is what the koota score does not see: each person's
  own 7th house and Venus (how they love, what they need from a partner), their
  Upapada and Navamsa rules (how they hold a commitment), and how their two
  current periods fit together. Use those. Do not just restate
  the koota rows; the app already lists them.
- Name both people by first name. Write to the couple as "you two" or "the
  two of you". Never compare them as better or worse.
- bond: 2-3 things that already work, each tied to a full-score koota, a
  shared sign or element, friendly lords, or a supportive period.
- care: 1-3 areas where a little effort helps, weakest first, each with one
  small step the two of them can take together this week. Low kootas and
  flags (Manglik, Gandanta, Stree Deergha, Rajju, Vedha) go here as "where
  care helps", never as a warning.
- each: one note per person, in the order given.
- this_period: both running periods by planet name is allowed here only as
  "a Jupiter period", with the year it ends; say what the overlap means for
  the two of them in daily life.
- Plain everyday words everywhere the reader sees: no Sanskrit, no koota,
  dosha, nakshatra, rashi, lagna, dasha, upapada, navamsa, vargottama or
  house numbers. Planet names only
  in this_period.
- `stage` says whether they are married or planning to marry. Write for that
  stage. For "married", never discuss whether they should have married. For
  "planning", never say whether they should marry; give understanding and
  steps, the choice is theirs and their families'.

Boundaries, non-negotiable:
- No verdict on the relationship: never "not compatible", "should not marry",
  "will divorce", "will separate", "doomed", or any certain outcome.
- A dosha or a low koota is a flag, not a verdict. Nothing is fixed or
  unavoidable. Say when a flag is cancelled or balanced, as the JSON says.
- Never speak of death, lifespan, illness, children's health, fertility,
  legal or money outcomes. Nadi is daily rhythm only.
- Practices are traditional and free; never something to pay for.

Deliver the result by calling the tool once.
""" + PLAIN_INDIAN_ENGLISH

BOUNDARY_NOTE = (
    "\n\nYour previous draft crossed a boundary ({kind}). Rewrite it without any verdict "
    "on the relationship, any certain outcome, or any statement about death, health, "
    "legal or money outcomes."
)
FIX_NOTE = "\n\nYour previous draft needs these fixes: {gaps}. Rewrite it with them."

# Outcome words the shared net does not cover because they are only a
# boundary in a couple's report.
_RELATIONSHIP_VERDICT = re.compile(
    r"\b(divorce|separation|will separate|break ?up|not compatible|incompatible|should not marry|"
    r"shouldn't marry|doomed|widow|widower|childless)\b",
    re.IGNORECASE,
)


def _sign_from(lagna_sign: str, house: int) -> str:
    return SIGNS[(SIGNS.index(lagna_sign) + house - 1) % 12]


def _running(chart, as_of: datetime | None) -> dict:
    current = (chart.dashas(as_of) or {}).get("current") or {}
    out = {}
    for level in ("mahadasha", "antardasha"):
        row = current.get(level)
        if row:
            out[level] = {"lord": row["lord"], "ends": str(row["end"])[:10]}
    return out


def person_input(chart, profile: dict, as_of: datetime | None = None) -> dict:
    """One person's chart facts the kootas do not use, and nothing else."""
    planets = chart.planet_details()
    lagna = chart.lagna_details()
    dignities = chart.dignities()
    seventh = _sign_from(lagna["sign"], 7)
    seventh_lord = SIGN_LORDS[SIGNS.index(seventh)]

    def place(name: str) -> dict:
        row = planets.get(name) or {}
        return {"sign": row.get("sign"), "house": row.get("house"),
                "dignity": (dignities.get(name) or {}).get("dignity")}

    manglik = (chart.doshas() or {}).get("manglik") or {}
    running = _running(chart, as_of)
    upapada = upapada_facts(int(chart.lagna_lon // 30), chart.positions, dignities)
    navamsa = navamsa_facts(chart.positions, chart.lagna_lon, seventh_lord,
                            chart.planetary_conditions()["rows"])
    return {
        "name": (profile.get("name") or chart.name or "").split(" ")[0],
        "rising_sign": lagna["sign"],
        "moon": {"sign": profile.get("rashi"), "star": profile.get("moon_nakshatra"),
                 "temperament": profile.get("gana")},
        "seventh_house": {
            "sign": seventh,
            "lord": seventh_lord,
            "lord_sits": place(seventh_lord),
            "planets_in_it": [name for name, row in planets.items() if row.get("house") == 7],
        },
        "venus": place("Venus"),
        "mars": place("Mars"),
        "manglik": {"active": bool(manglik.get("active")), "net_severity": manglik.get("net_severity")},
        "running_period": running,
        "upapada": {
            "sign": upapada["upapada"]["sign"],
            "planets_in_it": upapada["upapada"]["planets_in_it"],
            "aspected_by": upapada["upapada"]["aspected_by"],
            "lord": upapada["upapada_lord"],
            "second_from_it": {k: upapada["second_from_upapada"][k] for k in ("sign", "planets_in_it")},
        },
        "navamsa": {
            "seventh_sign": navamsa["seventh_sign"],
            "seventh_lord": navamsa["seventh_lord"],
            "venus": navamsa["venus"],
        },
        "classical_rules": classical_rules(planets, dignities, seventh_lord, manglik, running,
                                           upapada=upapada, navamsa=navamsa),
    }


def _with_meaning(row: dict, table: dict) -> dict:
    """A koota row with its standard meaning; the matching rules are standard
    practice, not in any book we hold (compat_classics.py)."""
    out = {k: row.get(k) for k in ("label", "points", "max", "note")}
    term = (table.get(row.get("label")) or {}).get("term")
    if term:
        out["meaning"] = term
    return out


def insight_input(chart_a, chart_b, result: dict, stage: str = "married",
                  as_of: datetime | None = None) -> dict:
    profiles = result.get("profiles") or {}
    extension = result.get("dashakoota_extension") or {}
    return {
        "stage": "married" if stage == "married" else "planning",
        "score": {"total": result.get("total"), "max": result.get("max")},
        "kootas": [_with_meaning(row, _KOOTA_TEXT) for row in result.get("rows") or []],
        "extra_checks": [_with_meaning(row, _FLAG_TEXT) for row in extension.get("rows") or []],
        "safety_checks": result.get("safety_checks"),
        "people": [
            person_input(chart_a, profiles.get("person1") or {}, as_of),
            person_input(chart_b, profiles.get("person2") or {}, as_of),
        ],
    }


def insight_texts(insight: CoupleInsight) -> list[str]:
    texts = [insight.headline, insight.summary, insight.this_period]
    texts += [f"{i.title}. {i.detail}" for i in insight.bond]
    texts += [f"{i.title}. {i.detail} {i.step}" for i in insight.care]
    texts += [f"{p.how_they_care} {p.what_helps}" for p in insight.each]
    return texts


def insight_boundary(insight: CoupleInsight) -> str | None:
    for text in insight_texts(insight):
        kind = reading_boundary(text)
        if kind:
            return kind
        if _RELATIONSHIP_VERDICT.search(text):
            return "relationship_verdict"
    return reading_boundary(" ".join(insight_texts(insight)))


# Matching terms the Today card's check (card_jargon) has no reason to know.
_MATCH_TERMS = ("koota", "kuta", "varna", "vashya", "yoni", "maitri", "gana", "bhakoot", "nadi",
                "manglik", "dosha", "gandanta", "rajju", "vedha", "deergha", "guna", "milan",
                "upapada", "navams", "vargottam", "arudha", "darapada")


def plain_words_jargon(text: str) -> list[str]:
    """Astrology terms in a line meant for readers who know none, as whole words."""
    found = card_jargon(text)
    return found + [word for word in re.findall(r"[a-z]+", text.lower()) if word.startswith(_MATCH_TERMS)]


def insight_gaps(insight: CoupleInsight, signals: dict) -> list[str]:
    """What can be checked without reading the prose for meaning."""
    gaps: list[str] = []
    for field in ("headline", "summary"):
        found = plain_words_jargon(getattr(insight, field))
        if found:
            gaps.append(f"{field} in plain words ({', '.join(found)})")
    for item in [*insight.bond, *insight.care]:
        found = plain_words_jargon(f"{item.title} {item.step if isinstance(item, CareItem) else ''}")
        if found:
            gaps.append(f"a plain title and step for '{item.title}'")
    given = {rule["id"] for person in signals["people"] for rule in person.get("classical_rules") or []}
    unknown = [rule_id for rule_id in insight.rules_used if rule_id not in given]
    if unknown:
        gaps.append(f"rules_used with only the ids given (not {', '.join(unknown)})")
    names = [p["name"] for p in signals["people"] if p.get("name")]
    whole = " ".join(insight_texts(insight)).lower()
    for name in names:
        if name.lower() not in whole:
            gaps.append(f"{name} by name")
    return gaps


class CompatInsightAgent(BaseAstroAgent):
    system_prompt = SYSTEM
    tools = []

    def write(self, signals: dict) -> CoupleInsight | None:
        """One section, or None when the model could not produce a safe one."""
        prompt = "Both charts, computed:\n" + json.dumps(signals, ensure_ascii=False, default=str)
        note = ""
        last_safe: CoupleInsight | None = None
        for _attempt in range(2):
            insight = self.run_structured([{"role": "user", "content": prompt + note}], CoupleInsight,
                                          tool_name="deliver_couple_insight")
            kind = insight_boundary(insight)
            if kind:
                note = BOUNDARY_NOTE.format(kind=kind)
                continue
            gaps = insight_gaps(insight, signals)
            if not gaps:
                return insight
            last_safe = insight
            note = FIX_NOTE.format(gaps="; ".join(gaps))
        return last_safe
