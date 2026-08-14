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
