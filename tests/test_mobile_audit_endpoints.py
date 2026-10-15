"""Endpoint tests the mobile audit (2026-10-14, item 19) found missing.

Each of these routes is called by a native screen and had no test at all:
the local-workspace migration the sign-in flow offers, reading feedback,
profile-fact disputes, and the muhurta refusal that the app must render as
a refer-out card rather than a failure.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import DEV_USER_ID, AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "33333333-3333-4333-8333-333333333333"
OTHER = "44444444-4444-4444-8444-444444444444"


def _kundli(name, user_id):
    return {
        "user_id": user_id, "name": name, "relation": "self",
        "birth_year": 1991, "birth_month": 8, "birth_day": 14,
        "birth_hour": 6, "birth_minute": 12,
        "birth_city": "Vijayawada", "birth_nation": "IN",
    }


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
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

    db = Session()
    mine = crud.create_kundli(db, _kundli("Mine", ME)).id
    theirs = crud.create_kundli(db, _kundli("Theirs", OTHER)).id
    db.close()

    state = {"user": AuthUser(id=ME, auth_enabled=True)}
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: state["user"]
    try:
        yield {"client": TestClient(app), "Session": Session,
               "mine": mine, "theirs": theirs, "state": state}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


class TestLocalWorkspaceMigration:
    def test_signed_in_reader_sees_and_claims_local_kundlis(self, env):
        db = env["Session"]()
        crud.create_kundli(db, _kundli("Local one", DEV_USER_ID))
        crud.create_kundli(db, _kundli("Local two", DEV_USER_ID))
        db.close()
        client = env["client"]

        status = client.get("/api/v1/auth/migration/local").json()
        assert status["available"] is True
        assert status["local_kundlis"] == 2

        claimed = client.post("/api/v1/auth/migration/local/claim").json()
        assert claimed["moved_kundlis"] == 2

        after = client.get("/api/v1/auth/migration/local").json()
        assert after["available"] is False
        assert after["local_kundlis"] == 0
        mine = {k["name"] for k in client.get("/api/v1/kundlis").json()}
        assert {"Mine", "Local one", "Local two"} <= mine

    def test_claim_is_refused_without_a_signed_in_account(self, env):
        env["state"]["user"] = AuthUser(id=DEV_USER_ID, auth_enabled=False)
        client = env["client"]
        status = client.get("/api/v1/auth/migration/local").json()
        assert status["available"] is False
        assert client.post("/api/v1/auth/migration/local/claim").status_code == 401


class TestReadingFeedback:
    def _reading(self, env, kundli_id):
        db = env["Session"]()
        reading = crud.save_reading(db, kundli_id, "daily", "A steady day for routine work.")
        rid = reading.id
        db.close()
        return rid

    def test_feedback_is_stored_and_echoed(self, env):
        rid = self._reading(env, env["mine"])
        response = env["client"].patch(
            f"/api/v1/readings/{env['mine']}/{rid}/feedback",
            json={"rating": 4, "feedback": "Close, but the afternoon was busier."},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["user_rating"] == 4
        assert body["user_feedback"] == "Close, but the afternoon was busier."
        assert body["reviewed_at"]

    def test_rating_is_bounded_one_to_five(self, env):
        rid = self._reading(env, env["mine"])
        response = env["client"].patch(
            f"/api/v1/readings/{env['mine']}/{rid}/feedback", json={"rating": 9},
        )
        assert response.status_code == 422

    def test_feedback_cannot_reach_another_readers_profile(self, env):
        rid = self._reading(env, env["theirs"])
        response = env["client"].patch(
            f"/api/v1/readings/{env['theirs']}/{rid}/feedback", json={"rating": 1},
        )
        assert response.status_code == 404


class TestProfileFactDispute:
    def _create_fact(self, env):
        response = env["client"].post(
            f"/api/v1/profiles/{env['mine']}/context/facts",
            json={
                "expected_revision": 0,
                "key": "employment_status",
                "value": {"code": "retired", "label": "Retired"},
                "valid_from": "2021-03-01",
                "source": {"kind": "profile_form", "channel": "profile_settings"},
                "consent": {"state": "granted", "surface": "profile_memory_v1"},
            },
            headers={"Idempotency-Key": "dispute-create-0001"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    def test_reader_can_dispute_a_fact_and_it_stays_visible_as_disputed(self, env):
        created = self._create_fact(env)
        fact_id = created["fact"]["id"]
        revision = created["revision"]
        response = env["client"].post(
            f"/api/v1/profiles/{env['mine']}/context/facts/{fact_id}/dispute",
            json={"expected_revision": revision},
            headers={"Idempotency-Key": "dispute-0001"},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {
            "revision": revision + 1, "fact_id": fact_id, "status": "disputed",
        }
        # A disputed fact leaves the active projection (Ask must not ground on
        # it) but stays visible in history, so the reader can see and undo it.
        active = env["client"].get(f"/api/v1/profiles/{env['mine']}/context").json()
        assert all(f["id"] != fact_id for f in active["facts"])
        history = env["client"].get(
            f"/api/v1/profiles/{env['mine']}/context", params={"include_history": "true"},
        ).json()
        assert any(f["id"] == fact_id and f["status"] == "disputed" for f in history["facts"])

    def test_dispute_with_a_stale_revision_is_refused(self, env):
        created = self._create_fact(env)
        response = env["client"].post(
            f"/api/v1/profiles/{env['mine']}/context/facts/{created['fact']['id']}/dispute",
            json={"expected_revision": 0},
            headers={"Idempotency-Key": "dispute-stale-0001"},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "stale_revision"

    def test_dispute_on_another_readers_profile_is_404(self, env):
        response = env["client"].post(
            f"/api/v1/profiles/{env['theirs']}/context/facts/any/dispute",
            json={"expected_revision": 0},
            headers={"Idempotency-Key": "dispute-foreign-0001"},
        )
        assert response.status_code == 404


class TestMuhurtaReferOut:
    @pytest.mark.parametrize("goal,domain", [
        ("surgery_date", "health"),
        ("court_hearing", "legal"),
        ("start_trading", "financial"),
    ])
    def test_excluded_intents_return_a_structured_refer_out(self, env, goal, domain):
        response = env["client"].get(
            f"/api/v1/muhurta/{env['mine']}", params={"goal": goal},
        )
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["kind"] == "refer_out"
        assert detail["domain"] == domain
        assert detail["message"]

    def test_refusal_is_not_an_unknown_goal_error(self, env):
        response = env["client"].get(
            f"/api/v1/muhurta/{env['mine']}", params={"goal": "definitely_not_a_goal"},
        )
        assert response.status_code == 400
        assert "refer_out" not in response.text
