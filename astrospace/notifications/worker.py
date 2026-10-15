"""Deliver due NotificationJob rows through the configured transports.

    python -m astrospace.notifications.worker --once      # schedule + deliver, exit
    python -m astrospace.notifications.worker             # loop every 15 minutes

Deliberately a plain loop, not APScheduler or Celery: one process, one DB,
SKIP LOCKED on Postgres (crud_mobile.claim_due_notifications) so two replicas
cannot double-send. Nothing here answers an HTTP request.
"""
from __future__ import annotations

import argparse
import logging
import time as _time
from datetime import datetime

from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import NotificationJob
from .morning_brief import schedule_morning_briefs
from .push import PushMessage, PushTransport, transports_from_env

log = logging.getLogger("astrospace.notifications")


def deliver_job(db: Session, job: NotificationJob,
                transports: dict[str, PushTransport]) -> bool:
    """Send one job to every active token its user has. One success marks
    the job sent; a job whose every token failed goes back to pending (up to
    the attempt cap in crud_mobile.mark_notification_failed)."""
    tokens = cm.list_active_push_tokens(db, job.user_id)
    if not tokens:
        cm.cancel_notification(db, job.id, reason="no active push token")
        return False

    message = PushMessage(
        title=job.title, body=job.body, deep_link=job.deep_link,
        data=job.payload or {}, category=job.category,
    )
    any_ok = False
    errors: list[str] = []
    for token in tokens:
        transport = transports.get(token.provider)
        if transport is None:
            result_error = f"no transport for provider {token.provider!r}"
            cm.record_delivery(db, job.id, "failed", push_token_id=token.id,
                               provider=token.provider, error=result_error)
            errors.append(result_error)
            continue
        result = transport.send(token.token, message)
        cm.record_delivery(
            db, job.id, "sent" if result.ok else "failed",
            push_token_id=token.id, provider=token.provider,
            provider_message_id=result.provider_message_id,
            error=result.error, receipt=result.receipt or {},
        )
        if result.ok:
            any_ok = True
        else:
            errors.append(result.error or "unknown error")
            if result.token_dead:
                cm.revoke_push_token(db, token.provider, token.token)

    if any_ok:
        cm.mark_notification_sent(db, job.id)
    else:
        cm.mark_notification_failed(db, job.id, "; ".join(errors)[:2000])
    return any_ok


def deliver_due(db: Session, transports: dict[str, PushTransport] | None = None,
                now: datetime | None = None, limit: int = 100) -> dict[str, int]:
    transports = transports or transports_from_env()
    sent = failed = 0
    for job in cm.claim_due_notifications(db, limit=limit, now=now):
        if deliver_job(db, job, transports):
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}


def run_once(db: Session, transports: dict[str, PushTransport] | None = None) -> dict:
    scheduled = schedule_morning_briefs(db)
    delivered = deliver_due(db, transports)
    summary = {"scheduled": len(scheduled), **delivered}
    log.info("notifications: %s", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AstroSpace push notification worker")
    parser.add_argument("--once", action="store_true", help="schedule and deliver once, then exit")
    parser.add_argument("--interval", type=int, default=900, help="seconds between runs (default 900)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    from ..db.database import SessionLocal

    transports = transports_from_env()
    while True:
        db = SessionLocal()
        try:
            run_once(db, transports)
        finally:
            db.close()
        if args.once:
            return 0
        _time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
