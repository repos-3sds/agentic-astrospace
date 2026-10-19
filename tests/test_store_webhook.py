"""RevenueCat webhook (D5): verified store events become plans and question
credits; nothing the app claims is trusted; retries are idempotent."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.db import get_db
from astrospace.db.database import Base
from astrospace.db.models import QuestionCredit
from astrospace.entitlements import resolve_entitlements
from main import app

USER = "store-buyer"
AUTH = {"Authorization": "Bearer test-webhook-secret"}


@pytest.fixture()
def env(monkeypatch):
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
    monkeypatch.setenv("REVENUECAT_WEBHOOK_AUTH", AUTH["Authorization"])
    try:
        yield TestClient(app), factory
    finally:
        app.dependency_overrides.pop(get_db, None)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


def _event(kind, product="siddha_plus_monthly", txn="txn-1", **extra):
    now = datetime.utcnow()
    return {"event": {
        "id": f"evt-{kind}-{txn}", "type": kind, "app_user_id": USER, "product_id": product,
        "transaction_id": txn, "original_transaction_id": txn,
        "purchased_at_ms": _ms(now), "expiration_at_ms": _ms(now + timedelta(days=30)),
        "environment": "PRODUCTION", "store": "PLAY_STORE", **extra,
    }}


def test_webhook_is_off_without_a_secret(env, monkeypatch):
    client, _ = env
    monkeypatch.delenv("REVENUECAT_WEBHOOK_AUTH")
    assert client.post("/api/v1/store/revenuecat/webhook", json=_event("INITIAL_PURCHASE")).status_code == 404


def test_wrong_secret_is_refused(env):
    client, _ = env
    response = client.post("/api/v1/store/revenuecat/webhook", json=_event("INITIAL_PURCHASE"),
                           headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_subscription_lifecycle(env):
    client, factory = env
    post = lambda body: client.post("/api/v1/store/revenuecat/webhook", json=body, headers=AUTH).json()["status"]
    assert post(_event("INITIAL_PURCHASE")) == "activated"
    assert post(_event("INITIAL_PURCHASE")) == "activated"  # retried delivery
    with factory() as db:
        snapshot = resolve_entitlements(db, USER)
        assert snapshot.access_tier == "plus"
        assert snapshot.entitlements["ask.answers.period"] == 30
    assert post(_event("CANCELLATION", cancel_reason="UNSUBSCRIBE")) == "will_not_renew"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "plus"
    assert post(_event("EXPIRATION")) == "expired"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"


def test_refund_revokes_the_plan(env):
    client, factory = env
    client.post("/api/v1/store/revenuecat/webhook", json=_event("INITIAL_PURCHASE"), headers=AUTH)
    client.post("/api/v1/store/revenuecat/webhook",
                json=_event("CANCELLATION", cancel_reason="CUSTOMER_SUPPORT"), headers=AUTH)
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"


def test_question_pack_credits_once_and_refund_revokes(env):
    client, factory = env
    pack = _event("NON_RENEWING_PURCHASE", product="siddha_questions_3", txn="pack-1")
    for _ in range(2):
        client.post("/api/v1/store/revenuecat/webhook", json=pack, headers=AUTH)
    with factory() as db:
        assert db.query(QuestionCredit).count() == 1
        assert resolve_entitlements(db, USER).question_credits == 3
    client.post("/api/v1/store/revenuecat/webhook",
                json=_event("CANCELLATION", product="siddha_questions_3", txn="pack-1",
                            cancel_reason="CUSTOMER_SUPPORT"), headers=AUTH)
    with factory() as db:
        assert resolve_entitlements(db, USER).question_credits == 0


def test_unknown_product_and_anonymous_buyer_are_acknowledged_not_applied(env):
    client, factory = env
    for body in (_event("INITIAL_PURCHASE", product="something_else"),
                 {"event": {**_event("INITIAL_PURCHASE")["event"], "app_user_id": "$RCAnonymousID:abc"}}):
        assert client.post("/api/v1/store/revenuecat/webhook", json=body, headers=AUTH).json()["status"] == "ignored"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"


def _post(client, body):
    return client.post("/api/v1/store/revenuecat/webhook", json=body, headers=AUTH).json()["status"]


def test_sandbox_purchase_is_acknowledged_not_applied(env):
    client, factory = env
    assert _post(client, _event("INITIAL_PURCHASE", environment="SANDBOX")) == "ignored_sandbox"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"


def test_sandbox_applies_when_a_test_deployment_opts_in(env, monkeypatch):
    client, factory = env
    monkeypatch.setenv("REVENUECAT_ACCEPT_SANDBOX", "1")
    assert _post(client, _event("INITIAL_PURCHASE", environment="SANDBOX")) == "activated"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "plus"


def test_transfer_moves_the_plan_and_packs_to_the_new_account(env):
    client, factory = env
    other = "restoring-user"
    assert _post(client, _event("INITIAL_PURCHASE")) == "activated"
    assert _post(client, _event("NON_RENEWING_PURCHASE", product="siddha_questions_3", txn="pack-1")) == "credited"
    transfer = {"event": {
        "id": "evt-transfer", "type": "TRANSFER", "environment": "PRODUCTION", "store": "PLAY_STORE",
        "transferred_from": [USER], "transferred_to": [other],
    }}
    assert _post(client, transfer) == "transferred"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"
        assert resolve_entitlements(db, other).access_tier == "plus"
        credit = db.query(QuestionCredit).one()
        assert credit.billing_account_id == resolve_entitlements(db, other).account_id
    # A renewal for the new owner lands on the moved grant.
    renewal = _event("RENEWAL")
    renewal["event"]["app_user_id"] = other
    assert _post(client, renewal) == "activated"
    with factory() as db:
        assert resolve_entitlements(db, other).access_tier == "plus"
        assert resolve_entitlements(db, USER).access_tier == "free"


def test_transfer_with_nothing_to_move_is_acknowledged(env):
    client, _ = env
    transfer = {"event": {"id": "evt-t2", "type": "TRANSFER", "environment": "PRODUCTION",
                          "transferred_from": ["nobody"], "transferred_to": ["someone"]}}
    assert _post(client, transfer) == "nothing_to_transfer"
