"""Notifications worker resilience (production audit 2026-10-15, P1
"Notifications"): one exception no longer ends a run, jobs a crashed worker
left in 'processing' are reaped, and a dedupe_key race is not a crash.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.db import crud_mobile as cm
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob
from astrospace.notifications import worker
from astrospace.notifications.push import PushResult

ME = "user-me"
NOW = datetime(2026, 10, 16, 6, 0)


class FakeTransport:
    provider = "fcm"

    def __init__(self, explode_on=()):
        self.sent = []
        self.explode_on = set(explode_on)

    def send(self, token, message):
        if message.title in self.explode_on:
            raise RuntimeError("transport bug")
        self.sent.append((token, message.title))
        return PushResult(ok=True, provider_message_id="m")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autoflush=False, bind=engine)()
    cm.upsert_push_token(session, ME, "fcm", "tok-me", timezone="Asia/Kolkata")
    yield session
    session.close()


def _job(db, title, **fields):
    return cm.schedule_notification(db, ME, "system", NOW - timedelta(hours=1), title,
                                    dedupe_key=f"test:{title}", **fields)


def test_reaper_returns_stale_processing_jobs(db):
    stale = _job(db, "stale")
    fresh = _job(db, "fresh")
    spent = _job(db, "spent")
    for job, claimed, attempts in ((stale, NOW - timedelta(minutes=20), 1),
                                   (fresh, NOW - timedelta(minutes=5), 1),
                                   (spent, NOW - timedelta(hours=2), 5)):
        job.status, job.updated_at, job.attempts = "processing", claimed, attempts
    db.commit()

    assert cm.reap_stale_notifications(db, now=NOW) == 2
    db.expire_all()
    assert db.get(NotificationJob, stale.id).status == "pending"
    assert "reaped" in db.get(NotificationJob, stale.id).last_error
    assert db.get(NotificationJob, fresh.id).status == "processing"
    # Out of attempts: failed, not retried forever.
    assert db.get(NotificationJob, spent.id).status == "failed"


def test_a_reaped_job_is_delivered_on_the_next_run(db):
    job = _job(db, "stuck")
    job.status, job.updated_at, job.attempts = "processing", NOW - timedelta(hours=1), 1
    db.commit()
    cm.reap_stale_notifications(db, now=NOW)
    transport = FakeTransport()
    assert worker.deliver_due(db, {"fcm": transport}, now=NOW) == {"sent": 1, "failed": 0}
    assert transport.sent == [("tok-me", "stuck")]


def test_claim_stamps_the_claim_time(db):
    job = _job(db, "claimed")
    job.updated_at = datetime(2020, 1, 1)
    db.commit()
    before = datetime.utcnow()
    cm.claim_due_notifications(db, now=NOW)
    db.expire_all()
    assert db.get(NotificationJob, job.id).updated_at >= before


def test_one_failing_job_does_not_stop_the_batch(db):
    bad = _job(db, "bad")
    good = _job(db, "good")
    transport = FakeTransport(explode_on={"bad"})
    result = worker.deliver_due(db, {"fcm": transport}, now=NOW)
    assert result == {"sent": 1, "failed": 0, "errored": 1}
    db.expire_all()
    assert db.get(NotificationJob, good.id).status == "sent"
    bad_row = db.get(NotificationJob, bad.id)
    assert bad_row.status == "pending"  # retryable, not stuck in processing
    assert "RuntimeError" in bad_row.last_error


def test_a_failing_stage_does_not_stop_delivery(db, monkeypatch):
    # Long past, so it is due whatever the clock says when this runs.
    cm.schedule_notification(db, ME, "system", datetime(2020, 1, 1), "queued",
                             dedupe_key="test:queued")

    def broken(session):
        raise RuntimeError("scheduler bug")

    monkeypatch.setattr(worker, "schedule_morning_briefs", broken)
    monkeypatch.setattr(worker, "schedule_window_alerts", lambda session: [])
    summary = worker.run_once(db, {"fcm": FakeTransport()})
    assert summary["scheduled"] == 0
    assert summary["sent"] == 1


def test_main_survives_a_failed_run_and_reports_it(monkeypatch):
    def explode(db, transports=None):
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(worker, "run_once", explode)
    monkeypatch.setattr(worker, "transports_from_env", lambda: {})
    assert worker.main(["--once"]) == 1


def test_dedupe_race_returns_the_winning_job(db, monkeypatch):
    winner = _job(db, "race")
    real_query = db.query
    calls = {"n": 0}

    def query(*args, **kwargs):
        # The first existence check misses (the other scheduler has not
        # committed yet), so the insert runs into the unique constraint.
        q = real_query(*args, **kwargs)
        if args and args[0] is NotificationJob and calls["n"] == 0:
            calls["n"] += 1
            return q.filter(NotificationJob.id == "no-such-id")
        return q

    monkeypatch.setattr(db, "query", query)
    again = cm.schedule_notification(db, ME, "system", NOW, "race", dedupe_key="test:race")
    assert again.id == winner.id
    monkeypatch.undo()
    assert db.query(NotificationJob).filter(NotificationJob.dedupe_key == "test:race").count() == 1
