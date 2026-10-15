"""D2 hybrid pricing: Ask credits are reserved before an answer, spent only
when a verified answer is delivered, and never spent on a refusal, refer-out
or failure. Monthly allowance first, then question packs."""
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.agents.domain_agent import DomainReadingAgent
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import QuestionCredit, UsageBucket
from astrospace.entitlements import EntitlementDenied, resolve_entitlements
from astrospace.entitlements.usage import (
    commit_ask_credit,
    month_bounds,
    release_ask_credit,
    reserve_ask_credit,
)
from main import app
from tests.test_ask_cost_logging import _generate

ME = "credit-reader"
BIRTH = {
    "name": "Reader", "relation": "self",
    "birth_year": 1991, "birth_month": 8, "birth_day": 14, "birth_hour": 6, "birth_minute": 12,
    "birth_city": "Vijayawada", "birth_nation": "IN",
}


@pytest.fixture()
def env():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    with factory() as db:
        kundli = crud.create_kundli(db, {"user_id": ME, **BIRTH}).id
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME, email="me@example.com", role="dev")
    try:
        yield TestClient(app), factory, kundli
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _bucket(db):
    return db.query(UsageBucket).filter_by(entitlement_key="ask.answers.period").one()


def _pack(db, quantity=3, txn="t1"):
    account_id = resolve_entitlements(db, ME).account_id
    db.add(QuestionCredit(
        billing_account_id=account_id, provider="test", provider_product_id="astrospace_questions_3",
        provider_transaction_id=txn, quantity=quantity, remaining=quantity,
    ))
    db.commit()


def test_month_bounds_roll_over_the_year():
    assert month_bounds(datetime(2026, 12, 31, 23))[0] == "2026-12"
    _, start, end = month_bounds(datetime(2026, 12, 5))
    assert (start, end) == (datetime(2026, 12, 1), datetime(2027, 1, 1))


def test_allowance_then_pack_then_limit_when_enforced(env, monkeypatch):
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    _, factory, _ = env
    with factory() as db:
        for _ in range(3):
            commit_ask_credit(db, reserve_ask_credit(db, ME))
        assert _bucket(db).consumed == 3
        _pack(db, quantity=1)
        held = reserve_ask_credit(db, ME)
        assert held.kind == "pack"
        commit_ask_credit(db, held)
        assert db.query(QuestionCredit).one().remaining == 0
        with pytest.raises(EntitlementDenied) as denied:
            reserve_ask_credit(db, ME)
        assert denied.value.decision.denial()["code"] == "entitlement_limit_reached"
        assert denied.value.decision.resets_at


def test_released_credits_come_back(env, monkeypatch):
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    _, factory, _ = env
    with factory() as db:
        _pack(db, quantity=2)
        for _ in range(3):
            commit_ask_credit(db, reserve_ask_credit(db, ME))
        held = reserve_ask_credit(db, ME)
        release_ask_credit(db, held)
        release_ask_credit(db, held)  # idempotent
        assert db.query(QuestionCredit).one().remaining == 2
        assert resolve_entitlements(db, ME).question_credits == 2


def test_not_enforced_counts_but_never_blocks(env, monkeypatch):
    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED", raising=False)
    _, factory, _ = env
    with factory() as db:
        for _ in range(5):
            commit_ask_credit(db, reserve_ask_credit(db, ME))
        assert _bucket(db).consumed == 5
        decision = resolve_entitlements(db, ME).decide("ask.answers.period")
        assert decision.allowed and decision.reason == "not_enforced"


def test_answered_question_spends_one_credit(env):
    client, factory, kundli = env
    with patch.object(DomainReadingAgent, "run_structured_reading", autospec=True, side_effect=_generate):
        response = client.post(f"/api/v1/ask/{kundli}", json={"question": "How is my career progressing?"})
    assert response.json()["status"] == "answered"
    with factory() as db:
        assert (_bucket(db).consumed, _bucket(db).reserved) == (1, 0)


def test_failed_answer_is_not_charged(env):
    client, factory, kundli = env

    def boom(self, messages):
        raise RuntimeError("model down")

    with patch.object(DomainReadingAgent, "run_structured_reading", autospec=True, side_effect=boom):
        response = client.post(f"/api/v1/ask/{kundli}", json={"question": "How is my career progressing?"})
    assert response.status_code == 502
    with factory() as db:
        assert (_bucket(db).consumed, _bucket(db).reserved) == (0, 0)


def test_refer_out_never_touches_a_credit(env):
    client, factory, kundli = env
    response = client.post(f"/api/v1/ask/{kundli}", json={"question": "When will I die?"})
    assert response.json()["status"] == "refer_out"
    with factory() as db:
        assert db.query(UsageBucket).count() == 0


def test_streamed_answer_spends_and_limit_is_a_402_before_streaming(env, monkeypatch):
    client, factory, kundli = env
    with patch.object(DomainReadingAgent, "run_structured_reading", autospec=True, side_effect=_generate):
        with client.stream("POST", f"/api/v1/ask/{kundli}/stream",
                           json={"question": "How is my career progressing?"}) as response:
            body = "".join(response.iter_text())
    assert '"status": "answered"' in body
    with factory() as db:
        assert (_bucket(db).consumed, _bucket(db).reserved) == (1, 0)
        bucket = _bucket(db)
        bucket.consumed = 3
        db.commit()
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    denied = client.post(f"/api/v1/ask/{kundli}/stream", json={"question": "How is my career progressing?"})
    assert denied.status_code == 402
    assert denied.json()["code"] == "entitlement_limit_reached"


def test_third_profile_needs_plus_when_enforced(env, monkeypatch):
    client, _, _ = env
    partner = {**BIRTH, "name": "Partner", "relation": "spouse"}
    assert client.post("/api/v1/kundlis", json=partner).status_code == 201
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    third = client.post("/api/v1/kundlis", json={**partner, "name": "Child", "relation": "child"})
    assert third.status_code == 402
    assert third.json()["entitlement"] == "profiles.max"
    assert third.json()["upgrade_options"][0] == "plus"


def test_products_list_d2_prices(env):
    client, _, _ = env
    products = {p["id"]: p for p in client.get("/api/v1/entitlements/products").json()["products"]}
    assert products["astrospace_plus_monthly"]["price_inr"] == 299
    assert products["astrospace_plus_yearly"]["price_inr"] == 1999
    assert products["astrospace_questions_3"]["questions"] == 3
