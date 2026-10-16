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
from .daily_briefs import schedule_daily_briefs
from .morning_brief import schedule_morning_briefs
from .push import PushMessage, PushTransport, transports_from_env
from .window_alerts import schedule_window_alerts

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
    """Deliver every claimed job, each in isolation: one job that raises (a
    transport bug, a bad payload, a lost connection) is rolled back, logged
    and returned to the queue, and the rest of the batch still goes out.
    Before this, the first exception ended the run and left every claimed
    job after it stuck in 'processing' for good."""
    transports = transports or transports_from_env()
    sent = failed = errored = 0
    for job in cm.claim_due_notifications(db, limit=limit, now=now):
        job_id = job.id
        try:
            if deliver_job(db, job, transports):
                sent += 1
            else:
                failed += 1
        except Exception as exc:
            errored += 1
            log.exception("notification job %s raised during delivery", job_id)
            db.rollback()
            try:
                cm.mark_notification_failed(db, job_id, f"worker error: {type(exc).__name__}")
            except Exception:
                # Left 'processing'; the next run's reaper returns it.
                db.rollback()
                log.exception("could not record failure for notification job %s", job_id)
    result = {"sent": sent, "failed": failed}
    if errored:
        result["errored"] = errored
    return result


def _step(db: Session, name: str, call, default):
    """Run one stage of a worker run; a failing stage is logged and the run
    moves on, so a scheduler bug never blocks delivery of what is queued."""
    try:
        return call()
    except Exception:
        log.exception("notifications: %s failed", name)
        db.rollback()
        return default


def run_once(db: Session, transports: dict[str, PushTransport] | None = None) -> dict:
    reaped = _step(db, "reap", lambda: cm.reap_stale_notifications(db), 0)
    # Before the morning briefs, so the brief behind the push is already written.
    briefs = _step(db, "daily briefs", lambda: schedule_daily_briefs(db), {})
    scheduled = _step(db, "morning briefs", lambda: schedule_morning_briefs(db), [])
    windows = _step(db, "window alerts", lambda: schedule_window_alerts(db), [])
    delivered = _step(db, "delivery", lambda: deliver_due(db, transports),
                      {"sent": 0, "failed": 0, "delivery_failed": True})
    summary = {"reaped": reaped, "daily_briefs": briefs, "scheduled": len(scheduled),
               "window_alerts": len(windows), **delivered}
    log.info("notifications: %s", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AstroSpace push notification worker")
    parser.add_argument("--once", action="store_true", help="schedule and deliver once, then exit")
    parser.add_argument("--interval", type=int, default=900, help="seconds between runs (default 900)")
    args = parser.parse_args(argv)
    from ..logging_config import configure_logging

    configure_logging()

    from ..db.database import SessionLocal

    transports = transports_from_env()
    while True:
        ok = True
        db = SessionLocal()
        try:
            run_once(db, transports)
        except Exception:
            # Per run: a failure (the database unreachable, say) is logged and
            # the loop carries on to the next interval instead of dying.
            ok = False
            log.exception("notifications: run failed")
        finally:
            db.close()
        if args.once:
            # Non-zero so the Cloud Run job execution shows as failed.
            return 0 if ok else 1
        _time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
