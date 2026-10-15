"""Natural read-aloud audio for Plus readers.

Thin wrapper over astrospace.voice: authenticates, checks the
`audio.natural_voice` entitlement, and returns MP3 bytes. Any failure the app
can recover from is a 503, which tells it to read with the phone's own voice.
"""
import threading
import time
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..db.database import release_connection
from ..entitlements.resolver import require_entitlement, resolve_entitlements
from ..voice import (
    MAX_SECTIONS,
    MAX_TOTAL_CHARS,
    Section,
    SpeechTooLong,
    SpeechUnavailable,
    TranslationUnavailable,
    natural_speech,
    telugu_sections,
)
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# Per-instance daily character budget per reader. A full day of Plus listening
# (a brief plus Plus's 30 answers) is ~40k characters; this stops a runaway
# client or a scripted account, not a heavy listener. Cloud Run may run several
# instances, so it is a ceiling per instance, not an exact quota — the real
# metered limit belongs with the CE-1 limits in the entitlement registry.
DAILY_CHAR_BUDGET = 120_000
_usage: dict[tuple[str, int], int] = defaultdict(int)
_usage_lock = threading.Lock()


def _today() -> int:
    return int(time.time() // 86400)


def _within_budget(user_id: str, chars: int) -> bool:
    day = _today()
    with _usage_lock:
        for key in [key for key in _usage if key[1] != day]:
            del _usage[key]
        return _usage[(user_id, day)] + chars <= DAILY_CHAR_BUDGET


def _charge(user_id: str, chars: int) -> None:
    with _usage_lock:
        _usage[(user_id, _today())] += chars


class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4500)
    language: Literal["en", "te", "auto"] = "auto"


@router.post("/speech", response_class=Response)
def create_speech(body: SpeechRequest, user: CurrentUser, db: Session = Depends(get_db)):
    require_entitlement(resolve_entitlements(db, user.id), "audio.natural_voice")
    if not _within_budget(user.id, len(body.text)):
        raise HTTPException(status_code=429, detail="Daily natural-voice allowance used; the phone voice still works.")
    # The entitlement check was the last database read. Synthesis can take
    # many seconds; don't hold a pooler connection open through it.
    release_connection(db)
    try:
        speech = natural_speech(body.text, None if body.language == "auto" else body.language)
    except SpeechTooLong as exc:
        raise HTTPException(status_code=413, detail=str(exc))
    except SpeechUnavailable:
        raise HTTPException(status_code=503, detail="Natural voice is unavailable right now.")
    if not speech.cached:
        # Only fresh synthesis costs money; replays from cache are free.
        _charge(user.id, len(body.text))
    return Response(
        content=speech.audio,
        media_type="audio/mpeg",
        headers={
            # Personal text: never shared caches.
            "Cache-Control": "private, max-age=86400",
            "X-Speech-Language": speech.language,
            "X-Speech-Voice": speech.voice,
            "X-Speech-Cached": "1" if speech.cached else "0",
        },
    )


class SectionBody(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=MAX_TOTAL_CHARS)


class TranslateRequest(BaseModel):
    sections: list[SectionBody] = Field(min_length=1, max_length=MAX_SECTIONS)
    language: Literal["te"] = "te"


@router.post("/translate")
def translate_sections(body: TranslateRequest, user: CurrentUser, db: Session = Depends(get_db)):
    """Telugu text for the Listen sheet, so the Telugu voice reads Telugu words."""
    require_entitlement(resolve_entitlements(db, user.id), "audio.natural_voice")
    if sum(len(section.text) for section in body.sections) > MAX_TOTAL_CHARS:
        raise HTTPException(status_code=413, detail="Too much text to translate at once.")
    release_connection(db)  # translation is a model call; see create_speech
    try:
        sections = telugu_sections([Section(s.label, s.text) for s in body.sections])
    except TranslationUnavailable:
        raise HTTPException(status_code=503, detail="Telugu is unavailable right now; reading in English.")
    return {
        "language": "te",
        "sections": [{"label": s.label, "text": s.text} for s in sections],
    }
