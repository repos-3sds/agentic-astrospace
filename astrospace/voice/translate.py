"""Telugu text for natural read-aloud of the morning brief.

The Today brief is assembled on the device in English, and Chirp's Telugu voice
can only sound Telugu when the words are Telugu, so the Listen sheet asks for a
Telugu rendering of its sections before playing them in Telugu. The rendering
uses the same model and the same "simple Telugu" register as Ask answers.

The brief is already safe English, but a translation can still drift into a
verdict, so every rendering passes the same output checks as an Ask answer and
is refused (the reader hears English) if it trips one.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from ..agents.safety import dosha_overclaim_kind, prohibited_verdict

MAX_SECTIONS = 8
MAX_TOTAL_CHARS = 6000

SYSTEM_PROMPT = """You translate a short spoken Vedic astrology morning brief from English into Telugu.

Write simple, conversational Telugu, with natural English words mixed in where Telugu
speakers commonly use them. Keep astrological terms such as Rahu, Shani, Guru, dasha,
tithi, nakshatra, Tarabala, Chandrabala, lagna and rashi as familiar transliterated terms in
Telugu script. Prefer plain everyday wording over literary or Sanskrit-heavy Telugu.

Translate faithfully. Do not add advice, predictions, warnings or reassurance that is not in
the English, and do not drop any. Keep the reader's name as written. The text will be read
aloud, so write it as speech: no lists, symbols, emoji or markdown.

Reply with only a JSON array of strings, one Telugu string per input section, in the same
order and the same count as the input."""


class TranslationUnavailable(Exception):
    """No Telugu text now; the Listen sheet stays in English."""


@dataclass(frozen=True)
class Section:
    label: str
    text: str


Translator = Callable[[str, str], str]
"""(system prompt, user prompt) -> model reply text."""

_translator: Translator | None = None
_cache: OrderedDict[str, list[str]] = OrderedDict()
_CACHE_MAX = 256
_lock = threading.Lock()


def _default_translator(system: str, prompt: str) -> str:
    from ..agents.base import BaseAstroAgent

    agent = BaseAstroAgent()
    agent.system_prompt = system
    return agent.run(prompt)


def set_translator_for_tests(translator: Translator | None) -> None:
    global _translator
    with _lock:
        _translator = translator
        _cache.clear()


def _key(texts: list[str]) -> str:
    return hashlib.sha256("\x1e".join(["te-v1", *texts]).encode("utf-8")).hexdigest()


def _parse(reply: str, expected: int) -> list[str]:
    match = re.search(r"\[.*\]", reply, re.S)
    if not match:
        raise TranslationUnavailable("model reply had no JSON array")
    try:
        values = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise TranslationUnavailable("model reply was not valid JSON") from exc
    if not isinstance(values, list) or len(values) != expected or not all(
        isinstance(value, str) and value.strip() for value in values
    ):
        raise TranslationUnavailable("model reply did not match the sections")
    return [" ".join(value.split()) for value in values]


def telugu_sections(sections: list[Section]) -> list[Section]:
    texts = [" ".join(section.text.split()) for section in sections]
    key = _key(texts)
    with _lock:
        hit = _cache.get(key)
        if hit is not None:
            _cache.move_to_end(key)
        translator = _translator or _default_translator
    if hit is None:
        prompt = json.dumps(texts, ensure_ascii=False)
        try:
            reply = translator(SYSTEM_PROMPT, prompt)
        except Exception as exc:  # provider outage, quota, missing key
            raise TranslationUnavailable("translation request failed") from exc
        hit = _parse(reply or "", len(texts))
        joined = " ".join(hit)
        if prohibited_verdict(joined) or dosha_overclaim_kind(joined):
            raise TranslationUnavailable("translation failed the output checks")
        with _lock:
            _cache[key] = hit
            while len(_cache) > _CACHE_MAX:
                _cache.popitem(last=False)
    return [Section(section.label, text) for section, text in zip(sections, hit)]
