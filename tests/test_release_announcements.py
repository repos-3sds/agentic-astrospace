"""What's new for testers: notes from merged pull requests, the team preview,
and reader emails only to readers with tips emails on.

Copy rules hold whatever the model writes: no prices, links or website, and
a broken line falls back to the tidied titles. Only the deployer's Google ID
token may call the routes.
"""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api import release_routes
from astrospace.db import crud_mobile as cm, get_db
from astrospace.db.database import Base
from astrospace.db.models import NotificationJob
from astrospace.notifications import release_announcements as ra
from astrospace.notifications.email import EmailResult
from astrospace.notifications.worker import deliver_due

NOW = datetime(2026, 10, 23, 6, 0)  # 11:30 in India
TITLES = [
    "Fix widgets that would not add, Listen play after resize, add widget opacity (#240)",
    "Testers get 10 Ask questions a month instead of 3 (#239)",
]


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


@pytest.fixture
def email_env(monkeypatch):
    monkeypatch.setenv("EMAIL_LINK_SECRET", "test-secret")
    monkeypatch.setenv("OWNER_ALERT_EMAILS", "team@example.com")


def _reader(db, user, *, tips=True, tz="Asia/Kolkata"):
    cm.upsert_email_recipient(db, user, f"{user}@example.com", timezone=tz)
    cm.set_notification_preference(db, user, "tips_email", enabled=tips, channels=["email"])


# ── Which changes count, and the words ────────────────────────────────────────

def test_only_changes_testers_can_see_count():
    assert ra.is_user_facing(["ui/src/app/features/mobile/today/today.component.ts"])
    assert ra.is_user_facing(["astrospace/agents/compat_insight_agent.py", "docs/x.md"])
    assert ra.is_user_facing(["ui/android/app/src/main/java/app/asksiddha/mobile/widgets/BaseWidget.java"])
    assert not ra.is_user_facing([".github/workflows/ship.yml", "scripts/play_upload.py", "docs/a.md"])
    assert not ra.is_user_facing(["ui/src/app/x.spec.ts", "tests/test_x.py", "firebase-public/index.html"])
    assert not ra.is_user_facing(["astrospace/admin/tester_pulse.py"])


def test_titles_are_tidied():
    assert ra.tidy_title("fix(mobile): logout on cold start (#241)") == "Logout on cold start"
    assert ra.tidy_title("Testers get 10 Ask questions a month (#239)") == "Testers get 10 Ask questions a month"


def test_model_notes_are_used_when_they_keep_the_rules():
    reply = json.dumps({"notes": ["Widgets now add to your home screen.", "Listen works after resizing"]})
    notes, source = ra.write_notes(TITLES, generate=lambda prompt: reply)
    assert source == "model"
    assert notes == ["Widgets now add to your home screen", "Listen works after resizing"]


@pytest.mark.parametrize("bad", [
    "Plus is now ₹300 a month",
    "Buy a plan at asksiddha.app/buy",
    "See https://example.com",
    "Fixed the API timeout",
    "Merged PR #240",
])
def test_a_note_that_breaks_a_rule_falls_back_to_titles(bad):
    reply = json.dumps({"notes": ["Widgets now add properly", bad]})
    notes, source = ra.write_notes(TITLES, generate=lambda prompt: reply)
    assert source == "titles"
    assert notes == [ra.tidy_title(t) for t in TITLES]


def test_a_failed_model_call_still_gives_notes():
    def boom(prompt):
        raise RuntimeError("quota")

    notes, source = ra.write_notes(TITLES, generate=boom)
    assert source == "titles" and len(notes) == 2


def test_no_changes_means_no_model_call():
    assert ra.write_notes([], generate=lambda p: pytest.fail("called")) == ([], "titles")


def test_texts_carry_the_store_link_and_no_test_link():
    ann = ra.announcement(580, ["Widgets now add to your home screen"])
    for key in ("whatsapp_channel", "whatsapp_broadcast", "play_notes"):
        assert "internaltest" not in ann[key] and "/buy" not in ann[key]
    assert ra.STORE_URL in ann["whatsapp_channel"]
    assert ra.REPLY_TO in ann["whatsapp_channel"]
    assert ann["play_notes"] == "• Widgets now add to your home screen."
    assert len(ra.play_notes(["x" * 110] * 5)) <= 500


