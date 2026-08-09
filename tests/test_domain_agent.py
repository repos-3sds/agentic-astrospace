"""Domain agent, orchestrator, and the streamed /ask/{kundli_id}/stream
route — career and marriage, end to end.

The Anthropic call is always stubbed. Most tests mock at
`DomainReadingAgent.run_structured_reading` (matching the established
pattern in test_ask_threads.py's `BaseAstroAgent.run_messages` mocks); one
test — `TestRunStructuredMockRealism` — mocks one level deeper, at
`client.messages.create`, using the real `anthropic.types.Message`/
`ToolUseBlock` classes rather than a bare dict or loose MagicMock. Tool-call
response parsing is where these plans quietly break; that test exists to
prove `response.content[0].input` access actually works against the SDK's
real object shape, not a stand-in that happens to have the right attributes.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.orchestrator import AskOrchestrator
from astrospace.agents.registry import AGENT_REGISTRY
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.api.auth import AuthUser, current_user
from astrospace.context import assemble_domain
from astrospace.core.vedic.chart import VedicChart
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "test-user-domain-agent"


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1993, 7, 20, 11, 28, "Rajahmundry", "IN")


def _good_reading(source: str = "houses", **overrides) -> StructuredReading:
    base = dict(
        acknowledgment="You're asking about timing.",
        technical_basis=[TechnicalBasisItem(factor="10th lord", reading="well placed", source=source)],
        interpretation="A supportive stretch, grounded in your chart.",
        summary_and_assurance="A good window, not a fixed outcome.",
        guidance=Guidance(follow_up_questions=["Which month is strongest?"]),
        confidence="medium",
    )
    base.update(overrides)
    return StructuredReading(**base)


class TestAssembleDomainShapes:
    """The bundles the agent prompts and the verifier depend on — if these
    drift, both silently stop matching reality."""

    def test_career_bundle_has_d10_and_primary_house(self, chart):
        bundle = assemble_domain(chart, "career")
        assert bundle["domain"] == "career"
        assert "D10" in bundle["vargas"]
        assert any(h["house"] == 10 and h["tier"] == "primary" for h in bundle["houses"])

    def test_marriage_bundle_has_d9_and_primary_house(self, chart):
        bundle = assemble_domain(chart, "marriage")
        assert bundle["domain"] == "marriage"
        assert "D9" in bundle["vargas"]
        assert any(h["house"] == 7 and h["tier"] == "primary" for h in bundle["houses"])

    def test_wealth_bundle_has_d2_and_primary_house(self, chart):
        bundle = assemble_domain(chart, "wealth")
        assert bundle["domain"] == "wealth"
        assert "D2" in bundle["vargas"]
        assert any(h["house"] in (2, 11) and h["tier"] == "primary" for h in bundle["houses"])

    def test_children_bundle_has_d7_and_primary_house(self, chart):
        bundle = assemble_domain(chart, "children")
        assert bundle["domain"] == "children"
        assert "D7" in bundle["vargas"]
        assert any(h["house"] == 5 and h["tier"] == "primary" for h in bundle["houses"])

    def test_health_bundle_has_d6_and_primary_house(self, chart):
        bundle = assemble_domain(chart, "health")
        assert bundle["domain"] == "health"
        assert "D6" in bundle["vargas"]
        assert any(h["house"] in (1, 6) and h["tier"] == "primary" for h in bundle["houses"])

    def test_foreign_bundle_has_d9_and_primary_house(self, chart):
        # No unique domain-specific varga here (taxonomy's primary vargas
        # for foreign are D1/D9, shared with marriage's D9) — the real
        # domain-scoping signal is the primary house tier (12th/9th).
        bundle = assemble_domain(chart, "foreign")
        assert bundle["domain"] == "foreign"
        assert "D9" in bundle["vargas"]
        assert any(h["house"] in (9, 12) and h["tier"] == "primary" for h in bundle["houses"])

    def test_personality_bundle_has_d1_and_primary_house(self, chart):
        bundle = assemble_domain(chart, "personality")
        assert bundle["domain"] == "personality"
        assert "D1" in bundle["vargas"]
        assert any(h["house"] == 1 and h["tier"] == "primary" for h in bundle["houses"])
        assert "Sun" in bundle["karakas"]
        assert "Moon" in bundle["karakas"]
        assert "Mercury" in bundle["karakas"]

    def test_personality_bundle_surfaces_lagna_lord_via_house_one(self, chart):
        """The domain's central evidence — the Ascendant lord — is not a
        fixed karaka (it varies by chart), so it cannot live in the static
        taxonomy karaka list the way Sun/Moon/Mercury do. It is already
        surfaced generically via house 1's own `lord`/`lord_placement`
        fields (the same mechanism every domain uses for its primary
        houses) — this pins that it actually resolves to a real planet
        brief, not a scoping gap the addendum has to work around."""
        bundle = assemble_domain(chart, "personality")
        house_one = next(h for h in bundle["houses"] if h["house"] == 1)
        assert house_one["tier"] == "primary"
        assert house_one["lord"]
        assert house_one["lord_placement"]["planet"] == house_one["lord"]
        assert house_one["lord_placement"]["dignity"]


class TestRunStructuredMockRealism:
    """Mocks the SDK boundary itself, not our own wrapper — proves
    `run_structured_reading` actually survives contact with the real
    `Message`/`ToolUseBlock` shape."""

    def test_parses_a_real_shaped_tool_use_response(self, chart):
        from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

        bundle = assemble_domain(chart, "career")
        agent = DomainReadingAgent(bundle, AGENT_REGISTRY["career"].domain_addendum)

        reading_dict = _good_reading().model_dump()
        fake_response = Message(
            id="msg_test", type="message", role="assistant", model=agent.model,
            content=[ToolUseBlock(type="tool_use", id="toolu_1", name="deliver_reading", input=reading_dict)],
            stop_reason="tool_use", stop_sequence=None,
            usage=Usage(input_tokens=10, output_tokens=5),
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_response
        agent.client = mock_client
        agent.provider = "anthropic"

        result = agent.run_structured_reading([{"role": "user", "content": "hi"}])
        assert isinstance(result, StructuredReading)
        assert result.interpretation == reading_dict["interpretation"]
        # Confirms tool_choice was actually forced, not left to the model's discretion.
        _, kwargs = mock_client.messages.create.call_args
        assert kwargs["tool_choice"] == {"type": "tool", "name": "deliver_reading"}

    def test_missing_tool_call_raises_rather_than_silently_returning_garbage(self, chart):
        from anthropic.types import Message, TextBlock, Usage

        bundle = assemble_domain(chart, "career")
        agent = DomainReadingAgent(bundle, AGENT_REGISTRY["career"].domain_addendum)
        fake_response = Message(
            id="msg_test", type="message", role="assistant", model=agent.model,
            content=[TextBlock(type="text", text="I refuse to use the tool.")],
            stop_reason="end_turn", stop_sequence=None,
            usage=Usage(input_tokens=10, output_tokens=5),
        )
        mock_client = MagicMock()
        mock_client.messages.create.return_value = fake_response
        agent.client = mock_client
        agent.provider = "anthropic"

        with pytest.raises(ValueError):
            agent.run_structured_reading([{"role": "user", "content": "hi"}])


class TestAskOrchestratorPrepare:
    @pytest.fixture
    def orchestrator(self, chart):
        return AskOrchestrator(chart_loader=lambda: chart)

    def test_refer_out_gates_before_routing(self, orchestrator):
        outcome = orchestrator.prepare("When will I die?")
        assert outcome.terminal_envelope["type"] == "refer_out"
        assert outcome.terminal_envelope["kind"] == "death"
        assert outcome.prepared is None

    def test_ambiguous_tie_needs_clarification(self, orchestrator):
        outcome = orchestrator.prepare("Is this a good time for my career and my marriage?")
        assert outcome.terminal_envelope["type"] == "clarification_needed"
        assert set(outcome.terminal_envelope["options"]) == {"career", "marriage", "wealth", "children", "health", "foreign", "personality"}

    def test_high_confidence_tie_also_needs_clarification(self, orchestrator):
        """Independent-review finding (personality-domain build, round 1,
        confirmed by two reviewers): `_needs_clarification` used to skip
        its tie check entirely whenever the primary domain scored 2+
        keyword hits ("high" confidence) — even when a real secondary
        domain scored only one hit fewer. A question naming two genuinely
        distinct personality keywords ("temperament" + "character") for
        what is actually a spirituality question used to be answered as
        personality with zero clarification signal, purely because 2 hits
        crossed the high-confidence threshold. The tie check now runs at
        any confidence level whenever a real secondary domain exists."""
        outcome = orchestrator.prepare(
            "Do I have the temperament of a devoted, spiritual character?"
        )
        assert outcome.terminal_envelope["type"] == "clarification_needed"
        # "options" is the static configured-domain list (routing.available_
        # domains), not the two domains that actually tied — spirituality
        # itself isn't even configured in AGENT_REGISTRY. The behavior this
        # test pins is that clarification fires at all despite personality
        # scoring "high" confidence (2 hits), which the pre-fix code never
        # did once any domain crossed that threshold.
        assert "personality" in outcome.terminal_envelope["options"]

    def test_high_confidence_with_no_real_competitor_still_answers_directly(self, orchestrator):
        """The fix above must not turn every high-confidence match into a
        clarification prompt — only a genuine close tie. A clean multi-
        keyword hit for one domain with nothing else in contention (no
        second entry in `ranked_domains`) must still answer immediately,
        the same as before this fix."""
        outcome = orchestrator.prepare("Is this a good year for a promotion at work?")
        assert outcome.prepared is not None
        assert outcome.prepared.domain == "career"

    def test_daily_guidance_only_needs_clarification_not_a_wrong_domain_answer(self, orchestrator):
        outcome = orchestrator.prepare("What should I focus on today?")
        assert outcome.terminal_envelope["type"] == "clarification_needed"
        assert orchestrator.route("What should I focus on today?").intent == "daily_guidance"

    def test_mixed_daily_and_career_question_still_answers_career(self, orchestrator):
        """intent tags the response; it never gates routing by itself."""
        outcome = orchestrator.prepare("Should I have a hard conversation at work today?")
        assert outcome.prepared is not None
        assert outcome.prepared.domain == "career"

    def test_unsupported_domain_is_not_ready(self, orchestrator):
        outcome = orchestrator.prepare("What does my chart show about property disputes with my siblings?")
        assert outcome.terminal_envelope["type"] == "domain_not_ready"
        assert outcome.terminal_envelope["domain"] == "family_property"
        assert outcome.terminal_envelope["domain_label"]
        assert outcome.terminal_envelope["available"] == ["career", "children", "foreign", "health", "marriage", "personality", "wealth"]

    def test_career_question_prepares_a_real_bundle(self, orchestrator):
        outcome = orchestrator.prepare("Is this a good year for a promotion at work?")
        assert outcome.prepared.domain == "career"
        assert outcome.prepared.bundle["domain"] == "career"
        assert "houses" in outcome.prepared.context_used

    def test_wealth_question_prepares_a_real_bundle(self, orchestrator):
        outcome = orchestrator.prepare("When will my financial situation improve?")
        assert outcome.prepared.domain == "wealth"
        assert outcome.prepared.bundle["domain"] == "wealth"
        assert "houses" in outcome.prepared.context_used

    def test_health_question_prepares_a_real_bundle(self, orchestrator):
        outcome = orchestrator.prepare("When will my health improve?")
        assert outcome.prepared.domain == "health"
        assert outcome.prepared.bundle["domain"] == "health"
        assert "houses" in outcome.prepared.context_used

    def test_foreign_question_prepares_a_real_bundle(self, orchestrator):
        outcome = orchestrator.prepare("Is this a good time to settle abroad?")
        assert outcome.prepared.domain == "foreign"
        assert outcome.prepared.bundle["domain"] == "foreign"
        assert "houses" in outcome.prepared.context_used

    def test_personality_question_prepares_a_real_bundle(self, orchestrator):
        outcome = orchestrator.prepare("What are my personality traits and character?")
        assert outcome.prepared.domain == "personality"
        assert outcome.prepared.bundle["domain"] == "personality"
        assert "houses" in outcome.prepared.context_used

    # Found missing by independent review of PR #12: every other tense/
    # profile-facts test in this codebase is a leaf unit test (detect_tense()
    # in isolation, profile_facts shape in isolation, verify() in isolation)
    # — nothing asserted the actual wiring between them. A refactor that
    # dropped `question_tense=routing.tense` at the DomainReadingAgent call
    # site would have silently disabled the whole feature with every one of
    # those unit tests still green. These two close that gap.
    def test_tense_flows_from_routing_into_the_agents_rendered_prompt(self, orchestrator):
        outcome = orchestrator.prepare("Why did I get passed over for that promotion?")
        assert outcome.prepared.tense == "retrospective"
        rendered = outcome.prepared.agent.system_prompt
        assert "retrospective" in rendered
        assert "{age_years}" not in rendered  # unformatted placeholder, not the actual value
        assert "{question_tense}" not in rendered
        profile_facts = outcome.prepared.bundle["profile_facts"]
        assert f"age_years {profile_facts['age_years']}" in rendered
        assert profile_facts["as_of"] in rendered

    def test_future_question_tense_is_future_not_retrospective(self, orchestrator):
        outcome = orchestrator.prepare("When will I get a promotion?")
        assert outcome.prepared.tense == "future"
        assert "houses" in outcome.prepared.context_used

    def test_pronoun_followup_without_thread_domain_asks_to_clarify(self, orchestrator):
        """Reproduces the reported bug directly: a follow-up with no
        domain keywords of its own ("this"/"it") has nothing to route on
        by itself."""
        outcome = orchestrator.prepare("Which month is strongest for this?")
        assert outcome.terminal_envelope["type"] == "clarification_needed"

    def test_pronoun_followup_continues_the_threads_established_domain(self, orchestrator):
        outcome = orchestrator.prepare("Which month is strongest for this?", thread_domain="career")
        assert outcome.prepared is not None
        assert outcome.prepared.domain == "career"

    def test_confident_topic_switch_is_not_pulled_back_to_thread_domain(self, orchestrator):
        """A follow-up that clearly names a different domain is a real
        switch, not ambiguity — thread_domain must not override a real signal."""
        outcome = orchestrator.prepare("Is this a good year for my marriage?", thread_domain="career")
        assert outcome.prepared.domain == "marriage"

    def test_unconfigured_thread_domain_hint_is_ignored_safely(self, orchestrator):
        """A domain_not_ready turn stores its own (unconfigured) domain name
        — that must never be treated as something to continue."""
        outcome = orchestrator.prepare("Which month is strongest for this?", thread_domain="litigation")
        assert outcome.terminal_envelope["type"] == "clarification_needed"

    def test_domain_override_bypasses_the_ambiguous_tie(self, orchestrator):
        """An explicit reader choice (tapping a clarification chip) must
        resolve on the first try — a question that ties between career and
        marriage keyword hits would otherwise clarify forever no matter how
        many times its text is re-submitted, since KeywordRouter only checks
        whether a keyword is present, not how many times."""
        outcome = orchestrator.prepare(
            "Is this a good time for my career and my marriage?", domain_override="career",
        )
        assert outcome.prepared is not None
        assert outcome.prepared.domain == "career"

    def test_domain_override_to_the_other_side_of_the_same_tie(self, orchestrator):
        outcome = orchestrator.prepare(
            "Is this a good time for my career and my marriage?", domain_override="marriage",
        )
        assert outcome.prepared is not None
        assert outcome.prepared.domain == "marriage"

    def test_domain_override_to_an_unconfigured_domain_still_reports_not_ready(self, orchestrator):
        """An override bypasses routing, not the registry gate — it must
        never reach a model call for a domain the registry doesn't know."""
        outcome = orchestrator.prepare("Anything you like", domain_override="litigation")
        assert outcome.terminal_envelope["type"] == "domain_not_ready"
        assert outcome.terminal_envelope["domain"] == "litigation"


