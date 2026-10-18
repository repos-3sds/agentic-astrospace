"""Email delivery end to end, without a provider, a model or the network.

What matters most here is consent: nothing is emailed unless the reader
turned that email on, turning it off (in the app or from the link in an
email) stops what is already queued, and an address that bounced or
complained is never written to again.
"""
import base64
import hashlib
import hmac
import json
import time as _time
from datetime import date, datetime, time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api.auth import AuthUser, current_user
from astrospace.api.email_routes import router as email_router
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob, NotificationPreference
from astrospace.notifications import email_jobs
from astrospace.notifications.email import (
    EmailContent, EmailResult, NotConfiguredEmail, ResendTransport, build_message,
    email_transport_from_env, read_unsubscribe_token, unsubscribe_token,
)
from astrospace.notifications.worker import deliver_due

ME = "user-me"
OTHER = "user-other"
SECRET = "test-link-secret"

BRIEF = {
    "card_title": "Finish what you started",
    "headline": "A steady day for loose ends",
    "summary": "Good for wrapping up, less so for new starts.",
    "narrative": "The Moon sits well for you today, so small finishing jobs go smoothly.",
    "practical_close": "Clear one thing off your list.",
    "focus": "Finish one task.",
    "energy": "steady",
    "areas": {"love": "Listen more than you speak.", "money": "Review, don't buy.",
              "work": "Close open threads.", "health": "Rest early.", "growth": "Read a little."},
    "do": [{"headline": "Finish routine work", "detail": "x"}],
    "avoid": [{"headline": "Avoid new purchases", "detail": "y"}],
    "timing_note": "Keep 10:30 to 12:00 for routine tasks.",
    "why": ["a", "b"],
    "spoken": [],
}


class FakeEmail:
    provider = "resend"

    def __init__(self, dead=False):
        self.sent = []
        self.dead = dead

    def send(self, message):
        self.sent.append(message)
        if self.dead:
            return EmailResult(ok=False, error="resend 422: invalid to", address_dead=True)
        return EmailResult(ok=True, provider_message_id=f"msg-{len(self.sent)}")


@pytest.fixture(autouse=True)
def link_secret(monkeypatch):
    monkeypatch.setenv("EMAIL_LINK_SECRET", SECRET)
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://siddha.test")


