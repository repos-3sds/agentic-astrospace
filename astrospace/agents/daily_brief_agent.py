"""Agent-written daily brief for the Today screen and its Listen sheet.

`context/daily.py` already computes every per-person signal for the day
(tarabala, chandrabala, the running dasha chain, active gochara, Rahu Kalam
and the other muhurta windows) and turns them into text by picking from fixed
phrase tables. Two people with the same tone got the same sentences. This
agent keeps the computation and replaces only the wording: one structured
model call, no tools, fed the signals the engine already produced.

What it covers is what the templated brief covers (context/daily.py), so
nothing a reader had before goes missing:

- the day's verdict and its narrative (`_verdict`), ending in the practical
  close the Why sheet shows;
- the tara, the Moon (chandrabala, and chandrashtama when it falls), the slow
  transits that support or test the chart, and the running dasha lord;
- do and avoid across the engine's life domains (Finance, Love, Health,
  Growth, Career) plus the tara row and personal ghatak markers, which reach
  the model through the engine's do/avoid candidates;
- energy and the love, money, work, health and growth tones (`_reading`);
- the timing windows: Rahu Kalam, Yamaganda, Gulika and Abhijit;
- the plain reasons. The technical reasons stay the engine's own list: they
  are facts, not wording.

`coverage_gaps` checks the parts that can be checked mechanically and sends
the draft back once when one is missing.

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
import os
import re
from typing import Literal

from pydantic import BaseModel, Field

from .base import BaseAstroAgent
from .period_agent import reading_boundary
from .style import PLAIN_INDIAN_ENGLISH
from ..config import flag

# Words a second the Listen sheet assumes at 1x, and its default speed.
LISTEN_WORDS_PER_SECOND = 2.35
LISTEN_DEFAULT_SPEED = 0.9
# 175 words is about 83 s at 0.9x: under the 90 s target with room for the
# pauses the natural voice puts between sections.
SPOKEN_WORD_LIMIT = 175
SPOKEN_WORD_TARGET = (130, 165)

SECTION_LABELS = ("Opening", "Overview", "Today", "Why", "Close")


def daily_brief_enabled() -> bool:
    """DAILY_BRIEF_AGENT=off stops every brief being written, scheduled or not."""
    return flag("DAILY_BRIEF_AGENT")


class BriefItem(BaseModel):
    headline: str = Field(description=(
        "The card title: a plain action in 2-6 everyday words, no full stop, no astrology "
        "terms. E.g. 'Review numbers and financial plans', 'Focus on routine work', "
        "'Avoid starting new things', 'Avoid long travel'."))
    detail: str = Field(description="One sentence naming the signal behind this item.")


class SpokenSection(BaseModel):
    label: Literal["Opening", "Overview", "Today", "Why", "Close"]
    text: str


class LifeAreas(BaseModel):
    """One sentence per area, as the template's relationship/money/work tones
    and its Finance/Love/Health/Growth/Career domains did."""

    love: str
    money: str
    work: str
    health: str = Field(description="Energy and rest only; never illness or treatment.")
    growth: str


class DailyBrief(BaseModel):
    card_title: str = Field(description=(
        "The card's small header above the headline, 2-5 everyday words on what today "
        "is for, e.g. \"Finish what you started\". Fresh each day; never \"What matters today\"."))
    headline: str = Field(description=(
        "The day in 3-7 words, written fresh for today's signals; never the engine's "
        "headline and never a stock phrase."))
    summary: str = Field(description=(
        "One or two plain sentences, at most 30 words, under the headline, in everyday "
        "words with no astrology terms."))
    narrative: str = Field(description="The day in 50-80 words: tara, Moon, slow transits, then the practical close.")
    practical_close: str = Field(description="The narrative's last sentence: what to actually do with the day.")
    focus: str = Field(description="One practical sentence on where to put energy today.")
    energy: Literal["drained", "fragmented", "steady", "vibrant"]
    areas: LifeAreas
    do: list[BriefItem] = Field(min_length=1, max_length=3)
    avoid: list[BriefItem] = Field(min_length=1, max_length=3)
    timing_note: str = Field(description=(
        "One short sentence about Rahu Kalam only, with its time: what to keep it for. "
        "No other window, no name."))
    why: list[str] = Field(min_length=2, max_length=4, description="Plain reasons, one sentence each: tara, Moon, transits, dasha.")
    spoken: list[SpokenSection] = Field(min_length=3, max_length=5)


MODE_GUIDE = {
    "guided": "The reader is new to astrology. Use no Sanskrit terms except a planet's name; explain everything in everyday words.",
    "balanced": "The reader knows the basics. In why, narrative and the spoken Why you may name Tarabala, Chandrabala or a dasha lord once each, with a plain gloss; the Today card stays plain.",
    "practitioner": "The reader is a practitioner. In why, narrative and the spoken Why you may name the tara, the house from the natal Moon, the tithi, the nakshatra and the dasha lords directly; the Today card stays plain.",
}
TONE_GUIDE = {
    "gentle": "Tone: gentle and warm. Lead with what is steady before what is strained, pair every caution with the step that goes with it, and frame cautions as care, never as warnings.",
    "direct": "Tone: direct. Say the finding first with no cushioning or preamble, then the step. Short sentences, no softening phrases such as \"you might find\" or \"it may be worth\". Direct is not harsh: no scolding, no drama.",
}

SYSTEM = f"""You write the daily brief in AstroSpace, a Vedic astrology app. The
astrology is already computed for this one person and given to you as JSON.
Your job is wording, not calculation.

