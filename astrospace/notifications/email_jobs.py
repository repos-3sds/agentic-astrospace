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
- Weekly and monthly outlooks, Learn your chart and tips: email_series.py.

Copy follows the app's rules: plain words, no fear, no verdicts. Moon days
are dated by the lunar day in force at sunrise at the reader's place; every
festival email names the place and says family and temple calendars can mark
the day differently.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, fields
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
    return asdict(content)


def content_from_payload(data: dict) -> EmailContent:
    known = {f.name for f in fields(EmailContent)}
    return EmailContent(**{k: v for k, v in data.items() if k in known})


def _date_line(day: date, city: str | None) -> str:
    label = f"{day:%A}, {day.day} {day:%B}"
    return f"{label} · {city}" if city else label


# ── Daily reading ─────────────────────────────────────────────────────────────

def stored_daily_brief(db: Session, kundli_id: str, day: date) -> tuple[dict, str | None] | None:
    """(brief, city) for the newest agent brief stored for this profile and
    day, whichever conventions it was written under (the worker and Today
    agree on those)."""
    rows = (
        db.query(DailyGuidanceCache)
        .filter(DailyGuidanceCache.kundli_id == kundli_id, DailyGuidanceCache.local_date == day)
        .order_by(DailyGuidanceCache.computed_at.desc())
        .all()
    )
    for row in rows:
        value = row.payload or {}
        if value.get("source") == "agent" and value.get("brief"):
            return value["brief"], (row.place or {}).get("city")
    return None


_ENERGY = {"drained": "Low energy", "fragmented": "Scattered energy",
           "steady": "Steady energy", "vibrant": "High energy"}
_AREAS = (("love", "Love"), ("work", "Work"), ("money", "Money"),
          ("health", "Energy"), ("growth", "Growth"))


