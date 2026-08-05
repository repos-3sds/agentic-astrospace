"""API tests for the remedy, muhurta and festival endpoints.

Auth/DB pattern follows test_api_v2.py: `get_db` and `current_user` are
overridden with an in-memory sqlite session and a fixed dev user, so these run
identically with or without Supabase configured.

Beyond status codes, these assert that the engines' safety framing survives
serialisation. A remedy that arrives at the client without its
`is_convention_dependent` flag, or a health intent that comes back as a list
of auspicious times, is a product bug even though the HTTP layer "worked".
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.core.vedic import festivals, muhurta
from astrospace.db import crud, get_db
from astrospace.db.database import Base

TEST_USER_ID = "test-user-mobile-routes"
OTHER_USER_ID = "someone-else"


@pytest.fixture(scope="module")
def client_and_kundli():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        return AuthUser(id=TEST_USER_ID, email="test@astrospace.dev", role="dev")

    db = TestingSession()
    kundli = crud.create_kundli(db, {
        "user_id": TEST_USER_ID,
        "name": "Mobile Routes Test",
        "relation": "self",
        "birth_year": 1991,
        "birth_month": 8,
        "birth_day": 14,
        "birth_hour": 6,
        "birth_minute": 12,
        "birth_city": "Vijayawada",
        "birth_nation": "IN",
    })
    # A second kundli owned by a different user, to prove the ownership check.
    foreign = crud.create_kundli(db, {
        "user_id": OTHER_USER_ID,
        "name": "Not Yours",
        "relation": "self",
        "birth_year": 1990, "birth_month": 1, "birth_day": 1,
        "birth_hour": 12, "birth_minute": 0,
        "birth_city": "New Delhi", "birth_nation": "IN",
    })
    ids = (kundli.id, foreign.id)
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield TestClient(app), ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


@pytest.fixture(scope="module")
def client(client_and_kundli):
    return client_and_kundli[0]


@pytest.fixture(scope="module")
def kundli_id(client_and_kundli):
    return client_and_kundli[1][0]


@pytest.fixture(scope="module")
def foreign_kundli_id(client_and_kundli):
    return client_and_kundli[1][1]


# ── Remedies ─────────────────────────────────────────────────────────────────

class TestRemedyRoutes:
    def test_catalog(self, client):
        body = client.get("/api/v1/remedies/catalog").json()
        assert body["remedies"]
        assert len({r["slug"] for r in body["remedies"]}) == len(body["remedies"])

    def test_recommendations_for_a_kundli(self, client, kundli_id):
        r = client.get(f"/api/v1/remedies/{kundli_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["groups"]
        assert body["count"] == len(body["groups"])

    def test_safety_framing_survives_serialisation(self, client, kundli_id):
        """The disclaimer and per-remedy provenance must reach the client."""
        body = client.get(f"/api/v1/remedies/{kundli_id}").json()
        assert "not a guarantee" in body["disclaimer"]
        assert "qualified professional" in body["disclaimer"]
        for group in body["groups"]:
            assert group["recommendation_id"]
            assert group["safety_note"]
            for remedy in group["practices"]:
                assert remedy["is_convention_dependent"] is True
                assert remedy["tradition_source"]

    def test_manglik_is_excluded_by_default(self, client, kundli_id):
        """US-PR-003: Manglik must never surface as a generic remedy card."""
        body = client.get(f"/api/v1/remedies/{kundli_id}").json()
        assert not [g for g in body["groups"] if g["trigger"].get("dosha") == "manglik"]

    def test_gemstones_can_be_excluded(self, client, kundli_id):
        body = client.get(
            f"/api/v1/remedies/{kundli_id}", params={"include_costly": "false"}
        ).json()
        types = {r["type"] for g in body["groups"] for r in g["practices"]}
        assert "gem" not in types

    def test_limit_is_honoured(self, client, kundli_id):
        body = client.get(f"/api/v1/remedies/{kundli_id}", params={"limit": 2}).json()
        assert body["count"] <= 2

    def test_unknown_kundli_404(self, client):
        assert client.get("/api/v1/remedies/does-not-exist").status_code == 404

    def test_another_users_kundli_404(self, client, foreign_kundli_id):
        """Ownership is enforced in the route, not just by RLS."""
        assert client.get(f"/api/v1/remedies/{foreign_kundli_id}").status_code == 404


# ── Yogas/Doshas KB catalog ────────────────────────────────────────────────

class TestVedicRulesRoutes:
    """The rules KB catalog is reference data — no kundli_id needed."""

    def test_list_all_rules(self, client):
        body = client.get("/api/v1/vedic/rules").json()
        assert body["count"] == len(body["rules"])
        assert body["count"] > 25
        assert {r["kind"] for r in body["rules"]} == {"yoga", "dosha"}

    def test_kind_filter(self, client):
        body = client.get("/api/v1/vedic/rules", params={"kind": "dosha"}).json()
        assert body["rules"]
        assert all(r["kind"] == "dosha" for r in body["rules"])

    def test_rule_detail_matches_list_entry(self, client):
        detail = client.get("/api/v1/vedic/rules/manglik_dosha").json()
        assert detail["classical_name"] == "Manglik / Kuja Dosha"
        assert detail["practitioner_explanation"]
        assert detail["lay_explanation"]
        assert detail["caveats"]

    def test_unknown_rule_id_returns_pending_shape_not_500(self, client):
        r = client.get("/api/v1/vedic/rules/not-a-real-rule")
        assert r.status_code == 200
        assert r.json()["status"] == "needs_review"


# ── Muhurta ──────────────────────────────────────────────────────────────────

class TestMuhurtaRoutes:
    def test_goal_catalog_matches_the_engine(self, client):
        body = client.get("/api/v1/muhurta/goals").json()
        assert {g["slug"] for g in body["goals"]} == set(muhurta.GOALS)

    def test_find_windows(self, client, kundli_id):
        r = client.get(f"/api/v1/muhurta/{kundli_id}", params={
            "goal": "sign_contract",
            "date_from": "2026-07-26",
            "date_to": "2026-08-10",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["goal"] == "sign_contract"
        assert body["results"]
        scores = [w["score"] for w in body["results"]]
        assert scores == sorted(scores, reverse=True)
        assert body["is_convention_dependent"] is True

    def test_defaults_to_a_two_week_window_from_today(self, client, kundli_id):
        r = client.get(f"/api/v1/muhurta/{kundli_id}", params={"goal": "start_journey"})
        assert r.status_code == 200
        assert r.json()["days_scanned"] > 0

    @pytest.mark.parametrize("goal,domain", [
        ("medical_treatment", "health"),
        ("surgery", "health"),
        ("litigation", "legal"),
        ("investment", "financial"),
    ])
    def test_excluded_intents_return_a_structured_refer_out(
        self, client, kundli_id, goal, domain
    ):
        """Refer-out is a designed response, so the app can render it as one."""
        r = client.get(f"/api/v1/muhurta/{kundli_id}", params={"goal": goal})
        assert r.status_code == 422
        detail = r.json()["detail"]
        assert detail["kind"] == "refer_out"
        assert detail["domain"] == domain
        assert "qualified professional" in detail["message"]

    def test_unknown_goal_400(self, client, kundli_id):
        r = client.get(f"/api/v1/muhurta/{kundli_id}", params={"goal": "nonsense"})
        assert r.status_code == 400

    def test_inverted_range_400(self, client, kundli_id):
        r = client.get(f"/api/v1/muhurta/{kundli_id}", params={
            "goal": "start_journey", "date_from": "2026-08-10", "date_to": "2026-07-01",
        })
        assert r.status_code == 400

    def test_malformed_date_400(self, client, kundli_id):
        r = client.get(f"/api/v1/muhurta/{kundli_id}", params={
            "goal": "start_journey", "date_from": "26-07-2026",
        })
        assert r.status_code == 400
        assert "YYYY-MM-DD" in r.json()["detail"]

    def test_unknown_kundli_404(self, client):
        r = client.get("/api/v1/muhurta/does-not-exist", params={"goal": "start_journey"})
        assert r.status_code == 404

    def test_another_users_kundli_404(self, client, foreign_kundli_id):
        r = client.get(f"/api/v1/muhurta/{foreign_kundli_id}", params={"goal": "start_journey"})
        assert r.status_code == 404


# ── Festivals ────────────────────────────────────────────────────────────────

class TestFestivalRoutes:
    def test_catalog_covers_the_whole_list(self, client):
        body = client.get("/api/v1/festivals/catalog").json()
        assert len(body["festivals"]) == len(festivals.FESTIVALS)

    def test_year_returns_iso_dates(self, client):
        body = client.get("/api/v1/festivals/year/2026",
                          params={"city": "Chennai"}).json()
        assert body["count"] == len(body["festivals"])
        assert body["place"]["city"] == "Chennai"
        dates = [f["occurs_on"] for f in body["festivals"]]
        assert dates == sorted(dates)
        assert all(isinstance(d, str) and d.startswith("2026-") for d in dates)

    def test_known_dates_survive_the_route(self, client):
        """The same anchors as the engine tests, through HTTP."""
        body = client.get("/api/v1/festivals/year/2026",
                          params={"city": "Chennai"}).json()
        by_slug = {f["slug"]: f["occurs_on"] for f in body["festivals"]}
        assert by_slug["maha_shivaratri"] == "2026-02-15"
        assert by_slug["diwali"] == "2026-11-08"
        assert by_slug["ugadi"] == "2026-03-19"
        assert by_slug["makar_sankranti"] == "2026-01-14"

    def test_convention_caveats_reach_the_client(self, client):
        """A date with more than one defensible answer must say so."""
        body = client.get("/api/v1/festivals/year/2026",
                          params={"city": "Chennai"}).json()
        flagged = [f for f in body["festivals"] if f["is_convention_dependent"]]
        assert flagged
        assert all(f["observance_note"] for f in flagged)

    def test_region_filter(self, client):
        body = client.get("/api/v1/festivals/year/2026", params={
            "city": "Chennai", "regions": ["south"],
        }).json()
        assert body["festivals"]
        assert all("south" in f["regions"] or "pan-india" in f["regions"]
                   for f in body["festivals"])

    def test_slug_filter(self, client):
        body = client.get("/api/v1/festivals/year/2026", params={
            "city": "Chennai", "slugs": ["diwali", "onam"],
        }).json()
        assert {f["slug"] for f in body["festivals"]} == {"diwali", "onam"}

    def test_unknown_region_400(self, client):
        r = client.get("/api/v1/festivals/year/2026", params={
            "city": "Chennai", "regions": ["west"],
        })
        assert r.status_code == 400
        assert "unknown region" in r.json()["detail"]

    def test_year_out_of_range_400(self, client):
        r = client.get("/api/v1/festivals/year/1500", params={"city": "Chennai"})
        assert r.status_code == 400

    def test_unknown_city_422(self, client):
        r = client.get("/api/v1/festivals/year/2026", params={"city": "Atlantis"})
        assert r.status_code == 422

    def test_city_is_required(self, client):
        """No hidden default — a wrong place gives confidently wrong dates."""
        assert client.get("/api/v1/festivals/year/2026").status_code == 422

    def test_upcoming_window(self, client):
        body = client.get("/api/v1/festivals/upcoming", params={
            "city": "Chennai", "from_date": "2026-10-01", "days": 45,
        }).json()
        assert body["from_date"] == "2026-10-01"
        assert body["to_date"] == "2026-11-15"
        assert all("2026-10-01" <= f["occurs_on"] <= "2026-11-15"
                   for f in body["festivals"])

    def test_upcoming_spans_a_year_boundary(self, client):
        body = client.get("/api/v1/festivals/upcoming", params={
            "city": "Chennai", "from_date": "2026-12-20", "days": 40,
        }).json()
        assert any(f["occurs_on"].startswith("2027-") for f in body["festivals"])

    def test_upcoming_rejects_a_bad_date(self, client):
        r = client.get("/api/v1/festivals/upcoming",
                       params={"city": "Chennai", "from_date": "01-10-2026"})
        assert r.status_code == 400
