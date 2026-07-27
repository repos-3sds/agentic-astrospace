"""
API tests for the v2 Vedic endpoints (jaimini, special-lagnas, masa,
yogini-dashas) plus payload-shape checks on /all, /shadbala, /dashas,
/transits and /doshas.

Auth/DB pattern: the app's `get_db` and `current_user` dependencies are
overridden with an in-memory sqlite session and a fixed dev user, so the
tests run identically whether or not Supabase env vars are configured.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import get_db
from astrospace.db.database import Base
from astrospace.db import crud

TEST_USER_ID = "test-user-api-v2"


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
        "name": "API V2 Test",
        "relation": "self",
        "birth_year": 1990,
        "birth_month": 1,
        "birth_day": 1,
        "birth_hour": 12,
        "birth_minute": 0,
        "birth_city": "New Delhi",
        "birth_nation": "IN",
    })
    kundli_id = kundli.id
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield TestClient(app), kundli_id
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


class TestJaiminiEndpoint:
    def test_jaimini_shape(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/jaimini")
        assert r.status_code == 200
        d = r.json()
        for key in ("chara_karakas", "arudha_lagna", "upapada", "arudha_padas"):
            assert key in d
        ordered = d["chara_karakas"]["ordered"]
        assert ordered[0]["code"] == "AK"
        assert ordered[-1]["code"] == "DK"
        assert d["arudha_lagna"]["sign_name"]
        assert set(d["arudha_padas"]["padas"]) >= {f"A{i}" for i in range(1, 13)}

    def test_jaimini_respects_ayanamsha_param(self, client_and_kundli):
        client, kid = client_and_kundli
        lahiri = client.get(f"/api/v1/vedic/{kid}/jaimini").json()
        raman = client.get(f"/api/v1/vedic/{kid}/jaimini",
                           params={"ayanamsha": "raman"}).json()
        ak_l = lahiri["chara_karakas"]["ordered"][0]
        ak_r = raman["chara_karakas"]["ordered"][0]
        assert ak_l["longitude"] != ak_r["longitude"]

    def test_unknown_kundli_404(self, client_and_kundli):
        client, _ = client_and_kundli
        r = client.get("/api/v1/vedic/nonexistent-id/jaimini")
        assert r.status_code == 404


class TestSpecialLagnasEndpoint:
    def test_special_lagnas_shape(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/special-lagnas")
        assert r.status_code == 200
        d = r.json()
        for key in ("bhava_lagna", "hora_lagna", "ghati_lagna", "lagna"):
            assert key in d
            assert "sign_name" in d[key]
            assert "dms" in d[key]
        assert d["hours_since_sunrise"] >= 0


class TestMasaEndpoint:
    def test_masa_shape(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/masa")
        assert r.status_code == 200
        d = r.json()
        # 1990-01-01 New Delhi: Pausha shukla, Hemanta, Uttarayana
        assert d["name"] == "Pausha"
        assert d["paksha"] == "Shukla"
        assert d["adhika"] is False
        assert d["ritu"] == "Hemanta"
        assert d["ayana"] == "Uttarayana"
        assert d["samvatsara"]["name"]


class TestYoginiDashasEndpoint:
    def test_yogini_shape(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/yogini-dashas")
        assert r.status_code == 200
        d = r.json()
        assert d["system"] == "Yogini"
        assert d["cycle_years"] == 36
        assert d["birth_nakshatra"]["name"]
        assert d["mahadashas"]
        maha = d["mahadashas"][0]
        for key in ("yogini", "lord", "start", "end", "years", "antardashas"):
            assert key in maha
        current = d["current"]["mahadasha"]
        assert current["active"] is True


class TestExistingPayloadsGainedSections:
    def test_all_includes_new_sections(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/all")
        assert r.status_code == 200
        d = r.json()
        for key in ("jaimini", "special_lagnas", "masa"):
            assert key in d
        assert d["jaimini"]["chara_karakas"]["ordered"]

    def test_shadbala_has_classical(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/shadbala")
        assert r.status_code == 200
        cl = r.json()["classical"]
        assert cl["available"] is True
        row = cl["rows"]["Sun"]
        for key in ("components", "total_virupas", "rupas",
                    "required_rupas", "ratio", "sufficient"):
            assert key in row
        assert cl["ranking"][0]["planet"]

    def test_dashas_current_has_sookshma_and_prana(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/dashas")
        assert r.status_code == 200
        current = r.json()["current"]
        for key in ("sookshmadasha", "sookshmadashas", "pranadasha", "pranadashas"):
            assert key in current
        assert current["sookshmadasha"]["lord"]

    def test_transits_have_ashtakavarga_context(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/transits")
        assert r.status_code == 200
        d = r.json()
        avt = d["ashtakavarga_transit"]
        assert set(avt["planets"]) == {"Sun", "Moon", "Mars", "Mercury",
                                       "Jupiter", "Venus", "Saturn"}
        sun = avt["planets"]["Sun"]
        for key in ("transit_sign", "bindus", "bav_support", "sav",
                    "sav_support", "kakshya"):
            assert key in sun
        assert "kakshya_lord" in sun["kakshya"]
        rules = d["gochara"]["rules"]
        assert rules
        assert "effective_severity" in rules[0]

    def test_doshas_have_gandanta_grahan_and_manglik_net(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.get(f"/api/v1/vedic/{kid}/doshas")
        assert r.status_code == 200
        d = r.json()
        for key in ("manglik", "gandanta", "grahan"):
            assert key in d
        assert "net_severity" in d["manglik"]
        assert "exceptions" in d["manglik"]
        assert "hits" in d["gandanta"]
        assert "hits" in d["grahan"]


class TestPublicChartEndpoint:
    def test_public_chart_includes_new_sections(self, client_and_kundli):
        client, _ = client_and_kundli
        r = client.post("/api/v1/vedic/chart", json={
            "name": "Public", "year": 1990, "month": 1, "day": 1,
            "hour": 12, "minute": 0, "city": "New Delhi",
        })
        assert r.status_code == 200
        d = r.json()
        for key in ("jaimini", "special_lagnas", "masa"):
            assert key in d


class TestContextEngineEndpoint:
    def test_context_routes_question_to_domains(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.post(f"/api/v1/context/{kid}", json={
            "question": "Will I settle abroad after marriage?",
            "include_gochara": False,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["routing"]["primary"] in {"marriage", "foreign"}
        domains = [row["domain"] for row in d["bundle"]["domains"]]
        assert {"marriage", "foreign"} <= set(domains)
        assert d["bundle"]["provenance"]["assembly"].startswith("deterministic")

    def test_context_accepts_explicit_domains(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.post(f"/api/v1/context/{kid}", json={
            "domains": ["career"],
            "include_gochara": False,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["routing"]["method"] == "explicit"
        assert d["bundle"]["domains"][0]["domain"] == "career"
        assert d["bundle"]["domains"][0]["vargas"]["D10"]["tier"] == "primary"

    def test_context_rejects_unknown_domain(self, client_and_kundli):
        client, kid = client_and_kundli
        r = client.post(f"/api/v1/context/{kid}", json={"domains": ["lottery"]})
        assert r.status_code == 400
        assert "Unknown context domains" in r.json()["detail"]


class TestSettingsEndpoint:
    def test_accepts_eastern_chart_style(self, client_and_kundli):
        client, _ = client_and_kundli
        payload = {
            "chart_style": "eastern",
            "ayanamsha": "lahiri",
            "node_type": "mean",
            "timezone_mode": "browser",
            "panchanga_place": None,
            "language": "en",
            "regional_format": "en-IN",
            "experience_mode": "practitioner",
            "tone": "direct",
        }

        r = client.put("/api/v1/settings", json=payload)
        assert r.status_code == 200
        assert r.json()["chart_style"] == "eastern"
        assert r.json()["experience_mode"] == "practitioner"
        assert r.json()["tone"] == "direct"

        saved = client.get("/api/v1/settings")
        assert saved.status_code == 200
        assert saved.json()["chart_style"] == "eastern"
        assert saved.json()["experience_mode"] == "practitioner"
