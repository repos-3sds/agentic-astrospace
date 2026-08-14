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
import json
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


def _store(facts: list[dict], revision: int = 1, calls: list | None = None,
          status: str = "ready", contradictions: tuple = ()) -> ProfileContextStore:
    """A fake, DB-free ProfileContextStore — the closure IS the frozen
    snapshot boundary in these tests; `calls` (if supplied) records every
    invocation so a test can assert it was built exactly once. `status`/
    `contradictions` let a test build the exact shape
    `build_profile_context_projection()` produces for an unresolved
    contradiction, without a real DB."""
    def projection(domain: str, as_of_iso: str) -> dict:
        if calls is not None:
            calls.append((domain, as_of_iso))
        relevant = [f for f in facts]  # domain filtering already applied by caller in these fixtures
        return {
            "facts": relevant, "revision": revision, "as_of": as_of_iso or "2026-08-14",
            "domain": domain, "status": status, "contradictions": list(contradictions),
        }
    return ProfileContextStore(projection=projection)


def _failing_store(calls: list | None = None) -> ProfileContextStore:
    """A configured store whose `projection()` always raises — simulates a
    transient ledger-query failure, distinct from no store being configured
    at all (see `AskOrchestrator.check_profile_context()`)."""
    def projection(domain: str, as_of_iso: str) -> dict:
        if calls is not None:
            calls.append((domain, as_of_iso))
        raise RuntimeError("ledger query failed")
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


# ── Review findings (2026-08-14): reproduced counterexamples against 3e503d9,
# fixed, pinned here so they cannot regress silently ──────────────────────

