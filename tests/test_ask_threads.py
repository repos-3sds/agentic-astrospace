"""Thread persistence for Ask-AI's web (non-streaming) endpoint.

The Anthropic call is stubbed at `DomainReadingAgent.run_structured_reading`
— matching the pattern established in test_domain_agent.py for the streamed
route, now that both endpoints share the same `AskOrchestrator` pipeline.
These tests cover the persistence contract, not the agent. Three behaviours
are worth guarding closely:

* a failed generation must leave the thread untouched, because a dangling user
  turn would make the next request replay two user messages in a row and the
  agent loop requires strict alternation;
* a stored thread outranks any `history` in the request body, or a client
  could rewrite its own conversation on the way in;
* every question used here that expects to reach the model must route
  confidently to a real registered domain — a generic/vague question now
  hits `clarification_needed` before the model is ever called, which is
  correct orchestrator behaviour but would silently break a test written
  against the old free-form `VedicQAAgent`, so wording matters here in a way
  it didn't before this migration.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base

ME = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


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


def _good_reading(text="Saturn is transiting your 10th house.") -> StructuredReading:
    return StructuredReading(
        acknowledgment="Here's what your chart shows.",
        technical_basis=[TechnicalBasisItem(factor="10th lord", reading="well placed", source="houses")],
        interpretation=text,
        summary_and_assurance="A tendency worth watching, not a certainty.",
        guidance=Guidance(follow_up_questions=[]),
        confidence="medium",
    )


def _reply(text="Saturn is transiting your 10th house."):
    """Stub the orchestrator's only model call point — matches the pattern
    established in test_domain_agent.py for the streamed route, now that
    both endpoints share `AskOrchestrator`."""
    return patch.object(DomainReadingAgent, "run_structured_reading",
                        return_value=_good_reading(text))


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
        with patch.object(DomainReadingAgent, "run_structured_reading") as run:
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": question,
            }).json()
        assert body["refer_out_kind"] == kind
        assert body["tools_used"] == []
        run.assert_not_called()

    @pytest.mark.parametrize("question", [
        "What does my chart say about my core personality traits?",
        "Is this a good time to negotiate a job offer?",
        "How is my financial situation looking this year?",
    ])
    def test_safe_tendency_and_timing_questions_remain_answerable(self, client, env, question):
        with _reply() as run:
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": question,
            }).json()
        assert body["refer_out_kind"] is None
        # At least once, not exactly once: `_good_reading()` is a minimal
        # fixture that doesn't cite every section `verify_coverage()` checks
        # for (e.g. career's D10/AmK), which legitimately triggers the
        # orchestrator's single repair attempt — real behavior, not
        # something this test should fight. The point here is routing
        # reached the model at all, not the exact call count.
        assert run.call_count >= 1

    def test_refer_out_is_persisted_on_the_assistant_turn(self, client, env):
        body = client.post(f"/api/v1/ask/{env['kundli']}", json={
            "question": "Should I buy crypto?",
            "start_thread": True,
        }).json()
        thread = client.get(f"/api/v1/ask/threads/{body['thread_id']}").json()
        assert thread["messages"][1]["refer_out_kind"] == "money"
        # domain=None on a refer-out turn, matching ask_stream_routes.py
        # exactly — a refusal never reached any domain's context, so
        # `domain` (which domain actually generated a reading) is honestly
        # None here, not the safety kind that was crossed. The pre-migration
        # VedicQAAgent path set domain="money" here; this is a deliberate
        # behavior change to match the already-shipped streaming contract,
        # not a regression.
        assert thread["messages"][1]["domain"] is None
        assert thread["messages"][1]["evidence"] == {
            "safety_policy": "excluded_verdict",
        }


class TestThreadPersistence:
    def test_start_thread_persists_both_turns(self, client, env):
        with _reply("Your career is entering a favourable phase."):
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career progressing?", "start_thread": True,
            }).json()
        assert body["thread_id"]

        thread = client.get(f"/api/v1/ask/threads/{body['thread_id']}").json()
        roles = [m["role"] for m in thread["messages"]]
        assert roles == ["user", "assistant"]
        assert thread["messages"][0]["content"] == "How is my career progressing?"
        assert thread["messages"][1]["content"] == "Your career is entering a favourable phase."

    def test_first_question_becomes_the_title(self, client, env):
        with _reply():
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "What about marriage timing?", "start_thread": True,
            }).json()
        assert body["thread"]["title"] == "What about marriage timing?"
        assert body["thread"]["message_count"] == 2

    def test_long_first_question_gets_an_explicit_title_ellipsis(self, env):
        db = next(app.dependency_overrides[get_db]())
        thread = cm.create_ask_thread(db, ME, env["kundli"])
        cm.add_ask_message(db, thread.id, "user", "x" * 100)
        assert cm.get_ask_thread(db, thread.id, ME).title == f"{'x' * 79}…"
        db.close()

    def test_continuing_a_thread_appends(self, client, env):
        """The second question ("Follow up") deliberately carries no domain
        keyword of its own — it must inherit the thread's established
        domain (`_thread_established_domain`) rather than hitting
        clarification, which is real orchestrator continuation behaviour
        this test now exercises rather than sidesteps."""
        with _reply():
            first = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career this year?", "start_thread": True,
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
                "question": "How is my career going?", "start_thread": True,
            }).json()["thread_id"]

        with _reply() as run:
            client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "And this", "thread_id": tid,
            })
        # First call, not the last — a possible repair attempt (see the
        # comment on test_safe_tendency_and_timing_questions_remain_answerable)
        # appends an extra "fix these problems" user turn to any later call,
        # which isn't what this test is checking.
        sent = run.call_args_list[0][0][0]
        assert [m["role"] for m in sent] == ["user", "assistant", "user"]
        assert sent[0]["content"] == "How is my career going?"
        assert sent[-1]["content"] == "And this"

    def test_body_history_cannot_override_a_thread(self, client, env):
        """Otherwise a client could rewrite its own conversation."""
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career shaping up?", "start_thread": True,
            }).json()["thread_id"]

        with _reply() as run:
            client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Next",
                "thread_id": tid,
                "history": [{"role": "user", "content": "FABRICATED"}],
            })
        contents = [m["content"] for m in run.call_args[0][0]]
        assert "FABRICATED" not in contents
        assert "How is my career shaping up?" in contents

    def test_assistant_turn_records_provenance(self, client, env):
        """Provenance now means the structured citation bridge shape
        (`_evidence_from_reading`), not a free-form tool-call list — the new
        pipeline has no tool loop to record tools_used from."""
        reading = _good_reading("Career answer with a real citation.")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=reading):
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career this quarter?", "start_thread": True,
            }).json()["thread_id"]
        messages = client.get(f"/api/v1/ask/threads/{tid}").json()["messages"]
        evidence = messages[1]["evidence"]
        assert evidence["schema_version"] == "ask_structured_v1"
        assert evidence["references"] == ["houses"]
        assert evidence["structured_reading"]["interpretation"] == reading.interpretation


class TestFailureLeavesNoPartialWrite:
    def test_failed_generation_writes_nothing_to_a_new_thread(self, client, env):
        before = client.get("/api/v1/ask/threads").json()["count"]
        with patch.object(DomainReadingAgent, "run_structured_reading",
                          side_effect=RuntimeError("upstream down")):
            r = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career outlook?", "start_thread": True,
            })
        assert r.status_code == 502
        assert client.get("/api/v1/ask/threads").json()["count"] == before

    def test_failed_generation_leaves_an_existing_thread_intact(self, client, env):
        """The first turn establishes a real domain (career) so the second,
        deliberately vague turn inherits it via thread continuation instead
        of hitting clarification — the failure needs to happen inside the
        model call to test what this class is actually about."""
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career doing?", "start_thread": True,
            }).json()["thread_id"]

        with patch.object(DomainReadingAgent, "run_structured_reading",
                          side_effect=RuntimeError("upstream down")):
            assert client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Doomed turn", "thread_id": tid,
            }).status_code == 502

        messages = client.get(f"/api/v1/ask/threads/{tid}").json()["messages"]
        assert [m["role"] for m in messages] == ["user", "assistant"]
        assert all(m["content"] != "Doomed turn" for m in messages)

    def test_verification_failure_writes_nothing_to_a_new_thread(self, client, env):
        """The generation-exception case above covers `generation_failed`;
        this covers the other terminal failure mode `verify()`/
        `verify_coverage()` can produce — `verification_failed` — which
        `VedicQAAgent` never had at all before this migration. An invented
        citation source fails safety_violations on both the original and
        the single repair attempt, so this never ships."""
        before = client.get("/api/v1/ask/threads").json()["count"]
        bad = _good_reading()
        bad.technical_basis[0].source = "totally_invented_ref"
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=bad):
            r = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career outlook this quarter?", "start_thread": True,
            })
        assert r.status_code == 502
        assert client.get("/api/v1/ask/threads").json()["count"] == before


class TestTerminalStatesAreExplicit:
    """`status` must never let clarification/domain_not_ready be mistaken
    for a real reading just because `answer` is non-empty text — see the
    field's own docstring in ask_routes.py and models.ts."""

    def test_answered_status(self, client, env):
        with _reply():
            body = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "How is my career doing this year?",
            }).json()
        assert body["status"] == "answered"

    def test_refer_out_status(self, client, env):
        body = client.post(f"/api/v1/ask/{env['kundli']}", json={
            "question": "When will I die?",
        }).json()
        assert body["status"] == "refer_out"

    def test_domain_not_ready_status(self, client, env):
        body = client.post(f"/api/v1/ask/{env['kundli']}", json={
            "question": "What subjects should I study in college?",
        }).json()
        assert body["status"] == "domain_not_ready"
        assert "isn't ready yet" in body["answer"]


