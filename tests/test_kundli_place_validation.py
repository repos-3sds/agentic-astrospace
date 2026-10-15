"""Unresolvable birth places are refused at the door (flow audit 2026-10-15, item 4.1).

A saved profile whose city the engines cannot resolve turned Today, Explore
and every chart screen into the same raw error, with no way out but
deleting it. The kundli API now checks the offline city table before saving.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from main import app

ME = "place-check"


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


def _body(city, nation="IN", relation="prospect"):
    return {
        "name": "Nisha", "relation": relation, "birth_year": 1994, "birth_month": 11, "birth_day": 22,
        "birth_hour": 10, "birth_minute": 15, "birth_city": city, "birth_nation": nation,
    }


def test_a_misspelt_city_is_refused_with_a_sentence_and_nothing_is_saved(client):
    api, _ = client
    res = api.post("/api/v1/kundlis", json=_body("Mumbaii"))
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "Mumbaii" in detail and "search results" in detail
    assert api.get("/api/v1/kundlis").json() == []


def test_a_known_city_is_accepted_whatever_its_case(client):
    api, _ = client
    assert api.post("/api/v1/kundlis", json=_body("mumbai", "in")).status_code == 201


def test_update_checks_the_place_only_when_it_changes(client):
    api, factory = client
    with factory() as db:
        legacy = crud.create_kundli(db, {"user_id": ME, **_body("Nowhereville-xyz", "ZZ")}).id
    # A rename of a profile saved before the check leaves its place alone.
    assert api.patch(f"/api/v1/kundlis/{legacy}", json={"name": "Renamed"}).status_code == 200
    # Changing the place to something the engines cannot find is refused.
    bad = api.patch(f"/api/v1/kundlis/{legacy}", json={"birth_city": "Atlantis"})
    assert bad.status_code == 422
    assert "Atlantis" in bad.json()["detail"]
    # And fixing it is how the profile recovers.
    good = api.patch(f"/api/v1/kundlis/{legacy}", json={"birth_city": "Chennai", "birth_nation": "IN"})
    assert good.status_code == 200
    assert good.json()["birth_city"] == "Chennai"
    assert good.json()["chart_data"] is not None
