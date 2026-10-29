"""Free's one-person-a-month compatibility limit is kept on the server
(sweep 2026-10-29 G-6); it used to live only in the phone's localStorage."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from main import app

ME = "11111111-1111-1111-1111-111111111111"
PEOPLE = (
    ("Ravi Kumar", "self", 1991, 3, 14, 6, 40, "Hyderabad"),
    ("Meera", "spouse", 1993, 8, 22, 21, 15, "Chennai"),
    ("Anu", "friend", 1994, 1, 5, 9, 10, "Pune"),
)


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "1")
    monkeypatch.delenv("ASTROSPACE_TESTERS_GET_PLUS", raising=False)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        ids = [crud.create_kundli(db, {
            "user_id": ME, "name": name, "relation": relation,
            "birth_year": y, "birth_month": m, "birth_day": d, "birth_hour": h, "birth_minute": mi,
            "birth_city": city, "birth_nation": "IN",
        }).id for name, relation, y, m, d, h, mi, city in PEOPLE]
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, role="dev")
    try:
        yield TestClient(app), ids
    finally:
        app.dependency_overrides.clear()


def _check(http, a, b):
    return http.get(f"/api/v1/vedic/{a}/compatibility/{b}")


def test_free_gets_one_person_a_month_and_may_reopen_them(env):
    http, (me, meera, anu) = env
    assert _check(http, me, meera).status_code == 200
    # The same person again, either way round (a groom-first match swaps them).
    assert _check(http, meera, me).status_code == 200
    assert _check(http, me, meera).status_code == 200
    second = _check(http, me, anu)
    assert second.status_code == 402
    assert second.json()["entitlement"] == "compatibility.checks.period"


def test_the_count_shows_in_the_snapshot(env):
    http, (me, meera, _anu) = env
    _check(http, me, meera)
    _check(http, meera, me)
    usage = http.get("/api/v1/entitlements").json()["usage"]["compatibility.checks.period"]
    assert usage["used"] == 1 and usage["remaining"] == 0


def test_counted_but_not_blocked_while_locks_are_off(env, monkeypatch):
    http, (me, meera, anu) = env
    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED")
    assert _check(http, me, meera).status_code == 200
    assert _check(http, me, anu).status_code == 200
    assert http.get("/api/v1/entitlements").json()["usage"]["compatibility.checks.period"]["used"] == 2
