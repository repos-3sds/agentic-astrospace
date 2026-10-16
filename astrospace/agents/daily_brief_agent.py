"""Agent-written daily brief for the Today screen and its Listen sheet.

`context/daily.py` already computes every per-person signal for the day
(tarabala, chandrabala, the running dasha chain, active gochara, Rahu Kalam
and the other muhurta windows) and turns them into text by picking from fixed
phrase tables. Two people with the same tone got the same sentences. This
agent keeps the computation and replaces only the wording: one structured
model call, no tools, fed the signals the engine already produced.

Two hard limits shape it:

- The spoken script must play in under 90 seconds at the Listen sheet's
  default 0.9x. The sheet estimates 2.35 words a second at 1x
  (listen-sheet.component.ts), so 0.9x is about 2.1 words a second and 90 s
  is about 190 words. SPOKEN_WORD_LIMIT keeps a margin below that; a longer
  script is retried once and then trimmed, never shipped long.
- The same boundary net as Readings (`reading_boundary`) runs over every
  string before anything is returned. A brief that crosses it is retried
  once and otherwise dropped, and the caller keeps the templated brief.
"""
from __future__ import annotations

import json
import math
import re
from typing import Literal

from pydantic import BaseModel, Field

from .base import BaseAstroAgent
from .period_agent import reading_boundary

# Words a second the Listen sheet assumes at 1x, and its default speed.
LISTEN_WORDS_PER_SECOND = 2.35
LISTEN_DEFAULT_SPEED = 0.9
# 175 words is about 83 s at 0.9x: under the 90 s target with room for the
# pauses the natural voice puts between sections.
SPOKEN_WORD_LIMIT = 175
SPOKEN_WORD_TARGET = (130, 165)

SECTION_LABELS = ("Opening", "Overview", "Today", "Why", "Close")


class BriefItem(BaseModel):
    headline: str = Field(description="Short card title, at most 8 words, no trailing full stop.")
    detail: str = Field(description="One sentence naming the signal behind this item.")


class SpokenSection(BaseModel):
    label: Literal["Opening", "Overview", "Today", "Why", "Close"]
    text: str


class DailyBrief(BaseModel):
    headline: str = Field(description="The day in at most 8 words.")
    summary: str = Field(description="One or two plain sentences, at most 30 words, under the headline.")
    focus: str = Field(description="One practical sentence on where to put energy today.")
    do: list[BriefItem] = Field(min_length=1, max_length=3)
    avoid: list[BriefItem] = Field(min_length=1, max_length=3)
    timing_note: str = Field(description="One sentence on timing, using the real window times given.")
    why: list[str] = Field(min_length=1, max_length=3, description="Plain reasons, one sentence each.")
    spoken: list[SpokenSection] = Field(min_length=3, max_length=5)


MODE_GUIDE = {
    "guided": "The reader is new to astrology. Use no Sanskrit terms except a planet's name; explain everything in everyday words.",
    "balanced": "The reader knows the basics. You may name Tarabala, Chandrabala or a dasha lord once each, with a plain gloss.",
    "practitioner": "The reader is a practitioner. You may name the tara, the house from the natal Moon, the tithi, the nakshatra and the dasha lords directly.",
}
TONE_GUIDE = {
    "gentle": "Tone: gentle and warm. Frame cautions as care, never as warnings.",
    "direct": "Tone: direct and clear. Short sentences, no hedging, still kind.",
}

SYSTEM = f"""You write the daily brief in AstroSpace, a Vedic astrology app. The
astrology is already computed for this one person and given to you as JSON.
Your job is wording, not calculation.

Ground every line in the signals given:
- Use only the tara, chandrabala, dasha chain, active transits, muhurta windows
  and the engine's do/avoid candidates in the JSON. Never invent a placement,
  transit, yoga or time. Use window times exactly as given.
- Pick the 2-3 strongest do items and 1-3 avoid items from the candidates.
  Rewrite them so they read as written for this person today, not as stock
  phrases. Keep each item's underlying signal.
- If `subject` is not "you", write about that person by first name in the
  third person; otherwise address the reader as "you".

Boundaries, non-negotiable:
- Never predict death, lifespan, illness, a medical, legal or investment
  outcome. Health stays at energy and rest.
- A dosha or difficult transit is a flag, not a verdict. Nothing is certain
  or unavoidable.
- Remedies, if any, are traditional practice, never something to pay for.

The `spoken` script is read aloud by a voice. It must:
- use sections in this order: Opening, Overview, Today, Why, Close (Why may
  be dropped for a guided reader);
- open with "Namaste, <first name>." and the date;
- total {SPOKEN_WORD_TARGET[0]}-{SPOKEN_WORD_TARGET[1]} words across all sections, and never
  more than {SPOKEN_WORD_LIMIT}. Count them;
- be plain speech: no markdown, no lists, no emoji, no abbreviations, times
  written as a voice would say them ("ten twenty-four to eleven fifty-two").

Deliver the result by calling the tool once.
"""

