"""The app's update check, asked on every launch and every return to the
front (ui/src/app/core/app-update.service.ts).

No sign-in: a reader on the sign-in screen with a build too old to work must
still be told to update. It reveals only build numbers and the store link.
The rules are in notifications/app_updates.py; the release rows are set by
GitHub Actions through /api/v1/releases/app-version (release_routes.py).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..notifications import app_updates as au

router = APIRouter(prefix="/api/v1/app", tags=["app"])


@router.get("/version")
def version(response: Response,
            platform: str = Query(..., pattern="^(android|ios)$"),
            build: int = Query(..., ge=0, le=10_000_000),
            db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return au.version_status(au.get_release(db, platform), platform, build)
