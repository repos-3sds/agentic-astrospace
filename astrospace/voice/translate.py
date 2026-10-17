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
import logging
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from ..agents.safety import dosha_overclaim_kind, prohibited_verdict

log = logging.getLogger("astrospace.voice")

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
    if agent.provider == "gemini":
        try:
            return _gemini_quick(agent, prompt)
        except Exception:
            log.warning("quick Telugu translation failed; retrying through the agent", exc_info=True)
    return agent.run(prompt)


def _gemini_quick(agent, prompt: str) -> str:
    """One plain call with thinking turned down. Translation needs no
    reasoning, and with the default thinking a brief took about 16 s
    (Cloud Run logs, 2026-10-17)."""
    types = agent._gemini_types()
    config = types.GenerateContentConfig(
        system_instruction=agent.system_prompt,
        max_output_tokens=4096,
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    )
    response = agent._gemini_client().models.generate_content(
        model=agent.model, contents=prompt, config=config,
    )
    agent._record_usage(response, "telugu_translation")
    text = getattr(response, "text", None) or ""
    if not text.strip():
        raise TranslationUnavailable("empty quick translation")
    return text


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
        hit = _stored(key, len(texts))
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
        _store(key, hit)
    with _lock:
        _cache[key] = hit
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return [Section(section.label, text) for section, text in zip(sections, hit)]


# The worker translates each brief the night before (daily_briefs.prerender_audio)
# and the API serves the Listen sheet's request, and they are different
# processes, so the in-memory cache alone never hits across them. The TTS
# bucket, when configured, keeps the translation for both.
def _object(key: str) -> str:
    return f"te/{key}.json"


def _stored(key: str, expected: int) -> list[str] | None:
    if _translator is not None:  # tests use their own translator, not the bucket
        return None
    from .tts import durable_read

    raw = durable_read(_object(key))
    if not raw:
        return None
    try:
        values = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(values, list) and len(values) == expected and all(isinstance(v, str) and v for v in values):
        return values
    return None


def _store(key: str, values: list[str]) -> None:
    if _translator is not None:
        return
    from .tts import durable_write

    durable_write(_object(key), json.dumps(values, ensure_ascii=False).encode("utf-8"), "application/json")
