"""The consultation validation loop, end to end — wealth domain.

The property this file exists to protect is an ORDER, not a feature. A
validation loop that asks before it commits is a cold-reading machine: the
reader discloses, the agent reflects the disclosure back as insight, and
nothing has been tested. Reversed — commit a falsifiable claim, then ask —
the same conversation produces an honest measurement.

That order is easy to break by accident and impossible to detect afterwards
from the data alone (a row with a claim and an answer looks identical either
way), so it is pinned here from several directions at once: the store cannot
revise a claim, the envelope cannot leak it to the reader before they answer,
and the probe is committed before the question is ever emitted.

The bundle is deterministic and pinned; the model's wording is not and never
is — every model call here is stubbed.
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
from astrospace.agents.orchestrator import AskOrchestrator, ValidationStore
from astrospace.agents.schema import Guidance, StructuredReading, TechnicalBasisItem
from astrospace.agents.validation_agent import (
    ValidationAgent, ValidationOption, ValidationProbeDraft, probe_violations,
)
from astrospace.api.auth import AuthUser, current_user
from astrospace.context import assemble_domain
from astrospace.context.validation import (
    life_context_section, score_answer, validation_slots,
)
from astrospace.core.vedic.chart import VedicChart
from astrospace.db import crud, crud_mobile as cm, get_db
from astrospace.db.database import Base
from astrospace.db.models import ValidationProbe

ME = "test-user-validation-loop"


@pytest.fixture(scope="module")
def chart():
    return VedicChart("Test Person", 1993, 7, 20, 11, 28, "Rajahmundry", "IN")


@pytest.fixture(scope="module")
def wealth_bundle(chart):
    return assemble_domain(chart, "wealth")


def _draft(slot, **overrides) -> ValidationProbeDraft:
    """A well-formed probe for whatever slot the engine picked — built from the
    slot rather than hard-coded, so these tests don't silently start passing
    against a stale candidate vocabulary."""
    substantive = [c["key"] for c in slot["candidates"] if c["key"] not in ("neither", "skip")]
    base = dict(
        committed_claim="Between 2021 and now the money mostly went into property, not savings.",
        committed_candidate=substantive[0],
        confidence=0.6,
        question="Since 2021, has more of your money gone into land or property than into savings?",
        options=[ValidationOption(key=c["key"], label=c["key"].replace("_", " "))
                 for c in slot["candidates"]],
    )
    base.update(overrides)
    return ValidationProbeDraft(**base)


# ── The timeline ──────────────────────────────────────────────────────────────

class TestTimeline:
    """Four overlapping dated windows in three differently-shaped sections is
    what this replaces. The value is that it is scannable, so the tests are
    about sortedness, status and completeness rather than any single date."""

    def test_entries_are_sorted_and_dated(self, wealth_bundle):
        timeline = wealth_bundle["timeline"]
        assert timeline["available"] is True
        starts = [row["start"] for row in timeline["entries"]]
        assert starts == sorted(starts)
        for row in timeline["entries"]:
            assert row["status"] in ("past", "current", "upcoming")
            assert row["kind"] in ("mahadasha", "antardasha", "gochara")

    def test_every_boundary_carries_an_age(self, wealth_bundle):
        """People remember their lives by age — a boundary without one is not
        checkable in the way this whole loop depends on."""
        for row in wealth_bundle["timeline"]["entries"]:
            if row["kind"] == "gochara" and row["start"] == "None":
                continue  # an active transit whose boundary walk found no date
            assert row["age_at_start"] is not None
            assert row["age_at_end"] is not None

    def test_exactly_one_current_mahadasha(self, wealth_bundle):
        current = [row for row in wealth_bundle["timeline"]["entries"]
                   if row["kind"] == "mahadasha" and row["status"] == "current"]
        assert len(current) == 1

    def test_next_transition_is_the_earliest_end_among_current_periods(self, wealth_bundle):
        timeline = wealth_bundle["timeline"]
        running = [row["end"] for row in timeline["entries"]
                   if row["status"] == "current" and row["end"] != "None"]
        assert timeline["next_transition"]["on"] == min(running)

    def test_domain_relevance_is_marked(self, wealth_bundle):
        """Which periods speak to money, versus which are simply the calendar
        the reader happens to be living in."""
        lords = {row["lord"] for row in wealth_bundle["timeline"]["entries"]
                 if row["domain_relevant"]}
        wealth_lords = {row["lord"] for row in wealth_bundle["houses"]}
        assert lords & wealth_lords

    def test_timeline_agrees_with_retrospect(self, wealth_bundle):
        """Same boundaries, two shapes — if these ever disagree, one of them is
        narrating a period the reader is not actually in."""
        retrospect = wealth_bundle["retrospect"]["current_chapter"]
        current = next(row for row in wealth_bundle["timeline"]["entries"]
                       if row["kind"] == "mahadasha" and row["status"] == "current")
        assert current["lord"] == retrospect["lord"]
        assert current["start"] == retrospect["start"]


# ── Slot selection ────────────────────────────────────────────────────────────

class TestSlotSelection:
    def test_wealth_produces_slots(self, wealth_bundle):
        assert validation_slots(wealth_bundle)

    def test_other_domains_produce_none(self, chart):
        """Wealth first, deliberately — hit rate has to be visible on one real
        domain before this generalises. Other domains return nothing rather
        than guessing at an ambiguity their generators were never written for."""
        for domain in ("career", "marriage", "health"):
            assert validation_slots(assemble_domain(chart, domain)) == []

    def test_every_slot_offers_at_least_two_substantive_readings(self, wealth_bundle):
        """A slot with one defensible reading is not ambiguity — it is the
        chart speaking clearly, and asking about it wastes the reader's
        patience for nothing."""
        for slot in validation_slots(wealth_bundle, limit=10):
            substantive = [c for c in slot["candidates"]
                           if c["key"] not in ("neither", "skip")]
            assert len(substantive) >= 2, slot["slot_id"]

    def test_every_slot_can_come_back_negative(self, wealth_bundle):
        """Without 'neither' the reader is forced into one of the chart's own
        guesses and the hit rate is inflated by construction. A probe that
        cannot fail is not a test."""
        for slot in validation_slots(wealth_bundle, limit=10):
            keys = {c["key"] for c in slot["candidates"]}
            assert "neither" in keys and "skip" in keys

    def test_every_slot_is_anchored_to_a_dated_window(self, wealth_bundle):
        for slot in validation_slots(wealth_bundle, limit=10):
            anchor = slot["anchor"]
            assert anchor["start"] and anchor["end"] and anchor["label"]
            assert anchor["status"] != "upcoming"

    def test_no_slot_asks_about_years_that_have_not_happened(self, wealth_bundle):
        """Found by reading the assembled prompt, not the code: a mahadasha the
        reader is currently in runs years into the future, so an anchor taken
        straight off the timeline produced "between 2021 and 2041, did your
        money mostly come through X" — fifteen years of which had not happened.
        A running window is truncated at today and flagged `in_progress`."""
        today = str(wealth_bundle["timeline"]["as_of"])[:10]
        for slot in validation_slots(wealth_bundle, limit=10):
            anchor = slot["anchor"]
            assert anchor["end"] <= today, slot["slot_id"]
            assert anchor["age_at_end"] <= wealth_bundle["profile_facts"]["age_years"]
            if anchor["in_progress"]:
                assert anchor["end"] == today
                assert anchor["period_end"] > today

    def test_exclude_is_the_asked_once_rule(self, wealth_bundle):
        first = validation_slots(wealth_bundle, limit=1)[0]
        again = validation_slots(wealth_bundle, limit=1, exclude={first["slot_id"]})
        assert not again or again[0]["slot_id"] != first["slot_id"]

    def test_selection_is_deterministic(self, wealth_bundle):
        assert (validation_slots(wealth_bundle, limit=3)
                == validation_slots(wealth_bundle, limit=3))

    def test_a_child_chart_is_never_probed(self):
        """A reader cannot validate years they spent as a small child, and a
        mahadasha can easily run twenty years — this chart's did, from age 2 to
        age 22, and the picker offered it as an anchor until the age floor
        existed."""
        young = VedicChart("Young", 2016, 5, 2, 9, 0, "Chennai", "IN")
        assert validation_slots(assemble_domain(young, "wealth")) == []

    def test_house_numbers_are_written_correctly(self):
        """The slot's `ambiguity` text reaches the model, and a bundle that
        says "2th lord" invites an answer that repeats it. The teens are the
        case worth pinning: 11/12/13 take "th" despite ending in 1/2/3, which
        is what a naive suffix lookup gets wrong."""
        from astrospace.context.validation import _ord
        assert [_ord(h) for h in range(1, 13)] == [
            "1st", "2nd", "3rd", "4th", "5th", "6th",
            "7th", "8th", "9th", "10th", "11th", "12th",
        ]


# ── Scoring and life context ──────────────────────────────────────────────────

class TestScoring:
    @pytest.mark.parametrize("claim,answer,expected", [
        ("h2_ruled", "h2_ruled", "confirmed"),
        ("h2_ruled", "h9_ruled", "missed"),
        ("h2_ruled", "neither", "missed"),
        ("gain_dominant", "both", "partial"),
        ("h2_ruled", "skip", "skipped"),
        ("h2_ruled", None, "skipped"),
    ])
    def test_score_answer(self, claim, answer, expected):
        assert score_answer(claim, answer) == expected

    def test_a_decline_is_never_evidence(self):
        """A reader who declines has told us nothing about their chart, so a
        skip must not move the hit rate in either direction."""
        section = life_context_section([
            {"status": "confirmed", "slot_id": "a"},
            {"status": "skipped", "slot_id": "b"},
        ])
        assert section["calibration"]["scored"] == 1
        assert section["calibration"]["hit_rate"] == 1.0
        assert section["calibration"]["skipped"] == 1

    def test_hit_rate_counts_a_partial_as_half(self):
        section = life_context_section([
            {"status": "confirmed", "slot_id": "a"},
            {"status": "partial", "slot_id": "b"},
            {"status": "missed", "slot_id": "c"},
            {"status": "missed", "slot_id": "d"},
        ])
        assert section["calibration"]["hit_rate"] == 0.38

    def test_unanswered_probes_are_not_life_context(self):
        """An outstanding commitment is not a fact about the reader's life.
        Leaking one into the bundle would hand the model its own unresolved
        prediction to narrate as though it were established."""
        section = life_context_section([{"status": "committed", "slot_id": "a"}])
        assert section["available"] is False
        assert section["reported"] == []

    def test_bundle_carries_an_empty_life_context_by_default(self, wealth_bundle):
        assert wealth_bundle["life_context"]["available"] is False


# ── The probe draft's own guardrails ──────────────────────────────────────────

class TestProbeViolations:
    @pytest.fixture
    def slot(self, wealth_bundle):
        return validation_slots(wealth_bundle, limit=1)[0]

    def test_a_well_formed_draft_passes(self, slot):
        assert probe_violations(_draft(slot), slot) == []

    @pytest.mark.parametrize("bad_candidate", ["neither", "skip"])
    def test_the_chart_may_not_commit_to_a_null_result(self, slot, bad_candidate):
        """'neither' and 'skip' are legitimate ANSWERS but neither is a claim
        about the chart. A probe predicting "neither of my own readings" tests
        nothing and would score as a free hit whenever the reader agreed."""
        draft = _draft(slot, committed_candidate=bad_candidate)
        assert probe_violations(draft, slot)

    def test_invented_option_keys_are_rejected(self, slot):
        draft = _draft(slot, options=[ValidationOption(key="made_up", label="x")])
        assert probe_violations(draft, slot)

    def test_dropping_a_substantive_option_is_rejected(self, slot):
        """The reader must be able to pick every reading the chart is choosing
        between — an option list missing one of them rigs the answer."""
        draft = _draft(slot, options=[
            ValidationOption(key=c["key"], label=c["key"])
            for c in slot["candidates"] if c["key"] != slot["candidates"][0]["key"]
        ])
        assert probe_violations(draft, slot)

    def test_a_question_that_telegraphs_the_claim_is_rejected(self, slot):
        claim = "Your money went into property between 2021 and 2024."
        draft = _draft(slot, committed_claim=claim,
                       question=f"Is this right: {claim}")
        assert probe_violations(draft, slot)


# ── The store: commit before ask, and no revision after ───────────────────────

class TestProbeStore:
    @pytest.fixture
    def db(self):
        engine = create_engine("sqlite:///:memory:",
                               connect_args={"check_same_thread": False},
                               poolclass=StaticPool)
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        crud.create_kundli(session, {
            "id": "k-probe", "user_id": ME, "name": "Probe", "relation": "self",
            "birth_year": 1993, "birth_month": 7, "birth_day": 20,
            "birth_hour": 11, "birth_minute": 28,
            "birth_city": "Rajahmundry", "birth_nation": "IN",
        })
        yield session
        session.close()

    @pytest.fixture
    def slot(self, wealth_bundle):
        slot = validation_slots(wealth_bundle, limit=1)[0]
        slot.setdefault("domain", "wealth")
        return slot

    def _commit(self, db, slot, **overrides):
        draft = _draft(slot, **overrides)
        return cm.commit_validation_probe(
            db, ME, "k-probe", "wealth", slot,
            claim_text=draft.committed_claim,
            claim_candidate=draft.committed_candidate,
            confidence=draft.confidence,
            question=draft.question,
            options=[o.model_dump() for o in draft.options],
        )

    def test_a_fresh_probe_is_a_prediction_with_no_answer(self, db, slot):
        probe = self._commit(db, slot)
        assert probe.status == "committed"
        assert probe.claim_text and probe.confidence is not None
        assert probe.committed_at is not None
        assert probe.answered_at is None and probe.answer_key is None

    def test_answering_scores_the_commitment(self, db, slot):
        probe = self._commit(db, slot)
        answered = cm.record_validation_answer(db, probe.id, ME, probe.claim_candidate)
        assert answered.status == "confirmed"
        assert answered.answered_at > answered.committed_at or \
               answered.answered_at >= answered.committed_at

    def test_the_claim_survives_the_answer_unchanged(self, db, slot):
        """The reason a hit rate over this table means anything: no code path
        can revise a prediction once its answer is in."""
        probe = self._commit(db, slot)
        before = (probe.claim_text, probe.claim_candidate, probe.confidence,
                  probe.committed_at)
        cm.record_validation_answer(db, probe.id, ME, "neither", "not really")
        after = db.get(ValidationProbe, probe.id)
        assert (after.claim_text, after.claim_candidate, after.confidence,
                after.committed_at) == before
        assert after.status == "missed"

    def test_a_probe_is_one_test_only(self, db, slot):
        probe = self._commit(db, slot)
        assert cm.record_validation_answer(db, probe.id, ME, "neither") is not None
        assert cm.record_validation_answer(db, probe.id, ME, probe.claim_candidate) is None

    def test_another_user_cannot_answer_this_probe(self, db, slot):
        probe = self._commit(db, slot)
        assert cm.record_validation_answer(db, probe.id, "someone-else", "neither") is None

    def test_the_same_slot_is_never_asked_twice(self, db, slot):
        """Question fatigue is the main way this loop stops being worth
        answering, so 'asked once' is a database constraint rather than a
        caller's good intentions."""
        self._commit(db, slot)
        with pytest.raises(Exception):
            self._commit(db, slot)
        db.rollback()


