"""Profile Context Ledger Phase 2 — deterministic Ask integration.

Two layers, matching the two ways this system is exercised:

- `TestOrchestratorPreflight*` / `TestFrozenSnapshot*`: real `AskOrchestrator`
  + real `VedicChart` + real `verify()`/`verify_coverage()`, with a FAKE
  `ProfileContextStore` (a plain closure, no DB) — the same pattern
  test_domain_agent.py's `TestAskOrchestratorRun` already uses for
  `chart_loader`. Only `DomainReadingAgent.run_structured_reading` is
  mocked, matching this repo's established mock-realism discipline.
- `TestLedgerIntegration*`: real DB (Phase 1's own `env` fixture, imported
  by pattern from test_profile_context_ledger.py) + `build_profile_context_projection`
  — proves isolation/deletion/domain-filtering hold against the real ledger,
  not just the fake store the orchestrator tests use.

No test here calls a real model. Every reading is an explicit fixture.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.agents.orchestrator import AskOrchestrator, ProfileContextStore
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.api.auth import AuthUser, current_user
from astrospace.context.profile_context import build_logical_preflight
from astrospace.core.vedic.chart import VedicChart
from astrospace.db import crud, get_db
from astrospace.db.crud_profile_context import build_profile_context_projection
from astrospace.db.database import Base
from astrospace.db.models import ProfileContextFact, ProfileContextLedger

ME = "test-user-pcl-phase2"


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1958, 4, 12, 9, 15, "Chennai", "IN")


def _reading(**overrides) -> StructuredReading:
    base = dict(
        acknowledgment="You're asking about this.",
        technical_basis=[TechnicalBasisItem(factor="10th lord", reading="well placed", source="houses")],
        interpretation="A supportive stretch, grounded in your chart.",
        summary_and_assurance="A good window, not a fixed outcome.",
        guidance=Guidance(follow_up_questions=["What else would help?"]),
        confidence="medium",
    )
    base.update(overrides)
    return StructuredReading(**base)


def _fact(key: str, value: dict, ref: str = "profile_fact:aaaa@1", status: str = "active") -> dict:
    return {"id": "aaaa", "key": key, "value": value, "status": status, "ref": ref,
            "category": "life_stage", "sensitivity": "personal"}


def _store(facts: list[dict], revision: int = 1, calls: list | None = None) -> ProfileContextStore:
    """A fake, DB-free ProfileContextStore — the closure IS the frozen
    snapshot boundary in these tests; `calls` (if supplied) records every
    invocation so a test can assert it was built exactly once."""
    def projection(domain: str, as_of_iso: str) -> dict:
        if calls is not None:
            calls.append((domain, as_of_iso))
        relevant = [f for f in facts]  # domain filtering already applied by caller in these fixtures
        return {
            "facts": relevant, "revision": revision, "as_of": as_of_iso or "2026-08-14",
            "domain": domain, "status": "ready", "contradictions": [],
        }
    return ProfileContextStore(projection=projection)


# ── 1. Retired reader asks when career will begin ──────────────────────────

class TestRetiredCareerInception:
    def test_blocked_frame_rejects_a_future_first_career_answer(self, chart):
        store = _store([_fact("employment_status", {"code": "retired"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        bad = _reading(interpretation="Your career will begin in earnest around 2029, a strong new start.")
        good = _reading(interpretation="Looking back, your working years were most active in the 1990s.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t1"))
        # The bad first attempt must not ship as-is; the repair must be
        # attempted and the corrected answer persisted.
        assert events[-1]["status"] == "answered"
        assert "will begin" not in events[-1]["reading"]["interpretation"]

    def test_twice_blocked_fails_verification_never_ships(self, chart):
        store = _store([_fact("employment_status", {"code": "retired"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        bad = _reading(interpretation="Your career will begin in earnest around 2029.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, bad]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: None))
        assert events[-1]["status"] == "verification_failed"
        assert "reading" not in events[-1]

    def test_no_ledger_fact_leaves_the_same_answer_untouched(self, chart):
        # Control: the identical bad-sounding text is fine when there is no
        # retirement fact — proves the block is ledger-driven, not a blanket
        # ban on the phrase.
        orchestrator = AskOrchestrator(chart_loader=lambda: chart)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        reading = _reading(interpretation="Your career will begin in earnest around 2029.")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=reading):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t3"))
        assert events[-1]["status"] == "answered"


# ── 2. Married reader asks about relationship timing ───────────────────────

class TestMarriedRelationshipTiming:
    def test_blocked_frame_rejects_first_marriage_framing(self, chart):
        store = _store([_fact("relationship_status", {"code": "married"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Will I ever get married?", domain_override="marriage")
        bad = _reading(interpretation="You will get married once Jupiter transits your 7th house.")
        good = _reading(interpretation="Your existing marriage strengthens further in this window.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t4"))
        assert events[-1]["status"] == "answered"
        assert "you will get married" not in events[-1]["reading"]["interpretation"].lower()

    def test_retrospective_tense_does_not_trigger_the_block(self, chart):
        # "Unless explicitly historical" — a retrospective question about an
        # already-married reader's marriage timing is not blocked.
        store = _store([_fact("relationship_status", {"code": "married"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When did I get married?", domain_override="marriage")
        assert outcome.prepared.tense == "retrospective"
        preflight = build_logical_preflight(
            profile_facts=outcome.prepared.bundle.get("profile_facts") or {},
            projection_facts=outcome.prepared.bundle["profile_context"]["facts"],
            tense=outcome.prepared.tense, question="When did I get married?", domain="marriage",
        )
        assert "first_marriage_framing" not in preflight.blocked_frames


# ── 3. Reader with children asks whether they will have children ───────────

class TestExistingChildrenFutureFraming:
    def test_blocked_frame_rejects_first_child_framing(self, chart):
        store = _store([_fact("has_children", {"value": True})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Will I ever have children?", domain_override="children")
        bad = _reading(interpretation="You will have a child once the 5th lord strengthens.")
        good = _reading(interpretation="Your existing children's milestones are well supported in this window.",
                        technical_basis=[TechnicalBasisItem(factor="5th house", reading="supports family",
                                                            source="profile_fact:aaaa@1")])
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t5"))
        assert events[-1]["status"] == "answered"
        assert "you will have a child" not in events[-1]["reading"]["interpretation"].lower()


# ── 4. Diagnosed illness + a health prediction is requested ────────────────

class TestDiagnosedIllnessPrognosis:
    def test_blocked_frame_rejects_a_recovery_guarantee(self, chart):
        store = _store([_fact("current_health_constraint", {"text": "recovering from surgery"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare(
            "How is my chart supporting me through this recovery period?", domain_override="health",
        )
        bad = _reading(interpretation="You will make a full recovery within weeks, guaranteed by this transit.")
        good = _reading(interpretation="This transit offers supportive energy; please follow your doctor's guidance "
                                       "for anything about your actual recovery.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t6"))
        assert events[-1]["status"] == "answered"
        assert "full recovery" not in events[-1]["reading"]["interpretation"].lower()

    def test_never_presents_disclosed_condition_as_a_chart_discovery(self, chart):
        store = _store([_fact("current_health_constraint", {"text": "recovering from surgery"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("What does my chart say about my health?", domain_override="health")
        bad = _reading(interpretation="Your chart reveals that you are currently recovering from an illness.")
        good = _reading(interpretation="Since you shared that you're recovering, this transit favours gentle pacing.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t7"))
        assert events[-1]["status"] == "answered"
        assert "your chart reveals" not in events[-1]["reading"]["interpretation"].lower()


# ── 5 & 11. Frozen snapshot: correction mid-stream / repair gets the same snapshot ──

class TestFrozenSnapshot:
    def test_projection_is_fetched_exactly_once_even_across_a_repair(self, chart):
        calls: list = []
        store = _store([_fact("employment_status", {"code": "retired"})], calls=calls)
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        assert len(calls) == 1  # fetched during prepare(), not lazily

        bad = _reading(interpretation="Your career will begin in earnest around 2029.")
        good = _reading(interpretation="Looking back at your working years, they peaked in the 1990s.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, good]):
            list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                  persist=lambda reading, status: "t8"))
        # The repair attempt reused prepared.agent (built once in prepare())
        # rather than re-fetching context — still exactly one call.
        assert len(calls) == 1

    def test_a_correction_committed_after_prepare_never_reaches_this_turn(self, chart):
        """Simulates 'fact corrected while an Ask response is streaming':
        the store here is a closure over a MUTABLE list a 'concurrent'
        correction could append to — proving the orchestrator's snapshot,
        once taken, ignores it."""
        facts = [_fact("employment_status", {"code": "retired"}, ref="profile_fact:aaaa@1")]
        calls: list = []
        store = _store(facts, calls=calls)
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")

        # The "correction" lands after prepare() already built the frozen
        # bundle — mutating the underlying list must not retroactively
        # change what this turn's bundle contains.
        facts.append(_fact("employment_status", {"code": "employed"}, ref="profile_fact:bbbb@2"))

        assert outcome.prepared.bundle["profile_context"]["facts"] == [
            _fact("employment_status", {"code": "retired"}, ref="profile_fact:aaaa@1")
        ]
        assert len(calls) == 1


# ── 6. Profile switched during projection or generation ────────────────────

class TestProfileSwitchIsolation:
    def test_two_orchestrators_bound_to_different_profiles_never_cross_contaminate(self, chart):
        store_a = _store([_fact("employment_status", {"code": "retired"})])
        store_b = _store([_fact("employment_status", {"code": "employed"})])
        orch_a = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store_a)
        orch_b = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store_b)

        outcome_a = orch_a.prepare("Tell me about my career.", domain_override="career")
        outcome_b = orch_b.prepare("Tell me about my career.", domain_override="career")

        facts_a = outcome_a.prepared.bundle["profile_context"]["facts"]
        facts_b = outcome_b.prepared.bundle["profile_context"]["facts"]
        assert facts_a[0]["value"]["code"] == "retired"
        assert facts_b[0]["value"]["code"] == "employed"


# ── 9 & 10. Foreign fact ID / multi-domain access — DB-level (real ledger) ──

@pytest.fixture()
def db_env():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    db = Session()
    mine = crud.create_kundli(db, {
        "user_id": ME, "name": "Mine", "relation": "self",
        "birth_year": 1958, "birth_month": 4, "birth_day": 12,
        "birth_hour": 9, "birth_minute": 15,
        "birth_city": "Chennai", "birth_nation": "IN",
    }).id
    theirs = crud.create_kundli(db, {
        "user_id": "someone-else", "name": "Theirs", "relation": "self",
        "birth_year": 1980, "birth_month": 3, "birth_day": 3,
        "birth_hour": 8, "birth_minute": 0,
        "birth_city": "Delhi", "birth_nation": "IN",
    }).id
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME)
    try:
        yield {"client": TestClient(app), "Session": Session, "mine": mine, "theirs": theirs}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _post_fact(env, profile, key, value, idem="create-0001", expected_revision=0):
    return env["client"].post(
        f"/api/v1/profiles/{profile}/context/facts",
        json={
            "expected_revision": expected_revision, "key": key, "value": value,
            "source": {"kind": "profile_form", "channel": "profile_settings"},
            "consent": {"state": "granted", "surface": "profile_memory_v1"},
        },
        headers={"Idempotency-Key": idem},
    )


class TestLedgerIntegrationForeignAndDomainScope:
    def test_foreign_profile_fact_never_appears_in_this_profiles_projection(self, db_env):
        db = db_env["Session"]()
        theirs_fact = ProfileContextFact(
            user_id="someone-else", profile_id=db_env["theirs"], category="life_stage",
            key="employment_status", value={"code": "retired"}, status="active",
            confidence="confirmed", sensitivity="personal", retention="until_removed",
            source={}, consent={}, revision=1,
        )
        db.add(theirs_fact)
        db.add(ProfileContextLedger(profile_id=db_env["theirs"], user_id="someone-else", revision=1))
        db.commit()
        theirs_ref = f"profile_fact:{theirs_fact.id}@1"
        db.close()

        # Building the projection for MY profile must never surface it,
        # even by wrong-profile fact_id/ref.
        db2 = db_env["Session"]()
        projection = build_profile_context_projection(
            db2, user_id=ME, profile_id=db_env["mine"], domain="career",
        )
        refs = {f["ref"] for f in projection.facts}
        assert theirs_ref not in refs
        db2.close()

    def test_fact_registered_for_one_domain_absent_from_an_unrelated_domain_projection(self, db_env):
        response = _post_fact(db_env, db_env["mine"], "employment_status", {"code": "retired"})
        assert response.status_code == 201

        db = db_env["Session"]()
        career_projection = build_profile_context_projection(
            db, user_id=ME, profile_id=db_env["mine"], domain="career",
        )
        marriage_projection = build_profile_context_projection(
            db, user_id=ME, profile_id=db_env["mine"], domain="marriage",
        )
        db.close()
        assert any(f["key"] == "employment_status" for f in career_projection.facts)
        assert not any(f["key"] == "employment_status" for f in marriage_projection.facts)


# ── 7 & 8. Fact deleted after an old thread was created / thread reopened ──

class TestLedgerIntegrationDeletionAndReopening:
    def test_deleting_a_fact_after_it_was_cited_does_not_retroactively_change_the_old_evidence_ref(self, db_env):
        created = _post_fact(db_env, db_env["mine"], "current_health_constraint", {"text": "recovering"})
        fact = created.json()["fact"]
        # add_profile_fact's own response doesn't carry a `ref` (only the
        # projection endpoint does) — build it the same way
        # build_profile_context_projection does, from id@revision.
        old_ref = f"profile_fact:{fact['id']}@{fact['revision']}"

        # Delete it (simulating: the old thread's stored evidence already
        # references old_ref, the reader now removes the fact).
        db_env["client"].request(
            "DELETE", f"/api/v1/profiles/{db_env['mine']}/context/facts/{fact['id']}",
            json={"expected_revision": 1}, headers={"Idempotency-Key": "delete-0001"},
        )

        db = db_env["Session"]()
        fresh_projection = build_profile_context_projection(
            db, user_id=ME, profile_id=db_env["mine"], domain="health",
        )
        db.close()
        # A NEW turn's frozen snapshot correctly no longer contains it —
        # the ref is not silently kept "current."
        assert old_ref not in {f["ref"] for f in fresh_projection.facts}

    def test_reopening_after_a_revision_change_gets_a_fresh_snapshot_not_the_old_one(self, db_env):
        first = _post_fact(db_env, db_env["mine"], "employment_status", {"code": "employed"})
        assert first.json()["revision"] == 1

        db = db_env["Session"]()
        old_snapshot = build_profile_context_projection(
            db, user_id=ME, profile_id=db_env["mine"], domain="career",
        )
        db.close()
        assert old_snapshot.revision == 1

        second = _post_fact(db_env, db_env["mine"], "occupation", {"text": "Teacher"}, idem="create-0002",
                            expected_revision=1)
        assert second.json()["revision"] == 2

        db2 = db_env["Session"]()
        new_snapshot = build_profile_context_projection(
            db2, user_id=ME, profile_id=db_env["mine"], domain="career",
        )
        db2.close()
        assert new_snapshot.revision == 2
        assert old_snapshot.revision != new_snapshot.revision


# ── verify()/verify_coverage() unit-level: nonexistent/wrong-profile refs ──

class TestVerifierEvidenceResolution:
    def test_citing_a_ref_absent_from_the_frozen_bundle_fails_verification(self, chart):
        store = _store([_fact("employment_status", {"code": "retired"}, ref="profile_fact:real@1")])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Tell me about my career.", domain_override="career")
        fabricated = _reading(technical_basis=[TechnicalBasisItem(
            factor="employment", reading="retired", source="profile_fact:does-not-exist@99",
        )])
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[fabricated, fabricated]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: None))
        assert events[-1]["status"] == "verification_failed"

    def test_citing_the_real_ref_from_the_frozen_bundle_passes(self, chart):
        store = _store([_fact("employment_status", {"code": "retired"}, ref="profile_fact:real@1")])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Tell me about my career.", domain_override="career")
        grounded = _reading(technical_basis=[TechnicalBasisItem(
            factor="employment status", reading="retired", source="profile_fact:real@1",
        )])
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=grounded):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t9"))
        assert events[-1]["status"] == "answered"
