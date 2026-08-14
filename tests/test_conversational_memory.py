from astrospace.context.conversational_memory import extract_memory_candidates
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from astrospace.api.ask_stream_routes import _memory_events
from astrospace.db import crud
from astrospace.db.database import Base
from astrospace.db.models import ProfileContextFact


def _one(text: str):
    candidates = extract_memory_candidates(text)
    assert len(candidates) == 1
    return candidates[0]


def test_extracts_clear_first_person_low_risk_assertion():
    candidate = _one("I am retired now.")
    assert candidate.key == "employment_status"
    assert candidate.value == {"code": "retired"}
    assert candidate.requires_confirmation is False


def test_extracts_assertion_when_question_follows_without_inference():
    candidate = _one("I am retired. What does my next dasha mean?")
    assert candidate.value == {"code": "retired"}


def test_rejects_questions_and_third_party_statements():
    assert extract_memory_candidates("Will I retire next year?") == []
    assert extract_memory_candidates("My mother is retired. What comes next for her?") == []


def test_rejects_hypothetical_and_conditional_framing():
    """Reproduced in PR #66 review: `_QUESTION_OPEN` only anchors at the
    start of the message, so a hypothetical marker placed mid-sentence
    ("Suppose ...", "What happens if ...") slipped past it and the
    embedded "I am retired"/"I am married" assertion got extracted as if
    the reader had actually stated it — in automatic mode this would have
    silently written a wrong fact to the active profile."""
    assert extract_memory_candidates("What happens if I am married?") == []
    assert extract_memory_candidates("Suppose I am retired, what would the chart say?") == []
    assert extract_memory_candidates("Imagine I am unemployed — how would that change things?") == []
    assert extract_memory_candidates("Let's say I am a student, does that matter here?") == []


def test_rejects_reported_and_quoted_speech():
    """Reproduced in PR #66 review: "My mother said 'I am retired now.'" is
    the mother's own quoted statement, not the reader's — `_THIRD_PERSON`
    alone missed it because a reporting verb ("said") sits between the
    third-person subject and the assertion, not is/am/are/has/have/works."""
    assert extract_memory_candidates("My mother said 'I am retired now.'") == []
    assert extract_memory_candidates('My friend told me "I am married" last week.') == []
    # A subject `_THIRD_PERSON` doesn't cover at all (not mother/father/
    # wife/husband/partner/son/daughter/child/he/she/they) reporting
    # someone else's claim about the reader — without the reporting-verb
    # guard this would be a bare, unqualified "I am retired" match.
    assert extract_memory_candidates("The astrologer said I am retired, is that accurate?") == []


def test_sensitive_relationship_and_children_always_require_confirmation():
    marriage = _one("I am married.")
    children = _one("I have two children.")
    assert marriage.requires_confirmation is True
    assert children.requires_confirmation is True


def test_occupation_is_bounded_and_does_not_duplicate_life_status():
    teacher = _one("I work as a teacher but I am considering a change.")
    assert teacher.key == "occupation"
    assert teacher.value == {"text": "teacher"}
    student = _one("I am a student.")
    assert student.key == "employment_status"


def _memory_db(mode="ask", enabled=True):
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    profile = crud.create_kundli(db, {
        "user_id": "reader", "name": "Reader", "relation": "self",
        "birth_year": 1980, "birth_month": 1, "birth_day": 1,
        "birth_hour": 8, "birth_minute": 0, "birth_city": "Chennai",
        "birth_nation": "IN",
    })
    crud.upsert_user_settings(db, "reader", {
        "memory_enabled": enabled, "memory_mode": mode,
    })
    return db, profile.id


def test_ask_mode_emits_candidate_without_writing():
    db, profile_id = _memory_db("ask")
    events = list(_memory_events(db, "reader", profile_id, "I am retired."))
    assert events[0]["type"] == "memory_candidate"
    assert events[0]["candidate"]["key"] == "employment_status"
    assert db.query(ProfileContextFact).count() == 0


def test_automatic_mode_writes_low_risk_but_not_sensitive_memory():
    db, profile_id = _memory_db("automatic")
    saved = list(_memory_events(db, "reader", profile_id, "I am retired."))
    assert saved[0]["type"] == "memory_saved"
    sensitive = list(_memory_events(db, "reader", profile_id, "I am married."))
    assert sensitive[0]["type"] == "memory_candidate"
    assert sensitive[0]["candidate"]["requires_confirmation"] is True


def test_disabled_and_duplicate_memory_emit_nothing():
    db, profile_id = _memory_db("automatic", enabled=False)
    assert list(_memory_events(db, "reader", profile_id, "I am retired.")) == []

    db2, profile_id2 = _memory_db("automatic")
    assert list(_memory_events(db2, "reader", profile_id2, "I am retired."))[0]["type"] == "memory_saved"
    assert list(_memory_events(db2, "reader", profile_id2, "I am retired.")) == []


def test_automatic_update_supersedes_instead_of_creating_a_contradiction():
    db, profile_id = _memory_db("automatic")
    assert list(_memory_events(db, "reader", profile_id, "I am a student."))[0]["type"] == "memory_saved"
    assert list(_memory_events(db, "reader", profile_id, "I am retired."))[0]["type"] == "memory_saved"
    active = db.query(ProfileContextFact).filter_by(profile_id=profile_id, status="active").all()
    superseded = db.query(ProfileContextFact).filter_by(profile_id=profile_id, status="superseded").all()
    assert [fact.value for fact in active] == [{"code": "retired"}]
    assert [fact.value for fact in superseded] == [{"code": "student"}]


def test_automatic_supersede_event_carries_supersedes_id_for_undo():
    """The Ask UI's Undo action (PR #66 review) branches on
    `fact.supersedes_id` to decide plain delete vs. undo-supersede — this
    pins that the SSE `memory_saved` event actually carries it, not just
    that the DB row does."""
    db, profile_id = _memory_db("automatic")
    first = list(_memory_events(db, "reader", profile_id, "I am a student."))[0]
    assert first["fact"]["supersedes_id"] is None
    second = list(_memory_events(db, "reader", profile_id, "I am retired."))[0]
    assert second["fact"]["supersedes_id"] == first["fact"]["id"]