class TestBlockedFrameNegationAware:
    """P1: `_BLOCKED_FRAME_PATTERNS` used a bare `.search()`, so a careful,
    correctly-hedged answer that merely CONTAINS the blocked phrase as a
    negated substring was rejected as if it had used the frame unhedged. A
    repair attempt facing this bug would just repeat the same safe wording
    and burn its one retry into `verification_failed` — turning a valid
    consultation into a failure. Fixed by routing the same shared
    negation check safety.py's overclaim patterns already use
    (`_negation_precedes`) through `_blocked_frame_violations`."""

    def test_a_hedged_denial_of_first_marriage_framing_is_not_rejected(self, chart):
        store = _store([_fact("relationship_status", {"code": "married"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Will I ever get married?", domain_override="marriage")
        safe = _reading(
            interpretation="This does not mean you will get married in this period.",
        )
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=safe):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t10"))
        assert events[-1]["status"] == "answered"

    def test_a_hedged_denial_of_a_recovery_guarantee_is_not_rejected(self, chart):
        store = _store([_fact("current_health_constraint", {"text": "recovering from surgery"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare(
            "How is my chart supporting me through this recovery period?", domain_override="health",
        )
        safe = _reading(interpretation="I cannot promise you will recover.")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=safe):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t11"))
        assert events[-1]["status"] == "answered"

    def test_an_unhedged_first_marriage_answer_is_still_rejected(self, chart):
        # Regression guard: the negation fix must not blunt the genuine
        # positive case this whole mechanism exists for.
        store = _store([_fact("relationship_status", {"code": "married"})])
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Will I ever get married?", domain_override="marriage")
        bad = _reading(interpretation="You will get married once Jupiter transits your 7th house.")
        with patch.object(DomainReadingAgent, "run_structured_reading", side_effect=[bad, bad]):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: None))
        assert events[-1]["status"] == "verification_failed"


class TestContradictoryLedgerFactsAreNotAuthoritative:
    """P1: the projection correctly flags simultaneous active
    `relationship_status=married` and `relationship_status=single` as
    `status: context_confirmation_needed` with `contradictions:
    ["relationship_status"]`, but `check_profile_context()` was handing ALL
    facts — including both contradictory ones — to
    `build_logical_preflight()`, which picked whichever value happened to
    come first in the list and built a hard blocked frame from it. Fixed by
    threading the projection's own `contradictions` through to
    `build_logical_preflight()`, which now excludes any contradicted key
    from every blocked/required-frame decision and surfaces the conflict in
    `missing_or_conflicting_context` instead. Both insertion orders are
    tested so DB row order cannot become policy either."""

    def test_married_then_single_is_not_authoritative(self, chart):
        store = _store(
            [_fact("relationship_status", {"code": "married"}, ref="profile_fact:a@1"),
             _fact("relationship_status", {"code": "single"}, ref="profile_fact:b@1")],
            status="context_confirmation_needed", contradictions=("relationship_status",),
        )
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Will I ever get married?", domain_override="marriage")
        preflight = outcome.prepared.bundle["profile_context"]["preflight"]
        assert "first_marriage_framing" not in preflight["blocked_frames"]
        assert not preflight["applicable_fact_refs"]
        assert any("relationship_status" in note
                   for note in preflight["missing_or_conflicting_context"])

    def test_single_then_married_is_not_authoritative(self, chart):
        # Same facts, opposite insertion order — the outcome must be
        # identical, proving neither value silently wins by being first.
        store = _store(
            [_fact("relationship_status", {"code": "single"}, ref="profile_fact:b@1"),
             _fact("relationship_status", {"code": "married"}, ref="profile_fact:a@1")],
            status="context_confirmation_needed", contradictions=("relationship_status",),
        )
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Will I ever get married?", domain_override="marriage")
        preflight = outcome.prepared.bundle["profile_context"]["preflight"]
        assert "first_marriage_framing" not in preflight["blocked_frames"]
        assert not preflight["applicable_fact_refs"]
        assert any("relationship_status" in note
                   for note in preflight["missing_or_conflicting_context"])

    def test_a_reading_can_still_ship_when_the_only_conflict_is_unrelated_to_the_question(self, chart):
        # The contradiction must not turn into a hard failure of its own —
        # it only removes that key's authority, it does not block the turn.
        store = _store(
            [_fact("relationship_status", {"code": "married"}, ref="profile_fact:a@1"),
             _fact("relationship_status", {"code": "single"}, ref="profile_fact:b@1")],
            status="context_confirmation_needed", contradictions=("relationship_status",),
        )
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("Tell me about my career.", domain_override="career")
        reading = _reading(interpretation="Your career shows a steady, supportive pattern this year.")
        with patch.object(DomainReadingAgent, "run_structured_reading", return_value=reading):
            events = list(orchestrator.run(outcome.prepared, [{"role": "user", "content": "q"}],
                                           persist=lambda reading, status: "t12"))
        assert events[-1]["status"] == "answered"


class TestLedgerRetrievalFailureBlocksGeneration:
    """P1: `check_profile_context()` caught every exception from a
    CONFIGURED `ProfileContextStore` and substituted an empty, `status:
    "ready"` projection — silently answering as if the reader had no saved
    facts at all whenever the ledger query merely failed once. For a
    retired/married/health-disclosed reader this recreates the exact
    unconstrained-answer failure Phase 2 exists to close, indistinguishable
    from a genuinely empty ledger. Fixed: a configured store's exception
    now short-circuits `prepare()` to a terminal `context_unavailable`
    envelope before any model call — no fact values exposed, generation
    never runs. No store configured at all is unaffected (stays additive,
    matching pre-Phase-2 behaviour) — see `TestRetiredCareerInception.
    test_no_ledger_fact_leaves_the_same_answer_untouched` for that control."""

    def test_a_configured_store_that_raises_blocks_the_turn_instead_of_answering_unconstrained(self, chart):
        calls: list = []
        store = _failing_store(calls=calls)
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        assert outcome.prepared is None
        assert outcome.terminal_envelope["type"] == "context_unavailable"
        assert outcome.terminal_envelope["domain"] == "career"
        assert outcome.terminal_envelope["retryable"] is True
        assert len(calls) == 1

    def test_no_fact_values_leak_into_the_terminal_envelope(self, chart):
        store = _failing_store()
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, profile_context_store=store)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        assert "facts" not in outcome.terminal_envelope
        assert "retired" not in str(outcome.terminal_envelope)

    def test_no_store_at_all_is_unaffected_and_still_answers(self, chart):
        # The additive/off case (tests, or any caller that never configured
        # a ledger) must not be swept into the new failure path.
        orchestrator = AskOrchestrator(chart_loader=lambda: chart)
        outcome = orchestrator.prepare("When will my career begin?", domain_override="career")
        assert outcome.terminal_envelope is None
        assert outcome.prepared is not None


class TestContextUnavailableAtTheRoutes:
    """The orchestrator-level tests above prove `prepare()` returns the
    right terminal envelope; these prove the two Ask routes actually handle
    that new envelope type end-to-end (real DB, real routing) rather than
    hitting the unhandled-terminal-state fallback added alongside it in
    ask_routes.py/ask_stream_routes.py. `build_profile_context_projection`
    is patched at its `astrospace.api.ask_routes` import site — the same
    name `_profile_context_store`'s closure resolves in both route
    modules, since `ask_stream_routes.py` imports that closure builder
    from `ask_routes.py` rather than duplicating it."""

    def test_non_streaming_route_returns_context_unavailable_without_a_500(self, db_env):
        with patch("astrospace.api.ask_routes.build_profile_context_projection",
                   side_effect=RuntimeError("ledger query failed")):
            response = db_env["client"].post(
                f"/api/v1/ask/{db_env['mine']}",
                json={"question": "How is my career progressing this year?"},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "context_unavailable"
        assert "retired" not in body["answer"].lower()

    def test_streaming_route_returns_context_unavailable_without_a_500(self, db_env):
        with patch("astrospace.api.ask_routes.build_profile_context_projection",
                   side_effect=RuntimeError("ledger query failed")):
            response = db_env["client"].post(
                f"/api/v1/ask/{db_env['mine']}/stream",
                json={"question": "How is my career progressing this year?",
                     "domain_override": "career"},
            )
        assert response.status_code == 200
        frames = [
            json.loads(line[len("data: "):])
            for line in response.text.splitlines() if line.startswith("data: ")
        ]
        assert any(frame.get("type") == "context_unavailable" for frame in frames)
