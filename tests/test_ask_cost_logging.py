"""Ask cost logging: tokens per answer, repair pass included (launch plan
gate "cost per verified answer is known")."""
import json
import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.agents.base import BaseAstroAgent, extract_usage
from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import AskMessage
from main import app

ME = "cost-reader"


class _Schema(StructuredReading):
    pass


def test_extract_usage_reads_both_providers_and_tolerates_neither():
    anthropic = SimpleNamespace(usage=SimpleNamespace(input_tokens=1200, output_tokens=340))
    gemini = SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=900, candidates_token_count=210))
    zero_cache = {"cached_tokens": 0}
    assert extract_usage(anthropic) == {"input_tokens": 1200, "output_tokens": 340, **zero_cache}
    assert extract_usage(gemini) == {"input_tokens": 900, "output_tokens": 210, **zero_cache}
    assert extract_usage(object()) == {"input_tokens": 0, "output_tokens": 0, **zero_cache}


def test_extract_usage_reports_the_cached_part_of_the_input():
    gemini = SimpleNamespace(usage_metadata=SimpleNamespace(
        prompt_token_count=40_000, candidates_token_count=900, cached_content_token_count=32_000))
    anthropic = SimpleNamespace(usage=SimpleNamespace(
        input_tokens=500, output_tokens=40, cache_read_input_tokens=12_000))
    assert extract_usage(gemini)["cached_tokens"] == 32_000
    assert extract_usage(anthropic)["cached_tokens"] == 12_000


def test_every_model_call_logs_one_usage_line_naming_its_feature(monkeypatch, caplog):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")

    class BriefAgent(BaseAstroAgent):
        pass

    agent = BriefAgent()
    response = SimpleNamespace(usage=SimpleNamespace(input_tokens=2300, output_tokens=800))
    with caplog.at_level("INFO", logger="astrospace.ai.usage"):
        agent._record_usage(response, "daily_brief")
    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "astrospace.ai.usage"]
    assert lines == [{
        "feature": "BriefAgent", "purpose": "daily_brief", "provider": "anthropic",
        "model": agent.model, "input_tokens": 2300, "output_tokens": 800, "cached_tokens": 0,
    }]


def test_structured_call_records_usage_on_the_agent(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    agent = BaseAstroAgent()
    block = SimpleNamespace(type="tool_use", name="deliver_result", input={
        "acknowledgment": "a", "technical_basis": [{"factor": "f", "reading": "r", "source": "houses"}],
        "interpretation": "i", "summary_and_assurance": "s", "guidance": {"follow_up_questions": []},
        "confidence": "medium",
    })
    response = SimpleNamespace(content=[block], stop_reason="tool_use",
                               usage=SimpleNamespace(input_tokens=1500, output_tokens=400))
    agent.client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: response))
    agent.run_structured([{"role": "user", "content": "q"}], StructuredReading)
    agent.run_structured([{"role": "user", "content": "q"}], StructuredReading)
    totals = agent.usage_totals()
    assert totals["calls"] == 2
    assert totals["input_tokens"] == 3000 and totals["output_tokens"] == 800
    assert totals["breakdown"][0]["purpose"] == "deliver_result"


@pytest.fixture()
def env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
            "user_id": ME, "name": "Reader", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14, "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@example.com", role="dev")
    try:
        yield TestClient(app), factory, kundli
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _reading():
    return StructuredReading(
        acknowledgment="Here's what your chart shows.",
        technical_basis=[TechnicalBasisItem(factor="10th lord", reading="well placed", source="houses")],
        interpretation="Saturn is transiting your 10th house.",
        summary_and_assurance="A tendency worth watching, not a certainty.",
        guidance=Guidance(follow_up_questions=[]),
        confidence="medium",
    )


def _generate(self, messages):
    # Stand in for the model call: the real one appends to usage_log itself.
    self.usage_log.append({"purpose": "deliver_reading", "provider": "anthropic", "model": "test",
                           "input_tokens": 1000, "output_tokens": 250})
    return _reading()


def test_answered_turn_persists_tokens_including_the_repair_pass(env, caplog):
    client, factory, kundli = env
    caplog.set_level(logging.INFO, logger="astrospace.ask.cost")
    with patch.object(DomainReadingAgent, "run_structured_reading", autospec=True, side_effect=_generate):
        body = client.post(f"/api/v1/ask/{kundli}", json={
            "question": "How is my career progressing?", "start_thread": True,
        }).json()
    assert body["thread_id"]
    with factory() as db:
        turns = db.query(AskMessage).filter(AskMessage.thread_id == body["thread_id"]).order_by(AskMessage.created_at).all()
    user_turn, assistant = turns[0], turns[-1]
    assert user_turn.input_tokens is None
    # The minimal reading above trips a coverage check, so the single repair
    # pass runs (conftest routes it back through run_structured_reading):
    # the persisted cost is the sum of both calls, not the last one.
    assert assistant.llm_calls["calls"] >= 1
    assert assistant.input_tokens == 1000 * assistant.llm_calls["calls"]
    assert assistant.output_tokens == 250 * assistant.llm_calls["calls"]
    assert assistant.llm_calls["repaired"] == (assistant.llm_calls["calls"] >= 2)
    assert assistant.model  # the agent's configured model, whatever the provider
    assert assistant.latency_ms is not None

    lines = [json.loads(r.getMessage()) for r in caplog.records if r.name == "astrospace.ask.cost"]
    assert lines and lines[-1]["event"] == "ask.cost"
    assert lines[-1]["status"] == "answered"
    assert lines[-1]["input_tokens"] == assistant.input_tokens


def test_refer_out_turn_carries_no_cost(env):
    client, factory, kundli = env
    with patch.object(DomainReadingAgent, "run_structured_reading") as run:
        body = client.post(f"/api/v1/ask/{kundli}", json={
            "question": "Should I buy crypto?", "start_thread": True,
        }).json()
    run.assert_not_called()
    with factory() as db:
        assistant = db.query(AskMessage).filter(AskMessage.thread_id == body["thread_id"], AskMessage.role == "assistant").one()
    assert assistant.input_tokens is None and assistant.llm_calls is None
