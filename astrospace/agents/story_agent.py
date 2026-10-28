"""Agent-written Your Story (Guided mode, Explore), grounded in the classics.

Until 2026-10-28 the screen was code inside the app: a headline from four
element labels, and per card one of two or three fixed paragraphs picked from
just two planets' houses. Most people read the same words, and the badges
were fixed (Career always "Blessed", Health always "Watch"). Hawk chose
"AI from classics rules, code backup" for the rebuild.

It is wording, not calculation: one structured model call, no tools, fed only
what the engine produced and the stored rules story_classics.py found this
chart meets. The model names the rule ids it relied on, and an id it was not
given sends the draft back. The badge on each area is decided in code from
the house lord's real strength, never by the model. When the model is off or
fails, story_classics.fallback_story() builds the same shape from plain lines
per placement, so the reader still gets their own chart.

Rules (design_principles.md §4 and §6, agents/style.py):

* Simple English for Indian readers. No astrology terms on screen; planet
  names only in the current chapter.
* No death, health, legal or money verdicts. Energy is rest and routine only.
* A dosha or weak placement is a flag, delivered as where care helps.
* Strengths first, one gentle growth note, never harsh.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..config import flag
from .base import BaseAstroAgent
from .compat_insight_agent import plain_words_jargon
from .period_agent import reading_boundary
from .story_classics import AREA_TITLES, area_tones, chart_facts, section_rules
from .style import PLAIN_INDIAN_ENGLISH

# Bump when the prompt, rules or schema change, so saved stories are rewritten.
STORY_VERSION = 1

AreaKey = Literal["work", "relationships", "money", "energy"]


def story_agent_enabled() -> bool:
    """LIFE_STORY_AGENT=off serves the code backup everywhere."""
    return flag("LIFE_STORY_AGENT")


class Trait(BaseModel):
    title: str = Field(description="2-5 plain everyday words naming the trait, no full stop.")
    detail: str = Field(description="One plain sentence, at most 22 words, saying how it shows in daily life.")


class Area(BaseModel):
    key: AreaKey
    text: str = Field(description="Two plain sentences, at most 40 words, for this person.")
    tip: str = Field(description="One small, concrete thing to do, at most 18 words.")


class LifeStory(BaseModel):
    headline: str = Field(description="This person in 5-10 plain words, specific to them. No astrology terms.")
    summary: str = Field(description="Two plain sentences, at most 40 words, that join the traits into one picture.")
    traits: list[Trait] = Field(min_length=4, max_length=6, description="Personality traits, strongest first.")
    growth: str = Field(description="One or two gentle sentences on one thing to grow, with a small step.")
    areas: list[Area] = Field(min_length=4, max_length=4, description="work, relationships, money, energy, in that order.")
    chapter: str = Field(description=(
        "Two or three plain sentences on the period they are running now and what it puts at the front "
        "of life, naming the planet and the year it ends."))
    rules_used: list[str] = Field(min_length=3, description=(
        "The ids of the classical rules the lines above rely on. Only ids that were given. Not shown."))


SYSTEM = """You write "Your story" in Siddha, a Vedic astrology app: a short,
warm portrait of one person from their birth chart. The astrology is already
computed and given to you as JSON. Your job is wording, not calculation.

Ground every line in the JSON:
- `rules` holds, for each section, the classical rules (from BPHS, Brihat
  Jataka, Saravali, Uttara Kalamritam, Phaladeepika) that code has already
  found this chart meets, each with why it applies. Interpret each section
  only through its rules. Do not bring in any other classical rule, yoga or
  combination. The plain nature of a planet or sign is standard and may be
  used. When a rule has `read_as`, deliver it that way. A rule may be left
  out if it adds nothing; never stretch one.
- When a rule says how strongly it shows (`applies_because` says strong,
  in part, or faintly), let that set how firmly you say it.
- `yogas` are the engine's active combinations with their plain meaning; use
  one only if it fits the section.
- List the ids you relied on in rules_used. Never name a book, verse or rule.

What to write:
- traits: 4-6 personality traits, strongest first, from the personality
  rules. Combine placements where they agree (rising sign with Moon, or the
  Moon's star with its sign); this is what makes the portrait this person's
  own rather than a sign description. Each trait: a short title and one
  sentence on how it shows in daily life.
- headline and summary: the whole person in plain words.
- growth: one gentle thing to grow, drawn from the same rules (a quick
  temper, a busy mind, holding on too long), with one small step. Never
  harsh, never a flaw of character.
- areas: work, relationships, money and energy, in that order, each from its
  own section's rules. `tones` says how each area leans (strong, steady or
  gentle); write to match it. Gentle means "asks for more patience and care",
  never bad. Each with one small, concrete tip.
- chapter: the running period (`running`), by planet name, with the year it
  ends, and what it puts at the front of life, from the chapter rules.

Plain words everywhere: second person ("you"), no Sanskrit, no house
numbers, and none of: ascendant, rising, lagna, rashi, nakshatra, dasha,
lord, yoga, dosha, manglik, navamsa, upapada, Moon, Sun or any other
planet name. Planet names are allowed only in chapter. No names of people.

Boundaries, non-negotiable:
- Never speak of death, lifespan, illness, the body failing, children's
  health or fertility, legal or money outcomes. Energy is rest, sleep, food
  and routine only.