# ── The orchestrator turn ─────────────────────────────────────────────────────

class TestValidationTurn:
    @pytest.fixture
    def orchestrator_and_log(self, chart):
        committed = []

        def commit(slot, draft):
            committed.append((slot, draft))
            return f"probe-{len(committed)}"

        store = ValidationStore(probes=lambda: [], commit=commit)
        return AskOrchestrator(chart_loader=lambda: chart,
                               validation_store=store), committed

    def test_off_by_default(self, chart):
        """Without a store, and without the flag, this is the pipeline exactly
        as it was before the loop existed."""
        plain = AskOrchestrator(chart_loader=lambda: chart)
        outcome = plain.prepare("When will my financial situation improve?")
        assert outcome.prepared is not None
        assert outcome.terminal_envelope is None

    def test_flag_off_never_commits(self, orchestrator_and_log):
        orchestrator, committed = orchestrator_and_log
        with patch.object(ValidationAgent, "run_probe") as run:
            outcome = orchestrator.prepare("When will my financial situation improve?")
        run.assert_not_called()
        assert committed == []
        assert outcome.prepared is not None

    def test_the_turn_asks_instead_of_answering(self, orchestrator_and_log):
        orchestrator, committed = orchestrator_and_log
        envelope = self._run(orchestrator)
        assert envelope["type"] == "validation_needed"
        assert envelope["domain"] == "wealth"
        assert envelope["question"]
        assert envelope["skippable"] is True
        assert len(committed) == 1

    def test_the_reader_never_sees_the_claim_before_answering(self, orchestrator_and_log):
        """Showing a reader what the chart expects tells them what to say, and
        the answer is then worth nothing. The claim goes to the database; the
        question goes to the reader."""
        orchestrator, committed = orchestrator_and_log
        envelope = self._run(orchestrator)
        claim = committed[0][1].committed_claim
        assert claim
        assert "committed_claim" not in envelope
        assert "confidence" not in envelope
        assert claim not in json_dump(envelope)

    def test_the_commitment_is_stored_before_the_question_is_returned(self, orchestrator_and_log):
        """The ordering, asserted directly: by the time an envelope exists, the
        claim is already committed."""
        orchestrator, committed = orchestrator_and_log
        envelope = self._run(orchestrator)
        assert committed, "commit() must have run before prepare() returned"
        assert envelope["probe_id"] == "probe-1"

    def test_the_options_are_the_engine_s_candidates(self, orchestrator_and_log):
        orchestrator, committed = orchestrator_and_log
        envelope = self._run(orchestrator)
        slot = committed[0][0]
        assert ({option["key"] for option in envelope["options"]}
                == {candidate["key"] for candidate in slot["candidates"]})

    def test_an_already_asked_slot_is_not_asked_again(self, chart, wealth_bundle):
        every_slot = [s["slot_id"] for s in validation_slots(wealth_bundle, limit=50)]
        store = ValidationStore(
            probes=lambda: [{"slot_id": slot_id, "status": "confirmed"}
                            for slot_id in every_slot],
            commit=lambda slot, draft: "never",
        )
        orchestrator = AskOrchestrator(chart_loader=lambda: chart, validation_store=store)
        outcome = orchestrator.prepare("When will my financial situation improve?",
                                       validate_first=True)
        assert outcome.prepared is not None

    def test_a_broken_probe_never_costs_the_reader_their_answer(self, orchestrator_and_log):
        """Failing open is deliberate at every step: the probe is a bonus, the
        reading is the product."""
        orchestrator, committed = orchestrator_and_log
        with patch.object(ValidationAgent, "run_probe", side_effect=RuntimeError("boom")):
            outcome = orchestrator.prepare("When will my financial situation improve?",
                                           validate_first=True)
        assert outcome.prepared is not None
        assert committed == []

    def test_an_invalid_draft_is_dropped_rather_than_asked(self, orchestrator_and_log):
        orchestrator, committed = orchestrator_and_log

        def bad_draft(bundle_slot=None):
            return ValidationProbeDraft(
                committed_claim="something", committed_candidate="skip",
                confidence=0.5, question="?",
                options=[ValidationOption(key="skip", label="skip")],
            )

        with patch.object(ValidationAgent, "run_probe", side_effect=bad_draft):
            outcome = orchestrator.prepare("When will my financial situation improve?",
                                           validate_first=True)
        assert outcome.prepared is not None
        assert committed == []

    def test_non_wealth_domains_are_unaffected(self, orchestrator_and_log):
        orchestrator, committed = orchestrator_and_log
        with patch.object(ValidationAgent, "run_probe") as run:
            outcome = orchestrator.prepare("Is this a good year for a promotion at work?",
                                           validate_first=True)
        run.assert_not_called()
        assert outcome.prepared.domain == "career"
        assert committed == []

    @staticmethod
    def _run(orchestrator) -> dict:
        """Drive one validation turn with a draft built from whichever slot the
        engine actually picked."""
        captured = {}
        real_init = ValidationAgent.__init__

        def capture_init(self, bundle, slot, api_key=None):
            captured["slot"] = slot
            real_init(self, bundle, slot, api_key)

        with patch.object(ValidationAgent, "__init__", capture_init), \
             patch.object(ValidationAgent, "run_probe",
                          new=lambda self: _draft(captured["slot"])):
            outcome = orchestrator.prepare("When will my financial situation improve?",
                                           validate_first=True)
        return outcome.terminal_envelope


