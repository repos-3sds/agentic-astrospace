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
from ..entitlements.resolver import require_entitlement, resolve_entitlements
from ..voice import SpeechTooLong, SpeechUnavailable, natural_speech
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