Ground every line in the signals given:
- Use only the tara, chandrabala, dasha chain, active transits, muhurta windows,
  the engine's verdict and its do/avoid candidates in the JSON. Never invent a
  placement, transit, yoga or time. Use window times exactly as given.
- Keep the engine's verdict tone. A caution day is not rewritten as a good day,
  nor the reverse.
- Cover every area the engine covers:
  * do: every do candidate's signal, in 1-3 items; avoid: every avoid
    candidate's signal, in 1-3 items (a chandrashtama or ghatak candidate is
    always kept). With no avoid candidate, the avoid item is Rahu Kalam.
  * why: the tara, the Moon (say so when chandrashtama is true), the slow
    transits (supporting or testing), and the running dasha lord.
  * areas: love, money, work, health and growth, one sentence each, each tied
    to a signal or to the day's tone. Health is energy and rest only.
  * timing_note: one window only, Rahu Kalam, with its time. The app shows a
    countdown for that window next to the note, so a second time confuses.
    Abhijit Muhurta, when given, may go in the spoken script or the focus.
  * headline: fresh for today, 3-7 words, specific to the signals; never the
    engine's headline or a stock phrase like "a day of friction and flow".
  * card_title: the small header above the headline, 2-5 everyday words on
    what today is for ("Finish what you started", "Money first, then rest").
    Fresh each day, different from the headline, never "What matters today".
  * narrative: tara, Moon and transits, then the practical close.
- Rewrite candidates so they read as written for this person today, not as
  stock phrases.
- The Today card is for people who know no astrology, whatever their
  experience level: card_title, headline, summary and focus are plain everyday
  words, with no astrology terms (no tara or its name, nakshatra, dasha, bala,
  gochara, Rahu, Ketu, Jupiter, Saturn or other planets except the Sun and the
  Moon, transit, Sanskrit). Say what it means for the day instead: "a good day
  for money and plans", not "Sampat Tarabala brings wealth energy". The
  astrology belongs in why, narrative and the spoken Why.
- Do and avoid titles are for people who know no astrology. Each title is a
  plain action in 2-6 everyday words: "Review numbers and financial plans",
  "Focus on routine work", "Avoid starting new things", "Avoid long travel".
  Never put an astrology term in a title: no tara or its name (Sampat,
  Sadhaka...), nakshatra, dasha, bala, gochara, Rahu Kalam, muhurta, planet or
  Sanskrit words. The signal goes in the item's detail, in plain words.
- When the tara is unfavourable, chandrashtama is true or the day's tone is
  caution, say what to hold off on in plain words: starting new things,
  long travel, big purchases or signing commitments.
- Address the reader as `address_as` says. When it is "you", the profile is
  the reader's own: say "you", never their name (the spoken Opening's
  "Namaste, <first name>." is the one exception). Otherwise write about that
  person by first name in the third person. Never put a name in timing_note.

Boundaries, non-negotiable:
- Never predict death, lifespan, illness, a medical, legal or investment
  outcome. Health stays at energy and rest.
- A dosha or difficult transit is a flag, not a verdict. Nothing is certain
  or unavoidable.
- Remedies, if any, are traditional practice, never something to pay for.

The `spoken` script is read aloud by a voice. It must:
- use sections in this order: Opening, Overview, Today, Why, Close (Why may
  be dropped for a guided reader);
- open with "Namaste, <first name>." the date and the place;
- in Today, say the main do, the main avoid and the Rahu Kalam time; in Why,
  the tara, the Moon and one transit or dasha signal;
- total {SPOKEN_WORD_TARGET[0]}-{SPOKEN_WORD_TARGET[1]} words across all sections, and never
  more than {SPOKEN_WORD_LIMIT}. Count them;
- be plain speech: no markdown, no lists, no emoji, no abbreviations, times
  written as a voice would say them ("ten twenty-four to eleven fifty-two").

