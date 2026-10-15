"""Ask releases its DB connection before the model call (production audit
2026-10-15, P1 "DB"), persists both turns in one transaction, and streams a
heartbeat without leaking token usage to the client.

A transaction held idle through a 10–90 s model call pins a Supabase pooler
connection, so the pool can be exhausted by a handful of readers waiting on
answers. These tests use a file-backed SQLite engine with a real QueuePool so
"how many connections are checked out" is a meaningful question.
"""
import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.api import ask_stream_routes
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base
from astrospace.db.models import AskMessage, AskThread
from main import app

ME = "release-reader"


@pytest.fixture()
def env(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'ask.db'}",
        connect_args={"check_same_thread": False},
        poolclass=QueuePool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        kundli = crud.create_kundli(db, {
            "user_id": ME, "name": "Reader", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@example.com", role="dev")
    try:
        yield TestClient(app), engine, factory, kundli
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)
        engine.dispose()


def _reading():
    return StructuredReading(
        acknowledgment="Here's what your chart shows.",
        technical_basis=[TechnicalBasisItem(factor="10th lord", reading="well placed", source="houses")],
        interpretation="Saturn is transiting your 10th house.",
        summary_and_assurance="A tendency worth watching, not a certainty.",
        guidance=Guidance(follow_up_questions=[]),
        confidence="medium",
    )


def _frames(response) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in response.text.splitlines()
            if line.startswith("data: ")]


@pytest.mark.parametrize("path", ["/api/v1/ask/{k}", "/api/v1/ask/{k}/stream"])
def test_no_connection_is_held_during_generation(env, path):
    client, engine, factory, kundli = env
    checked_out = []

    def generate(self, messages):
        checked_out.append(engine.pool.checkedout())
        return _reading()

    with patch.object(DomainReadingAgent, "run_structured_reading", autospec=True, side_effect=generate):
        response = client.post(path.format(k=kundli), json={
            "question": "How is my career progressing?", "start_thread": True,
        })
    assert response.status_code == 200
    assert checked_out and all(count == 0 for count in checked_out)
    with factory() as db:
        roles = [m.role for m in db.query(AskMessage).order_by(AskMessage.created_at)]
    assert roles == ["user", "assistant"]


def test_continuing_a_thread_after_release_appends_both_turns(env):
    client, engine, factory, kundli = env
    with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_reading()):
        first = client.post(f"/api/v1/ask/{kundli}", json={
            "question": "How is my career progressing?", "start_thread": True,
        }).json()
        second = client.post(f"/api/v1/ask/{kundli}", json={
            "question": "And what about promotion at work?", "thread_id": first["thread_id"],
        }).json()
    assert second["thread_id"] == first["thread_id"]
    assert second["thread"]["message_count"] == 4
    with factory() as db:
        roles = [m.role for m in db.query(AskMessage).order_by(AskMessage.created_at)]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_a_failed_turn_write_leaves_no_half_turn_and_no_empty_thread(env):
    _client, _engine, factory, kundli = env
    real = cm.add_ask_message
    calls = []

    def fail_on_answer(db, thread_id, role, content, **fields):
        calls.append(role)
        if role == "assistant":
            raise RuntimeError("db is down")
        return real(db, thread_id, role, content, **fields)

    with factory() as db, patch.object(cm, "add_ask_message", side_effect=fail_on_answer):
        with pytest.raises(RuntimeError):
            cm.add_ask_turn(db, thread_id=None, user_id=ME, kundli_id=kundli,
                            question="q", answer="a")
    assert calls == ["user", "assistant"]
    with factory() as db:
        assert db.query(AskMessage).count() == 0
        assert db.query(AskThread).count() == 0


def test_stream_sends_heartbeats_and_no_usage(env, monkeypatch):
    client, _engine, _factory, kundli = env
    monkeypatch.setattr(ask_stream_routes, "HEARTBEAT_SECONDS", 0.05)

    def slow(self, messages):
        time.sleep(0.4)
        return _reading()

    with patch.object(DomainReadingAgent, "run_structured_reading", autospec=True, side_effect=slow):
        response = client.post(f"/api/v1/ask/{kundli}/stream", json={
            "question": "How is my career progressing?", "start_thread": True,
        })
    assert ": ping" in response.text.splitlines()
    done = _frames(response)[-1]
    assert done["type"] == "done" and done["status"] == "answered"
    assert "usage" not in done
    assert done["thread_id"]