@pytest.fixture
def Session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db(Session):
    session = Session()
    for user, name, accuracy in ((ME, "Me", "exact"), (OTHER, "Them", "unknown")):
        crud.create_kundli(session, {
            "user_id": user, "name": name, "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12, "birth_time_accuracy": accuracy,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        })
    yield session
    session.close()


def _opt_in(db, user, category, email=None, tz="Asia/Kolkata"):
    cm.upsert_email_recipient(db, user, email or f"{user}@example.com", timezone=tz)
    cm.set_notification_preference(db, user, category, enabled=True, channels=["email"])


def _store_brief(db, user, day):
    kundli = crud.list_kundlis(db, user)[0]
    cm.put_cached_daily_guidance(db, kundli.id, day, "hash", {"source": "agent", "brief": BRIEF},
                                 language="en")
    return kundli


# ── Links and transport ───────────────────────────────────────────────────────

class TestLinks:
    def test_token_round_trips_and_rejects_tampering(self):
        token = unsubscribe_token(ME, "daily_email")
        assert read_unsubscribe_token(token) == (ME, "daily_email")
        user, category, mac = token.split(".")
        forged = f"{base64.urlsafe_b64encode(OTHER.encode()).decode().rstrip('=')}.{category}.{mac}"
        assert read_unsubscribe_token(forged) is None
        assert read_unsubscribe_token("garbage") is None

    def test_every_marketing_email_has_one_click_unsubscribe(self):
        message = build_message("a@b.c", EmailContent(subject="S", preview="P", heading="H", intro="I"),
                                user_id=ME, category="daily_email")
        assert message.headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
        assert message.headers["List-Unsubscribe"].startswith("<https://siddha.test/api/v1/email/unsubscribe?t=")
        assert "Stop all emails" in message.html and "Siddha, 3 Senses Design Studio, India 533005" in message.html
        assert "Stop these emails: https://siddha.test/" in message.text

    def test_model_copy_is_escaped(self):
        content = EmailContent(subject="S", preview="P", heading="<script>x</script>", intro="a & b")
        message = build_message("a@b.c", content, user_id=ME, category="daily_email")
        assert "<script>x" not in message.html and "&lt;script&gt;" in message.html

    def test_not_configured_without_key_or_secret(self, monkeypatch):
        assert isinstance(email_transport_from_env({}), NotConfiguredEmail)
        assert isinstance(email_transport_from_env({"RESEND_API_KEY": "k"}), NotConfiguredEmail)
        transport = email_transport_from_env({"RESEND_API_KEY": "k", "EMAIL_LINK_SECRET": "s"})
        assert isinstance(transport, ResendTransport)
        assert transport.sender == "Siddha <asksiddha@3senses.design>"

    def test_resend_payload(self):
        class Http:
            def post(self, url, json, timeout, headers):
                self.call = (url, json, headers)

                class R:
                    status_code = 200
                    text = ""

                    def json(self):
                        return {"id": "re_1"}
                return R()

        http = Http()
        result = ResendTransport("key", http=http).send(
            build_message("a@b.c", EmailContent(subject="S", preview="P", heading="H", intro="I"),
                          user_id=ME, category="daily_email"))
        url, payload, headers = http.call
        assert result.ok and result.provider_message_id == "re_1"
        assert url == "https://api.resend.com/emails" and headers["Authorization"] == "Bearer key"
        assert payload["to"] == ["a@b.c"] and payload["reply_to"] == "asksiddha@3senses.design"
        assert "List-Unsubscribe" in payload["headers"]


# ── Scheduling ────────────────────────────────────────────────────────────────

class TestDaily:
    def test_nothing_without_opt_in(self, db):
        _store_brief(db, ME, date(2026, 10, 16))
        cm.upsert_email_recipient(db, ME, "me@example.com", timezone="Asia/Kolkata")
        assert email_jobs.schedule_daily_emails(db, now=datetime.fromisoformat("2026-10-16T05:00+05:30")) == []

    def test_queued_at_morning_from_the_stored_brief(self, db):
        _opt_in(db, ME, "daily_email")
        _store_brief(db, ME, date(2026, 10, 16))
        jobs = email_jobs.schedule_daily_emails(db, now=datetime.fromisoformat("2026-10-16T05:00+05:30"))
        assert len(jobs) == 1
        job = jobs[0]
        # 06:30 IST is 01:00 UTC.
        assert job.scheduled_for == datetime(2026, 10, 16, 1, 0)
        assert job.title == "A steady day for loose ends"
        assert job.payload["channel"] == "email"
        # Once a day, however many runs see it.
        assert email_jobs.schedule_daily_emails(db, now=datetime.fromisoformat("2026-10-16T05:15+05:30")) == []

    def test_waits_for_the_brief_then_gives_up_late(self, db):
        _opt_in(db, ME, "daily_email")
        assert email_jobs.schedule_daily_emails(db, now=datetime.fromisoformat("2026-10-16T05:00+05:30")) == []
        _store_brief(db, ME, date(2026, 10, 16))
        assert email_jobs.schedule_daily_emails(db, now=datetime.fromisoformat("2026-10-16T11:30+05:30")) == []

    def test_content_carries_the_whole_brief(self):
        content = email_jobs.daily_content(BRIEF, date(2026, 10, 16), "Kakinada")
        blocks = {b["heading"]: b for b in content.blocks}
        assert content.date_line == "Friday, 16 October · Kakinada"
        assert content.eyebrow == "Finish what you started" and content.chips == ["Steady energy"]
        assert blocks["Good for today"]["items"] == [["Finish routine work", "x"]]
        assert ["Energy", "Rest early."] in blocks["Across your life"]["rows"]
        assert blocks["Timing"]["body"] == "Keep 10:30 to 12:00 for routine tasks."
        assert "Why today feels this way" in blocks
        # Stored as plain data in the job and read back unchanged.
        assert email_jobs.content_from_payload(email_jobs._content_dict(content)) == content


class TestFestival:
    def test_moon_day_copy_names_the_convention(self):
        content = email_jobs.festival_content(date(2026, 10, 26), {"moon": "full", "festivals": []}, "Kakinada",
                                              [["Sun 8 Nov", "Diwali / Deepavali"]])
        assert content.subject == "Tomorrow is a full moon day"
        assert [b["heading"] for b in content.blocks] == ["How people mark it", "Something simple to try", "Coming up"]
        assert "Kakinada" in content.note and "temple calendar" in content.note

    def test_festival_leads_and_moon_follows(self):
        fest = {"name": "Sharad Purnima", "description": "Harvest full moon.", "prep_guidance": None,
                "observance_note": None}
        content = email_jobs.festival_content(date(2026, 10, 25), {"moon": "full", "festivals": [fest]}, "Pune")
        assert content.subject == "Tomorrow is Sharad Purnima"
        assert content.blocks[-1]["heading"] == "It is also a full moon day"

    def test_ordinary_day_sends_nothing(self):
        assert email_jobs.festival_content(date(2026, 10, 27), {"moon": None, "festivals": []}, "Pune") is None

    def test_queued_for_the_evening_before(self, db, monkeypatch):
        _opt_in(db, ME, "festival_email")
        monkeypatch.setattr(email_jobs, "days_of_note",
                            lambda day, city, nation: {"moon": "new", "festivals": []})
        jobs = email_jobs.schedule_festival_emails(db, now=datetime.fromisoformat("2026-10-16T09:00+05:30"))
        assert len(jobs) == 1
        assert jobs[0].scheduled_for == datetime(2026, 10, 16, 12, 30)  # 18:00 IST
        assert jobs[0].dedupe_key == f"festival_email:{ME}:2026-10-17"

    def test_coming_up_lists_the_next_fortnight(self):
        rows = email_jobs.coming_up(date(2026, 10, 25), "Kakinada", "IN")
        assert ["Mon 26 Oct", "Full moon"] in rows
        assert all(len(r) == 2 for r in rows)

    def test_real_calendar_finds_moon_days(self):
        # Two full and two new moons fall in any 60-day stretch.
        start = date(2026, 10, 1)
        moons = [email_jobs.days_of_note(date.fromordinal(start.toordinal() + i), "Kakinada", "IN")["moon"]
                 for i in range(60)]
        assert moons.count("full") >= 2 and moons.count("new") >= 2


class TestWelcome:
    def test_once_and_only_after_opting_in(self, db):
        cm.upsert_email_recipient(db, OTHER, "them@example.com")
        assert email_jobs.schedule_welcome_emails(db) == []
        _opt_in(db, OTHER, "festival_email")
        jobs = email_jobs.schedule_welcome_emails(db)
        assert len(jobs) == 1 and jobs[0].category == "system"
        # Their birth time is unknown, so the welcome asks for it.
        content = email_jobs.content_from_payload(jobs[0].payload["content"])
        assert any(b.get("heading") == "One thing that helps" for b in content.blocks)
        assert email_jobs.schedule_welcome_emails(db) == []


# ── Delivery ──────────────────────────────────────────────────────────────────

def _due_job(db, user=ME, category="daily_email"):
    content = EmailContent(subject="Hi", preview="P", heading="H", intro="I")
    return email_jobs._queue(db, user, category, datetime(2026, 1, 1), content, f"{category}:{user}:t")


class TestDelivery:
    def test_sent_through_the_email_transport(self, db):
        _opt_in(db, ME, "daily_email")
        job_id = _due_job(db).id
        fake = FakeEmail()
        assert deliver_due(db, transports={}, email=fake, now=datetime(2026, 1, 2)) == {"sent": 1, "failed": 0}
        assert fake.sent[0].to == f"{ME}@example.com"
        assert db.get(NotificationJob, job_id).status == "sent"

    def test_turned_off_after_queueing_is_not_sent(self, db):
        _opt_in(db, ME, "daily_email")
        job_id = _due_job(db).id
        cm.set_notification_preference(db, ME, "daily_email", enabled=False)
        fake = FakeEmail()
        deliver_due(db, transports={}, email=fake, now=datetime(2026, 1, 2))
        assert fake.sent == [] and db.get(NotificationJob, job_id).status == "cancelled"

    def test_refused_address_is_suppressed(self, db):
        _opt_in(db, ME, "daily_email")
        _due_job(db)
        deliver_due(db, transports={}, email=FakeEmail(dead=True), now=datetime(2026, 1, 2))
        assert cm.get_email_recipient(db, ME).suppressed_at is not None
        assert cm.email_subscribers(db, "daily_email") == []

    def test_unconfigured_stays_retryable(self, db):
        _opt_in(db, ME, "daily_email")
        job_id = _due_job(db).id
        deliver_due(db, transports={}, email=NotConfiguredEmail("not configured"), now=datetime(2026, 1, 2))
        assert db.get(NotificationJob, job_id).status == "pending"


# ── API ───────────────────────────────────────────────────────────────────────

@pytest.fixture
def client(Session, db):
    app = FastAPI()
    app.include_router(email_router)

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@example.com")
    return TestClient(app)


class TestApi:
    def test_settings_default_off_and_toggle(self, client):
        state = client.get("/api/v1/me/email").json()
        assert state["address"] == "me@example.com"
        assert state["categories"] == {"daily_email": False, "festival_email": False}
        state = client.put("/api/v1/me/email/daily_email",
                           json={"enabled": True, "timezone": "Asia/Kolkata"}).json()
        assert state["categories"]["daily_email"] is True and state["deliverable"] is True
        assert client.put("/api/v1/me/email/window_alert", json={"enabled": True}).status_code == 404

    def test_get_never_unsubscribes_post_does(self, client, db):
        client.put("/api/v1/me/email/daily_email", json={"enabled": True})
        token = unsubscribe_token(ME, "daily_email")
        page = client.get(f"/api/v1/email/unsubscribe?t={token}")
        assert page.status_code == 200 and "Yes, stop them" in page.text
        db.expire_all()
        assert cm.get_notification_preferences(db, ME)["daily_email"]["enabled"] is True
        # The one-click POST a mail app sends.
        done = client.post(f"/api/v1/email/unsubscribe?t={token}",
                           data={"List-Unsubscribe": "One-Click"})
        assert done.status_code == 200 and "Done" in done.text
        db.expire_all()
        assert cm.get_notification_preferences(db, ME)["daily_email"]["enabled"] is False

    def test_unsubscribe_all_and_bad_token(self, client, db):
        client.put("/api/v1/me/email/daily_email", json={"enabled": True})
        client.put("/api/v1/me/email/festival_email", json={"enabled": True})
        client.post("/api/v1/email/unsubscribe", data={"t": unsubscribe_token(ME, "all")})
        db.expire_all()
        prefs = cm.get_notification_preferences(db, ME)
        assert not prefs["daily_email"]["enabled"] and not prefs["festival_email"]["enabled"]
        assert client.post("/api/v1/email/unsubscribe?t=nope").status_code == 400

    def test_old_link_after_account_deletion_writes_nothing(self, client, db):
        # No recipient row: the account was deleted, or was never emailed.
        token = unsubscribe_token("deleted-reader", "all")
        done = client.post("/api/v1/email/unsubscribe", data={"t": token})
        assert done.status_code == 200 and "Done" in done.text
        assert db.query(NotificationPreference).filter_by(user_id="deleted-reader").count() == 0

    def _signed(self, secret_b64, body, stamp=None):
        stamp = str(stamp or int(_time.time()))
        sig = base64.b64encode(hmac.new(base64.b64decode(secret_b64), f"msg_1.{stamp}.".encode() + body,
                                        hashlib.sha256).digest()).decode()
        return {"svix-id": "msg_1", "svix-timestamp": stamp, "svix-signature": f"v1,{sig}",
                "content-type": "application/json"}

    def test_webhook_suppresses_hard_bounce_only_when_signed(self, client, db, monkeypatch):
        secret = base64.b64encode(b"webhook-secret").decode()
        monkeypatch.setenv("RESEND_WEBHOOK_SECRET", f"whsec_{secret}")
        client.put("/api/v1/me/email/daily_email", json={"enabled": True})
        body = json.dumps({"type": "email.bounced",
                           "data": {"to": ["ME@example.com"], "bounce": {"type": "Permanent"}}}).encode()
        bad = dict(self._signed(secret, body), **{"svix-signature": "v1,AAAA"})
        assert client.post("/api/v1/email/webhooks/resend", content=body, headers=bad).status_code == 401
        old = self._signed(secret, body, stamp=int(_time.time()) - 3600)
        assert client.post("/api/v1/email/webhooks/resend", content=body, headers=old).status_code == 401
        ok = client.post("/api/v1/email/webhooks/resend", content=body, headers=self._signed(secret, body))
        assert ok.json() == {"ok": True, "suppressed": 1}
        transient = json.dumps({"type": "email.bounced",
                                "data": {"to": ["x@example.com"], "bounce": {"type": "Transient"}}}).encode()
        assert client.post("/api/v1/email/webhooks/resend", content=transient,
                           headers=self._signed(secret, transient)).json()["suppressed"] == 0
        state = client.get("/api/v1/me/email").json()
        assert state["deliverable"] is False and state["suppressed_reason"] == "hard bounce"
