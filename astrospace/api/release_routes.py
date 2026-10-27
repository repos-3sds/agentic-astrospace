"""What's new for testers, called only by GitHub Actions.

/api/v1/releases/draft      ship.yml, on each upload to internal testing:
                            plain notes from the merged pull requests, and a
                            preview email to the team. Nothing to readers.
/api/v1/releases/announce   announce.yml, on Hawk's word: the notes, as
                            previewed, emailed to readers with tips emails on.

The caller proves who it is with a Google-signed ID token for the deployer
service account, minted through the same Workload Identity Federation the
deploy uses, so there is no shared secret to set or rotate. A token from any
other account, or for another audience, is refused.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..notifications import release_announcements as ra
from ..notifications.email import DEFAULT_BASE_URL

router = APIRouter(prefix="/api/v1/releases", tags=["releases"])
log = logging.getLogger(__name__)

DEFAULT_CALLER = "github-deployer@gen-lang-client-0058562386.iam.gserviceaccount.com"


def _verify_google_id_token(token: str, audience: str) -> dict:
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    return id_token.verify_oauth2_token(token, google_requests.Request(), audience)


def release_caller(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    audience = os.getenv("RELEASE_TOKEN_AUDIENCE") or DEFAULT_BASE_URL
    allowed = os.getenv("RELEASE_CALLER") or DEFAULT_CALLER
    try:
        claims = _verify_google_id_token(authorization[7:].strip(), audience)
    except Exception:
        raise HTTPException(401, "invalid token")
    if claims.get("email") != allowed or not claims.get("email_verified"):
        raise HTTPException(403, "not the release caller")
    return claims["email"]


class Change(BaseModel):
    title: str = Field(max_length=300)
    files: list[str] = Field(default_factory=list, max_length=2000)


class DraftBody(BaseModel):
    version_code: int = Field(gt=0)
    changes: list[Change] = Field(default_factory=list, max_length=200)


class AnnounceBody(BaseModel):
    version_code: int = Field(gt=0)
    notes: list[str] = Field(max_length=ra.MAX_NOTES)
    # The update's poster, a picture the app serves under /email/updates/.
    poster: str | None = Field(default=None, pattern=r"^/email/updates/[a-z0-9-]+\.(jpg|png)$")


@router.post("/draft")
async def draft(body: DraftBody, _: str = Depends(release_caller), db: Session = Depends(get_db)):
    titles = [c.title for c in body.changes if ra.is_user_facing(c.files)]
    notes, source = await run_in_threadpool(ra.write_notes, titles)
    ann = ra.announcement(body.version_code, notes)
    ra.queue_team_email(db, body.version_code, ann, stage="draft")
    return {**ann, "source": source, "considered": len(body.changes), "user_facing": len(titles)}


@router.post("/announce")
def announce(body: AnnounceBody, _: str = Depends(release_caller), db: Session = Depends(get_db)):
    notes = [n.strip().rstrip(".") for n in body.notes if n.strip()]
    bad = [n for n in notes if not ra._acceptable(n)]
    if bad:
        raise HTTPException(422, {"message": "a note breaks a copy rule", "notes": bad})
    ann = ra.announcement(body.version_code, notes)
    readers = ra.queue_reader_emails(db, body.version_code, notes, poster=body.poster)
    ra.queue_team_email(db, body.version_code, ann, stage="sent", readers=readers)
    log.info("release %s announced: %s reader emails queued", body.version_code, readers)
    return {**ann, "reader_emails_queued": readers}
