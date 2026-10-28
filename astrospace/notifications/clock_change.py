"""Tell readers abroad, the evening before, that their clocks change tonight.

India keeps one clock all year, so this only ever reaches readers whose phone
is in a zone with daylight saving (US and Canada fall back on 1 Nov 2026,
the UK and Europe on the last Sunday of October, Australia in April and
October). The tz database says when each zone changes; nothing here knows
any country's rule.

One push at 18:00 local the evening before, and an email instead for a
reader who has no phone to push to but has the daily reading email on. The
copy says when the clock moves and that nothing needs doing: Today, the
window alerts and the phone's panchang alarms are all worked out on each
day's own clock, so they follow the change by themselves (checked across
1 Nov 2026 in New York, Los Angeles and Toronto; tests/test_clock_change.py).

Respects the reader's settings: a reader who has turned every notification
off gets nothing, and `clock_change` is its own preference so a Settings
switch can turn it off later. CLOCK_CHANGE_NOTICES=off stops it everywhere.
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import NotificationJob, PushToken
from .email import EmailContent
from .email_jobs import _queue, _tz_for, _utc
from .morning_brief import _zone

CATEGORY = "clock_change"
EMAIL_CATEGORY = "daily_email"
SEND_TIME = time(18, 0)
# Queued after this local hour only if the change is still ahead and the
# reader is likely awake; later than this the push would wake people.
LAST_SEND_TIME = time(21, 0)
LOOK_AHEAD = timedelta(hours=48)
DEEP_LINK = "/m/today"
# The push switches a reader can see in Settings. With all of them off the
# reader has said "no notifications", and this is a notification.
PUSH_SWITCHES = ("morning_brief", "window_alert", "festival_reminder",
                 "remedy_reminder", "daily_subhashita")

UTC = ZoneInfo("UTC")


def enabled(environ=None) -> bool:
    env = os.environ if environ is None else environ
    return (env.get("CLOCK_CHANGE_NOTICES") or "on").strip().lower() not in ("0", "off", "false", "no")


def next_change(zone: ZoneInfo, after: datetime, within: timedelta = LOOK_AHEAD) -> dict | None:
    """The zone's next clock change in (after, after + within], or None.

    `at` is the UTC instant; `shift_minutes` is negative when clocks go back.
    """
    after = after.astimezone(UTC)
    before = after.astimezone(zone).utcoffset()
    step = timedelta(minutes=30)
    t = after
    while t < after + within:
        nxt = t + step
        if nxt.astimezone(zone).utcoffset() != before:
            lo, hi = t, nxt  # find the exact minute
            while hi - lo > timedelta(minutes=1):
                mid = lo + (hi - lo) / 2
                if mid.astimezone(zone).utcoffset() == before:
                    lo = mid
                else:
                    hi = mid
            at = hi.replace(second=0, microsecond=0)
            if at.astimezone(zone).utcoffset() == before:
                at += timedelta(minutes=1)
            after_offset = at.astimezone(zone).utcoffset()
            return {
                "at": at,
                "shift_minutes": int((after_offset - before).total_seconds() // 60),
                "old_wall": (at.replace(tzinfo=None) + before),
                "new_wall": at.astimezone(zone).replace(tzinfo=None),
            }
        t = nxt
    return None


def _eve(change: dict) -> date:
    """The evening the reader should hear about it: the day before a change
    in the small hours, the same day for one at midnight's end."""
    just_before = change["old_wall"] - timedelta(seconds=1)
    return just_before.date() if just_before.time() >= time(12, 0) else just_before.date() - timedelta(days=1)


def _clock(wall: datetime) -> str:
    """02:00 -> "2 am", 02:30 -> "2:30 am", 00:00 -> "midnight"."""
    if wall.hour == 0 and wall.minute == 0:
        return "midnight"
    hour = wall.hour % 12 or 12
    suffix = "am" if wall.hour < 12 else "pm"
    return f"{hour} {suffix}" if wall.minute == 0 else f"{hour}:{wall.minute:02d} {suffix}"


def _amount(minutes: int) -> str:
    minutes = abs(minutes)
    if minutes == 60:
        return "one hour"
    if minutes % 60 == 0:
        return f"{minutes // 60} hours"
    return f"{minutes} minutes"


