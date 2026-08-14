"""Account deletion is confirmed server-side and scoped to the caller."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import (
    Kundli, ProfileContextAuditEvent, ProfileContextFact,
    ProfileContextLedger, ProfileContextMutation, UserProfile,
)


@pytest.fixture()
def deletion_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    user_id = "delete-me"
    other_id = "keep-me"
    db = session_factory()
    db.add_all([
        UserProfile(user_id=user_id, display_name="Delete Me"),
        UserProfile(user_id=other_id, display_name="Keep Me"),
    ])
    db.commit()
    for owner, name in ((user_id, "Mine"), (other_id, "Theirs")):
        crud.create_kundli(db, {
            "user_id": owner,
            "name": name,
            "relation": "self",
            "birth_year": 1991,
            "birth_month": 8,
            "birth_day": 14,
            "birth_hour": 6,
            "birth_minute": 12,
            "birth_city": "Vijayawada",
            "birth_nation": "IN",
        })
    db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(
        id=user_id, email="delete@example.com", role="dev",
    )
    try:
        yield TestClient(app), session_factory, user_id, other_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def test_rejects_missing_typed_confirmation(deletion_client):
    client, session_factory, user_id, _ = deletion_client
    response = client.request(
        "DELETE", "/api/v1/me", json={"confirmation": "not delete"},
    )
    assert response.status_code == 400
    with session_factory() as db:
        assert db.get(UserProfile, user_id) is not None


def test_deletes_only_the_authenticated_user(deletion_client):
    client, session_factory, user_id, other_id = deletion_client
    with session_factory() as db:
        profile_id = db.query(Kundli).filter(Kundli.user_id == user_id).one().id
        db.add(ProfileContextLedger(profile_id=profile_id, user_id=user_id, revision=1))
        fact = ProfileContextFact(
            user_id=user_id, profile_id=profile_id, category="life_stage",
            key="employment_status", value={"code": "retired"}, status="active",
            confidence="confirmed", sensitivity="personal", retention="until_removed",
            source={"kind": "profile_form"}, consent={"state": "granted"}, revision=1,
        )
        db.add(fact)
        db.flush()
        db.add(ProfileContextMutation(
            user_id=user_id, profile_id=profile_id, idempotency_key="account-delete-test",
            request_hash="hash", action="created", fact_id=fact.id,
            resulting_revision=1, response={"revision": 1, "fact_id": fact.id},
        ))
        db.add(ProfileContextAuditEvent(
            user_id=user_id, profile_id=profile_id, fact_id=fact.id,
            action="created", category="life_stage", key="employment_status", revision=1,
        ))
        db.commit()
    response = client.request(
        "DELETE", "/api/v1/me", json={"confirmation": "DELETE"},
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    with session_factory() as db:
        assert db.get(UserProfile, user_id) is None
        assert db.query(Kundli).filter(Kundli.user_id == user_id).count() == 0
        assert db.get(UserProfile, other_id) is not None
        assert db.query(Kundli).filter(Kundli.user_id == other_id).count() == 1
        assert db.query(ProfileContextFact).filter_by(user_id=user_id).count() == 0
        assert db.query(ProfileContextMutation).filter_by(user_id=user_id).count() == 0
        assert db.query(ProfileContextAuditEvent).filter_by(user_id=user_id).count() == 0
