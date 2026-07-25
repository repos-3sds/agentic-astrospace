"""
Ask-AI tests: the QA agent's tools are exercised directly (no Anthropic
call, so no cost), and the route's validation paths are checked. The
full agent loop is verified manually against the live server.
"""
from types import SimpleNamespace

import pytest

from astrospace.agents.qa_agent import VedicQAAgent


@pytest.fixture(scope="module")
def agent():
    kundli = SimpleNamespace(
        name="Test Person", birth_year=1993, birth_month=7, birth_day=20,
        birth_hour=11, birth_minute=28, birth_city="Rajahmundry", birth_nation="IN",
    )
    return VedicQAAgent(kundli)


class TestQATools:
    def test_birth_chart_sections(self, agent):
        d = agent._tool_get_birth_chart()
        for key in ("person", "lagna", "planets", "dignities", "avkahada"):
            assert key in d
        assert len(d["planets"]) == 9

    def test_varga_chart_valid_and_invalid(self, agent):
        d9 = agent._tool_get_varga_chart("d9")   # case-insensitive
        assert d9["varga"] == "D9"
        assert len(d9["planets"]) == 9
        bad = agent._tool_get_varga_chart("D99")
        assert "error" in bad

    def test_today_panchanga_has_windows_and_personal(self, agent):
        p = agent._tool_get_today_panchanga("2026-07-07")
        assert p["vara"]["name"] == "Tuesday"
        assert p["windows"]["inauspicious"]
        assert p["personal"]["tarabala"]["tara"]
        assert "horas" not in p  # trimmed for token budget

    def test_gochara_and_sade_sati(self, agent):
        g = agent._tool_get_current_gochara()
        assert len(g["gochara"]) == 9
        for planet, det in g["gochara"].items():
            assert 1 <= det["house_from_lagna"] <= 12
            assert 1 <= det["house_from_moon"] <= 12
        assert g["sade_sati"]["saturn_house_from_moon"] == g["gochara"]["Saturn"]["house_from_moon"]
        assert g["sade_sati"]["active"] == (g["sade_sati"]["saturn_house_from_moon"] in (12, 1, 2))

    def test_tool_error_containment(self, agent):
        # dispatch wraps exceptions into error payloads instead of raising
        result = agent._dispatch_tool("get_varga_chart", {"varga": None})
        assert "error" in result


class TestAskRoute:
    """Route validation only — the agent itself is covered above.

    Both `current_user` and `get_db` are overridden. Without the first, these
    tests pass or fail depending on whether the developer happens to have
    SUPABASE_* in a .env, since main.py calls load_dotenv() at import and the
    route then demands a bearer token. Without the second, they run against
    whatever DATABASE_URL points at — in practice, production.
    """

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from main import app
        from astrospace.api.auth import AuthUser, current_user
        from astrospace.db import get_db
        from astrospace.db.database import Base

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

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_user] = lambda: AuthUser(
            id="test-user-ask", email="test@astrospace.dev", role="dev"
        )
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(current_user, None)

    def test_unknown_kundli_404(self, client):
        r = client.post("/api/v1/ask/nonexistent-id", json={"question": "hi"})
        assert r.status_code == 404

    def test_empty_question_422(self, client):
        r = client.post("/api/v1/ask/nonexistent-id", json={"question": ""})
        assert r.status_code == 422

    def test_bad_history_role_422(self, client):
        r = client.post("/api/v1/ask/nonexistent-id", json={
            "question": "hi",
            "history": [{"role": "system", "content": "x"}],
        })
        assert r.status_code == 422
