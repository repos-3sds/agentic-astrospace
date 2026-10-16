"""Queue the emails a reader turned on, and deliver one email job.

Runs in the notification worker beside the push schedulers, on the same
`notification_jobs` queue: a job whose payload says `"channel": "email"` is
delivered here instead of to a phone. Dedupe keys keep every email to once
per reader per day, however many runs see it.

- Daily reading (`daily_email`): the brief the worker already wrote for the
  reader's own profile (daily_briefs.py), sent at their chosen time, 06:30
  local by default. No new model call. If the brief is not written by 11:00
  local, that day's email is skipped rather than sent late or half-made.
- Moon and festival days (`festival_email`): the evening before a full moon,
  a new moon or a pan-India festival at the reader's place, 18:00 local.
  Regional festivals wait for the region preference to reach the server.
- Welcome: once, when a reader first turns an email on. It confirms what
  they will get, and asks for a birth time when theirs is missing.

Copy follows the app's rules: plain words, no fear, no verdicts. Moon days
are dated by the lunar day in force at sunrise at the reader's place; every
festival email names the place and says family and temple calendars can mark
the day differently.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import DailyGuidanceCache, NotificationJob
from .email import EmailContent, EmailTransport, build_message
from .morning_brief import _primary_kundli, _zone

log = logging.getLogger("astrospace.notifications")

DEFAULT_EMAIL_TIMEZONE = "Asia/Kolkata"
DAILY_SEND_TIME = time(6, 30)
DAILY_GIVE_UP_AT = time(11, 0)
FESTIVAL_SEND_TIME = time(18, 0)
CHANNEL = "email"


def _tz_for(db: Session, recipient) -> str:
    """The reader's clock: what the app last reported, else their phone's
    push token, else India."""
    if recipient.timezone:
        return recipient.timezone
    tokens = sorted(cm.list_active_push_tokens(db, recipient.user_id),
                    key=lambda t: t.last_seen_at or datetime.min, reverse=True)
    return next((t.timezone for t in tokens if t.timezone), None) or DEFAULT_EMAIL_TIMEZONE


def _utc(local: datetime) -> datetime:
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def _queue(db: Session, user_id: str, category: str, when_utc: datetime, content: EmailContent,
           dedupe_key: str, **fields) -> NotificationJob:
    return cm.schedule_notification(
        db, user_id, category, when_utc, content.subject, dedupe_key=dedupe_key,
        body=content.preview, deep_link=content.button_path,
        payload={"channel": CHANNEL, "content": _content_dict(content)}, **fields,
    )


def _content_dict(content: EmailContent) -> dict:
    return {
        "subject": content.subject, "preview": content.preview, "heading": content.heading,
        "intro": content.intro, "sections": [list(s) for s in content.sections],
        "lists": [[h, list(items)] for h, items in content.lists],
        "button_label": content.button_label, "button_path": content.button_path,
        "note": content.note,
    }


def content_from_payload(data: dict) -> EmailContent:
    return EmailContent(
        subject=data["subject"], preview=data.get("preview") or "", heading=data["heading"],
        intro=data.get("intro") or "",
        sections=[(s[0], s[1]) for s in data.get("sections") or []],
        lists=[(h, list(items)) for h, items in data.get("lists") or []],
        button_label=data.get("button_label") or "Open Siddha",
        button_path=data.get("button_path") or "/m/today",
        note=data.get("note"),
    )


# ── Daily reading ─────────────────────────────────────────────────────────────

def stored_daily_brief(db: Session, kundli_id: str, day: date) -> dict | None:
    """The newest agent brief stored for this profile and day, whichever
    conventions it was written under (the worker and Today agree on those)."""
    rows = (
        db.query(DailyGuidanceCache)
        .filter(DailyGuidanceCache.kundli_id == kundli_id, DailyGuidanceCache.local_date == day)
        .order_by(DailyGuidanceCache.computed_at.desc())
        .all()
    )
    for row in rows:
        value = row.payload or {}
        if value.get("source") == "agent" and value.get("brief"):
            return value["brief"]
    return None


def daily_content(brief: dict, day: date) -> EmailContent:
    areas = brief.get("areas") or {}
    sections: list[tuple[str | None, str]] = [(None, brief.get("narrative") or "")]
    for key, label in (("love", "Love"), ("work", "Work"), ("money", "Money")):
        if areas.get(key):
            sections.append((label, areas[key]))
    lists = []
    if brief.get("do"):
        lists.append(("Good for today", [i["headline"] for i in brief["do"]]))
    if brief.get("avoid"):
        lists.append(("Better left for another day", [i["headline"] for i in brief["avoid"]]))
    headline = brief.get("headline") or "Your day is ready"
    return EmailContent(
        subject=headline,
        preview=brief.get("summary") or "",
        heading=headline,
        intro=brief.get("summary") or "",
        sections=sections,
        lists=lists,
        button_label="See your full day",
        button_path="/m/today",
        note=(brief.get("timing_note") or None),
    )


def schedule_daily_emails(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    jobs: list[NotificationJob] = []
    for recipient in cm.email_subscribers(db, "daily_email"):
        user_id = recipient.user_id
        zone = _zone(_tz_for(db, recipient))
        local_now = now.astimezone(zone) if now else datetime.now(zone)
        day = local_now.date()
        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        dedupe_key = f"daily_email:{user_id}:{day.isoformat()}"
        if db.query(NotificationJob.id).filter(NotificationJob.dedupe_key == dedupe_key).first():
            continue
        if local_now.time() >= DAILY_GIVE_UP_AT:
            continue
        brief = stored_daily_brief(db, kundli.id, day)
        if brief is None:
            continue  # the brief writer has not reached them yet; next run
        prefs = cm.get_notification_preferences(db, user_id).get("daily_email", {})
        send_at = prefs.get("preferred_time") or DAILY_SEND_TIME
        if isinstance(send_at, str):
            hh, mm = send_at.split(":")[:2]
            send_at = time(int(hh), int(mm))
        when = _utc(datetime.combine(day, send_at, tzinfo=zone))
        jobs.append(_queue(db, user_id, "daily_email", when, daily_content(brief, day), dedupe_key,
                           kundli_id=kundli.id, timezone=zone.key))
    return jobs


# ── Moon and festival days ────────────────────────────────────────────────────

@lru_cache(maxsize=64)
def _year_at(year: int, city: str, nation: str) -> tuple[tuple, tuple]:
    """(festival rows, sunrise facts) for a year at a place. Cached: a run
    sees many readers in the same few cities, and a year scan is not cheap."""
    from ..core.vedic import festivals
    from ..core.vedic.festivals import resolve_location

    rows = festivals.occurrences(year, city=city, nation=nation, regions=["pan-india"])
    lat, lng, tz_str = resolve_location(city, nation, None, None, None)
    facts = festivals._scan_year(year, lat, lng, tz_str)
    return tuple(rows), tuple(facts)


def days_of_note(day: date, city: str, nation: str) -> dict:
    """What `day` is at this place: {"moon": "full"|"new"|None, "festivals": [...]}."""
    rows, facts = _year_at(day.year, city, nation)
    moon = None
    for f in facts:
        if f["date"] == day and f["tithi_number"] == 15:
            moon = "full" if f["paksha"] == "Shukla" else "new"
            break
    return {"moon": moon, "festivals": [r for r in rows if r["occurs_on"] == day]}


_MOON_LINES = {
    "full": ("a full moon day",
             "Many keep a light fast, light a lamp in the evening or spend a quiet moment in "
             "gratitude. It suits finishing things and giving thanks."),
    "new": ("a new moon day",
            "A natural pause in the month. Many remember their elders and ancestors, rest, and "
            "set an intention for the weeks ahead."),
}


def festival_content(day: date, note: dict, city: str) -> EmailContent | None:
    moon = note["moon"]
    fests = note["festivals"]
    if not moon and not fests:
        return None
    weekday = f"{day:%A}"
    sections: list[tuple[str | None, str]] = []
    if fests:
        lead = fests[0]
        subject = f"Tomorrow is {lead['name']}"
        intro = lead.get("description") or f"{lead['name']} falls on {weekday}."
        for extra in fests[1:]:
            sections.append((extra["name"], extra.get("description") or ""))
        if lead.get("prep_guidance"):
            sections.append(("Getting ready", lead["prep_guidance"]))
        if moon:
            label, line = _MOON_LINES[moon]
            sections.append((f"Also {label}", line))
    else:
        label, line = _MOON_LINES[moon]
        subject = f"Tomorrow is {label}"
        intro = line
    notes = [f["observance_note"] for f in fests if f.get("observance_note")]
    convention = (
        f"Dates are worked out for {city}. "
        "Your family or temple calendar may mark a day apart; follow theirs."
    )
    return EmailContent(
        subject=subject,
        preview=f"{weekday} in {city}",
        heading=subject,
        intro=intro,
        sections=sections,
        button_label="Open your calendar",
        button_path="/m/calendar",
        note=" ".join(notes + [convention]),
    )


def schedule_festival_emails(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    from ..api.timing_place import resolve_timing_place

    jobs: list[NotificationJob] = []
    for recipient in cm.email_subscribers(db, "festival_email"):
        user_id = recipient.user_id
        zone = _zone(_tz_for(db, recipient))
        local_now = now.astimezone(zone) if now else datetime.now(zone)
        if local_now.time() >= FESTIVAL_SEND_TIME:
            continue  # tomorrow's evening email is queued during today
        tomorrow = local_now.date() + timedelta(days=1)
        dedupe_key = f"festival_email:{user_id}:{tomorrow.isoformat()}"
        if db.query(NotificationJob.id).filter(NotificationJob.dedupe_key == dedupe_key).first():
            continue
        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        try:
            place = resolve_timing_place(kundli, zone.key)
            content = festival_content(tomorrow, days_of_note(tomorrow, place.city, place.nation),
                                       place.city)
        except Exception:
            log.exception("festival email for %s failed", user_id)
            db.rollback()
            continue
        if content is None:
            continue
        when = _utc(datetime.combine(local_now.date(), FESTIVAL_SEND_TIME, tzinfo=zone))
        jobs.append(_queue(db, user_id, "festival_email", when, content, dedupe_key,
                           kundli_id=kundli.id, timezone=zone.key))
    return jobs


# ── Welcome ───────────────────────────────────────────────────────────────────

def welcome_content(db: Session, user_id: str, prefs: dict) -> EmailContent:
    chosen = []
    if prefs.get("daily_email", {}).get("enabled"):
        chosen.append("Your daily reading, each morning")
    if prefs.get("festival_email", {}).get("enabled"):
        chosen.append("Full moon, new moon and festival days, the evening before")
    sections: list[tuple[str | None, str]] = []
    kundli = _primary_kundli(db, user_id)
    path = "/m/today"
    if kundli is not None and (kundli.birth_time_accuracy or "exact") != "exact":
        sections.append((
            "One thing that helps",
            "Your birth time is marked as not exact. If you can find it (a birth certificate or a "
            "family record), add it in the app. It makes the daily reading noticeably more personal.",
        ))
        path = "/m/settings"
    return EmailContent(
        subject="You're set up for Siddha emails",
        preview="Here's what will arrive, and how to change it.",
        heading="You're all set",
        intro="Thanks for turning on emails from Siddha. Here's what you'll get:",
        lists=[("Coming your way", chosen)] if chosen else [],
        sections=sections + [(None, "You can change this any time in Settings, Notifications, or "
                                    "with the link at the bottom of every email.")],
        button_label="Open Siddha",
        button_path=path,
    )


def schedule_welcome_emails(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    from ..db.models import EmailRecipient

    jobs: list[NotificationJob] = []
    now_utc = (now.astimezone(ZoneInfo("UTC")).replace(tzinfo=None) if now else datetime.utcnow())
    pending = (
        db.query(EmailRecipient)
        .filter(EmailRecipient.welcomed_at.is_(None), EmailRecipient.suppressed_at.is_(None))
        .all()
    )
    for recipient in pending:
        prefs = cm.get_notification_preferences(db, recipient.user_id)
        if not any(prefs.get(c, {}).get("enabled") for c in cm.EMAIL_CATEGORIES):
            continue  # they have not asked for email yet
        content = welcome_content(db, recipient.user_id, prefs)
        jobs.append(_queue(db, recipient.user_id, "system", now_utc, content,
                           f"welcome_email:{recipient.user_id}"))
        recipient.welcomed_at = now_utc
        db.commit()
    return jobs


def schedule_emails(db: Session, now: datetime | None = None) -> dict:
    return {
        "welcome": len(schedule_welcome_emails(db, now)),
        "daily": len(schedule_daily_emails(db, now)),
        "festival": len(schedule_festival_emails(db, now)),
    }


# ── Delivery ──────────────────────────────────────────────────────────────────

def is_email_job(job: NotificationJob) -> bool:
    return (job.payload or {}).get("channel") == CHANNEL


def deliver_email_job(db: Session, job: NotificationJob, transport: EmailTransport) -> bool:
    """Send one email job. Re-checks consent at send time: a reader who
    turned a category off after it was queued gets nothing."""
    recipient = cm.get_email_recipient(db, job.user_id)
    if recipient is None or recipient.suppressed_at is not None:
        cm.cancel_notification(db, job.id, reason="no deliverable email address")
        return False
    if job.category != "system":
        prefs = cm.get_notification_preferences(db, job.user_id).get(job.category, {})
        if not prefs.get("enabled"):
            cm.cancel_notification(db, job.id, reason=f"{job.category} turned off")
            return False
    content = content_from_payload((job.payload or {})["content"])
    message = build_message(recipient.email, content, user_id=job.user_id, category=job.category)
    result = transport.send(message)
    cm.record_delivery(
        db, job.id, "sent" if result.ok else "failed", provider=transport.provider,
        provider_message_id=result.provider_message_id, error=result.error,
        receipt=result.receipt or {},
    )
    if result.ok:
        cm.mark_notification_sent(db, job.id)
        return True
    if result.address_dead:
        cm.suppress_email(db, recipient.email, "refused by provider")
        cm.mark_notification_failed(db, job.id, result.error or "address refused", retry=False)
    else:
        cm.mark_notification_failed(db, job.id, result.error or "unknown error")
    return False
