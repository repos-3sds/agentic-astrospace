"""One self profile per account (flow audit 2026-10-15, item 4.3)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from main import app

ME = "self-once"


@pytest.fixture()
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@example.com", role="dev")
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _body(name, relation):
    return {
        "name": name, "relation": relation, "birth_year": 1991, "birth_month": 8, "birth_day": 14,
        "birth_hour": 6, "birth_minute": 12, "birth_city": "Vijayawada", "birth_nation": "IN",
    }


def test_second_self_profile_is_refused_with_a_sentence(client):
    api, _ = client
    assert api.post("/api/v1/kundlis", json=_body("Me", "self")).status_code == 201
    second = api.post("/api/v1/kundlis", json=_body("Me again", "Self"))
    assert second.status_code == 409
    assert "yourself" in second.json()["detail"]
    assert api.post("/api/v1/kundlis", json=_body("Partner", "partner")).status_code == 201
    assert [k["relation"] for k in api.get("/api/v1/kundlis").json()] == ["self", "partner"]


def test_another_account_s_self_profile_does_not_count(client):
    api, factory = client
    with factory() as db:
        crud.create_kundli(db, {"user_id": "someone-else", **_body("Them", "self")})
    assert api.post("/api/v1/kundlis", json=_body("Me", "self")).status_code == 201
