"""Queue one Today's Subhashita push per user per day.

Each reader's verse comes from their own rotation (astrospace.core.subhashita),
the same one the app shows them, so this needs no chart and no ephemeris: only the reader's local date and
time. It goes out at 10:00 local (Hawk, 2026-10-17), unless the reader set
their own time. Once the early afternoon has passed (LAST_QUEUE_TIME)
nothing is queued for that day: a verse arriving at 9 pm because someone
installed the app in the evening reads as noise. The tap opens the verse in
the app, where it can be shared.
"""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..core import subhashita
from ..db import crud_mobile as cm
from ..db.models import NotificationJob, PushToken

DEFAULT_SEND_TIME = time(10, 0)
LAST_QUEUE_TIME = time(14, 0)
CATEGORY = "daily_subhashita"
DEEP_LINK = "/m/subhashita"


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def _send_time(value) -> time:
    if isinstance(value, str):
        try:
            hh, mm = value.split(":")[:2]
            return time(int(hh), int(mm))
        except ValueError:
            return DEFAULT_SEND_TIME
    return value or DEFAULT_SEND_TIME


def schedule_daily_subhashita(db: Session, today: date | None = None,
                              now: datetime | None = None) -> list[NotificationJob]:
    """Idempotent: re-running for the same local day returns the existing jobs."""
    user_ids = {
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    }
    jobs: list[NotificationJob] = []
    for user_id in sorted(user_ids):
        prefs = cm.get_notification_preferences(db, user_id).get(CATEGORY, {})
        if not prefs.get("enabled", True):
            continue
        tokens = cm.list_active_push_tokens(db, user_id)
        zone = _zone(prefs.get("timezone") or next((t.timezone for t in tokens if t.timezone), None))
        local_now = (now or datetime.now(ZoneInfo("UTC"))).astimezone(zone)
        day = today or local_now.date()
        send_at = _send_time(prefs.get("preferred_time"))
        if day == local_now.date() and local_now.time() >= max(send_at, LAST_QUEUE_TIME):
            continue
        local_when = datetime.combine(day, send_at, tzinfo=zone)
        verse = subhashita.for_day(day, user_id)
        jobs.append(cm.schedule_notification(
            db, user_id, CATEGORY,
            local_when.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
            subhashita.TITLE,
            dedupe_key=f"{CATEGORY}:{user_id}:{day.isoformat()}",
            timezone=zone.key,
            body=f"{verse['english']} ({verse['source']} {verse['ref']})",
            deep_link=DEEP_LINK,
            payload={"date": day.isoformat(), "subhashita_id": verse["id"]},
        ))
    return jobs