# ── Queuing and delivery ──────────────────────────────────────────────────────

def test_reader_emails_go_only_to_tips_subscribers_once(db, email_env):
    _reader(db, "asha")
    _reader(db, "ravi", tips=False)
    assert ra.queue_reader_emails(db, 580, ["Widgets now add"], now=NOW) == 1
    assert ra.queue_reader_emails(db, 580, ["Widgets now add"], now=NOW) == 0
    jobs = db.query(NotificationJob).all()
    assert [(j.user_id, j.category) for j in jobs] == [("asha", "tips_email")]

    transport = FakeEmail()
    deliver_due(db, transports={}, email=transport, now=NOW)
    [message] = transport.sent
    assert message.to == "asha@example.com"
    assert message.subject == "New in Siddha: Widgets now add"
    assert "List-Unsubscribe" in message.headers
    assert "Widgets now add." in message.text


def test_the_update_poster_leads_the_email_from_our_own_site(db, email_env):
    _reader(db, "asha")
    ra.queue_reader_emails(db, 588, ["Panchang alarms"], now=NOW,
                           poster="/email/updates/panchang-alarms.jpg")
    transport = FakeEmail()
    deliver_due(db, transports={}, email=transport, now=NOW)
    [message] = transport.sent
    assert '/email/updates/panchang-alarms.jpg" alt="What&#x27;s new in Siddha"' in message.html
    assert message.html.index("panchang-alarms.jpg") < message.html.index("Panchang alarms.")
    assert "[What's new in Siddha]" in message.text


@pytest.mark.parametrize("src", ["https://evil.example/x.png", "/email/../secret", "//evil/x.png", None])
def test_an_image_from_anywhere_else_is_dropped(src):
    from astrospace.notifications.email import _block_html
    assert "<img" not in _block_html({"type": "image", "src": src, "alt": "x"})


def test_a_reader_who_turns_tips_off_before_sending_gets_nothing(db, email_env):
    _reader(db, "asha")
    ra.queue_reader_emails(db, 580, ["Widgets now add"], now=NOW)
    cm.set_notification_preference(db, "asha", "tips_email", enabled=False)
    transport = FakeEmail()
    deliver_due(db, transports={}, email=transport, now=NOW)
    assert transport.sent == []


def test_late_at_night_waits_for_ten_in_the_morning(db, email_env):
    _reader(db, "asha")
    ra.queue_reader_emails(db, 580, ["Widgets now add"], now=datetime(2026, 10, 23, 17, 0))  # 22:30 IST
    job = db.query(NotificationJob).one()
    assert job.scheduled_for == datetime(2026, 10, 24, 4, 30)  # 10:00 IST next day


def test_team_preview_goes_to_owner_addresses_with_whatsapp_texts(db, email_env):
    ann = ra.announcement(580, ["Widgets now add to your home screen"])
    ra.queue_team_email(db, 580, ann, stage="draft", now=NOW)
    ra.queue_team_email(db, 580, ann, stage="draft", now=NOW)  # once per build
    transport = FakeEmail()
    deliver_due(db, transports={}, email=transport, now=NOW)
    [message] = transport.sent
    assert message.to == "team@example.com"
    assert "580" in message.subject
    assert "WHATSAPP CHANNEL POST" in message.text and ra.STORE_URL in message.text
    assert "List-Unsubscribe" not in message.headers


# ── The routes ────────────────────────────────────────────────────────────────

@pytest.fixture
def client(db, monkeypatch):
    from main import app

    claims = {"email": release_routes.DEFAULT_CALLER, "email_verified": True}
    monkeypatch.setattr(release_routes, "_verify_google_id_token", lambda token, aud: dict(claims))
    monkeypatch.setattr(ra, "_gemini", lambda prompt: json.dumps({"notes": ["Widgets now add"]}))
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app), claims
    app.dependency_overrides.pop(get_db, None)