def json_dump(payload) -> str:
    return json.dumps(payload, default=str)


# ── The route ─────────────────────────────────────────────────────────────────

class TestValidationRoute:
    @pytest.fixture(scope="class")
    def env(self):
        engine = create_engine("sqlite:///:memory:",
                               connect_args={"check_same_thread": False},
                               poolclass=StaticPool)
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
            "user_id": ME, "name": "Probed", "relation": "self",
            "birth_year": 1993, "birth_month": 7, "birth_day": 20,
            "birth_hour": 11, "birth_minute": 28,
            "birth_city": "Rajahmundry", "birth_nation": "IN",
        }).id
        db.close()
        try:
            yield {"client": TestClient(app), "kundli": kundli_id, "Session": Session}
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(current_user, None)

    @staticmethod
    def _frames(response) -> list[dict]:
        return [json.loads(line[len("data: "):])
                for line in response.text.splitlines() if line.startswith("data: ")]

    @staticmethod
    def _ask(client, kundli, question, **body):
        captured = {}
        real_init = ValidationAgent.__init__

        def capture_init(self, bundle, slot, api_key=None):
            captured["slot"] = slot
            real_init(self, bundle, slot, api_key)

        with patch.object(ValidationAgent, "__init__", capture_init), \
             patch.object(ValidationAgent, "run_probe",
                          new=lambda self: _draft(captured["slot"])), \
             patch.object(DomainReadingAgent, "run_structured_reading",
                          return_value=StructuredReading(
                              acknowledgment="You asked about money.",
                              technical_basis=[TechnicalBasisItem(
                                  factor="2nd lord", reading="well placed", source="houses")],
                              interpretation="A steady stretch for savings.",
                              summary_and_assurance="A window, not a verdict.",
                              guidance=Guidance(), confidence="medium")):
            return client.post(f"/api/v1/ask/{kundli}/stream",
                               json={"question": question, **body})

    def test_wealth_is_unchanged_unless_the_flag_is_set(self, env):
        """The loop ships off. A `validation_needed` envelope no client can
        render is a wealth question that silently returns nothing."""
        r = self._ask(env["client"], env["kundli"], "When will my financial situation improve?")
        done = self._frames(r)[-1]
        assert done["type"] == "done" and done["status"] == "answered"

    def test_the_flag_turns_the_turn_on(self, env):
        r = self._ask(env["client"], env["kundli"],
                      "When will my financial situation improve?", validate_first=True)
        frame = self._frames(r)[0]
        assert frame["type"] == "validation_needed"
        assert frame["probe_id"] and frame["question"] and frame["options"]

    def test_answering_scores_the_claim_and_reveals_it(self, env):
        client = env["client"]
        r = self._ask(client, env["kundli"], "How are my savings looking this year?",
                      validate_first=True)
        frame = self._frames(r)[0]
        assert frame["type"] == "validation_needed"

        answer = client.post(f"/api/v1/ask/validation/{frame['probe_id']}/answer",
                             json={"answer_key": "neither", "answer_text": "not really"})
        assert answer.status_code == 200
        body = answer.json()
        assert body["status"] == "missed"
        # Only now — the reader has committed their own answer, so showing them
        # the prediction can no longer influence it.
        assert body["committed_claim"]
        assert body["confidence"] is not None

        # And a second answer is refused rather than overwriting the first.
        again = client.post(f"/api/v1/ask/validation/{frame['probe_id']}/answer",
                            json={"answer_key": "skip"})
        assert again.status_code == 404

    def test_an_answered_probe_becomes_life_context(self, env):
        """The payoff: what the reader reported reaches the next reading as
        context the chart could not have supplied."""
        session = env["Session"]()
        probes = cm.list_validation_probes(session, ME, env["kundli"], answered_only=True)
        assert probes, "the previous test should have left an answered probe"
        section = life_context_section([{
            "status": p.status, "slot_id": p.slot_id, "slot_kind": p.slot_kind,
            "question": p.question, "answer_key": p.answer_key,
            "answer_text": p.answer_text, "anchor_label": p.anchor_label,
            "anchor_start": p.anchor_start, "anchor_end": p.anchor_end,
        } for p in probes])
        session.close()
        assert section["available"] is True
        assert section["reported"][0]["answer"] == "neither"
        assert section["calibration"]["scored"] >= 1

    def test_an_unknown_probe_is_a_404(self, env):
        r = env["client"].post("/api/v1/ask/validation/does-not-exist/answer",
                               json={"answer_key": "skip"})
        assert r.status_code == 404
