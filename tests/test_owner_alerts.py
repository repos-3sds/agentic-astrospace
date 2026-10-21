"""Team emails on a reader's first sign-in and first question.

Off without OWNER_ALERT_EMAILS; once per reader per event however many runs
see it; never to the reader; never with the words of the question.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.db import crud, crud_mobile as cm
from astrospace.db.database import Base
from astrospace.db.models import AskMessage, AskThread, BillingAccount, NotificationJob
from astrospace.notifications.email import EmailResult
from astrospace.notifications.owner_alerts import schedule_owner_alerts
from astrospace.notifications.worker import deliver_due

NOW = datetime(2026, 10, 20, 9, 0)
TEAM = {"OWNER_ALERT_EMAILS": "team@example.com"}


class FakeEmail:
    provider = "resend"

    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)
        return EmailResult(ok=True, provider_message_id=f"msg-{len(self.sent)}")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    session.close()


def _join(db, user, at, email=None):
    db.add(BillingAccount(owner_user_id=user, kind="individual", created_at=at, updated_at=at))
    db.commit()
    if email:
        cm.upsert_email_recipient(db, user, email)


def _ask(db, user, at, words="Will my exam go well?"):
    kundli = crud.create_kundli(db, {
        "user_id": user, "name": "Me", "relation": "self",
        "birth_year": 1991, "birth_month": 8, "birth_day": 14,
        "birth_hour": 6, "birth_minute": 12, "birth_city": "Vijayawada", "birth_nation": "IN",
    })
    thread = AskThread(user_id=user, kundli_id=kundli.id)
    db.add(thread)
    db.commit()
    db.add(AskMessage(thread_id=thread.id, role="user", content=words, created_at=at))
    db.commit()


def test_off_without_team_address(db):
    _join(db, "u1", NOW - timedelta(minutes=5), "dhanvi@example.com")
    assert schedule_owner_alerts(db, NOW, environ={}) == {}
    assert db.query(NotificationJob).count() == 0


def test_first_sign_in_mails_the_team_once(db):
    _join(db, "u1", NOW - timedelta(minutes=5), "dhanvi@example.com")
    for _ in range(3):
        schedule_owner_alerts(db, NOW, environ=TEAM)
    jobs = db.query(NotificationJob).all()
    assert len(jobs) == 1
    email = FakeEmail()
    deliver_due(db, transports={}, now=NOW, email=email)
    deliver_due(db, transports={}, now=NOW, email=email)
    assert [m.to for m in email.sent] == ["team@example.com"]
    assert email.sent[0].subject == "New on Siddha: dhanvi@example.com"
    assert "14:25 IST" in email.sent[0].text


def test_old_accounts_are_not_mailed(db):
    _join(db, "u1", NOW - timedelta(days=3), "old@example.com")
    assert schedule_owner_alerts(db, NOW, environ=TEAM) == {"joined": 0, "first_question": 0, "answer_report": 0}


def test_first_question_says_when_not_what(db):
    _join(db, "u1", NOW - timedelta(days=3), "lalitha@example.com")
    _ask(db, "u1", NOW - timedelta(minutes=10), words="private words")
    schedule_owner_alerts(db, NOW, environ=TEAM)
    email = FakeEmail()
    deliver_due(db, transports={}, now=NOW, email=email)
    assert len(email.sent) == 1
    message = email.sent[0]
    assert message.subject == "First question: lalitha@example.com"
    assert "private words" not in message.text + message.html


def test_later_questions_do_not_mail(db):
    _join(db, "u1", NOW - timedelta(days=3), "a@example.com")
    _ask(db, "u1", NOW - timedelta(days=1))
    _ask(db, "u1", NOW - timedelta(minutes=10))
    assert schedule_owner_alerts(db, NOW, environ=TEAM)["first_question"] == 0
