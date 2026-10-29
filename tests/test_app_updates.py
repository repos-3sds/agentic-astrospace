"""Update reminders: the app's launch check, the reminder pushes to phones
still on an older build, and the release rows only GitHub Actions may set.

Nothing is ever blocked unless a build is marked required (or a grace period
is set); the reminders stop at five per build, and never reach a phone that
has already updated.
"""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api import release_routes
from astrospace.db import crud_mobile as cm, get_db
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob
from astrospace.notifications import app_updates as au
from astrospace.notifications.push import PushResult
from astrospace.notifications.worker import deliver_due

# Thu 29 Oct 2026 06:00 UTC = 11:30 in India.
RELEASED = datetime(2026, 10, 29, 6, 0)
SIX_HOURS = RELEASED + timedelta(hours=6)  # 17:30 in India
OLD, NEW = 640, 650


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()


def _phone(db, user, token, build, provider="fcm", tz="Asia/Kolkata", seen=RELEASED):
    row = cm.upsert_push_token(db, user, provider, token, timezone=tz, app_build=build)
    row.last_seen_at = seen
    db.commit()
    return row


def _release(db, platform="android", latest=NEW, **fields):
    return au.set_release(db, platform, latest_build=latest, by="test", now=RELEASED, **fields)


def _reminders(db):
    return db.query(NotificationJob).filter(NotificationJob.category == au.CATEGORY).all()


# ── The launch check ──────────────────────────────────────────────────────────

def test_nothing_set_means_every_build_is_current(db):
    status = au.version_status(au.get_release(db, "android"), "android", 1)
    assert status["status"] == "current"
    assert status["update_url"] == au.DEFAULT_UPDATE_URL["android"]


def test_an_older_build_is_offered_the_update_and_never_blocked_by_default(db):
    row = _release(db)
    assert au.version_status(row, "android", OLD, RELEASED + timedelta(days=90))["status"] == "update_available"
    assert au.version_status(row, "android", NEW)["status"] == "current"
    assert au.version_status(row, "android", NEW + 3)["status"] == "current"  # internal testers run ahead


def test_a_required_build_blocks_only_the_builds_below_it(db):
    row = _release(db, required_build=645)
    assert au.version_status(row, "android", OLD)["status"] == "update_required"
    assert au.version_status(row, "android", 646)["status"] == "update_available"


def test_a_grace_period_blocks_once_it_has_passed(db):
    row = _release(db, block_after_days=3)
    assert au.version_status(row, "android", OLD, RELEASED + timedelta(days=2))["status"] == "update_available"
    assert au.version_status(row, "android", OLD, RELEASED + timedelta(days=3))["status"] == "update_required"


def test_ios_goes_to_testflight(db):
    assert au.version_status(_release(db, "ios"), "ios", OLD)["update_url"].startswith("itms-beta://")


def test_the_route_needs_no_sign_in(db):
    from main import app

    _release(db)
    app.dependency_overrides[get_db] = lambda: db
    try:
        http = TestClient(app)
        r = http.get("/api/v1/app/version", params={"platform": "android", "build": OLD})
        assert r.status_code == 200
        assert r.json()["status"] == "update_available"
        assert r.headers["cache-control"] == "no-store"
        assert http.get("/api/v1/app/version", params={"platform": "web", "build": 1}).status_code == 422
    finally:
        app.dependency_overrides.pop(get_db, None)


# ── Reminder pushes ───────────────────────────────────────────────────────────

def test_first_reminder_waits_for_the_store_then_goes_to_the_old_phone_only(db):
    _phone(db, "behind", "tok-old", OLD)
    _phone(db, "current", "tok-new", NEW)
    _release(db)
    assert au.schedule_update_reminders(db, now=RELEASED + timedelta(hours=1)) == []
    jobs = au.schedule_update_reminders(db, now=SIX_HOURS)
    assert [j.user_id for j in jobs] == ["behind"]
    job = jobs[0]
    assert job.title == "A new version of Siddha is ready"
    assert "Google Play" in job.body and "new" not in job.body.lower().replace("a new version", "")
    assert job.payload["below_build"] == NEW
    assert job.scheduled_for == SIX_HOURS