def daily_content(brief: dict, day: date, city: str | None = None) -> EmailContent:
    """Everything the Today card holds, written out in full: the day, where
    to put your energy, each part of life, what suits the day and what to
    leave (each with its reason), the timing, and why."""
    areas = brief.get("areas") or {}
    blocks: list[dict] = [{"type": "text", "heading": "Your day", "body": brief.get("narrative") or ""}]
    if brief.get("focus"):
        blocks.append({"type": "callout", "heading": "Where to put your energy", "body": brief["focus"]})
    rows = [[label, areas[key]] for key, label in _AREAS if areas.get(key)]
    if rows:
        blocks.append({"type": "rows", "heading": "Across your life", "rows": rows})
    if brief.get("do"):
        blocks.append({"type": "items", "heading": "Good for today", "tone": "good",
                       "items": [[i["headline"], i.get("detail") or ""] for i in brief["do"]]})
    if brief.get("avoid"):
        blocks.append({"type": "items", "heading": "Better left for another day", "tone": "care",
                       "items": [[i["headline"], i.get("detail") or ""] for i in brief["avoid"]]})
    if brief.get("timing_note"):
        blocks.append({"type": "text", "heading": "Timing", "body": brief["timing_note"]})
    if brief.get("why"):
        blocks.append({"type": "text", "heading": "Why today feels this way",
                       "body": "\n\n".join(brief["why"])})
    headline = brief.get("headline") or "Your day is ready"
    chips = [c for c in (_ENERGY.get(brief.get("energy") or ""),) if c]
    return EmailContent(
        subject=headline,
        preview=brief.get("summary") or "",
        eyebrow=brief.get("card_title") or "Your day",
        heading=headline,
        intro=brief.get("summary") or "",
        date_line=_date_line(day, city),
        chips=chips,
        blocks=blocks,
        button_label="Open today in Siddha",
        button_path="/m/today",
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
        found = stored_daily_brief(db, kundli.id, day)
        if found is None:
            continue  # the brief writer has not reached them yet; next run
        brief, city = found
        prefs = cm.get_notification_preferences(db, user_id).get("daily_email", {})
        send_at = prefs.get("preferred_time") or DAILY_SEND_TIME
        if isinstance(send_at, str):
            hh, mm = send_at.split(":")[:2]
            send_at = time(int(hh), int(mm))
        when = _utc(datetime.combine(day, send_at, tzinfo=zone))
        jobs.append(_queue(db, user_id, "daily_email", when, daily_content(brief, day, city), dedupe_key,
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


_MOON = {
    "full": {
        "label": "a full moon day",
        "what": ("The full moon closes the bright half of the lunar month. For centuries it has been "
                 "kept as a day of completion: the moon is at its fullest, and so, the tradition says, "
                 "is what you have been working on."),
        "custom": ("Many families keep a light fast until the moon rises, light a lamp at dusk, or offer "
                   "a simple prayer of thanks. Some read or listen to a favourite scripture; others "
                   "visit a temple or spend a quiet hour outdoors in the moonlight."),
        "try": ("Finish one thing you have been carrying, and say thank you to someone who helped you "
                "with it. Keep the evening calm and the meal light."),
    },
    "new": {
        "label": "a new moon day",
        "what": ("The new moon is the quiet point of the lunar month, when the moon is not seen at all. "
                 "Traditionally it is a day for rest and remembering, not for big beginnings."),
        "custom": ("Many families remember their elders and ancestors on this day, often with a small "
                   "offering of food or water and a moment of silence. It is also a common day for "
                   "cleaning the home and clearing what is no longer needed."),
        "try": ("Slow down for an evening. Clear one drawer, one inbox or one worry, and write down a "
                "single intention for the fortnight ahead."),
    },
}


def coming_up(after: date, city: str, nation: str, days: int = 14) -> list[list[str]]:
    """[[date label, what], ...] for notable days in the window after `after`."""
    rows = []
    for offset in range(1, days + 1):
        day = after + timedelta(days=offset)
        note = days_of_note(day, city, nation)
        names = [f["name"] for f in note["festivals"]]
        if note["moon"]:
            names.append("Full moon" if note["moon"] == "full" else "New moon")
        if names:
            rows.append([f"{day:%a} {day.day} {day:%b}", ", ".join(names)])
    return rows


def festival_content(day: date, note: dict, city: str,
                     upcoming: list[list[str]] | None = None) -> EmailContent | None:
    moon = note["moon"]
    fests = note["festivals"]
    if not moon and not fests:
        return None
    blocks: list[dict] = []
    if fests:
        lead = fests[0]
        subject = f"Tomorrow is {lead['name']}"
        intro = lead.get("description") or f"{lead['name']} falls tomorrow."
        if len(fests) > 1:
            blocks.append({"type": "items", "heading": "Also tomorrow",
                           "items": [[f["name"], f.get("description") or ""] for f in fests[1:]]})
        if lead.get("prep_guidance"):
            blocks.append({"type": "callout", "heading": "Getting ready", "body": lead["prep_guidance"]})
        if moon:
            m = _MOON[moon]
            blocks.append({"type": "text", "heading": f"It is also {m['label']}",
                           "body": f"{m['what']}\n\n{m['custom']}"})
    else:
        m = _MOON[moon]
        subject = f"Tomorrow is {m['label']}"
        intro = m["what"]
        blocks.append({"type": "text", "heading": "How people mark it", "body": m["custom"]})
        blocks.append({"type": "callout", "heading": "Something simple to try", "body": m["try"]})
    if upcoming:
        blocks.append({"type": "rows", "heading": "Coming up", "rows": upcoming})
    notes = [f["observance_note"] for f in fests if f.get("observance_note")]
    convention = (
        f"Dates are worked out for {city}. "
        "Your family or temple calendar may mark a day apart; follow theirs."
    )
    return EmailContent(
        subject=subject,
        preview=intro[:120],
        # Sent the evening before, so the date is tomorrow's, said as such.
        eyebrow=f"Tomorrow · {day:%A}, {day.day} {day:%B}",
        heading=subject,
        intro=intro,
        date_line=city,
        blocks=blocks,
        button_label="Open your calendar",
        button_path="/m/calendar",
        note=" ".join(notes + [convention]),
    )


def schedule_festival_emails(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    from ..context.timing_place import resolve_timing_place

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
            note = days_of_note(tomorrow, place.city, place.nation)
            content = None
            if note["moon"] or note["festivals"]:
                content = festival_content(tomorrow, note, place.city,
                                           coming_up(tomorrow, place.city, place.nation))
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

WELCOME_ITEMS = (
    ("daily_email", "Your daily reading",
     "Each morning at 6:30: what the day is for, where to put your energy, what suits the day and "
     "what to leave, and the reasons behind it, worked out from your own chart."),
    ("festival_email", "Moon and festival days",
     "The evening before a full moon, a new moon or a major festival: what the day is, how families "
     "traditionally mark it, and a simple way to take part, dated for where you are."),
    ("weekly_email", "Your week ahead",
     "Every Monday morning: the theme of the week for love, work and rest, and one thing to try."),
    ("monthly_email", "Your month ahead",
     "On the 1st of each month: the shape of the month and where to put your effort."),
    ("lessons_email", "Learn your chart",
     "Eight short lessons, a few days apart, each using your own chart: your rising sign, your "
     "Moon, your birth star and more."),
    ("tips_email", "Tips and reminders",
     "Now and then: a feature worth trying, and what is coming up if you have been away a while."),
)


def welcome_content(db: Session, user_id: str, prefs: dict) -> EmailContent:
    chosen = [[title, detail] for category, title, detail in WELCOME_ITEMS
              if prefs.get(category, {}).get("enabled")]
    blocks: list[dict] = []
    if chosen:
        blocks.append({"type": "items", "heading": "What you'll get", "items": chosen})
    kundli = _primary_kundli(db, user_id)
    path = "/m/today"
    if kundli is not None and (kundli.birth_time_accuracy or "exact") != "exact":
        blocks.append({
            "type": "callout", "heading": "One thing that helps",
            "body": ("Your birth time is marked as not exact. If you can find it, on a birth "
                     "certificate or in a family record, add it in the app. It makes the daily "
                     "reading noticeably more personal."),
        })
        path = "/m/settings"
    blocks.append({"type": "text", "heading": "Changing your mind",
                   "body": ("You can turn any of these off at any time in Settings, then Notifications, "
                            "or with the link at the bottom of every email. Replies to this address "
                            "reach a person.")})
    return EmailContent(
        subject="You're set up for Siddha emails",
        preview="Here's what will arrive, and how to change it.",
        eyebrow="Welcome",
        heading="You're all set",
        intro=("Thanks for joining Siddha by email. Everything we send is written for you, from your "
               "own chart and your own place, never generic lines."),
        blocks=blocks,
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
    from .email_series import schedule_lesson_emails, schedule_outlook_emails, schedule_tip_emails

    summary = {
        "welcome": len(schedule_welcome_emails(db, now)),
        "daily": len(schedule_daily_emails(db, now)),
        "festival": len(schedule_festival_emails(db, now)),
    }
    # Each set on its own, so one failing never stops the others.
    for name, run in (("outlook", lambda: schedule_outlook_emails(db, now)),
                      ("lessons", lambda: len(schedule_lesson_emails(db, now))),
                      ("tips", lambda: len(schedule_tip_emails(db, now)))):
        try:
            summary[name] = run()
        except Exception:
            log.exception("%s emails failed", name)
            db.rollback()
    return summary


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
