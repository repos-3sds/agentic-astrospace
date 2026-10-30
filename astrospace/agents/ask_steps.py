"""The reader-facing working steps Ask shows while an answer is prepared.

Every line names a lookup this turn really made: a section the context
bundle carries (`bundle_steps`), or a tool the exploring agent called
(`ask_tools.summarize_call`). Nothing here is the model's thinking, and
nothing names a book or an AI provider (design_principles.md, copy rules).

Headlines stay plain for Indian readers: "your 7th house, marriage and
partners", "Jupiter's period", "your marriage chart". The app shows the
lines one under another, ticking each off as the next arrives.
"""
from __future__ import annotations

import re

# A few plain words per house, for "Looking at your 7th house, marriage
# and partners". Short enough for one line on a phone.
HOUSE_PLAIN = {
    1: "you and your health",
    2: "money and family",
    3: "effort and siblings",
    4: "home and mother",
    5: "children and learning",
    6: "work, debts and rivals",
    7: "marriage and partners",
    8: "sudden changes",
    9: "luck and father",
    10: "career and name",
    11: "gains and friends",
    12: "spending and travel abroad",
}

# Divisional charts by what a reader would call them.
VARGA_PLAIN = {
    "D1": "birth chart",
    "D2": "wealth chart",
    "D3": "siblings chart",
    "D4": "home and property chart",
    "D7": "children chart",
    "D9": "marriage chart",
    "D10": "career chart",
    "D12": "parents chart",
    "D16": "vehicles and comforts chart",
    "D20": "spiritual chart",
    "D24": "education chart",
    "D27": "strengths chart",
    "D30": "challenges chart",
    "D40": "mother's line chart",
    "D45": "father's line chart",
    "D60": "past-life chart",
}

WRITING_STEP = "Our Siddha Agents are writing and checking your answer…"

_SLOW_MOVERS = ("Saturn", "Jupiter", "Rahu", "Ketu")


def house_step(number: int) -> str:
    plain = HOUSE_PLAIN.get(number)
    tail = f", {plain}" if plain else ""
    return f"Looking at your {ordinal(number)} house{tail}…"


def varga_step(division: str | None) -> str:
    name = VARGA_PLAIN.get(str(division or "").upper())
    return f"Reading your {name}…" if name else "Reading a closer chart for this…"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _joined(names: list[str]) -> str:
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} and {names[-1]}"


def bundle_steps(bundle: dict) -> list[str]:
    """One plain line per lookup the bundle holds, in reading order.

    Only sections that are present and non-empty produce a line, so a
    focused bundle (scope.focus_bundle) shows fewer steps, never invented
    ones."""
    steps = ["Reading your birth chart…"]

    primary = [row.get("house") for row in bundle.get("houses") or []
               if row.get("tier") == "primary" and isinstance(row.get("house"), int)]
    for number in primary[:2]:
        steps.append(house_step(number))

    if bundle.get("karakas"):
        names = list(bundle["karakas"])[:3]
        steps.append(f"Checking {_joined(names)} in your chart…")

    chain = (bundle.get("dasha_relevance") or {}).get("chain") or []
    lords = [row.get("lord") for row in chain[:2] if row.get("lord")]
    if lords:
        steps.append(f"Checking your current period, {'–'.join(lords)}…")

    gochara = bundle.get("gochara") or {}
    moving = [p for p in _SLOW_MOVERS if p in (gochara.get("planets") or {})]
    if moving:
        steps.append(f"Looking at where {_joined(moving[:2])} are moving now…")

    vargas = bundle.get("vargas") or {}
    for division, row in list(vargas.items())[:1] if isinstance(vargas, dict) else []:
        if division != "D1" and (row or {}).get("planets"):
            steps.append(varga_step(division))

    if bundle.get("yogas") or bundle.get("doshas"):
        steps.append("Checking yogas and doshas that touch this…")

    if bundle.get("muhurta_search"):
        steps.append("Finding good dates in the calendar…")

    if bundle.get("references") or bundle.get("source_passages"):
        steps.append("Matching your chart against time-tested rules…")

    return steps


# Words a reader must never see while the agent works: books and authors,
# AI providers, chart jargon kept for Practitioner screens, and verdict
# words the product never shows (design_principles.md §4).
_NOTE_BLOCKED = re.compile(
    r"\b(bphs|parashar\w*|phala\w*|saravali|jataka|kalamrit\w*|classic\w*|book\w*|text|"
    r"sloka|shloka|verse|author|"
    r"ai|llm|model|claude|gemini|gpt|openai|anthropic|google|prompt|tool\w*|"
    r"ashtakavarga|bindu\w*|karaka\w*|arudha\w*|upapada|varga\w*|navamsa|dasamsa|"
    r"shadbala|avastha\w*|vimshopaka|jaimini|d\d{1,2}|"
    r"death|die|dies|dying|longevity|accident\w*|disease\w*|illness|divorce\w*|"
    r"curse\w*|danger\w*|doom\w*)\b",
    re.IGNORECASE,
)
_NOTE_SHAPE = re.compile(r"^[A-Za-z][A-Za-z0-9 ,'’\-–]*$")
NOTE_MAX_CHARS = 72


def clean_reader_note(note) -> str | None:
    """The agent's own line for the reader, or None to fall back to the fixed
    line. Kept only when short, plain and free of blocked words."""
    if not isinstance(note, str):
        return None
    text = " ".join(note.split()).rstrip(".…!").strip()
    if not (8 <= len(text) <= NOTE_MAX_CHARS) or not _NOTE_SHAPE.match(text):
        return None
    if _NOTE_BLOCKED.search(text):
        return None
    return f"{text[0].upper()}{text[1:]}…"
