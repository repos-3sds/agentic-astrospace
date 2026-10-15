"""Push delivery end to end, without an ephemeris or a network.

Mobile audit item 20. The API half (register/revoke tokens, preferences) is
covered by test_me_practice_routes.py; this covers what happens after: a
morning brief is queued once per user per day at their preferred local time,
delivered to every active token, dead tokens are revoked, and an
unconfigured provider leaves the job retryable rather than lost.
"""
from datetime import date, datetime, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.db import crud, crud_mobile as cm
from astrospace.db.database import Base
from astrospace.db.models import NotificationDelivery, NotificationJob, PushToken
from astrospace.notifications.morning_brief import schedule_morning_briefs
from astrospace.notifications.push import NotConfiguredTransport, PushResult, transports_from_env
from astrospace.notifications.worker import deliver_due, run_once

ME = "user-me"
OTHER = "user-other"


class FakeTransport:
    provider = "fcm"

    def __init__(self, dead_tokens=(), fail_all=False):
        self.sent = []
        self.dead_tokens = set(dead_tokens)
        self.fail_all = fail_all

    def send(self, token, message):
        self.sent.append((token, message))
        if self.fail_all:
            return PushResult(ok=False, error="boom")
        if token in self.dead_tokens:
            return PushResult(ok=False, error="fcm NOT_FOUND: UNREGISTERED", token_dead=True)
        return PushResult(ok=True, provider_message_id=f"projects/x/messages/{len(self.sent)}")


def fake_headline(kundli, as_of, tz_name):
    return f"Steady day for {kundli.name}"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    for user, name, relation in ((ME, "Me", "self"), (ME, "Partner", "partner"), (OTHER, "Them", "friend")):
        crud.create_kundli(session, {
            "user_id": user, "name": name, "relation": relation,
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        })
    cm.upsert_push_token(session, ME, "fcm", "tok-me-phone", timezone="Asia/Kolkata")
    cm.upsert_push_token(session, ME, "fcm", "tok-me-tablet", timezone="Asia/Kolkata")
    cm.upsert_push_token(session, OTHER, "fcm", "tok-other", timezone="Europe/London")
    yield session
    session.close()


class TestScheduling:
    def test_one_brief_per_user_at_local_preferred_time(self, db):
        cm.set_notification_preference(db, ME, "morning_brief", preferred_time=time(6, 30))
        jobs = schedule_morning_briefs(db, today=date(2026, 10, 16), headline=fake_headline)
        by_user = {j.user_id: j for j in jobs}
        assert set(by_user) == {ME, OTHER}
        # 06:30 IST is 01:00 UTC; the default 07:00 BST is 06:00 UTC.
        assert by_user[ME].scheduled_for == datetime(2026, 10, 16, 1, 0)
        assert by_user[OTHER].scheduled_for == datetime(2026, 10, 16, 6, 0)
        # The reader's own chart, not the partner's, even though "Me" sorts after.
        assert by_user[ME].title == "Steady day for Me"
        assert by_user[ME].deep_link == "/m/today"
        assert by_user[ME].timezone == "Asia/Kolkata"

    def test_rerun_is_idempotent(self, db):
        first = schedule_morning_briefs(db, today=date(2026, 10, 16), headline=fake_headline)
        second = schedule_morning_briefs(db, today=date(2026, 10, 16), headline=fake_headline)
        assert {j.id for j in first} == {j.id for j in second}
        assert db.query(NotificationJob).count() == 2

    def test_disabled_preference_is_respected(self, db):
        cm.set_notification_preference(db, ME, "morning_brief", enabled=False)
        jobs = schedule_morning_briefs(db, today=date(2026, 10, 16), headline=fake_headline)
        assert [j.user_id for j in jobs] == [OTHER]

    def test_revoked_only_user_is_skipped(self, db):
        cm.revoke_push_token(db, "fcm", "tok-other")
        jobs = schedule_morning_briefs(db, today=date(2026, 10, 16), headline=fake_headline)
        assert [j.user_id for j in jobs] == [ME]

    def test_headline_failure_cancels_only_that_job(self, db):
        def flaky(kundli, as_of, tz_name):
            if kundli.user_id == ME:
                raise ValueError("no such city")
            return "fine"

        jobs = schedule_morning_briefs(db, today=date(2026, 10, 16), headline=flaky)
        statuses = {j.user_id: j.status for j in jobs}
        assert statuses == {ME: "cancelled", OTHER: "pending"}
        assert "headline failed" in next(j for j in jobs if j.user_id == ME).skip_reason


