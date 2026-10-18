"""Natural read-aloud audio from Google Cloud Text-to-Speech (Chirp 3 HD).

The phone's own voice reads everything for free users and whenever this path
is unavailable; this module only exists to make Plus listening sound like a
person rather than a screen reader. Chosen over Sarvam and ElevenLabs on
2026-10-15 after listening to samples: similar cost, already in our GCP
project, and en-IN, hi-IN and te-IN voices. Deferred follow-ups (overnight
pre-generation, a real quota, a durable bucket) are in the deferred backlog of
docs/backend_astro_depth_checklist_2026-08-06.md.

Design points that are easy to undo by accident:

- Speaking rate is fixed server-side. The app changes speed with the audio
  element's playbackRate instead, so one cached file serves every speed.
- Everything is cached by a hash of (model, voice, language, rate, text).
  Briefs are personal, so the cache mostly serves replays and section jumps,
  but those are exactly when a reader notices an 8–13 s synthesis wait.
- Synthesis is one request per section, never per sentence: sentence-level
  requests reset intonation, which is the robotic sound this replaces.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Literal, Protocol

log = logging.getLogger(__name__)

Language = Literal["en", "te"]

# Measured on 2026-10-15: an ~870-character brief took 8–13 s. Requests are
# capped below Google's 5,000-byte input limit; Telugu is three bytes per
# character in UTF-8, so the byte cap is what binds for it.
MAX_TEXT_BYTES = 4500
SPEAKING_RATE = 0.95
TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"
TTS_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

VOICES: dict[Language, tuple[str, str]] = {
    # (languageCode, voice name). Aoede, the female voice, for both languages:
    # Hawk was happy with both genders in the blind listen, and one voice
    # across languages keeps a mixed-language session sounding like one person.
    "en": ("en-IN", "en-IN-Chirp3-HD-Aoede"),
    "te": ("te-IN", "te-IN-Chirp3-HD-Aoede"),
}

_TELUGU = re.compile(r"[ఀ-౿]")


class SpeechUnavailable(Exception):
    """Natural speech can't be produced now; the app falls back to the phone voice."""


class SpeechTooLong(ValueError):
    pass


def detect_language(text: str) -> Language:
    """Telugu if the text is mostly Telugu script, else Indian English.

    Ask answers arrive in whichever language the reader chose, and a brief may
    quote Sanskrit terms in Latin script, so the script decides rather than a
    preference the text might not match.
    """
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return "en"
    telugu = sum(1 for ch in letters if _TELUGU.match(ch))
    return "te" if telugu / len(letters) >= 0.3 else "en"


class Synthesizer(Protocol):
    def synthesize(self, text: str, language_code: str, voice_name: str, rate: float) -> bytes: ...


class GoogleChirpSynthesizer:
    """Calls Cloud Text-to-Speech with application-default credentials.

    On Cloud Run that is the service's own service account; locally it is
    `gcloud auth application-default login`. No key file is involved.
    """

    def __init__(self) -> None:
        self._session = None
        self._lock = threading.Lock()

    def _authorized_session(self):
        with self._lock:
            if self._session is None:
                try:
                    import google.auth  # google-auth ships with google-genai
                    from google.auth.transport.requests import AuthorizedSession
                    credentials, project = google.auth.default(scopes=[TTS_SCOPE])
                except Exception as exc:  # no ADC configured
                    raise SpeechUnavailable("no Google credentials") from exc
                session = AuthorizedSession(credentials)
                quota_project = os.getenv("ASTROSPACE_TTS_PROJECT") or project
                if quota_project:
                    session.headers["x-goog-user-project"] = quota_project
                self._session = session
            return self._session

    def synthesize(self, text: str, language_code: str, voice_name: str, rate: float) -> bytes:
        import base64

        try:
            response = self._authorized_session().post(
                TTS_ENDPOINT,
                json={
                    "input": {"text": text},
                    "voice": {"languageCode": language_code, "name": voice_name},
                    "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate},
                },
                timeout=30,
            )
        except SpeechUnavailable:
            raise
        except Exception as exc:
            raise SpeechUnavailable("speech request failed") from exc
        if response.status_code != 200:
            raise SpeechUnavailable(f"speech provider returned {response.status_code}")
        try:
            return base64.b64decode(response.json()["audioContent"])
        except Exception as exc:
            raise SpeechUnavailable("speech provider returned no audio") from exc