OVER_LIMIT_NOTE = (
    "\n\nYour previous spoken script was {words} words. Rewrite it to "
    f"{SPOKEN_WORD_TARGET[0]}-{SPOKEN_WORD_TARGET[1]} words in total. Keep the other fields."
)
BOUNDARY_NOTE = (
    "\n\nYour previous draft crossed a boundary ({kind}). Rewrite it without any "
    "statement about death, lifespan, medical, legal or investment outcomes, or a "
    "dosha or transit as a fixed verdict."
)


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def spoken_words(brief: DailyBrief) -> int:
    return sum(word_count(section.text) for section in brief.spoken)


def listen_seconds(words: int, speed: float = LISTEN_DEFAULT_SPEED) -> int:
    """The Listen sheet's own estimate, so the number matches what it shows."""
    return max(12, math.ceil(words / LISTEN_WORDS_PER_SECOND / speed))


def trim_spoken(brief: DailyBrief, limit: int = SPOKEN_WORD_LIMIT) -> DailyBrief:
    """Cut whole sentences from the longest middle sections until it fits.

    Opening and Close are kept whole: they are short and the script sounds
    broken without them. Only the last resort after a rewrite was asked for.
    """
    sections = [section.model_copy() for section in brief.spoken]
    while sum(word_count(s.text) for s in sections) > limit:
        middle = [s for s in sections if s.label not in ("Opening", "Close")] or sections
        longest = max(middle, key=lambda s: word_count(s.text))
        sentences = re.split(r"(?<=[.!?])\s+", longest.text.strip())
        if len(sentences) > 1:
            longest.text = " ".join(sentences[:-1])
        else:
            words = longest.text.split()
            over = sum(word_count(s.text) for s in sections) - limit
            longest.text = " ".join(words[: max(1, len(words) - over)]).rstrip(",;:") + "."
    sections = [s for s in sections if s.text.strip()]
    return brief.model_copy(update={"spoken": sections})


def brief_boundary(brief: DailyBrief) -> str | None:
    texts = [brief.headline, brief.summary, brief.focus, brief.timing_note, *brief.why]
    texts += [f"{item.headline}. {item.detail}" for item in [*brief.do, *brief.avoid]]
    texts += [section.text for section in brief.spoken]
    for text in texts:
        kind = reading_boundary(text)
        if kind:
            return kind
    return reading_boundary(" ".join(texts))


def brief_input(payload: dict, first_name: str, date_label: str) -> dict:
    """The signals the model may use, and nothing it could mistake for more.

    KB references, colours, lucky numbers and panchanga detail are left out:
    the brief does not speak to them, and every extra field is tokens paid on
    every brief.
    """
    context = payload.get("context") or {}
    return {
        "first_name": first_name,
        "subject": payload.get("subject"),
        "relation": payload.get("relation"),
        "date": date_label,
        "vara": payload.get("vara"),
        "engine_verdict": {
            "tone": payload["verdict"]["tone"],
            "headline": payload["verdict"]["headline"],
        },
        "tarabala": payload.get("tarabala"),
        "chandrabala": payload.get("chandrabala"),
        "star_of_day": payload.get("star_of_day"),
        "dasha_chain": context.get("dasha_chain", [])[:3],
        "active_transits": [
            {k: row.get(k) for k in ("name", "planet", "severity", "houses", "summary") if row.get(k) is not None}
            for row in context.get("active_gochara", [])[:4]
        ],
        "muhurta_windows": payload.get("muhurta_windows", []),
        "do_candidates": [{"headline": r.get("headline"), "text": r.get("text")} for r in payload.get("do_today", [])],
        "avoid_candidates": [{"headline": r.get("headline"), "text": r.get("text")} for r in payload.get("avoid_today", [])],
        "engine_reasons": payload.get("reading", {}).get("plain_why", []),
    }


class DailyBriefAgent(BaseAstroAgent):
    system_prompt = SYSTEM
    tools = []

    def write(self, payload: dict, *, first_name: str, date_label: str,
              tone: str = "direct", mode: str = "balanced") -> DailyBrief | None:
        """One brief, or None when the model could not produce a safe one."""
        signals = json.dumps(brief_input(payload, first_name, date_label), ensure_ascii=False, default=str)
        prompt = (
            f"{MODE_GUIDE.get(mode, MODE_GUIDE['balanced'])}\n"
            f"{TONE_GUIDE.get(tone, TONE_GUIDE['direct'])}\n\n"
            f"Today's computed signals:\n{signals}"
        )
        note = ""
        too_long: DailyBrief | None = None
        for _attempt in range(2):
            brief = self.run_structured([{"role": "user", "content": prompt + note}], DailyBrief,
                                        tool_name="deliver_daily_brief")
            kind = brief_boundary(brief)
            if kind:
                note = BOUNDARY_NOTE.format(kind=kind)
                continue
            words = spoken_words(brief)
            if words > SPOKEN_WORD_LIMIT:
                too_long = brief
                note = OVER_LIMIT_NOTE.format(words=words)
                continue
            return brief
        # A safe draft that only ran long is trimmed rather than thrown away.
        if too_long is None:
            return None
        trimmed = trim_spoken(too_long)
        return None if brief_boundary(trimmed) else trimmed