- Nothing is fixed or unavoidable. A weak placement is where care helps.
- No verdicts on marriage, divorce or anyone's character.
- Practices are free and simple; never something to pay for.

Deliver the result by calling the tool once.
""" + PLAIN_INDIAN_ENGLISH

BOUNDARY_NOTE = (
    "\n\nYour previous draft crossed a boundary ({kind}). Rewrite it without any statement about "
    "death, illness, legal or money outcomes, or anything fixed or unavoidable."
)
FIX_NOTE = "\n\nYour previous draft needs these fixes: {gaps}. Rewrite it with them."

# Words the reader of this screen should never meet, beyond the shared list.
_STORY_TERMS = ("ascendant", "rising", "lord", "lords", "moon", "sun", "yoga", "yogas")


def story_input(chart, as_of: datetime | None = None) -> dict:
    facts = chart_facts(chart, as_of)
    return {
        "rules": section_rules(facts),
        "tones": area_tones(facts),
        "yogas": facts["yogas"],
        "running": facts["running"],
        "_facts": facts,
    }


def model_input(signals: dict) -> dict:
    """What the model sees: everything but the raw facts used to build it."""
    return {k: v for k, v in signals.items() if not k.startswith("_")}


def story_texts(story: LifeStory) -> list[str]:
    texts = [story.headline, story.summary, story.growth, story.chapter]
    texts += [f"{t.title}. {t.detail}" for t in story.traits]
    texts += [f"{a.text} {a.tip}" for a in story.areas]
    return texts


# The shared net reads verdicts ("you will need surgery"); a portrait has no
# reason to name an illness at all, so any of these words sends it back.
_BODY_OR_HARM = re.compile(
    r"\b(disease|diseases|illness|ill|sick|sickly|sickness|cancer|diabetes|tumou?r|surgery|operation|"
    r"hospital|chronic|infection|injury|injuries|accident|accidents|die|dies|death|dying|divorce|"
    r"poverty|bankrupt|lawsuit|court case)\b",
    re.IGNORECASE,
)


def story_boundary(story: LifeStory) -> str | None:
    for text in story_texts(story):
        kind = reading_boundary(text)
        if kind:
            return kind
        if _BODY_OR_HARM.search(text):
            return "illness_or_harm"
    return reading_boundary(" ".join(story_texts(story)))


def _jargon(text: str) -> list[str]:
    found = plain_words_jargon(text)
    return found + [w for w in re.findall(r"[a-z]+", text.lower()) if w in _STORY_TERMS and w not in found]


def story_gaps(story: LifeStory, signals: dict) -> list[str]:
    """What can be checked without reading the prose for meaning."""
    gaps: list[str] = []
    for field in ("headline", "summary", "growth"):
        found = _jargon(getattr(story, field))
        if found:
            gaps.append(f"{field} in plain words ({', '.join(found)})")
    for trait in story.traits:
        found = _jargon(f"{trait.title} {trait.detail}")
        if found:
            gaps.append(f"plain words in the trait '{trait.title}' ({', '.join(found)})")
    keys = [area.key for area in story.areas]
    if keys != ["work", "relationships", "money", "energy"]:
        gaps.append("areas in the order work, relationships, money, energy")
    for area in story.areas:
        found = _jargon(f"{area.text} {area.tip}")
        if found:
            gaps.append(f"plain words in the {area.key} area ({', '.join(found)})")
    given = {rule["id"] for rules in signals["rules"].values() for rule in rules}
    unknown = [rule_id for rule_id in story.rules_used if rule_id not in given]
    if unknown:
        gaps.append(f"rules_used with only the ids given (not {', '.join(unknown)})")
    personality = {rule["id"] for rule in signals["rules"].get("personality") or []}
    if personality and not personality & set(story.rules_used):
        gaps.append("traits drawn from the personality rules, listed in rules_used")
    period = (signals.get("running") or {}).get("mahadasha")
    if period and period["lord"].lower() not in story.chapter.lower():
        gaps.append(f"the chapter naming the {period['lord']} period")
    return gaps


def to_payload(story: LifeStory, signals: dict) -> dict:
    """The stored and served shape, with each area's badge set in code."""
    tones = signals["tones"]
    return {
        "headline": story.headline,
        "summary": story.summary,
        "traits": [t.model_dump() for t in story.traits],
        "growth": story.growth,
        "areas": [{"key": a.key, "title": AREA_TITLES[a.key], "text": a.text, "tip": a.tip,
                   "tone": tones[a.key]} for a in story.areas],
        "chapter": story.chapter,
        "rules_used": story.rules_used,
    }


class LifeStoryAgent(BaseAstroAgent):
    system_prompt = SYSTEM
    tools = []

    def write(self, signals: dict) -> LifeStory | None:
        """One story, or None when the model could not produce a safe one."""
        prompt = "This person's chart, computed:\n" + json.dumps(model_input(signals), ensure_ascii=False, default=str)
        note = ""
        last_safe: LifeStory | None = None
        for _attempt in range(2):
            story = self.run_structured([{"role": "user", "content": prompt + note}], LifeStory,
                                        tool_name="deliver_life_story")
            kind = story_boundary(story)
            if kind:
                note = BOUNDARY_NOTE.format(kind=kind)
                continue
            gaps = story_gaps(story, signals)
            if not gaps:
                return story
            last_safe = story
            note = FIX_NOTE.format(gaps="; ".join(gaps))
        return last_safe
