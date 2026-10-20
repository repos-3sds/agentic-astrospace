"""Website checkout over Razorpay: only verified payments become plans and
credits, on the account that paid; retries and late events are harmless."""
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrospace.api.auth import AuthUser, current_user
from astrospace.db import get_db
from astrospace.db.database import Base
from astrospace.db.models import SubscriptionGrant
from astrospace.entitlements import razorpay, resolve_entitlements
from main import app

USER = "web-buyer"
KEY_SECRET = "key-secret"
WEBHOOK_SECRET = "hook-secret"


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
    app.dependency_overrides[current_user] = lambda: AuthUser(id=USER, email="buyer@example.com", auth_enabled=True)
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abc")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("RAZORPAY_PLAN_IDS", "siddha_plus_monthly=plan_plus,siddha_practitioner_monthly=plan_pro")
    monkeypatch.delenv("RAZORPAY_ALLOWED_EMAILS", raising=False)
    remote: dict[str, dict] = {}
    calls: list[tuple] = []

    def fake_call(cfg, method, path, body=None):
        calls.append((method, path, body))
        if method == "POST" and path == "/subscriptions":
            sub = {"id": f"sub_{len(remote)}", "status": "created", "notes": body["notes"]}
            remote[sub["id"]] = sub
            return sub
        if method == "POST" and path == "/orders":
            order = {"id": f"order_{len(remote)}", "status": "created", "amount": body["amount"],
                     "currency": "INR", "notes": body["notes"]}
            remote[order["id"]] = order
            return order
        if method == "POST" and path.endswith("/cancel"):
            sub = remote[path.split("/")[2]]
            return sub
        if method == "GET":
            return remote[path.split("/")[2]]
        raise AssertionError(path)

    monkeypatch.setattr(razorpay, "_call", fake_call)
    try:
        yield TestClient(app), factory, remote, calls
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _sig(message: str, secret: str = KEY_SECRET) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _hook(client, event: str, **entities):
    body = json.dumps({"event": event, "payload": {k: {"entity": v} for k, v in entities.items()}}).encode()
    return client.post("/api/v1/store/razorpay/webhook", content=body,
                       headers={"X-Razorpay-Signature": _sig(body.decode(), WEBHOOK_SECRET)})


def _live(sub: dict, days: int = 30) -> dict:
    now = int(time.time())
    sub.update(status="active", start_at=now, current_start=now, current_end=now + days * 86400)
    return sub


def test_config_is_closed_without_keys(env, monkeypatch):
    client, *_ = env
    monkeypatch.delenv("RAZORPAY_KEY_ID")
    assert client.get("/api/v1/store/web/config").json() == {"enabled": False}
    assert client.post("/api/v1/store/web/checkout", json={"product_id": "siddha_plus_monthly"}).status_code == 404


def test_plan_checkout_then_confirm_turns_plus_on(env):
    client, factory, remote, _ = env
    checkout = client.post("/api/v1/store/web/checkout", json={"product_id": "siddha_plus_monthly"}).json()
    sub_id = checkout["subscription_id"]
    assert remote[sub_id]["notes"] == {"user_id": USER, "product_id": "siddha_plus_monthly"}
    _live(remote[sub_id])
    paid = {"razorpay_payment_id": "pay_1", "razorpay_subscription_id": sub_id,
            "razorpay_signature": _sig(f"pay_1|{sub_id}")}
    response = client.post("/api/v1/store/web/confirm", json=paid).json()
    assert response["status"] == "activated"
    assert response["web_plans"][0]["tier"] == "plus"
    with factory() as db:
        snapshot = resolve_entitlements(db, USER)
        assert snapshot.access_tier == "plus"
        assert snapshot.source == "razorpay"
    # The webhook for the same subscription changes nothing.
    assert _hook(client, "subscription.activated", subscription=remote[sub_id]).json()["status"] == "activated"
    with factory() as db:
        assert db.query(SubscriptionGrant).count() == 1
    # Plus can't be bought twice.
    again = client.post("/api/v1/store/web/checkout", json={"product_id": "siddha_plus_monthly"})
    assert again.status_code == 409


def test_forged_signature_is_refused(env):
    client, factory, remote, _ = env
    sub_id = client.post("/api/v1/store/web/checkout", json={"product_id": "siddha_plus_monthly"}).json()["subscription_id"]
    _live(remote[sub_id])
    bad = {"razorpay_payment_id": "pay_1", "razorpay_subscription_id": sub_id, "razorpay_signature": "0" * 64}
    assert client.post("/api/v1/store/web/confirm", json=bad).status_code == 400
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"


