"""Server-made natural speech for read-aloud (Plus)."""

from .tts import (
    SpeechUnavailable,
    SpeechTooLong,
    detect_language,
    natural_speech,
    set_synthesizer_for_tests,
)

__all__ = [
    "SpeechUnavailable",
    "SpeechTooLong",
    "detect_language",
    "natural_speech",
    "set_synthesizer_for_tests",
]