Deliver the result by calling the tool once.
""" + PLAIN_INDIAN_ENGLISH

OVER_LIMIT_NOTE = (
    "\n\nYour previous spoken script was {words} words. Rewrite it to "
    f"{SPOKEN_WORD_TARGET[0]}-{SPOKEN_WORD_TARGET[1]} words in total. Keep the other fields."
)
BOUNDARY_NOTE = (
    "\n\nYour previous draft crossed a boundary ({kind}). Rewrite it without any "
    "statement about death, lifespan, medical, legal or investment outcomes, or a "
    "dosha or transit as a fixed verdict."
)


# Do/avoid card titles are read by people who know no astrology (Hawk,
# 2026-10-16): no term here may appear in one, and none runs past 6 words.
TITLE_MAX_WORDS = 6
TITLE_JARGON = (
    "tara", "sampat", "sadhaka", "kshema", "vipat", "pratyari", "vadha", "mitra", "janma",
    "nakshatra", "dasha", "bala", "gochara", "rahu", "ketu", "kalam", "muhurta", "abhijit",
    "chandrashtama", "ghatak", "jupiter", "saturn", "mars", "venus", "mercury", "guru",
    "transit", "lagna", "rashi",
)

# The card check matches whole words, so "balance", "transition" and
# "marshal" stay plain while "Tarabala", "Chandrabala" and "Rahu" do not.
CARD_JARGON_PREFIXES = (
    "tara", "sampat", "sadhaka", "kshema", "vipat", "pratyari", "vadha", "janma", "nakshatra",
    "dasha", "gochara", "rahu", "ketu", "kalam", "muhurta", "abhijit", "chandrashtama", "ghatak",
    "lagna", "rashi",
)
CARD_JARGON_WORDS = (
    "transit", "transits", "bala", "guru", "mitra",
    "jupiter", "saturn", "mars", "venus", "mercury",
)


def card_jargon(text: str) -> list[str]:
    """Astrology terms in a line of the Today card, as whole words."""
    return [word for word in re.findall(r"[a-z]+", text.lower())
            if word in CARD_JARGON_WORDS or word.startswith(CARD_JARGON_PREFIXES)
            or word.endswith(("bala", "tara"))]


COVERAGE_NOTE = (
    "\n\nYour previous draft left out: {gaps}. Rewrite it covering them, within the same "
    "word limit for the spoken script."
)


def _window(payload: dict, name: str) -> str | None:
    for row in payload.get("muhurta_windows") or []:
        if row.get("name") == name and row.get("time"):
            return row["time"]
    return None


def _times(window: str) -> list[str]:
    return re.findall(r"\d{1,2}:\d{2}", window)


def _is_own_profile(payload: dict) -> bool:
    return (payload.get("relation") or "self").strip().lower() in ("self", "me", "myself")


def coverage_gaps(brief: "DailyBrief", payload: dict, first_name: str = "") -> list[str]:
    """What the template covered that this draft does not, where that can be
    checked without reading the prose for meaning."""
    gaps: list[str] = []
    rahu = _window(payload, "Rahu Kalam")
    if rahu and not all(t in brief.timing_note for t in _times(rahu)):
        gaps.append(f"the Rahu Kalam time ({rahu}) in timing_note")
    others = [t for row in payload.get("muhurta_windows") or [] if row.get("name") != "Rahu Kalam"
              for t in _times(row.get("time") or "")]
    if any(t in brief.timing_note for t in others):
        gaps.append("only Rahu Kalam in timing_note (one window; drop the other time)")
    engine_headline = ((payload.get("verdict") or {}).get("headline") or "").strip().lower()
    if engine_headline and brief.headline.strip().lower().rstrip(".") == engine_headline:
        gaps.append("a fresh headline for today instead of the engine's")
    title = brief.card_title.strip().lower().rstrip(".")
    if title in ("what matters today", "your rhythm today") or title == brief.headline.strip().lower().rstrip("."):
        gaps.append("a card_title of its own for today, not the fixed header or the headline")
    name = first_name.lower() if first_name else ""
    if name and _is_own_profile(payload):
        named = [brief.headline, brief.summary, brief.focus, brief.timing_note, brief.narrative,
                 *brief.why, *(f"{i.headline} {i.detail}" for i in [*brief.do, *brief.avoid])]
        if any(re.search(rf"\b{re.escape(name)}\b", text.lower()) for text in named):
            gaps.append('"you" instead of the reader\'s name outside the spoken greeting')
    elif name and re.search(rf"\b{re.escape(name)}\b", brief.timing_note.lower()):
        gaps.append("no name in timing_note")
    if (payload.get("chandrabala") or {}).get("chandrashtama"):
        moon_text = " ".join([*brief.why, *(f"{i.headline} {i.detail}" for i in brief.avoid)]).lower()
        if "moon" not in moon_text:
            gaps.append("chandrashtama (the Moon's sensitive day) in why or avoid")
    for field in ("card_title", "headline", "summary", "focus"):
        found = card_jargon(getattr(brief, field))
        if found:
            gaps.append(f"{field} in plain words without astrology terms ({', '.join(found)})")
    for item in [*brief.do, *brief.avoid]:
        title = item.headline.lower()
        if len(title.split()) > TITLE_MAX_WORDS or any(re.search(rf"\b{w}", title) for w in TITLE_JARGON):
            gaps.append(f"a plain action title without astrology terms instead of '{item.headline}'")
    if len(brief.do) < min(len(payload.get("do_today") or []), 3):
        gaps.append("one do item per do candidate")
    if len(brief.avoid) < min(len(payload.get("avoid_today") or []), 3):
        gaps.append("one avoid item per avoid candidate")
    return gaps


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
    areas = brief.areas
    texts = [brief.headline, brief.summary, brief.narrative, brief.practical_close, brief.focus,
             brief.timing_note, *brief.why, areas.love, areas.money, areas.work, areas.health, areas.growth]
    texts += [f"{item.headline}. {item.detail}" for item in [*brief.do, *brief.avoid]]
    texts += [section.text for section in brief.spoken]
    for text in texts:
        kind = reading_boundary(text)
        if kind:
            return kind
    return reading_boundary(" ".join(texts))


def brief_input(payload: dict, first_name: str, date_label: str, place: str | None = None) -> dict:
    """The signals the model may use, and nothing it could mistake for more.

    KB references, colours, lucky numbers and panchanga detail are left out:
    the brief does not speak to them, and every extra field is tokens paid on
    every brief.
    """
    context = payload.get("context") or {}
    return {
        "first_name": first_name,
        "address_as": "you" if _is_own_profile(payload) else first_name,
        "relation": payload.get("relation"),
        "date": date_label,
        "place": place or ((payload.get("provenance") or {}).get("place") or {}).get("city"),
        "vara": payload.get("vara"),
        "engine_verdict": {
            "tone": payload["verdict"]["tone"],
            "score": payload["verdict"].get("day_score", payload["verdict"].get("score")),
            "headline": payload["verdict"]["headline"],
            "narrative": payload["verdict"].get("text"),
        },
        "engine_energy": (payload.get("reading") or {}).get("energy"),
        "tarabala": payload.get("tarabala"),
        "chandrabala": payload.get("chandrabala"),
        "star_of_day": payload.get("star_of_day"),
        # All levels: the engine's Career line reads the finest one (sookshma).
        "dasha_chain": context.get("dasha_chain", []),
        "active_transits": [
            {k: row.get(k) for k in ("name", "planet", "severity", "av_bindus") if row.get(k) is not None}
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

    def write(self, payload: dict, *, first_name: str, date_label: str, place: str | None = None,
              tone: str = "gentle", mode: str = "balanced") -> DailyBrief | None:
        """One brief, or None when the model could not produce a safe one."""
        signals = json.dumps(brief_input(payload, first_name, date_label, place), ensure_ascii=False, default=str)
        prompt = (
            f"{MODE_GUIDE.get(mode, MODE_GUIDE['balanced'])}\n"
            f"{TONE_GUIDE.get(tone, TONE_GUIDE['gentle'])}\n\n"
            f"Today's computed signals:\n{signals}"
        )
        note = ""
        too_long: DailyBrief | None = None
        last_safe: DailyBrief | None = None
        for attempt in range(2):
            brief = self.run_structured([{"role": "user", "content": prompt + note}], DailyBrief,
                                        tool_name="deliver_daily_brief")
            kind = brief_boundary(brief)
            if kind:
                note = BOUNDARY_NOTE.format(kind=kind)
                continue
            gaps = coverage_gaps(brief, payload, first_name)
            words = spoken_words(brief)
            if words > SPOKEN_WORD_LIMIT:
                too_long = brief
                note = OVER_LIMIT_NOTE.format(words=words)
                if gaps:
                    note += COVERAGE_NOTE.format(gaps="; ".join(gaps))
                continue
            if gaps and attempt == 0:
                note = COVERAGE_NOTE.format(gaps="; ".join(gaps))
                too_long = None
                last_safe = brief
                continue
            return brief
        # A safe draft that only ran long is trimmed rather than thrown away;
        # a safe draft with a coverage gap after its rewrite still beats the
        # template's stock phrases.
        if too_long is not None:
            trimmed = trim_spoken(too_long)
            return None if brief_boundary(trimmed) else trimmed
        return last_safe
