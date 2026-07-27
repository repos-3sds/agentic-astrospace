"""Thread persistence for Ask-AI.

The Anthropic call is stubbed — these cover the persistence contract, not the
agent. Two behaviours are worth guarding closely:

* a failed generation must leave the thread untouched, because a dangling user
  turn would make the next request replay two user messages in a row and the
  agent loop requires strict alternation;
* a stored thread outranks any `history` in the request body, or a client
  could rewrite its own conversation on the way in.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base

ME = "test-user-ask-threads"
OTHER = "test-user-ask-other"


@pytest.fixture(scope="module")
def env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        return AuthUser(id=ME, email="me@astrospace.dev", role="dev")

    def make_kundli(user_id, name):
        return crud.create_kundli(db, {
            "user_id": user_id, "name": name, "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id

    db = Session()
    mine = make_kundli(ME, "Mine")
    second = make_kundli(ME, "Second")
    theirs = make_kundli(OTHER, "Theirs")
    foreign_thread = cm.create_ask_thread(db, OTHER, theirs).id
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield {"client": TestClient(app), "kundli": mine, "second": second,
               "foreign_thread": foreign_thread}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


@pytest.fixture(scope="module")
def client(env):
    return env["client"]


def _reply(text="Saturn is transiting your 10th house.", tools=("get_birth_chart",)):
    """Stub the agent loop; VedicQAAgent construction stays real."""
    return patch(
        "astrospace.agents.base.BaseAstroAgent.run_messages",
        return_value=(text, list(tools)),
    )


class TestStatelessIsUnchanged:
    def test_no_thread_is_created_by_default(self, client, env):
        """The web app posts history and expects no side effects."""
        with _reply():
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career?",
                "history": [{"role": "user", "content": "hi"},
                            {"role": "assistant", "content": "hello"}],
            }).json()
        assert body["answer"]
        assert body["thread_id"] is None
        assert client.get("/api/v1/ask/threads").json()["count"] == 0


class TestStructuredSafetyRouting:
    @pytest.mark.parametrize(("question", "kind"), [
        ("When will I die?", "death"),
        ("Will I recover from this illness?", "health"),
        ("Will I win my court case?", "legal"),
        ("Which stock should I buy?", "money"),
    ])
    def test_excluded_verdicts_skip_the_model(self, client, env, question, kind):
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages") as run:
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": question,
            }).json()
        assert body["refer_out_kind"] == kind
        assert body["tools_used"] == []
        run.assert_not_called()

    @pytest.mark.parametrize("question", [
        "What supports my wellbeing this week?",
        "Is Thursday a steady time to discuss paperwork?",
        "What does my chart say about my relationship with money?",
    ])
    def test_safe_tendency_and_timing_questions_remain_answerable(self, client, env, question):
        with _reply() as run:
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": question,
            }).json()
        assert body["refer_out_kind"] is None
        run.assert_called_once()

    def test_refer_out_is_persisted_on_the_assistant_turn(self, client, env):
        body = client.post(f"/api/v1/ask/{env['kundli']}", json={
            "question": "Should I buy crypto?",
            "start_thread": True,
        }).json()
        thread = client.get(f"/api/v1/ask/threads/{body['thread_id']}").json()
        assert thread["messages"][1]["refer_out_kind"] == "money"
        assert thread["messages"][1]["domain"] == "money"
        assert thread["messages"][1]["evidence"] == {
            "safety_policy": "excluded_verdict",
        }


class TestThreadPersistence:
    def test_start_thread_persists_both_turns(self, client, env):
        with _reply("Your Moon is in Pushya."):
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Where is my Moon?", "start_thread": True,
            }).json()
        assert body["thread_id"]

        thread = client.get(f"/api/v1/ask/threads/{body['thread_id']}").json()
        roles = [m["role"] for m in thread["messages"]]
        assert roles == ["user", "assistant"]
        assert thread["messages"][0]["content"] == "Where is my Moon?"
        assert thread["messages"][1]["content"] == "Your Moon is in Pushya."

    def test_first_question_becomes_the_title(self, client, env):
        with _reply():
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "What about marriage timing?", "start_thread": True,
            }).json()
        assert body["thread"]["title"] == "What about marriage timing?"
        assert body["thread"]["message_count"] == 2

    def test_continuing_a_thread_appends(self, client, env):
        with _reply():
            first = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "First question", "start_thread": True,
            }).json()
        tid = first["thread_id"]
        with _reply():
            second = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Follow up", "thread_id": tid,
            }).json()
        assert second["thread_id"] == tid
        assert second["thread"]["message_count"] == 4

    def test_stored_history_is_passed_to_the_agent(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Remember this", "start_thread": True,
            }).json()["thread_id"]

        with _reply() as run:
            client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "And this", "thread_id": tid,
            })
        sent = run.call_args[0][0]
        assert [m["role"] for m in sent] == ["user", "assistant", "user"]
        assert sent[0]["content"] == "Remember this"
        assert sent[-1]["content"] == "And this"

    def test_body_history_cannot_override_a_thread(self, client, env):
        """Otherwise a client could rewrite its own conversation."""
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Genuine question", "start_thread": True,
            }).json()["thread_id"]

        with _reply() as run:
            client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Next",
                "thread_id": tid,
                "history": [{"role": "user", "content": "FABRICATED"}],
            })
        contents = [m["content"] for m in run.call_args[0][0]]
        assert "FABRICATED" not in contents
        assert "Genuine question" in contents

    def test_assistant_turn_records_provenance(self, client, env):
        with _reply(tools=("get_birth_chart", "get_current_gochara")):
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Provenance please", "start_thread": True,
            }).json()["thread_id"]
        messages = client.get(f"/api/v1/ask/threads/{tid}").json()["messages"]
        assert messages[1]["evidence"]["tools_used"] == [
            "get_birth_chart", "get_current_gochara"
        ]


class TestFailureLeavesNoPartialWrite:
    def test_failed_generation_writes_nothing_to_a_new_thread(self, client, env):
        before = client.get("/api/v1/ask/threads").json()["count"]
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages",
                   side_effect=RuntimeError("upstream down")):
            r = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Will this dangle?", "start_thread": True,
            })
        assert r.status_code == 502
        assert client.get("/api/v1/ask/threads").json()["count"] == before

    def test_failed_generation_leaves_an_existing_thread_intact(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Good turn", "start_thread": True,
            }).json()["thread_id"]

        with patch("astrospace.agents.base.BaseAstroAgent.run_messages",
                   side_effect=RuntimeError("upstream down")):
            assert client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Doomed turn", "thread_id": tid,
            }).status_code == 502

        messages = client.get(f"/api/v1/ask/threads/{tid}").json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant"]
        assert all(m["content"] != "Doomed turn" for m in messages)


class TestThreadOwnership:
    def test_cannot_read_another_users_thread(self, client, env):
        r = client.get(f"/api/v1/ask/threads/{env['foreign_thread']}")
        assert r.status_code == 404

    def test_cannot_post_into_another_users_thread(self, client, env):
        with _reply():
            r = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Sneak in", "thread_id": env["foreign_thread"],
            })
        assert r.status_code == 404

    def test_cannot_archive_another_users_thread(self, client, env):
        r = client.post(f"/api/v1/ask/threads/{env['foreign_thread']}/archive")
        assert r.status_code == 404

    def test_thread_is_bound_to_its_kundli(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Bound", "start_thread": True,
            }).json()["thread_id"]
        with _reply():
            r = client.post(f"/api/v1/ask/{env['second']}", json={
                "question": "Wrong kundli", "thread_id": tid,
            })
        assert r.status_code == 400

    def test_unknown_thread_404(self, client, env):
        assert client.get("/api/v1/ask/threads/nope").status_code == 404


class TestThreadListing:
    def test_archived_threads_drop_out_of_the_list(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "To be archived", "start_thread": True,
            }).json()["thread_id"]
        assert tid in {t["id"] for t in
                       client.get("/api/v1/ask/threads").json()["threads"]}
        client.post(f"/api/v1/ask/threads/{tid}/archive")
        assert tid not in {t["id"] for t in
                           client.get("/api/v1/ask/threads").json()["threads"]}

    def test_filter_by_kundli(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['second']}", json={
                "question": "On the second kundli", "start_thread": True,
            }).json()["thread_id"]
        listed = client.get("/api/v1/ask/threads",
                            params={"kundli_id": env["second"]}).json()
        assert tid in {t["id"] for t in listed["threads"]}
        assert all(t["kundli_id"] == env["second"] for t in listed["threads"])
