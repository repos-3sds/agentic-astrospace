"""Email the team when a reader first signs in, asks their first question,
or reports an answer.

For the friends-and-family test: the people running it want to know, within
one worker run, that an invite turned into a sign-in and a sign-in into a
question. Off unless `OWNER_ALERT_EMAILS` (comma-separated) is set on the
worker job.

Only events in the last `LOOKBACK` are looked at, so turning this on (or a
deploy) does not mail out the whole history; the worker runs every 15
minutes, which leaves room for a few missed runs. Each event is queued once,
through the usual notification queue, under a dedupe key per reader per
event, and delivered here rather than to the reader.

The email names the reader by their sign-in address and says when. It never
carries what they asked: the team gets the fact of a first question, not its
words. A report carries the reason the reader chose and their own note, which
they wrote for the team; the reported question and answer stay in /admin.
"""
from __future__ import annotations

import html
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import AnswerReport, AskMessage, AskThread, BillingAccount, EmailRecipient, NotificationJob
from .email import EmailMessage, EmailTransport

log = logging.getLogger("astrospace.notifications")

CHANNEL = "owner_email"
CATEGORY = "owner_alert"
LOOKBACK = timedelta(hours=2)
# The team reads these in India time.
TEAM_TIMEZONE = ZoneInfo("Asia/Kolkata")


def owner_addresses(environ: dict | None = None) -> list[str]:
    env = os.environ if environ is None else environ
    return [a.strip() for a in (env.get("OWNER_ALERT_EMAILS") or "").split(",") if a.strip()]


def _new_accounts(db: Session, since: datetime) -> list[tuple[str, str | None, datetime]]:
    """(user id, sign-in address, first seen) for accounts made since `since`.

    On Supabase this is auth.users, the sign-in itself. Elsewhere (tests,
    local SQLite) there is no auth schema, so the first billing account,
    made on the reader's first signed-in app open, stands in for it.
    """
    if db.get_bind().dialect.name == "postgresql":
        rows = db.execute(text(
            "select id::text, email, created_at from auth.users "
            "where created_at >= :since order by created_at"
        ), {"since": since}).all()
        return [(r[0], r[1], r[2]) for r in rows]
    rows = (
        db.query(BillingAccount.owner_user_id, EmailRecipient.email, BillingAccount.created_at)
        .outerjoin(EmailRecipient, EmailRecipient.user_id == BillingAccount.owner_user_id)
        .filter(BillingAccount.kind == "individual", BillingAccount.created_at >= since)
        .order_by(BillingAccount.created_at)
        .all()
    )
    return [(r[0], r[1], r[2]) for r in rows]


def _first_questions(db: Session, since: datetime) -> list[tuple[str, datetime]]:
    """(user id, when) for readers whose first question came since `since`."""
    first = func.min(AskMessage.created_at)
    rows = (
        db.query(AskThread.user_id, first)
        .join(AskMessage, AskMessage.thread_id == AskThread.id)
        .filter(AskMessage.role == "user")
        .group_by(AskThread.user_id)
        .having(first >= since)
        .all()
    )
    return [(r[0], r[1]) for r in rows]


def _address_for(db: Session, user_id: str) -> str | None:
    if db.get_bind().dialect.name == "postgresql":
        return db.execute(text("select email from auth.users where id::text = :uid"),
                          {"uid": user_id}).scalar()
    recipient = db.get(EmailRecipient, user_id)
    return recipient.email if recipient else None


def _team_time(at: datetime) -> str:
    local = at.replace(tzinfo=ZoneInfo("UTC")) if at.tzinfo is None else at
    return local.astimezone(TEAM_TIMEZONE).strftime("%-d %b, %H:%M IST")


# The reasons a reader can pick on "Report this answer", as the team reads them.
REPORT_REASON_LABELS = {
    "wrong": "Wrong or made up",
    "harmful": "Harmful or frightening",
    "offensive": "Rude or offensive",
    "advice": "Health, legal or money advice",
    "other": "Something else",
}


def _new_reports(db: Session, since: datetime) -> list[AnswerReport]:
    return (
        db.query(AnswerReport)
        .filter(AnswerReport.created_at >= since)
        .order_by(AnswerReport.created_at)
        .all()
    )


def _queue(db: Session, user_id: str, kind: str, subject: str, line: str,
           to: list[str], now: datetime, key: str | None = None) -> NotificationJob:
    return cm.schedule_notification(
        db, user_id, CATEGORY, now, subject,
        dedupe_key=f"{CATEGORY}:{kind}:{key or user_id}",
        body=line, payload={"channel": CHANNEL, "to": to, "kind": kind},
    )


def schedule_owner_alerts(db: Session, now: datetime | None = None,
                          environ: dict | None = None) -> dict:
    to = owner_addresses(environ)
    if not to:
        return {}
    now = now or datetime.utcnow()
    since = now - LOOKBACK
    joined = questions = 0
    for user_id, address, at in _new_accounts(db, since):
        who = address or f"reader {user_id[:8]}"
        _queue(db, user_id, "joined", f"New on Siddha: {who}",
               f"{who} signed in to Siddha for the first time at {_team_time(at)}.", to, now)
        joined += 1
    for user_id, at in _first_questions(db, since):
        who = _address_for(db, user_id) or f"reader {user_id[:8]}"
        _queue(db, user_id, "first_question", f"First question: {who}",
               f"{who} asked Siddha their first question at {_team_time(at)}.", to, now)
        questions += 1
    reports = 0
    for report in _new_reports(db, since):
        who = _address_for(db, report.user_id) or f"reader {report.user_id[:8]}"
        reason = REPORT_REASON_LABELS.get(report.reason, report.reason)
        line = (f"{who} reported an Ask answer at {_team_time(report.created_at)}. "
                f"Reason: {reason}.")
        if report.note:
            line += f" Their note: \u201c{report.note}\u201d"
        line += " Read it in Admin, under Answer reports."
        # One email per report, however many runs see it.
        _queue(db, report.user_id, "answer_report", f"Answer reported: {reason}",
               line, to, now, key=report.id)
        reports += 1
    return {"joined": joined, "first_question": questions, "answer_report": reports}


def is_owner_job(job: NotificationJob) -> bool:
    return (job.payload or {}).get("channel") == CHANNEL


def deliver_owner_job(db: Session, job: NotificationJob, transport: EmailTransport) -> bool:
    payload = job.payload or {}
    to = payload.get("to") or []
    if not to:
        cm.cancel_notification(db, job.id, reason="no team address")
        return False
    line = job.body or job.title
    body = f"{line}\n"
    message_html = (
        f'<p style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;font-size:15px">'
        f"{html.escape(line)}</p>"
    )
    ok = True
    errors: list[str] = []
    for address in to:
        result = transport.send(EmailMessage(
            to=address, subject=job.title, html=message_html, text=body,
            tags={"category": CATEGORY},
        ))
        cm.record_delivery(
            db, job.id, "sent" if result.ok else "failed", provider=transport.provider,
            provider_message_id=result.provider_message_id, error=result.error,
            receipt=result.receipt or {},
        )
        if not result.ok:
            ok = False
            errors.append(result.error or "unknown error")
    if ok:
        cm.mark_notification_sent(db, job.id)
    else:
        cm.mark_notification_failed(db, job.id, "; ".join(errors))
    return ok
