"""Queue one morning brief per user per day.

What goes in the push is the day's headline and nothing else: opt-in, never
fear-based (ui/.../settings/notifications.component.ts). The verdict text,
the windows and the why all stay behind the tap, where they come with their
provenance. A notification that says "Avoid Rahu Kalam at 10:30" with no
context is exactly the dread this product refuses to sell.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..db import crud, crud_mobile as cm
from ..db.models import NotificationJob, PushToken

DEFAULT_SEND_TIME = time(7, 0)
DEFAULT_TIMEZONE = "UTC"
CATEGORY = "morning_brief"


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except Exception:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _primary_kundli(db: Session, user_id: str):
    """The reader's own chart when there is one, else their first profile."""
    kundlis = crud.list_kundlis(db, user_id)
    if not kundlis:
        return None
    return next((k for k in kundlis if (k.relation or "").lower() == "self"), kundlis[0])


def headline_for(kundli, as_of: datetime, tz_name: str,
                 ayanamsha: str = "lahiri", node_type: str = "mean") -> str:
    """The Today verdict headline, computed the same way the Today screen does."""
    from ..context.timing_place import resolve_timing_place
    from ..context.daily import daily_guidance
    from ..core.vedic.chart import VedicChart

    chart = VedicChart(
        kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
        kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation,
        ayanamsha=ayanamsha, node_type=node_type,
    )
    place = resolve_timing_place(kundli, tz_name)
    payload = daily_guidance(
        chart, relation=kundli.relation or "", as_of=as_of,
        city=place.city, nation=place.nation, lat=place.lat, lng=place.lng, tz_str=place.tz_str,
    )
    return payload["verdict"]["headline"]


def schedule_morning_briefs(db: Session, today: date | None = None,
                            headline: Callable[..., str] = headline_for) -> list[NotificationJob]:
    """Idempotent: re-running for the same day returns the existing jobs.

    `headline` is injectable so tests do not need the ephemeris.
    """
    user_ids = {
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    }
    jobs: list[NotificationJob] = []
    for user_id in sorted(user_ids):
        prefs = cm.get_notification_preferences(db, user_id).get(CATEGORY, {})
        if not prefs.get("enabled", True):
            continue
        tokens = cm.list_active_push_tokens(db, user_id)
        tz_name = prefs.get("timezone") or next((t.timezone for t in tokens if t.timezone), None)
        zone = _zone(tz_name)
        day = today or datetime.now(zone).date()
        send_at = prefs.get("preferred_time") or DEFAULT_SEND_TIME
        if isinstance(send_at, str):
            hh, mm = send_at.split(":")[:2]
            send_at = time(int(hh), int(mm))
        local_when = datetime.combine(day, send_at, tzinfo=zone)
        scheduled_for = local_when.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        dedupe_key = f"{CATEGORY}:{kundli.id}:{day.isoformat()}"
        existing = db.query(NotificationJob).filter(NotificationJob.dedupe_key == dedupe_key).first()
        if existing:
            jobs.append(existing)
            continue
        try:
            ayanamsha, node_type = crud.chart_convention(db, user_id)
            title = headline(kundli, local_when, zone.key, ayanamsha=ayanamsha, node_type=node_type)
        except Exception as exc:  # a bad birth record must not stall everyone else
            jobs.append(cm.schedule_notification(
                db, user_id, CATEGORY, scheduled_for, "Your day is ready",
                dedupe_key=dedupe_key, kundli_id=kundli.id, timezone=zone.key,
                status="cancelled", skip_reason=f"headline failed: {exc}"[:200],
            ))
            continue
        jobs.append(cm.schedule_notification(
            db, user_id, CATEGORY, scheduled_for, title,
            dedupe_key=dedupe_key, kundli_id=kundli.id, timezone=zone.key,
            body="Open Today for the why, the windows and the practical close.",
            deep_link="/m/today",
            payload={"kundli_id": kundli.id, "date": day.isoformat()},
        ))
    return jobs


def next_run_after(now: datetime, minutes: int = 15) -> datetime:
    return now + timedelta(minutes=minutes)