class TestAskOrchestratorRun:
    @pytest.fixture
    def prepared(self, chart):
        orchestrator = AskOrchestrator(chart_loader=lambda: chart)
        outcome = orchestrator.prepare("Is this a good year for a promotion at work?")
        return orchestrator, outcome.prepared

    def test_clean_reading_persists_on_first_try(self, prepared):
        orchestrator, run = prepared
        persisted = []
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            events = list(orchestrator.run(run, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: persisted.append((reading, status)) or "thread-1"))
        done = events[-1]
        assert done["status"] == "answered"
        assert done["thread_id"] == "thread-1"
        assert persisted[0][1] == "answered"

    def test_done_envelope_carries_tense(self, chart):
        orchestrator = AskOrchestrator(chart_loader=lambda: chart)
        outcome = orchestrator.prepare("Why did I get passed over for that promotion?")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "thread-tense"))
        assert events[-1]["tense"] == "retrospective"

    def test_bad_then_good_repairs_once_and_persists(self, prepared):
        orchestrator, run = prepared
        bad = _good_reading(source="totally_invented_ref")
        good = _good_reading()
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            events = list(orchestrator.run(run, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "thread-2"))
        assert events[-1]["status"] == "answered"
        assert events[-1]["thread_id"] == "thread-2"

    def test_bad_twice_fails_verification_and_persists_nothing_new(self, prepared):
        orchestrator, run = prepared
        bad = _good_reading(source="totally_invented_ref")
        persisted = []
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, bad]):
            events = list(orchestrator.run(run, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: persisted.append((reading, status)) or None))
        assert events[-1]["status"] == "verification_failed"
        assert "reading" not in events[-1]
        assert persisted[0] == (None, "verification_failed")

    def test_generation_exception_reported_as_generation_failed(self, prepared):
        orchestrator, run = prepared
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=RuntimeError("boom")):
            events = list(orchestrator.run(run, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: None))
        assert events[-1]["status"] == "generation_failed"


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

    def test_career_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
            })
        assert r.status_code == 200
        frames = self._frames(r)
        done = frames[-1]
        assert done["type"] == "done"
        assert done["status"] == "answered"
        assert done["domain"] == "career"
        assert done["schema_version"] == "ask_structured_v1"
        assert done["reading"]["interpretation"] == _good_reading().interpretation
        assert any(f["type"] == "status" for f in frames)

    def test_marriage_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for my marriage?",
            })
        assert r.status_code == 200
        done = self._frames(r)[-1]
        assert done["domain"] == "marriage"
        assert done["status"] == "answered"

    def test_wealth_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "When will my financial situation improve?",
            })
        assert r.status_code == 200
        done = self._frames(r)[-1]
        assert done["domain"] == "wealth"
        assert done["status"] == "answered"

    def test_children_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Will I have children soon?",
            })
        assert r.status_code == 200
        done = self._frames(r)[-1]
        assert done["domain"] == "children"
        assert done["status"] == "answered"

    def test_health_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "When will my health improve?",
            })
        assert r.status_code == 200
        done = self._frames(r)[-1]
        assert done["domain"] == "health"
        assert done["status"] == "answered"

    def test_foreign_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time to settle abroad?",
            })
        assert r.status_code == 200
        done = self._frames(r)[-1]
        assert done["domain"] == "foreign"
        assert done["status"] == "answered"

    def test_personality_question_answers_with_structured_reading(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "What are my personality traits and character?",
            })
        assert r.status_code == 200
        done = self._frames(r)[-1]
        assert done["domain"] == "personality"
        assert done["status"] == "answered"

    def test_unsupported_domain_never_calls_an_agent(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading") as run:
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "What does my chart show about property disputes with my siblings?",
            })
        assert r.status_code == 200
        run.assert_not_called()
        frame = self._frames(r)[0]
        assert frame["type"] == "domain_not_ready"
        assert frame["available"] == ["career", "children", "foreign", "health", "marriage", "personality", "wealth"]

    def test_ambiguous_question_asks_for_clarification(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading") as run:
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time for my career and my marriage?",
            })
        run.assert_not_called()
        frame = self._frames(r)[0]
        assert frame["type"] == "clarification_needed"

    def test_refer_out_gates_before_any_agent_call(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading") as run:
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "When will I die?",
            })
        run.assert_not_called()
        frame = self._frames(r)[0]
        assert frame["type"] == "refer_out"
        assert frame["kind"] == "death"

    def test_unknown_kundli_404_before_streaming(self, client):
        r = client.post("/api/v1/ask/nonexistent-id/stream", json={"question": "hi"})
        assert r.status_code == 404

    def test_thread_persists_structured_evidence(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time to change my job?",
                "start_thread": True,
            })
        thread_id = self._frames(r)[-1]["thread_id"]
        assert thread_id
        thread = client.get(f"/api/v1/ask/threads/{thread_id}").json()
        assistant_msg = next(m for m in thread["messages"] if m["role"] == "assistant")
        assert assistant_msg["domain"] == "career"
        assert assistant_msg["evidence"]["schema_version"] == "ask_structured_v1"
        assert assistant_msg["evidence"]["structured_reading"]["interpretation"]

    def test_unhandled_exception_mid_stream_yields_fatal_error_not_a_hang(self, client, env):
        """Reproduces the gap the fatal_error contract exists for: a failure
        outside the two guarded model-call spots (here, the DB write inside
        persist_prepared) used to just kill the SSE connection with no
        terminal frame at all. Patches astrospace.db.crud_mobile.add_ask_message
        — the exact call persist_turn makes — to blow up after a clean,
        successful generation, proving _safe_stream's guarantee holds even
        when the failure isn't a model-call error."""
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()), \
             patch("astrospace.db.crud_mobile.add_ask_message", side_effect=RuntimeError("db is down")):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
                "start_thread": True,
            })
        assert r.status_code == 200
        frames = self._frames(r)
        assert frames, "stream must end in a terminal frame, not silently close"
        last = frames[-1]
        assert last["type"] == "fatal_error"
        assert last["retryable"] is True
        assert not any(f["type"] == "done" for f in frames)

    def test_failed_verification_persists_nothing_new(self, client, env):
        bad = _good_reading(source="totally_invented_ref")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, bad]):
            r = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
                "start_thread": True,
            })
        done = self._frames(r)[-1]
        assert done["status"] == "verification_failed"
        assert done["thread_id"] is None

    def test_pronoun_followup_in_same_thread_continues_career_not_clarify(self, client, env):
        """The reported bug, exercised through the real route + real thread
        persistence: a career thread's follow-up with no domain keywords of
        its own ("this") must continue career, not re-ask to clarify."""
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            first = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
                "start_thread": True,
            })
        thread_id = self._frames(first)[-1]["thread_id"]
        assert thread_id

        followup_reading = _good_reading(interpretation="July through September looks strongest.")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=followup_reading):
            second = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Which month is strongest for this?",
                "thread_id": thread_id,
            })
        frames = self._frames(second)
        done = frames[-1]
        assert done["type"] == "done"
        assert done["status"] == "answered"

    def test_clarification_chip_resolves_on_first_click_not_a_loop(self, client, env):
        """Reproduces the reported bug end-to-end: an ambiguous question ties
        between career and marriage, and tapping the "career" chip must
        answer as career immediately — not re-trigger the same
        clarification_needed response, which is what happened when the chip
        click was resent as re-wrapped question text instead of an explicit
        domain_override."""
        with patch.object(DomainReadingAgent, "run_structured_reading") as run:
            first = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time for my career and my marriage?",
                "start_thread": True,
            })
        run.assert_not_called()
        first_frame = self._frames(first)[0]
        assert first_frame["type"] == "clarification_needed"
        thread_id = first_frame["thread_id"]
        assert thread_id

        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            second = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good time for my career and my marriage?",
                "thread_id": thread_id,
                "domain_override": "career",
            })
        done = self._frames(second)[-1]
        assert done["type"] == "done"
        assert done["status"] == "answered"
        assert done["domain"] == "career"
        assert done["thread_id"] == thread_id

        thread = client.get(f"/api/v1/ask/threads/{thread_id}").json()
        assert thread["messages"][-1]["domain"] == "career"

    def test_confident_domain_switch_in_thread_is_not_pulled_back(self, client, env):
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            first = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for a promotion at work?",
                "start_thread": True,
            })
        thread_id = self._frames(first)[-1]["thread_id"]

        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=_good_reading()):
            second = client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                "question": "Is this a good year for my marriage?",
                "thread_id": thread_id,
            })
        assert self._frames(second)[-1]["domain"] == "marriage"