class TestNonStreamingSafetyParity:
    """The web (non-streaming) and native (streaming) Ask endpoints now
    share one `AskOrchestrator` pipeline. These pin down that both routes
    reach the *identical* safety decision for the same question — not that
    the guardrails themselves are correct (test_refer_out_boundary.py and
    test_verifier.py already own that), just that migrating this route
    didn't fork the decision between the two surfaces."""

    @staticmethod
    def _stream_done(response) -> dict:
        import json
        frames = [json.loads(line[len("data: "):])
                 for line in response.text.splitlines()
                 if line.startswith("data: ")]
        return frames[-1]

    @pytest.mark.parametrize(("question", "expected_kind"), [
        ("When will I die?", "death"),
        ("Will I recover from this illness?", "health"),
        ("Will I win my court case?", "legal"),
        ("Which stock should I buy?", "money"),
    ])
    def test_refer_out_kind_matches_across_both_endpoints(self, client, env, question, expected_kind):
        non_stream = client.post(f"/api/v1/ask/{env['kundli']}", json={"question": question}).json()
        stream_done = self._stream_done(
            client.post(f"/api/v1/ask/{env['kundli']}/stream", json={"question": question})
        )
        assert non_stream["refer_out_kind"] == expected_kind
        assert non_stream["status"] == "refer_out"
        assert stream_done["type"] == "refer_out"
        assert stream_done["kind"] == expected_kind

    def test_unconfigured_domain_matches_across_both_endpoints(self, client, env):
        question = "What subjects should I study in college?"
        non_stream = client.post(f"/api/v1/ask/{env['kundli']}", json={"question": question}).json()
        stream_done = self._stream_done(
            client.post(f"/api/v1/ask/{env['kundli']}/stream", json={"question": question})
        )
        assert non_stream["status"] == "domain_not_ready"
        assert stream_done["type"] == "domain_not_ready"
        assert stream_done["domain"] == "education"
        # The non-streaming response has no `domain` field to compare against
        # (see AskResponse) — its `answer` text is the only carrier here, and
        # both routes build it from the same `envelope["domain_label"]`.
        assert "isn't ready yet" in non_stream["answer"]

    def test_accident_outcome_overclaim_rejected_identically_on_both_endpoints(self, client, env):
        """Output-side parity, not just input-side: a health reading that
        crosses from a caution into a definite accident-outcome verdict
        (dosha_overclaim_kind's health_outcome_overclaim category) must fail
        verification on both endpoints, not just the streamed one. The mock
        always returns the same overclaiming text, so both the original
        attempt and the single repair fail identically -- verification_failed
        on both surfaces."""
        overclaim = _good_reading("You will have an accident next year.")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=overclaim):
            non_stream = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Will I have an accident this year?",
            })
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=overclaim):
            stream_done = self._stream_done(
                client.post(f"/api/v1/ask/{env['kundli']}/stream", json={
                    "question": "Will I have an accident this year?",
                })
            )
        assert non_stream.status_code == 502
        assert stream_done["status"] == "verification_failed"


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
        assert tid in {t["id"] for t in client.get(
            "/api/v1/ask/threads", params={"archived": True},
        ).json()["threads"]}
        archived_detail = client.get(f"/api/v1/ask/threads/{tid}").json()["thread"]
        assert archived_detail["archived_at"] is not None

    def test_archived_thread_can_be_restored(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Restore this career thread", "start_thread": True,
            }).json()["thread_id"]
        client.post(f"/api/v1/ask/threads/{tid}/archive")
        restored = client.post(f"/api/v1/ask/threads/{tid}/restore")
        assert restored.status_code == 200
        assert restored.json() == {"archived": False}
        assert tid in {t["id"] for t in client.get(
            "/api/v1/ask/threads", params={"kundli_id": env["kundli"]},
        ).json()["threads"]}

    def test_owned_thread_can_be_deleted_with_its_messages(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['kundli']}", json={
                "question": "Delete this career thread", "start_thread": True,
            }).json()["thread_id"]
        assert client.delete(f"/api/v1/ask/threads/{tid}").json() == {"deleted": True}
        assert client.get(f"/api/v1/ask/threads/{tid}").status_code == 404

    def test_cannot_restore_or_delete_another_users_thread(self, client, env):
        assert client.post(
            f"/api/v1/ask/threads/{env['foreign_thread']}/restore",
        ).status_code == 404
        assert client.delete(
            f"/api/v1/ask/threads/{env['foreign_thread']}",
        ).status_code == 404

    def test_filter_by_kundli(self, client, env):
        with _reply():
            tid = client.post(f"/api/v1/ask/{env['second']}", json={
                "question": "On the second kundli", "start_thread": True,
            }).json()["thread_id"]
        listed = client.get("/api/v1/ask/threads",
                            params={"kundli_id": env["second"]}).json()
        assert tid in {t["id"] for t in listed["threads"]}
        assert all(t["kundli_id"] == env["second"] for t in listed["threads"])