def test_copy_never_says_what_is_new():
    for platform in au.PLATFORMS:
        for required in (False, True):
            title, body = au.copy_for(platform, required)
            assert "feature" not in body.lower() and "group" not in body.lower()


def test_never_at_night(db):
    _phone(db, "behind", "tok-old", OLD, tz="America/New_York")
    _release(db)
    # 12:00 UTC is 08:00 in New York: held to 10:00 there (14:00 UTC).
    job = au.schedule_update_reminders(db, now=datetime(2026, 10, 29, 12, 0))[0]
    assert job.scheduled_for == datetime(2026, 10, 29, 14, 0)


def test_reminders_space_out_and_stop_at_five(db):
    _phone(db, "behind", "tok-old", OLD)
    _release(db)
    when = SIX_HOURS
    sent_at = []
    for _ in range(160):
        for job in au.schedule_update_reminders(db, now=when):
            job.status = "sent"
            db.commit()
            sent_at.append(job.scheduled_for)
        when += timedelta(hours=6)
    gaps = [(b - a).days for a, b in zip(sent_at, sent_at[1:])]
    assert len(sent_at) == 5
    assert gaps == [2, 4, 7, 7]


def test_a_required_build_reminds_every_two_days_up_to_eight(db):
    _phone(db, "behind", "tok-old", OLD)
    _release(db, required_build=NEW)
    when, sent = SIX_HOURS, []
    for _ in range(120):
        for job in au.schedule_update_reminders(db, now=when):
            assert job.title == "Please update Siddha" and job.payload["required"]
            job.status = "sent"
            db.commit()
            sent.append(job.scheduled_for)
        when += timedelta(hours=6)
    assert len(sent) == 8
    assert {(b - a).days for a, b in zip(sent, sent[1:])} == {2}


def test_a_newer_release_replaces_the_pending_reminder(db):
    _phone(db, "behind", "tok-old", OLD)
    _release(db)
    first = au.schedule_update_reminders(db, now=SIX_HOURS)[0]
    au.set_release(db, "android", latest_build=NEW + 5, now=SIX_HOURS)
    second = au.schedule_update_reminders(db, now=SIX_HOURS + timedelta(hours=6))
    db.refresh(first)
    assert first.status == "cancelled"
    assert second and second[0].payload["below_build"] == NEW + 5


def test_respects_a_reader_who_turned_every_notification_off(db):
    _phone(db, "quiet", "tok-q", OLD)
    for cat in au.PUSH_SWITCHES:
        cm.set_notification_preference(db, "quiet", cat, enabled=False)
    _release(db)
    assert au.schedule_update_reminders(db, now=SIX_HOURS) == []


def test_off_switch_and_long_gone_phones(db):
    _phone(db, "gone", "tok-gone", OLD, seen=RELEASED - timedelta(days=90))
    _release(db)
    assert au.schedule_update_reminders(db, now=SIX_HOURS) == []
    _phone(db, "here", "tok-here", OLD)
    assert au.schedule_update_reminders(db, now=SIX_HOURS, environ={"APP_UPDATE_REMINDERS": "off"}) == []


def test_builds_before_this_feature_count_as_behind(db):
    _phone(db, "old-app", "tok-legacy", None)
    _release(db)
    assert [j.user_id for j in au.schedule_update_reminders(db, now=SIX_HOURS)] == ["old-app"]


def test_a_legacy_registration_of_an_updated_phone_is_not_reminded(db):
    _phone(db, "updated", "tok-legacy", None, seen=RELEASED - timedelta(days=3))
    _phone(db, "updated", "tok-now", NEW)
    _release(db)
    assert au.schedule_update_reminders(db, now=SIX_HOURS) == []


def test_a_release_at_or_before_the_last_silent_build_reminds_nobody_without_a_build(db):
    _phone(db, "old-app", "tok-legacy", None)
    _release(db, latest=au.LAST_SILENT_BUILD)
    assert au.schedule_update_reminders(db, now=SIX_HOURS) == []