def test_someone_elses_payment_does_not_apply(env):
    client, factory, remote, _ = env
    remote["sub_x"] = _live({"id": "sub_x", "notes": {"user_id": "someone-else", "product_id": "siddha_plus_monthly"}})
    paid = {"razorpay_payment_id": "pay_9", "razorpay_subscription_id": "sub_x", "razorpay_signature": _sig("pay_9|sub_x")}
    assert client.post("/api/v1/store/web/confirm", json=paid).status_code == 403


def test_question_pack_order_credits_once(env):
    client, factory, remote, _ = env
    checkout = client.post("/api/v1/store/web/checkout", json={"product_id": "siddha_questions_3"}).json()
    order_id = checkout["order_id"]
    assert checkout["amount"] == 13000
    remote[order_id].update(status="paid", amount_paid=13000)
    paid = {"razorpay_payment_id": "pay_2", "razorpay_order_id": order_id, "razorpay_signature": _sig(f"{order_id}|pay_2")}
    assert client.post("/api/v1/store/web/confirm", json=paid).json()["status"] == "credited"
    assert _hook(client, "order.paid", order=remote[order_id]).json()["status"] == "duplicate"
    with factory() as db:
        before = resolve_entitlements(db, USER).question_credits
    # A full refund removes what is left of the pack.
    payment = {"id": "pay_2", "amount": 13000, "order_id": order_id}
    assert _hook(client, "refund.processed", payment=payment, refund={"amount": 13000}).json()["status"] == "revoked"
    with factory() as db:
        assert resolve_entitlements(db, USER).question_credits == before - 3


def test_webhook_signature_is_required(env, monkeypatch):
    client, *_ = env
    body = b'{"event": "order.paid", "payload": {}}'
    response = client.post("/api/v1/store/razorpay/webhook", content=body, headers={"X-Razorpay-Signature": "nope"})
    assert response.status_code == 401
    monkeypatch.delenv("RAZORPAY_WEBHOOK_SECRET")
    assert client.post("/api/v1/store/razorpay/webhook", content=body).status_code == 404


def test_renewal_failure_cancel_and_expiry(env):
    client, factory, remote, _ = env
    sub = _live({"id": "sub_r", "notes": {"user_id": USER, "product_id": "siddha_plus_monthly"}})
    remote["sub_r"] = sub
    assert _hook(client, "subscription.activated", subscription=sub).json()["status"] == "activated"
    # A failed renewal keeps the plan on while Razorpay retries.
    assert _hook(client, "subscription.pending", subscription={**sub, "status": "pending"}).json()["status"] == "grace"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "plus"
    assert _hook(client, "subscription.charged", subscription=sub).json()["status"] == "activated"
    # Stopping renewal from the website keeps the paid month.
    status = client.post("/api/v1/store/web/cancel", json={"subscription_id": "sub_r"}).json()
    assert status["web_plans"][0]["renews_at"] is None
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "plus"
    # Razorpay's cancelled event at the end of the month ends it.
    ended = {**sub, "status": "cancelled", "current_end": int(time.time()) - 60}
    assert _hook(client, "subscription.cancelled", subscription=ended).json()["status"] == "expired"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"


def test_late_plus_event_does_not_undo_an_upgrade(env):
    client, factory, remote, _ = env
    plus = _live({"id": "sub_plus", "notes": {"user_id": USER, "product_id": "siddha_plus_monthly"}})
    pro = _live({"id": "sub_pro", "notes": {"user_id": USER, "product_id": "siddha_practitioner_monthly"}})
    _hook(client, "subscription.activated", subscription=plus)
    _hook(client, "subscription.activated", subscription=pro)
    _hook(client, "subscription.charged", subscription=plus)
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "pro"


def test_allow_list_limits_who_can_buy(env, monkeypatch):
    client, *_ = env
    monkeypatch.setenv("RAZORPAY_ALLOWED_EMAILS", "hawk@example.com")
    response = client.post("/api/v1/store/web/checkout", json={"product_id": "siddha_questions_1"})
    assert response.status_code == 403
    assert client.get("/api/v1/store/web/me").json()["may_buy"] is False


def test_unknown_product_is_not_sold(env):
    client, *_ = env
    assert client.post("/api/v1/store/web/checkout", json={"product_id": "nope"}).status_code == 404


def test_refund_of_a_subscription_payment_ends_the_plan(env):
    client, factory, remote, _ = env
    sub = _live({"id": "sub_f", "notes": {"user_id": USER, "product_id": "siddha_plus_monthly"}})
    remote["sub_f"] = sub
    remote["inv_1"] = {"id": "inv_1", "subscription_id": "sub_f"}
    _hook(client, "subscription.activated", subscription=sub)
    payment = {"id": "pay_5", "amount": 30000, "invoice_id": "inv_1"}
    assert _hook(client, "refund.processed", payment=payment, refund={"amount": 30000}).json()["status"] == "revoked"
    with factory() as db:
        assert resolve_entitlements(db, USER).access_tier == "free"

