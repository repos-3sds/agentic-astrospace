""""Report this answer" on Ask (Google Play's AI-generated content rule).

A reader can flag any answer with a reason and an optional note. The report
keeps a copy of what they saw, links only their own thread and message, is
deleted with the account, mails the team once (reason and note, never the
answer), and is read in /admin by full administrators only.
"""
from datetime import datetime, timedelta
from typing import get_type_hints

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace import ratelimit
from astrospace.admin.security import FullAdminUser
from astrospace.api import admin_routes
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base
from astrospace.db.models import AnswerReport, NotificationJob
from astrospace.notifications.email import EmailResult
from astrospace.notifications.owner_alerts import schedule_owner_alerts
from astrospace.notifications.worker import deliver_due

ME = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
TEAM = {"OWNER_ALERT_EMAILS": "team@example.com"}


@pytest.fixture()
def env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    db = Session()
    ids = {}
    for owner, key in ((ME, "mine"), (OTHER, "theirs")):
        kundli = crud.create_kundli(db, {
            "user_id": owner, "name": key, "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12, "birth_city": "Vijayawada", "birth_nation": "IN",
        })
        thread = cm.add_ask_turn(db, thread_id=None, user_id=owner, kundli_id=kundli.id,
                                 question="Will my job change?", answer="A steady year at work.")
        messages = cm.get_thread_messages(db, thread.id)
        ids[key] = {"thread": thread.id,
                    "answer": next(m.id for m in messages if m.role == "assistant"),
                    "question": next(m.id for m in messages if m.role == "user")}
    db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@example.com", role="dev")
    try:
        yield TestClient(app), Session, ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _report(client, **fields):
    body = {"reason": "wrong", "answer": "A steady year at work.", "question": "Will my job change?",
            **fields}
    return client.post("/api/v1/ask/reports", json=body)


def test_report_is_stored_with_a_copy_of_the_answer(env):
    client, Session, ids = env
    response = _report(client, note="  It said the wrong house.  ", thread_id=ids["mine"]["thread"],
                       message_id=ids["mine"]["answer"], experience_mode="guided", language="en")
    assert response.status_code == 201
    assert response.json()["received"] is True
    with Session() as db:
        row = db.query(AnswerReport).one()
        assert row.user_id == ME
        assert row.thread_id == ids["mine"]["thread"]
        assert row.message_id == ids["mine"]["answer"]
        assert row.note == "It said the wrong house."
        assert row.answer == "A steady year at work."
        assert row.status == "open"


def test_someone_elses_thread_is_never_linked(env):
    client, Session, ids = env
    assert _report(client, thread_id=ids["theirs"]["thread"],
                   message_id=ids["theirs"]["answer"]).status_code == 201
    with Session() as db:
        row = db.query(AnswerReport).one()
        assert row.thread_id is None and row.message_id is None


def test_a_question_or_local_id_is_not_linked_as_the_answer(env):
    client, Session, ids = env
    _report(client, thread_id=ids["mine"]["thread"], message_id=ids["mine"]["question"])
    _report(client, thread_id=ids["mine"]["thread"], message_id="local-assistant-123")
    _report(client, thread_id="not-a-uuid")
    with Session() as db:
        rows = db.query(AnswerReport).all()
        assert [r.message_id for r in rows] == [None, None, None]
        assert [r.thread_id for r in rows] == [ids["mine"]["thread"]] * 2 + [None]


@pytest.mark.parametrize("fields", [
    {"reason": "spam"},
    {"answer": ""},
    {"note": "x" * 1001},
])
def test_bad_reports_are_refused(env, fields):
    client, Session, _ = env
    assert _report(client, **fields).status_code == 422
    with Session() as db:
        assert db.query(AnswerReport).count() == 0


