"""Queue the "Festival reminders" push: a few days ahead of each festival.

Settings > Notifications has offered this switch, on by default, since the
first native build, and nothing sent it (sweep 2026-10-29 G-2/F-3). The
reader's lead time is `festival_reminder.lead_time_days` (default 3). The
push goes out at 6 pm local on the day that many days before the festival,
the same hour as the "Moon and festival days" email, and opens that day in
Calendar. Festivals are the all-India list the email uses, dated for the
reader's timing place (the account holder's city, context/timing_place.py).
A convention-dependent date says so in the body, as Calendar does.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import NotificationJob, PushToken
from .morning_brief import _primary_kundli, _zone

log = logging.getLogger("astrospace.notifications")

CATEGORY = "festival_reminder"
SEND_TIME = time(18, 0)
# Lead 0 means "on the day": a 6 pm note about the same day is too late.
SAME_DAY_TIME = time(7, 0)
DEFAULT_LEAD_DAYS = 3
MAX_LEAD_DAYS = 30


def _lead(prefs: dict) -> int:
    value = prefs.get("lead_time_days")
    if value is None:
        return DEFAULT_LEAD_DAYS
    return max(0, min(MAX_LEAD_DAYS, int(value)))


def reminder_text(festival: dict, day: date, lead: int) -> tuple[str, str]:
    """(title, body) for one festival `lead` days ahead of `day`."""
    name = festival["name"]
    when = f"{day:%A} {day.day} {day:%b}"
    if lead == 0:
        title, body = f"{name} is today", f"{name} falls today, {when}."
    elif lead == 1:
        title, body = f"{name} is tomorrow", f"{name} falls tomorrow, {when}."
    else:
        title, body = f"{name} in {lead} days", f"{name} falls on {when}."
    if festival.get("is_convention_dependent"):
        body += " The day can vary by family tradition; tap to see the rule used."
    return title, body


def schedule_festival_reminders(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    """Idempotent per reader, festival and date."""
    from ..context.timing_place import resolve_timing_place
    from .email_jobs import days_of_note

    user_ids = {
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    }
    jobs: list[NotificationJob] = []
    for user_id in sorted(user_ids):
        prefs = cm.get_notification_preferences(db, user_id).get(CATEGORY, {})
        if not prefs.get("enabled", True):
            continue
        lead = _lead(prefs)
        send_time = SAME_DAY_TIME if lead == 0 else SEND_TIME
        tokens = cm.list_active_push_tokens(db, user_id)
        zone = _zone(prefs.get("timezone") or next((t.timezone for t in tokens if t.timezone), None))
        local_now = (now or datetime.now(ZoneInfo("UTC"))).astimezone(zone)
        if local_now.time() >= send_time:
            continue  # today's reminder time has passed; tomorrow's run queues the next
        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        festival_day = local_now.date() + timedelta(days=lead)
        try:
            place = resolve_timing_place(kundli, zone.key)
            festivals = days_of_note(festival_day, place.city, place.nation)["festivals"]
        except Exception:
            log.exception("festival reminder for %s failed", user_id)
            db.rollback()
            continue
        when = datetime.combine(local_now.date(), send_time, tzinfo=zone)
        for festival in festivals:
            title, body = reminder_text(festival, festival_day, lead)
            jobs.append(cm.schedule_notification(
                db, user_id, CATEGORY,
                when.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
                title,
                dedupe_key=f"{CATEGORY}:{user_id}:{festival_day.isoformat()}:{festival['slug']}",
                timezone=zone.key,
                body=body,
                deep_link=f"/m/calendar/day?date={festival_day.isoformat()}",
                kundli_id=kundli.id,
                payload={"date": festival_day.isoformat(), "festival": festival["slug"]},
            ))
    return jobs