class _MemoryCache:
    """Bounded per-instance LRU. Cloud Run instances are short-lived, so this
    covers replays within a listening session; GCS covers the rest."""

    def __init__(self, max_bytes: int = 64 * 1024 * 1024) -> None:
        self._items: OrderedDict[str, bytes] = OrderedDict()
        self._bytes = 0
        self._max = max_bytes
        self._lock = threading.Lock()

    def get(self, key: str) -> bytes | None:
        with self._lock:
            value = self._items.get(key)
            if value is not None:
                self._items.move_to_end(key)
            return value

    def put(self, key: str, value: bytes) -> None:
        with self._lock:
            if key in self._items:
                return
            self._items[key] = value
            self._bytes += len(value)
            while self._bytes > self._max and self._items:
                _, old = self._items.popitem(last=False)
                self._bytes -= len(old)


class _BucketCache:
    """Optional durable cache in a GCS bucket (ASTROSPACE_TTS_BUCKET).

    Failures are swallowed: a cache miss costs one synthesis, never a reading.
    """

    def __init__(self, bucket: str, synthesizer: GoogleChirpSynthesizer) -> None:
        self._bucket = bucket
        self._synthesizer = synthesizer

    def _object(self, key: str) -> str:
        return f"tts/{key}.mp3"

    def get(self, key: str) -> bytes | None:
        return self.read(self._object(key))

    def put(self, key: str, value: bytes) -> None:
        self.write(self._object(key), value, "audio/mpeg")

    def read(self, name: str) -> bytes | None:
        from urllib.parse import quote

        try:
            response = self._synthesizer._authorized_session().get(
                f"https://storage.googleapis.com/storage/v1/b/{self._bucket}/o/"
                f"{quote(name, safe='')}?alt=media",
                timeout=10,
            )
        except Exception:
            return None
        return response.content if response.status_code == 200 else None

    def write(self, name: str, value: bytes, content_type: str) -> None:
        from urllib.parse import quote

        try:
            self._synthesizer._authorized_session().post(
                f"https://storage.googleapis.com/upload/storage/v1/b/{self._bucket}/o"
                f"?uploadType=media&name={quote(name, safe='')}",
                data=value,
                headers={"Content-Type": content_type},
                timeout=15,
            )
        except Exception:
            # The audio still plays; only the cache misses next time (audit I10).
            log.warning("tts cache write failed for %s", name, exc_info=True)


@dataclass(frozen=True)
class Speech:
    audio: bytes
    language: Language
    voice: str
    cached: bool


_memory = _MemoryCache()
_synthesizer: Synthesizer | None = None
_bucket: _BucketCache | None = None
_init_lock = threading.Lock()


def _backends() -> tuple[Synthesizer, _BucketCache | None]:
    global _synthesizer, _bucket
    with _init_lock:
        if _synthesizer is None:
            google = GoogleChirpSynthesizer()
            _synthesizer = google
            bucket = os.getenv("ASTROSPACE_TTS_BUCKET", "").strip()
            _bucket = _BucketCache(bucket, google) if bucket else None
        return _synthesizer, _bucket


def set_synthesizer_for_tests(synthesizer: Synthesizer | None) -> None:
    global _synthesizer, _bucket, _memory
    with _init_lock:
        _synthesizer = synthesizer
        _bucket = None
        _memory = _MemoryCache()


def durable_read(name: str) -> bytes | None:
    """An object from the TTS bucket, or None when there is no bucket or no object."""
    try:
        _, bucket = _backends()
    except Exception:
        return None
    return bucket.read(name) if bucket is not None else None


def durable_write(name: str, value: bytes, content_type: str) -> None:
    """Best-effort write to the TTS bucket; does nothing without one."""
    try:
        _, bucket = _backends()
    except Exception:
        return
    if bucket is not None:
        bucket.write(name, value, content_type)


def cache_key(text: str, language_code: str, voice: str, rate: float) -> str:
    material = "\x1f".join(["chirp3-hd", language_code, voice, f"{rate:.2f}", text])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def natural_speech(text: str, language: Language | None = None) -> Speech:
    text = " ".join(text.split())
    if not text:
        raise SpeechTooLong("nothing to read")
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise SpeechTooLong("text too long for one request; split it by section")
    lang = language or detect_language(text)
    language_code, voice = VOICES[lang]
    key = cache_key(text, language_code, voice, SPEAKING_RATE)

    hit = _memory.get(key)
    if hit is not None:
        return Speech(hit, lang, voice, cached=True)
    synthesizer, bucket = _backends()
    if bucket is not None:
        stored = bucket.get(key)
        if stored:
            _memory.put(key, stored)
            return Speech(stored, lang, voice, cached=True)

    audio = synthesizer.synthesize(text, language_code, voice, SPEAKING_RATE)
    _memory.put(key, audio)
    if bucket is not None:
        bucket.put(key, audio)
    return Speech(audio, lang, voice, cached=False)