def test_ios_reminders_go_to_apns_phones_only(db):
    _phone(db, "two-phones", "fcm-tok", NEW)
    _phone(db, "two-phones", "apns-tok", OLD, provider="apns")
    _release(db, "android")
    _release(db, "ios")
    jobs = au.schedule_update_reminders(db, now=SIX_HOURS)
    assert [(j.payload["platform"], "TestFlight" in j.body) for j in jobs] == [("ios", True)]


# ── Delivery ──────────────────────────────────────────────────────────────────

class Recorder:
    def __init__(self, provider):
        self.provider = provider
        self.tokens = []

    def send(self, token, message):
        self.tokens.append(token)
        return PushResult(ok=True, provider_message_id="m")


def test_delivered_only_to_the_phone_still_behind(db):
    _phone(db, "two-phones", "tok-old", OLD)
    _phone(db, "two-phones", "tok-other", OLD)
    _release(db)
    au.schedule_update_reminders(db, now=SIX_HOURS)
    # The second phone updates before the reminder goes out.
    _phone(db, "two-phones", "tok-other", NEW)
    fcm = Recorder("fcm")
    result = deliver_due(db, {"fcm": fcm, "apns": Recorder("apns")}, now=SIX_HOURS, email=object())
    assert result["sent"] == 1
    assert fcm.tokens == ["tok-old"]


def test_cancelled_when_every_phone_updated_first(db):
    _phone(db, "behind", "tok-old", OLD)
    _release(db)
    job = au.schedule_update_reminders(db, now=SIX_HOURS)[0]
    _phone(db, "behind", "tok-old", NEW)
    fcm = Recorder("fcm")
    deliver_due(db, {"fcm": fcm}, now=SIX_HOURS, email=object())
    db.refresh(job)
    assert job.status == "cancelled" and fcm.tokens == []


def test_other_jobs_still_reach_every_phone():
    class T:
        def __init__(self, i, build):
            self.id, self.app_build = i, build
    tokens = [T("a", 1), T("b", None)]
    assert au.tokens_for_job(tokens, {}) == tokens
    assert au.tokens_for_job(tokens, None) == tokens


# ── Setting the release ───────────────────────────────────────────────────────

@pytest.fixture
def client(db, monkeypatch):
    from main import app

    claims = {"email": release_routes.DEFAULT_CALLER, "email_verified": True}
    monkeypatch.setattr(release_routes, "_verify_google_id_token", lambda token, aud: dict(claims))
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), claims
    app.dependency_overrides.pop(get_db, None)


def test_only_the_deployer_sets_a_release(client):
    http, claims = client
    body = {"platform": "android", "latest_build": NEW}
    assert http.post("/api/v1/releases/app-version", json=body).status_code == 401
    claims["email"] = "someone@example.com"
    assert http.post("/api/v1/releases/app-version", json=body,
                     headers={"Authorization": "Bearer t"}).status_code == 403


def test_setting_changes_only_the_fields_sent(client, db):
    http, _ = client
    auth = {"Authorization": "Bearer t"}
    r = http.post("/api/v1/releases/app-version", headers=auth,
                  json={"platform": "android", "latest_build": NEW, "required_build": 600})
    assert r.status_code == 200
    assert r.json()["latest_build"] == NEW and r.json()["required_build"] == 600
    r = http.post("/api/v1/releases/app-version", headers=auth,
                  json={"platform": "android", "latest_build": NEW + 1})
    assert r.json()["required_build"] == 600
    r = http.post("/api/v1/releases/app-version", headers=auth,
                  json={"platform": "android", "required_build": None})
    assert r.json()["required_build"] is None and r.json()["latest_build"] == NEW + 1
    bad = http.post("/api/v1/releases/app-version", headers=auth,
                    json={"platform": "android", "update_url": "http://evil.example"})
    assert bad.status_code == 422


def test_the_app_reports_its_build_with_the_push_token(db):
    from main import app
    from astrospace.api.auth import current_user as get_current_user

    from astrospace.api.auth import AuthUser

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: AuthUser(id="reader", email="r@example.com")
    try:
        r = TestClient(app).put("/api/v1/me/push-tokens",
                                json={"provider": "fcm", "token": "t1", "app_build": NEW})
        assert r.status_code == 200
        assert cm.list_active_push_tokens(db, "reader")[0].app_build == NEW
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