class TestDelivery:
    def _queue(self, db, when=datetime(2026, 10, 16, 1, 0)):
        return schedule_morning_briefs(db, today=date(2026, 10, 16), headline=fake_headline)

    def test_sends_to_every_token_and_marks_sent(self, db):
        self._queue(db)
        transport = FakeTransport()
        result = deliver_due(db, {"fcm": transport}, now=datetime(2026, 10, 16, 6, 0))
        assert result == {"sent": 2, "failed": 0}
        assert sorted(t for t, _ in transport.sent) == ["tok-me-phone", "tok-me-tablet", "tok-other"]
        assert {j.status for j in db.query(NotificationJob)} == {"sent"}
        assert db.query(NotificationDelivery).filter_by(status="sent").count() == 3
        message = transport.sent[0][1]
        assert message.deep_link == "/m/today"
        assert message.category == "morning_brief"

    def test_not_due_yet_is_left_alone(self, db):
        self._queue(db)
        result = deliver_due(db, {"fcm": FakeTransport()}, now=datetime(2026, 10, 16, 0, 30))
        assert result == {"sent": 0, "failed": 0}
        assert {j.status for j in db.query(NotificationJob)} == {"pending"}

    def test_dead_token_is_revoked_and_job_still_sent(self, db):
        self._queue(db)
        transport = FakeTransport(dead_tokens={"tok-me-tablet"})
        deliver_due(db, {"fcm": transport}, now=datetime(2026, 10, 16, 6, 0))
        tablet = db.query(PushToken).filter_by(token="tok-me-tablet").one()
        assert tablet.revoked_at is not None
        me_job = db.query(NotificationJob).filter_by(user_id=ME).one()
        assert me_job.status == "sent"
        assert db.query(NotificationDelivery).filter_by(push_token_id=tablet.id, status="failed").count() == 1

    def test_unconfigured_transport_keeps_job_retryable(self, db):
        self._queue(db)
        result = deliver_due(db, {"fcm": NotConfiguredTransport("fcm")}, now=datetime(2026, 10, 16, 6, 0))
        assert result == {"sent": 0, "failed": 2}
        job = db.query(NotificationJob).filter_by(user_id=ME).one()
        assert job.status == "pending"
        assert job.attempts == 1
        assert "not configured" in job.last_error

    def test_job_gives_up_after_attempt_cap(self, db):
        self._queue(db)
        transport = FakeTransport(fail_all=True)
        for _ in range(5):
            deliver_due(db, {"fcm": transport}, now=datetime(2026, 10, 16, 6, 0))
        assert {j.status for j in db.query(NotificationJob)} == {"failed"}

    def test_no_active_token_cancels(self, db):
        self._queue(db)
        cm.revoke_push_token(db, "fcm", "tok-other")
        deliver_due(db, {"fcm": FakeTransport()}, now=datetime(2026, 10, 16, 6, 0))
        other = db.query(NotificationJob).filter_by(user_id=OTHER).one()
        assert other.status == "cancelled"
        assert other.skip_reason == "no active push token"


def test_transports_from_env_without_credentials_is_not_configured(tmp_path):
    transports = transports_from_env({})
    assert set(transports) == {"fcm", "apns", "web"}
    assert all(isinstance(t, NotConfiguredTransport) for t in transports.values())
    assert "FCM_SERVICE_ACCOUNT_FILE" in transports["fcm"].reason


def test_run_once_schedules_and_delivers(db, monkeypatch):
    import astrospace.notifications.worker as worker
    monkeypatch.setattr(worker, "schedule_morning_briefs",
                        lambda session: schedule_morning_briefs(session, today=date(2020, 1, 1), headline=fake_headline))
    summary = run_once(db, {"fcm": FakeTransport()})
    assert summary["scheduled"] == 2
    # A 2020 send time is long past, so both go out on the same run.
    assert summary["sent"] == 2