def test_reports_are_rate_limited(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setenv("ASTROSPACE_LIMIT_REPORT_PER_MINUTE", "2")
    ratelimit.reset()
    assert _report(client).status_code == 201
    assert _report(client).status_code == 201
    response = _report(client)
    assert response.status_code == 429
    assert "many reports" in response.json()["detail"]


def test_account_deletion_removes_reports_and_export_carries_them(env):
    client, Session, ids = env
    _report(client, thread_id=ids["mine"]["thread"], message_id=ids["mine"]["answer"])
    with Session() as db:
        db.add(AnswerReport(user_id=OTHER, reason="other", answer="theirs"))
        db.commit()
    exported = client.get("/api/v1/me/export").json()
    assert [r["reason"] for r in exported["answer_reports"]] == ["wrong"]
    assert client.request("DELETE", "/api/v1/me", json={"confirmation": "DELETE"}).status_code == 200
    with Session() as db:
        assert [r.user_id for r in db.query(AnswerReport).all()] == [OTHER]


class FakeEmail:
    provider = "resend"

    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return EmailResult(ok=True, provider_message_id=f"msg-{len(self.sent)}")


def test_team_is_mailed_once_per_report_with_reason_and_note_only(env):
    _, Session, _ = env
    # A day ahead of the real clock, so the fixture's own questions (made at
    # the real clock) fall outside the lookback and only the reports count.
    now = datetime.utcnow() + timedelta(days=1)
    with Session() as db:
        for note in ("It frightened my mother.", None):
            db.add(AnswerReport(user_id=ME, reason="harmful", note=note,
                                question="private question", answer="private answer",
                                created_at=now - timedelta(minutes=5)))
        db.add(AnswerReport(user_id=ME, reason="wrong", answer="old",
                            created_at=now - timedelta(days=2)))
        db.commit()
        for _ in range(3):
            result = schedule_owner_alerts(db, now, environ=TEAM)
        assert result["answer_report"] == 2
        assert db.query(NotificationJob).filter(NotificationJob.payload.isnot(None)).count() == 2
        email = FakeEmail()
        deliver_due(db, transports={}, now=now, email=email)
    assert [m.to for m in email.sent] == ["team@example.com"] * 2
    assert {m.subject for m in email.sent} == {"Answer reported: Harmful or frightening"}
    text = " ".join(m.text + m.html for m in email.sent)
    assert "It frightened my mother." in text
    assert "Answer reports" in text
    assert "private question" not in text and "private answer" not in text


def test_admin_routes_are_for_full_administrators_only():
    for route in (admin_routes.answer_reports, admin_routes.update_answer_report):
        assert get_type_hints(route, include_extras=True)["user"] == FullAdminUser


class FakeAdminClient:
    def __init__(self, rows):
        self.rows_data = rows
        self.patched = []

    def rows(self, table, params=None):
        assert table == "answer_reports"
        rows = self.rows_data
        if params.get("status"):
            rows = [r for r in rows if f"eq.{r['status']}" == params["status"]]
        return rows

    def auth_users(self):
        return [{"id": ME, "email": "me@example.com"}]

    def patch(self, table, params, payload):
        self.patched.append((table, params, payload))
        return [{"id": params["id"][3:], **payload}]


def test_admin_lists_open_reports_with_the_readers_address(monkeypatch):
    fake = FakeAdminClient([
        {"id": "r1", "user_id": ME, "status": "open", "reason": "wrong"},
        {"id": "r2", "user_id": ME, "status": "reviewed", "reason": "other"},
    ])
    monkeypatch.setattr(admin_routes, "_client", lambda: fake)
    admin = AuthUser(id="admin", email="owner@example.com", role="admin")
    body = admin_routes.answer_reports(admin, status="open", limit=100)
    assert body["open"] == 1
    assert [(r["id"], r["email"]) for r in body["reports"]] == [("r1", "me@example.com")]


def test_admin_marks_a_report_reviewed(monkeypatch):
    fake = FakeAdminClient([])
    monkeypatch.setattr(admin_routes, "_client", lambda: fake)
    admin = AuthUser(id="admin", email="owner@example.com", role="admin")
    report_id = "33333333-3333-4333-8333-333333333333"
    row = admin_routes.update_answer_report(
        report_id, admin_routes.ReportStatusPayload(status="reviewed"), admin)
    assert row["status"] == "reviewed" and row["reviewed_by"] == "owner@example.com"
    with pytest.raises(admin_routes.HTTPException) as err:
        admin_routes.update_answer_report(
            "nope", admin_routes.ReportStatusPayload(status="open"), admin)
    assert err.value.status_code == 404
