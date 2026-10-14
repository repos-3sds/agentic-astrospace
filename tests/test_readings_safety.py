"""`POST /readings/{id}/generate` was the one LLM surface with no safety layer
and the only one computing from the tropical zodiac. These tests pin both
fixes: the output-side boundary (nothing crossing it is ever persisted), and
the chart the agent reads from (sidereal, same engine as the Kundli tabs).

The model call is stubbed at `PeriodAgent.run`, the single provider-reaching
entry point of this agent; nothing here needs credentials.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.period_agent import PERIOD_SYSTEM, PeriodAgent, reading_boundary
from astrospace.api.auth import AuthUser, current_user
from astrospace.core.vedic.chart import VedicChart
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "33333333-3333-4333-8333-333333333333"

CLEAN = (
    "## Overall theme\nJupiter transits your natal Sun in Cancer, your 12th house "
    "from the Leo lagna, so this month favours quiet, reflective work over launches.\n\n"
    "## Career\nSaturn's gochara supports slow, steady progress; avoid rushing decisions."
)
DEATH = CLEAN + "\n\n## Health\nSaturn's return suggests you will die before the year ends."
OVERCLAIM = CLEAN + "\n\n## Relationships\nWith Manglik dosha active, your marriage will fail."


@pytest.fixture(scope="module")
def env():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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

    def override_current_user():
        return AuthUser(id=ME, email="me@astrospace.dev", role="dev")

    db = Session()
    kundli = crud.create_kundli(db, {
        "user_id": ME, "name": "Mine", "relation": "self",
        "birth_year": 1991, "birth_month": 8, "birth_day": 14,
        "birth_hour": 6, "birth_minute": 12,
        "birth_city": "Vijayawada", "birth_nation": "IN",
    }).id
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    try:
        yield {"client": TestClient(app), "kundli": kundli}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


@pytest.fixture
def client(env):
    return env["client"]


def _generate(client, kundli, period="monthly"):
    return client.post(f"/api/v1/readings/{kundli}/generate",
                       json={"period": period, "force_refresh": True})


class TestOutputBoundary:
    def test_death_verdict_is_declined_and_never_persisted(self, client, env):
        with patch.object(PeriodAgent, "run", side_effect=[DEATH, DEATH]) as run:
            res = _generate(client, env["kundli"], "yearly")
        assert res.status_code == 422
        detail = res.json()["detail"]
        assert detail["kind"] == "refer_out"
        assert detail["domain"] == "death"
        assert "does not predict death" in detail["message"]
        assert run.call_count == 2, "one retry with the boundary named, then decline"
        assert "crossed a boundary (death)" in run.call_args_list[1].args[0]

        listed = client.get(f"/api/v1/readings/{env['kundli']}?period=yearly").json()
        assert listed == []
        claims = client.get(f"/api/v1/readings/{env['kundli']}/claims").json()
        assert claims == []

    def test_dosha_overclaim_is_declined(self, client, env):
        with patch.object(PeriodAgent, "run", side_effect=[OVERCLAIM, OVERCLAIM]):
            res = _generate(client, env["kundli"], "quarterly")
        assert res.status_code == 422
        assert res.json()["detail"]["domain"] == "dosha_overclaim"
        assert "flag, not a verdict" in res.json()["detail"]["message"]

    def test_retry_that_comes_back_clean_is_published(self, client, env):
        with patch.object(PeriodAgent, "run", side_effect=[DEATH, CLEAN]) as run:
            res = _generate(client, env["kundli"], "weekly")
        assert res.status_code == 200
        assert run.call_count == 2
        assert res.json()["content"] == CLEAN
        assert res.json()["cached"] is False

    def test_clean_reading_is_published_on_the_first_call(self, client, env):
        with patch.object(PeriodAgent, "run", return_value=CLEAN) as run:
            res = _generate(client, env["kundli"], "monthly")
        assert res.status_code == 200
        assert run.call_count == 1
        assert res.json()["content"] == CLEAN
        claims = client.get(f"/api/v1/readings/{env['kundli']}/claims").json()
        assert claims, "clean readings still feed the prediction ledger"

    def test_reading_boundary_mirrors_the_ask_verifier(self):
        assert reading_boundary(CLEAN) is None
        assert reading_boundary(DEATH) == "death"
        assert reading_boundary(OVERCLAIM) == "dosha_overclaim"


class TestSiderealChart:
    """1991-08-14 06:12 Vijayawada: tropical Sun is 20° Leo, sidereal Sun is
    Cancer. The old agent handed the model the first; the Kundli tabs show
    the second. One person, one chart."""

    @pytest.fixture
    def agent(self):
        chart = VedicChart("Mine", 1991, 8, 14, 6, 12, "Vijayawada", "IN")
        with patch.dict("os.environ", {"AI_PROVIDER": "anthropic"}):
            return PeriodAgent(chart)

    def test_natal_tool_is_the_engine_chart(self, agent):
        natal = agent._tool_get_natal_chart()
        assert natal["zodiac"] == "sidereal"
        assert natal["ayanamsha"] == "lahiri"
        assert natal["lagna"]["sign"] == "Leo"
        assert natal["planets"]["Sun"]["sign"] == "Cancer"
        assert natal["planets"]["Sun"]["house"] == 12
        assert natal["planets"]["Sun"]["longitude"] == round(agent.chart.positions["Sun"]["lon"], 4)
        assert set(natal["planets"]) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
        assert set(natal["current_dasha"]) >= {"mahadasha", "antardasha"}
        assert "antardashas" not in natal["current_dasha"]["mahadasha"], "trimmed for the prompt"

    def test_transit_tools_count_houses_from_the_sidereal_lagna_and_moon(self, agent):
        now = agent._tool_get_current_transits()
        assert now["zodiac"] == "sidereal"
        assert set(now["gochara"]) == {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}
        for row in now["gochara"].values():
            assert 1 <= row["house_from_lagna"] <= 12
            assert 1 <= row["house_from_moon"] <= 12
        assert now["sade_sati"]["saturn_house_from_moon"] == now["gochara"]["Saturn"]["house_from_moon"]

        contacts = agent._tool_get_transits_to_natal()
        assert contacts["zodiac"] == "sidereal"
        assert contacts["natal"] == {"lagna_sign": "Leo", "moon_sign": "Virgo"}
        assert all(rule["trigger"] for rule in contacts["active_gochara_rules"])
        assert len(contacts["active_aspects"]) <= 8

    def test_prompt_states_the_boundaries_and_the_zodiac(self, agent):
        for phrase in ("Never predict death", "flag, not a verdict", "sidereal",
                       "never something to pay for"):
            assert phrase in PERIOD_SYSTEM
        prompt = agent.reading_prompt("daily", agent.chart.moment.dt_local)
        assert "sidereal, lahiri ayanamsha" in prompt
        assert "Vijayawada" in prompt


def test_unresolvable_birth_place_is_a_422_not_a_crash(client, env):
    """The old agent fell back to an online GeoNames lookup for unknown
    cities; the engine refuses, and the route says so."""
    from astrospace.db import get_db as _get_db  # noqa: F401  (overridden above)
    db = next(app.dependency_overrides[get_db]())
    lost = crud.create_kundli(db, {
        "user_id": ME, "name": "Lost", "relation": "friend",
        "birth_year": 1990, "birth_month": 1, "birth_day": 1,
        "birth_hour": 12, "birth_minute": 0,
        "birth_city": "Nowhereville-xyz", "birth_nation": "ZZ",
    }).id
    db.close()
    with patch.object(PeriodAgent, "run", return_value=CLEAN) as run:
        res = _generate(client, lost)
    assert res.status_code == 422
    assert run.call_count == 0
