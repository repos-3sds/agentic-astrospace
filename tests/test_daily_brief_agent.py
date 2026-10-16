"""Agent-written daily brief: spoken length, boundaries, fallback and cache.

The model is stubbed: these tests pin what the app is promised (a script that
plays in under 90 s at 0.9x, nothing that crosses a boundary, the templated
brief kept on any failure), not what a model happens to write.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.agents import daily_brief_agent as dba
from astrospace.api import context_routes
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from main import app

ME = "brief-reader"
AS_OF = "2026-10-16T08:00:00+05:30"


def _brief(spoken_words_each: int = 30, avoid_detail: str = "Ketu from the Moon asks for rest.") -> dba.DailyBrief:
    words = " ".join(["word"] * (spoken_words_each - 1)) + "."
    return dba.DailyBrief(
        headline="A day for finishing things",
        summary="Steady ground for closing open loops.",
        focus="Finish the task you have been circling.",
        do=[dba.BriefItem(headline="Close an open task", detail="Sadhaka tara favours completion.")],
        avoid=[dba.BriefItem(headline="Overextending yourself", detail=avoid_detail)],
        timing_note="Keep 10:24 to 11:52 for routine work.",
        why=["Your tara today is an accomplishment star."],
        spoken=[dba.SpokenSection(label=label, text=f"{label}: {words}")
                for label in ("Opening", "Overview", "Today", "Why", "Close")],
    )


def _payload() -> dict:
    from astrospace.context import daily_guidance
    from astrospace.core.vedic import VedicChart

    chart = VedicChart("Reader", 1991, 8, 14, 6, 12, "Vijayawada", "IN")
    return daily_guidance(chart, relation="self",
                          as_of=datetime(2026, 10, 16, 8, 0, tzinfo=ZoneInfo("Asia/Kolkata")))


class _Scripted(dba.DailyBriefAgent):
    """Returns the queued briefs in order and records the prompts."""

    def __init__(self, briefs):
        self.provider, self.model, self.usage_log = "gemini", "stub", []
        self.queue, self.prompts = list(briefs), []

    def run_structured(self, messages, schema, tool_name="deliver_result", input_schema=None):
        self.prompts.append(messages[0]["content"])
        self.usage_log.append({"purpose": tool_name, "input_tokens": 3000, "output_tokens": 600})
        return self.queue.pop(0)


def test_word_limit_plays_under_ninety_seconds_at_the_sheets_default_speed():
    assert dba.listen_seconds(dba.SPOKEN_WORD_LIMIT) < 90
    assert dba.listen_seconds(dba.SPOKEN_WORD_TARGET[1]) < 90


def test_a_brief_within_the_limit_is_returned_first_time():
    agent = _Scripted([_brief(30)])
    brief = agent.write(_payload(), first_name="Reader", date_label="Friday, 16 October")
    assert brief is not None and dba.spoken_words(brief) == 150
    assert len(agent.prompts) == 1


def test_a_long_script_is_rewritten_with_its_word_count():
    agent = _Scripted([_brief(50), _brief(30)])
    brief = agent.write(_payload(), first_name="Reader", date_label="Friday, 16 October")
    assert dba.spoken_words(brief) == 150
    assert "was 250 words" in agent.prompts[1]


def test_a_script_still_long_after_the_rewrite_is_trimmed_not_shipped_long():
    agent = _Scripted([_brief(50), _brief(48)])
    brief = agent.write(_payload(), first_name="Reader", date_label="Friday, 16 October")
    assert brief is not None
    assert dba.spoken_words(brief) <= dba.SPOKEN_WORD_LIMIT
    labels = [section.label for section in brief.spoken]
    assert labels[0] == "Opening" and labels[-1] == "Close"


def test_a_boundary_crossing_brief_is_retried_then_dropped():
    bad = "This dosha will destroy your marriage."
    agent = _Scripted([_brief(30, avoid_detail=bad), _brief(30, avoid_detail=bad)])
    assert agent.write(_payload(), first_name="Reader", date_label="Friday, 16 October") is None
    assert "crossed a boundary" in agent.prompts[1]


def test_the_model_sees_signals_not_kb_references_or_colours():
    agent = _Scripted([_brief(30)])
    agent.write(_payload(), first_name="Reader", date_label="Friday, 16 October", mode="guided", tone="gentle")
    prompt = agent.prompts[0]
    assert "Sadhaka" in prompt or "tarabala" in prompt
    assert "references" not in prompt and "lucky" not in prompt
    assert "new to astrology" in prompt and "gentle" in prompt


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        kundli = crud.create_kundli(db, {
            "user_id": ME, "name": "Reader Name", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14,
            "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    context_routes._brief_cache.clear()
    try:
        yield TestClient(app), kundli
    finally:
        app.dependency_overrides.clear()
        context_routes._brief_cache.clear()


def test_endpoint_returns_the_agent_brief_and_caches_it(client, monkeypatch):
    http, kundli = client
    calls = []

    def fake_write(kundli_row, payload, tone, mode):
        calls.append((tone, mode))
        return _brief(30), {"provider": "gemini", "model": "stub", "calls": 1,
                            "input_tokens": 3000, "output_tokens": 600}

    monkeypatch.setattr(context_routes, "_write_brief", fake_write)
    first = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF, "tone": "gentle"}).json()
    again = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF, "tone": "gentle"}).json()
    assert first["source"] == "agent" and first["cached"] is False
    assert first["spoken_words"] == 150 and first["listen_seconds"] < 90
    assert first["brief"]["spoken"][0]["label"] == "Opening"
    assert again["cached"] is True and calls == [("gentle", "balanced")]
    # A different reading style is a different brief.
    http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF, "tone": "direct"})
    assert len(calls) == 2


def test_endpoint_falls_back_to_the_template_and_does_not_cache_failures(client, monkeypatch):
    http, kundli = client
    outcomes = iter([RuntimeError("API key not valid"), (None, None)])

    def failing_write(*_args):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(context_routes, "_write_brief", failing_write)
    for _ in range(2):
        body = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF}).json()
        assert body == {"date": "2026-10-16", "valid_until": body["valid_until"],
                        "source": "template", "brief": None}
    assert not context_routes._brief_cache


def test_endpoint_can_be_switched_off(client, monkeypatch):
    http, kundli = client
    monkeypatch.setenv("DAILY_BRIEF_AGENT", "off")
    monkeypatch.setattr(context_routes, "_write_brief", lambda *a: pytest.fail("agent called while off"))
    body = http.get(f"/api/v1/context/{kundli}/daily/brief", params={"as_of": AS_OF}).json()
    assert body["source"] == "template" and body["brief"] is None


def test_other_users_profiles_are_not_found(client):
    http, _kundli = client
    assert http.get("/api/v1/context/someone-else/daily/brief").status_code == 404