def copy_for(change: dict) -> tuple[str, str]:
    """(title, body) in plain words. Never says what to fear; says nothing
    needs doing, because nothing does."""
    direction = "back" if change["shift_minutes"] < 0 else "forward"
    title = f"Clocks go {direction} {_amount(change['shift_minutes'])} tonight"
    body = (f"At {_clock(change['old_wall'])} it becomes {_clock(change['new_wall'])}. "
            "Your Rahu Kalam, sunrise and alarms will follow the new time on their own.")
    return title, body


def email_content(change: dict) -> EmailContent:
    title, body = copy_for(change)
    return EmailContent(
        subject=title, preview=body, heading=title, intro=body,
        blocks=[{"type": "text", "heading": None,
                 "body": "Siddha works out each day's timings on that day's own clock, "
                         "so there is nothing to change in the app."}],
        button_label="Open Today", button_path=DEEP_LINK,
    )


def _send_at(change: dict, zone: ZoneInfo, now: datetime) -> datetime | None:
    """18:00 on the eve, or now if that has passed; None when it is too late
    to send kindly (after 21:00, or the change has happened)."""
    planned = datetime.combine(_eve(change), SEND_TIME, tzinfo=zone)
    when = max(planned, now)
    local = when.astimezone(zone)
    if when >= change["at"] or (local.date() == _eve(change) and local.time() > LAST_SEND_TIME):
        return None
    if local.date() > _eve(change):  # past the eve, in the small hours before the change
        return None
    return when


def _wants_push(prefs: dict) -> bool:
    if not prefs.get(CATEGORY, {}).get("enabled", True):
        return False
    return any(prefs.get(cat, {}).get("enabled") for cat in PUSH_SWITCHES)


def _phone_zone(tokens: list[PushToken]) -> str | None:
    """The clock on the phone the reader used last: that is the one that moves."""
    for token in sorted(tokens, key=lambda t: t.last_seen_at or datetime.min, reverse=True):
        if token.timezone:
            return token.timezone
    return None


def schedule_clock_change_notices(db: Session, now: datetime | None = None,
                                  environ=None) -> list[NotificationJob]:
    """Idempotent: one job per reader per clock change, whatever the number of runs."""
    if not enabled(environ):
        return []
    now_utc = (now or datetime.utcnow()).replace(tzinfo=UTC)
    jobs: list[NotificationJob] = []
    pushed: set[str] = set()
    user_ids = {
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    }
    for user_id in sorted(user_ids):
        pushed.add(user_id)
        prefs = cm.get_notification_preferences(db, user_id)
        if not _wants_push(prefs):
            continue
        zone = _zone(_phone_zone(cm.list_active_push_tokens(db, user_id)))
        change = next_change(zone, now_utc)
        when = _send_at(change, zone, now_utc) if change else None
        if when is None:
            continue
        title, body = copy_for(change)
        jobs.append(cm.schedule_notification(
            db, user_id, CATEGORY, _utc(when), title,
            dedupe_key=f"{CATEGORY}:{user_id}:{change['at']:%Y-%m-%dT%H:%MZ}",
            timezone=zone.key, body=body, deep_link=DEEP_LINK,
            payload={"change_at": change["at"].isoformat(),
                     "shift_minutes": change["shift_minutes"]},
        ))

    # Email only for readers with no phone to push to, so nobody hears it twice.
    for recipient in cm.email_subscribers(db, EMAIL_CATEGORY):
        if recipient.user_id in pushed:
            continue
        prefs = cm.get_notification_preferences(db, recipient.user_id)
        if not prefs.get(CATEGORY, {}).get("enabled", True):
            continue
        zone = _zone(_tz_for(db, recipient))
        change = next_change(zone, now_utc)
        when = _send_at(change, zone, now_utc) if change else None
        if when is None:
            continue
        jobs.append(_queue(
            db, recipient.user_id, EMAIL_CATEGORY, _utc(when), email_content(change),
            dedupe_key=f"{CATEGORY}_email:{recipient.user_id}:{change['at']:%Y-%m-%dT%H:%MZ}",
            timezone=zone.key,
        ))
    return jobs
