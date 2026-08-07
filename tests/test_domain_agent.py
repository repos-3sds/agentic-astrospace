"""Career domain agent, end to end: assemble_domain() shape, the agent's
system prompt, and the streamed /ask/{kundli_id}/stream orchestrator.

The Anthropic call is always stubbed (patching `run_messages_stream` /
`run_messages` on `BaseAstroAgent`, same pattern as test_ask_threads.py) —
these cover assembly, routing, SSE framing and persistence, not the model.
"""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.domain_agent import DOMAIN_AGENTS, CareerReadingAgent
from astrospace.api.auth import AuthUser, current_user
from astrospace.context import assemble_domain
from astrospace.core.vedic.chart import VedicChart
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "test-user-domain-agent"


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1993, 7, 20, 11, 28, "Rajahmundry", "IN")


class TestAssembleDomainForCareer:
    """The bundle a CareerReadingAgent's prompt is built from — if this
    shape ever drifts, the agent's grounding rules (which reference these
    exact field names) silently stop matching reality."""

    def test_career_bundle_has_the_fields_the_agent_prompt_depends_on(self, chart):
        bundle = assemble_domain(chart, "career")
        assert bundle["domain"] == "career"
        assert bundle["domain_name"]
        assert "D10" in bundle["vargas"]
        assert bundle["vargas"]["D10"]["tier"] == "primary"
        assert any(h["house"] == 10 and h["tier"] == "primary" for h in bundle["houses"])
        assert isinstance(bundle["references"], list)
        assert isinstance(bundle["source_passages"], list)
        assert isinstance(bundle["dasha_relevance"]["chain"], list)
        assert bundle["gochara"] is not None

    def test_career_bundle_only_surfaces_career_relevant_yogas(self, chart):
        """_filter_rules keeps a yoga if its rule_id OR its category matches
        the domain — career's `yoga_categories` includes "Pancha Mahapurusha",
        so e.g. bhadra_yoga shows up by category even though it isn't in
        career's explicit `rule_ids` list. Both routes count as relevant."""
        bundle = assemble_domain(chart, "career")
        from astrospace.context.taxonomy import get_domain
        spec = get_domain("career")
        allowed_ids = set(spec.rule_ids)
        allowed_categories = set(spec.yoga_categories)
        for yoga in bundle["yogas"]:
            assert yoga["rule_id"] in allowed_ids or yoga["category"] in allowed_categories


class TestCareerReadingAgentPrompt:
    def test_system_prompt_embeds_the_bundle_and_career_framing(self, chart):
        bundle = assemble_domain(chart, "career")
        agent = CareerReadingAgent(bundle, api_key="test-key-not-called")
        assert "Career & Profession" in agent.system_prompt
        assert '"D10"' in agent.system_prompt
        assert "dashamsa" in agent.system_prompt
        assert "never predict death" in agent.system_prompt.lower()
        assert agent.tools == []

    def test_registry_only_has_career_for_now(self):
        assert set(DOMAIN_AGENTS) == {"career"}


