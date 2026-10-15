"""Server-made natural speech for read-aloud (Plus)."""

from .tts import (
    SpeechUnavailable,
    SpeechTooLong,
    detect_language,
    natural_speech,
    set_synthesizer_for_tests,
)
from .translate import (
    MAX_SECTIONS,
    MAX_TOTAL_CHARS,
    Section,
    TranslationUnavailable,
    set_translator_for_tests,
    telugu_sections,
)

__all__ = [
    "SpeechUnavailable",
    "SpeechTooLong",
    "detect_language",
    "natural_speech",
    "set_synthesizer_for_tests",
    "MAX_SECTIONS",
    "MAX_TOTAL_CHARS",
    "Section",
    "TranslationUnavailable",
    "set_translator_for_tests",
    "telugu_sections",
]