def test_routes_need_the_deployer_token(client, monkeypatch):
    http, claims = client
    assert http.post("/api/v1/releases/announce", json={"version_code": 1, "notes": []}).status_code == 401
    claims["email"] = "someone@example.com"
    r = http.post("/api/v1/releases/announce", json={"version_code": 1, "notes": []},
                  headers={"Authorization": "Bearer t"})
    assert r.status_code == 403

    def bad(token, aud):
        raise ValueError("wrong audience")

    monkeypatch.setattr(release_routes, "_verify_google_id_token", bad)
    r = http.post("/api/v1/releases/announce", json={"version_code": 1, "notes": []},
                  headers={"Authorization": "Bearer t"})
    assert r.status_code == 401


def test_draft_filters_changes_and_queues_only_the_team(client, db):
    http, _ = client
    _reader(db, "asha")
    r = http.post("/api/v1/releases/draft", headers={"Authorization": "Bearer t"}, json={
        "version_code": 580,
        "changes": [
            {"title": TITLES[0], "files": ["ui/src/app/x.ts"]},
            {"title": "Ship from GitHub (#237)", "files": [".github/workflows/ship.yml"]},
        ],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["notes"] == ["Widgets now add"] and body["user_facing"] == 1
    assert ra.STORE_URL in body["whatsapp_channel"]
    assert [j.user_id for j in db.query(NotificationJob).all()] == [ra.TEAM_USER]


def test_announce_queues_readers_and_refuses_a_rule_breaking_note(client, db):
    http, _ = client
    _reader(db, "asha")
    headers = {"Authorization": "Bearer t"}
    r = http.post("/api/v1/releases/announce", headers=headers,
                  json={"version_code": 580, "notes": ["Plans now ₹300"]})
    assert r.status_code == 422
    r = http.post("/api/v1/releases/announce", headers=headers,
                  json={"version_code": 580, "notes": ["Widgets now add"]})
    assert r.status_code == 200 and r.json()["reader_emails_queued"] == 1
    assert sorted(j.user_id for j in db.query(NotificationJob).all()) == ["asha", ra.TEAM_USER]


def test_announce_takes_only_a_poster_under_email_updates(client, db):
    http, _ = client
    headers = {"Authorization": "Bearer t"}
    r = http.post("/api/v1/releases/announce", headers=headers,
                  json={"version_code": 588, "notes": ["Panchang alarms"], "poster": "https://x.example/p.png"})
    assert r.status_code == 422
    _reader(db, "asha")
    r = http.post("/api/v1/releases/announce", headers=headers,
                  json={"version_code": 588, "notes": ["Panchang alarms"],
                        "poster": "/email/updates/panchang-alarms.jpg"})
    assert r.status_code == 200
    job = next(j for j in db.query(NotificationJob).all() if j.user_id == "asha")
    assert job.payload["content"]["blocks"][0] == {
        "type": "image", "src": "/email/updates/panchang-alarms.jpg", "alt": "What's new in Siddha"}


# ── Changes between two builds ────────────────────────────────────────────────

def test_release_changes_finds_the_build_by_commit_count(tmp_path, monkeypatch):
    import subprocess
    import sys

    sys.path.insert(0, "scripts")
    import release_changes

    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q", "-b", "main")
    for n, (title, path) in enumerate([("Start (#1)", "README"), ("Today card (#2)", "ui/src/a.ts"),
                                       ("Ship (#3)", ".github/x.yml"), ("Calendar (#4)", "ui/src/b.ts")]):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(str(n))
        git("add", "-A")
        git("-c", "user.email=a@b.c", "-c", "user.name=t", "commit", "-q", "-m", title)
    monkeypatch.chdir(tmp_path)
    base = release_changes.commit_for_version(2)
    assert base is not None
    found = release_changes.changes(base)
    assert [c["title"] for c in found] == ["Calendar (#4)", "Ship (#3)"]
    assert found[0]["files"] == ["ui/src/b.ts"]
    assert release_changes.commit_for_version(99) is None
