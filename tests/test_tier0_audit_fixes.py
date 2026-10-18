"""Tier 0 fixes from the 2026-10-18 end-to-end audit.

- U1/I2: profile big-three signs are sidereal, as on every other screen.
- S1/I4: always-on per-account ceilings on model-backed work.
- S3/I3: the legacy /api/v1 LLM routes and /chart are gone.
- S2: email buttons can only link inside the app.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace import ratelimit
from astrospace.api.auth import AuthUser, current_user
from astrospace.api.context_routes import _may_write_brief
from astrospace.core.vedic import VedicChart
from astrospace.core.vedic.positions import sidereal_big_three, sign_index, sign_name
from astrospace.db import Kundli, get_db
from astrospace.db.database import Base
from astrospace.notifications.email import safe_app_path
from main import app

ME = "tier0-user"
BIRTH = dict(birth_year=1990, birth_month=1, birth_day=15, birth_hour=12, birth_minute=0,
             birth_city="Hyderabad", birth_nation="IN")


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


@pytest.fixture(autouse=True)
def _fresh_limits():
    ratelimit.reset()
    yield
    ratelimit.reset()


def _vedic_signs():
    chart = VedicChart("x", 1990, 1, 15, 12, 0, "Hyderabad", "IN")
    return {
        "sun_sign": sign_name(sign_index(chart.positions["Sun"]["lon"])),
        "moon_sign": sign_name(sign_index(chart.positions["Moon"]["lon"])),
        "ascendant": sign_name(sign_index(chart.lagna_lon)),
    }


def test_big_three_matches_the_vedic_chart():
    signs = sidereal_big_three(1990, 1, 15, 12, 0, "Hyderabad", "IN")
    assert signs == _vedic_signs()
    # The reproduction from the audit: kerykeion said Virgo, the chart says Leo.
    assert signs["moon_sign"] == "Leo"


def test_a_new_profile_stores_sidereal_signs(client):
    api, _ = client
    res = api.post("/api/v1/kundlis", json={"name": "Asha", "relation": "self", **BIRTH})
    assert res.status_code == 201, res.text
    body = res.json()
    assert {k: body[k] for k in ("sun_sign", "moon_sign", "ascendant")} == _vedic_signs()


def test_a_profile_saved_with_tropical_signs_reads_back_sidereal(client):
    api, factory = client
    with factory() as db:
        db.add(Kundli(id="old-row", user_id=ME, name="Old", relation="friend",
                      sun_sign="Capricorn", moon_sign="Virgo", ascendant="Aries", **BIRTH))
        db.commit()
    listed = api.get("/api/v1/kundlis").json()
    assert listed[0]["moon_sign"] == "Leo"
    assert api.get("/api/v1/kundlis/old-row").json()["moon_sign"] == "Leo"


@pytest.mark.parametrize("path", ["/api/v1/chart", "/api/v1/reading", "/api/v1/horoscope",
                                  "/api/v1/compatibility", "/api/v1/transits"])
def test_legacy_llm_routes_are_gone(client, path):
    api, _ = client
    assert api.post(path, json={}).status_code in (404, 405)


def test_ceiling_blocks_past_the_daily_limit(monkeypatch):
    monkeypatch.setenv("ASTROSPACE_LIMIT_ASK_PER_DAY", "3")
    monkeypatch.setenv("ASTROSPACE_LIMIT_ASK_PER_MINUTE", "100")
    assert [ratelimit.take("u", "ask", now=float(i)) for i in range(4)] == [True, True, True, False]
    # A different account has its own allowance.
    assert ratelimit.take("other", "ask", now=4.0)
    # A day later the window has moved on.
    assert ratelimit.take("u", "ask", now=ratelimit.DAY + 1)


def test_ceiling_blocks_bursts_within_a_minute():
    limit = ratelimit.LIMITS["ask"].per_minute
    assert all(ratelimit.take("u", "ask", now=1.0) for _ in range(limit))
    assert not ratelimit.take("u", "ask", now=2.0)
    assert ratelimit.take("u", "ask", now=1.0 + ratelimit.MINUTE)


def test_require_answers_429_with_a_readable_sentence(monkeypatch):
    monkeypatch.setenv("ASTROSPACE_LIMIT_READING_PER_DAY", "0")
    with pytest.raises(HTTPException) as err:
        ratelimit.require("u", "reading")
    assert err.value.status_code == 429
    assert "readings" in err.value.detail


def test_refund_gives_back_the_last_unit(monkeypatch):
    monkeypatch.setenv("ASTROSPACE_LIMIT_READING_PER_DAY", "1")
    assert ratelimit.take("u", "reading")
    ratelimit.refund("u", "reading")
    assert ratelimit.take("u", "reading")


def test_on_open_brief_only_for_days_near_today():
    from datetime import date, timedelta
    today = date.today()
    assert _may_write_brief("u", {"date": today.isoformat()})
    assert not _may_write_brief("u", {"date": (today + timedelta(days=5)).isoformat()})
    assert not _may_write_brief("u", {"date": "1999-01-01"})
    assert not _may_write_brief("u", {})


@pytest.mark.parametrize("path,expected", [
    ("/m/today", "/m/today"),
    ("/m/calendar?d=2026-10-18", "/m/calendar?d=2026-10-18"),
    ("@evil.example/login", "/m/today"),
    ("//evil.example", "/m/today"),
    ("/m/x@evil.example", "/m/today"),
    ("https://evil.example", "/m/today"),
    ("", "/m/today"),
])
def test_email_button_links_stay_inside_the_app(path, expected):
    assert safe_app_path(path) == expected
