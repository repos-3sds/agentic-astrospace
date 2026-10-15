"""The Readings review flow: what claims a reading yields, and which of them
are put in front of the person to review.

Two defects this pins, both seen walking the flow on 2026-10-15: claims were
cut from whitespace-collapsed markdown, so a `##` header fused with the next
sentence and was offered for review ("## Career and money A delayed
payment…"); and every "Generate new" left the previous version's unreviewed
claims in the queue, so the same prediction appeared twice.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.agents.period_agent import PeriodAgent
from astrospace.api.auth import AuthUser, current_user
from astrospace.api.reading_routes import _extract_prediction_claims
from astrospace.db import crud, get_db
from astrospace.db.database import Base

ME = "44444444-4444-4444-8444-444444444444"

READING = """## Overall theme
Jupiter transits your 10th house from the Moon, which supports visible progress at work.

## Career and money
A delayed payment is likely to clear before the period ends. **Avoid** signing long contracts in a hurry this week.

## Guidance
- Focus on finishing open work rather than starting new projects this week.
- Keep evenings lighter so that your sleep stays good through the week.
"""


def _claims(content):
    return _extract_prediction_claims(
        content, kundli_id="k", reading_id="r", user_id=ME, reading_type="weekly",
        period_label="Week", generated_local_date="2026-10-15",
        target_start_date="2026-10-15", target_end_date="2026-10-21",
    )


class TestClaimText:
    def test_headers_never_reach_a_claim(self):
        texts = [c["claim_text"] for c in _claims(READING)]
        assert texts, "the reading has predictions to extract"
        assert not any("#" in t for t in texts)
        assert not any(t.startswith(("Career and money", "Guidance", "Overall theme")) for t in texts)

    def test_sentences_are_kept_whole_and_unwrapped(self):
        texts = [c["claim_text"] for c in _claims(READING)]
        assert "A delayed payment is likely to clear before the period ends." in texts
        assert "Avoid signing long contracts in a hurry this week." in texts
        assert "Focus on finishing open work rather than starting new projects this week." in texts
        assert not any(t.startswith("-") or "**" in t for t in texts)


@pytest.fixture(scope="module")
def env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    db = Session()
    kundli = crud.create_kundli(db, {
        "user_id": ME, "name": "Mine", "relation": "self",
        "birth_year": 1990, "birth_month": 3, "birth_day": 15,
        "birth_hour": 8, "birth_minute": 30,
        "birth_city": "Hyderabad", "birth_nation": "IN",
    }).id
    db.close()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@astrospace.dev", role="dev")
    try:
        yield {"client": TestClient(app), "kundli": kundli}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def test_a_new_version_retires_the_old_versions_unreviewed_claims(env):
    client, kundli = env["client"], env["kundli"]
    gen = lambda: client.post(f"/api/v1/readings/{kundli}/generate", json={"period": "weekly", "force_refresh": True})

    with patch.object(PeriodAgent, "run", return_value=READING):
        first = gen().json()
    claims = client.get(f"/api/v1/readings/{kundli}/claims").json()
    assert claims and all(c["reading_id"] == first["id"] for c in claims)
    assert all(c["reading_version"] == 1 for c in claims)
    kept = claims[0]
    client.patch(f"/api/v1/readings/{kundli}/claims/{kept['id']}", json={"status": "accurate"})

    with patch.object(PeriodAgent, "run", return_value=READING):
        second = gen().json()
    assert second["version"] == 2

    claims = client.get(f"/api/v1/readings/{kundli}/claims").json()
    from_first = [c for c in claims if c["reading_id"] == first["id"]]
    assert [c["id"] for c in from_first] == [kept["id"]], "only the reviewed claim of v1 survives"
    assert all(c["status"] != "pending" for c in from_first)
    assert any(c["reading_id"] == second["id"] for c in claims)

    everything = client.get(f"/api/v1/readings/{kundli}/claims?include_superseded=true").json()
    assert len(everything) > len(claims), "nothing is deleted; superseded claims are only hidden"