class TestAskStreamRoute:
    @pytest.fixture(scope="class")
    def env(self):
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

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_user] = lambda: AuthUser(
            id=ME, email="me@astrospace.dev", role="dev",
        )

        db = Session()
        kundli_id = crud.create_kundli(db, {
            "user_id": ME, "name": "Streamed", "relation": "self",
            "birth_year": 1993, "birth_month": 7, "birth_day": 20,
            "birth_hour": 11, "birth_minute": 28,
            "birth_city": "Rajahmundry", "birth_nation": "IN",
        }).id
        db.close()

        try:
            yield {"client": TestClient(app), "kundli": kundli_id}
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(current_user, None)

    @pytest.fixture(scope="class")
    def client(self, env):
        return env["client"]

    @staticmethod
    def _frames(response) -> list[dict]:
        out = []
        for line in response.text.splitlines():
            if line.startswith("data: "):
                out.append(json.loads(line[len("data: "):]))
        return out

    def test_career_question_streams_through_the_domain_agent(self, client, env):
        chunks = ["Your 10th ", "lord is well placed."]
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages_stream",
                   return_value=iter(chunks)) as run:
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
            })
        assert r.status_code == 200
        run.assert_called_once()
        frames = self._frames(r)
        deltas = [f["delta"] for f in frames if "delta" in f and not f.get("reset")]
        assert "".join(deltas) == "".join(chunks)
        done = frames[-1]
        assert done["done"] is True
        assert done["domain"] == "career"
        assert done["refer_out_kind"] is None

    def test_non_career_question_falls_back_to_vedic_qa_agent(self, client, env):
        # "health" has no registered agent yet (DOMAIN_AGENTS only has
        # "career") — routes cleanly away from career by keyword match, not
        # the router's own career-shaped default-domain fallback.
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages",
                   return_value=("The Moon supports steady routines this week.", [])) as run:
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time for my health and energy levels?",
            })
        assert r.status_code == 200
        run.assert_called_once()
        frames = self._frames(r)
        assert frames[0]["delta"] == "The Moon supports steady routines this week."
        assert frames[-1]["done"] is True
        assert frames[-1]["domain"] == "health"
        assert frames[-1]["refer_out_kind"] is None

    def test_refer_out_gates_before_any_model_call(self, client, env):
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages_stream") as stream, \
             patch("astrospace.agents.base.BaseAstroAgent.run_messages") as run:
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "When will I die?",
            })
        assert r.status_code == 200
        stream.assert_not_called()
        run.assert_not_called()
        frames = self._frames(r)
        assert frames[0]["delta"] == "AstroSpace does not predict death or lifespan, for anyone."
        assert frames[-1]["domain"] is None
        assert frames[-1]["refer_out_kind"] == "death"

    def test_prohibited_verdict_mid_stream_resets_the_client(self, client, env):
        chunks = ["You will ", "win your case for sure."]
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages_stream",
                   return_value=iter(chunks)):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "How does my chart look for career authority?",
            })
        assert r.status_code == 200
        frames = self._frames(r)
        reset_frames = [f for f in frames if f.get("reset")]
        assert reset_frames, "expected a reset frame once the output-side gate tripped"
        assert "cannot predict legal outcomes" in reset_frames[0]["delta"]
        # The question was genuinely routed to career before the output-side
        # gate tripped mid-stream — domain records where it was routed,
        # refer_out_kind records why the answer was replaced.
        assert frames[-1]["domain"] == "career"
        assert frames[-1]["refer_out_kind"] == "legal"

    def test_stream_generation_failure_returns_visible_fallback(self, client, env):
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages_stream",
                   side_effect=TypeError("missing model auth")):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
                "start_thread": True,
            })
        assert r.status_code == 200
        frames = self._frames(r)
        assert frames[0]["delta"].startswith("Siddha's Ask agents")
        assert frames[-1]["done"] is True
        assert frames[-1]["domain"] == "career"
        assert frames[-1]["refer_out_kind"] is None
        assert frames[-1]["thread_id"]

    def test_unknown_kundli_404_before_streaming(self, client):
        r = client.post("/api/v1/ask/nonexistent-id/stream", json={"question": "hi"})
        assert r.status_code == 404

    def test_thread_persists_career_domain_and_evidence(self, client, env):
        with patch("astrospace.agents.base.BaseAstroAgent.run_messages_stream",
                   return_value=iter(["A grounded career answer."])):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time to change jobs?",
                "start_thread": True,
            })
        thread_id = self._frames(r)[-1]["thread_id"]
        assert thread_id
        thread = client.get(f"/api/v1/ask/threads/{thread_id}").json()
        assistant_msg = next(m for m in thread["messages"] if m["role"] == "assistant")
        assert assistant_msg["domain"] == "career"
        assert assistant_msg["content"] == "A grounded career answer."
