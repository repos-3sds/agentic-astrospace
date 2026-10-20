"""Razorpay: plans and question packs bought on asksiddha.app/buy.

Google Play's Payments policy lets an app honour purchases made outside it, as
long as the app itself never links to or mentions the cheaper route (Hawk,
2026-10-20: "add Razorpay to asksiddha.app first"). So the website sells, the
server records the purchase in the same tables the Play webhook writes
(`SubscriptionGrant` / `QuestionCredit` with provider "razorpay"), and the app
just sees a plan.

Nothing the browser says is trusted. A purchase lands only after one of:
  - the checkout handler's signature checks out against the key secret and
    the subscription or order, fetched back from Razorpay, carries this
    person's user id in its notes (`confirm_*`), or
  - a webhook whose body is signed with the webhook secret (`apply_webhook`).
Both paths are idempotent on the Razorpay subscription or order id.

Configuration (all unset = the website shows no buy buttons):
    RAZORPAY_KEY_ID          rzp_live_... or rzp_test_...
    RAZORPAY_KEY_SECRET      secret
    RAZORPAY_WEBHOOK_SECRET  secret; the webhook answers 404 without it
    RAZORPAY_PLAN_IDS        siddha_plus_monthly=plan_X,siddha_practitioner_monthly=plan_Y
    RAZORPAY_ALLOWED_EMAILS  optional; when set, only these emails can buy
                             (for testing on the live site with test keys)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from sqlalchemy.orm import Session

from ..db.models import (
    BillingAccount,
    EntitlementAuditEvent,
    PlanAssignment,
    QuestionCredit,
    SubscriptionGrant,
)
from .products import PRODUCTS, Product
from .resolver import _billing_account

log = logging.getLogger("astrospace.razorpay")

PROVIDER = "razorpay"
API = "https://api.razorpay.com/v1"
TIER_RANK = {"free": 0, "plus": 1, "pro": 2}
# Razorpay keeps a subscription for this many monthly cycles; ten years is "until cancelled".
TOTAL_CYCLES = 120
# A renewal is charged at current_end and its webhook can lag; access runs a day past it.
RENEWAL_SLACK = timedelta(days=1)
# After a failed renewal Razorpay retries for a few days before halting the subscription.
GRACE = timedelta(days=7)
LIVE_STATUSES = {"authenticated", "active"}


class RazorpayError(Exception):
    """Razorpay refused or could not be reached; the message is safe to show."""


@dataclass(frozen=True)
class Config:
    key_id: str
    key_secret: str
    plan_ids: dict[str, str]
    allowed_emails: frozenset[str]

    @property
    def test_mode(self) -> bool:
        return self.key_id.startswith("rzp_test_")


def config() -> Config | None:
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    plan_ids = {}
    for pair in os.getenv("RAZORPAY_PLAN_IDS", "").split(","):
        product_id, _, plan_id = pair.partition("=")
        if product_id.strip() in PRODUCTS and plan_id.strip():
            plan_ids[product_id.strip()] = plan_id.strip()
    if not key_id or not key_secret:
        return None
    allowed = frozenset(
        email.strip().casefold() for email in os.getenv("RAZORPAY_ALLOWED_EMAILS", "").split(",") if email.strip()
    )
    return Config(key_id, key_secret, plan_ids, allowed)


def sellable(cfg: Config) -> list[Product]:
    """Packs are always sellable; a plan only once its Razorpay plan id is set."""
    return [p for p in PRODUCTS.values() if p.kind == "question_pack" or p.id in cfg.plan_ids]


def may_buy(cfg: Config, email: str | None) -> bool:
    return not cfg.allowed_emails or (email or "").casefold() in cfg.allowed_emails


# --- Razorpay API -----------------------------------------------------------

_http = requests.Session()


def _call(cfg: Config, method: str, path: str, body: dict | None = None) -> dict:
    try:
        response = _http.request(method, f"{API}{path}", json=body, auth=(cfg.key_id, cfg.key_secret), timeout=10)
    except requests.RequestException as exc:
        log.warning("razorpay %s %s failed: %s", method, path, exc)
        raise RazorpayError("The payment service did not answer. Please try again.") from exc
    if response.status_code >= 400:
        log.warning("razorpay %s %s returned %s: %s", method, path, response.status_code, response.text[:300])
        raise RazorpayError("The payment service refused this request. Please try again.")
    return response.json()


def create_subscription(cfg: Config, product: Product, user_id: str) -> dict:
    return _call(cfg, "POST", "/subscriptions", {
        "plan_id": cfg.plan_ids[product.id], "total_count": TOTAL_CYCLES, "quantity": 1,
        "customer_notify": 1, "notes": {"user_id": user_id, "product_id": product.id},
    })


def create_order(cfg: Config, product: Product, user_id: str) -> dict:
    return _call(cfg, "POST", "/orders", {
        "amount": product.price_inr * 100, "currency": "INR",
        "receipt": f"{product.id}:{user_id[:20]}",
        "notes": {"user_id": user_id, "product_id": product.id},
    })


def fetch_subscription(cfg: Config, subscription_id: str) -> dict:
    return _call(cfg, "GET", f"/subscriptions/{subscription_id}")


def fetch_order(cfg: Config, order_id: str) -> dict:
    return _call(cfg, "GET", f"/orders/{order_id}")


def cancel_subscription(cfg: Config, subscription_id: str, *, at_cycle_end: bool = True) -> dict:
    return _call(cfg, "POST", f"/subscriptions/{subscription_id}/cancel",
                 {"cancel_at_cycle_end": 1 if at_cycle_end else 0})


# --- Signatures -------------------------------------------------------------

def _hmac(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def checkout_signature_ok(cfg: Config, *, payment_id: str, signature: str,
                          subscription_id: str | None = None, order_id: str | None = None) -> bool:
    # Razorpay signs "payment|subscription" for subscriptions and "order|payment" for orders.
    if subscription_id:
        message = f"{payment_id}|{subscription_id}"
    elif order_id:
        message = f"{order_id}|{payment_id}"
    else:
        return False
    return hmac.compare_digest(_hmac(cfg.key_secret, message.encode()), signature or "")


def webhook_signature_ok(body: bytes, signature: str | None) -> bool | None:
    """None when no webhook secret is configured (the route then 404s)."""
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
    if not secret:
        return None
    return bool(signature) and hmac.compare_digest(_hmac(secret, body), signature)


# --- Applying purchases -----------------------------------------------------

def _ts(value) -> datetime | None:
    return datetime.utcfromtimestamp(int(value)) if value else None


def _bump(account: BillingAccount) -> int:
    account.entitlement_revision += 1
    return account.entitlement_revision


def audit(db: Session, account: BillingAccount, user_id: str, action: str, detail: dict) -> None:
    db.add(EntitlementAuditEvent(billing_account_id=account.id, user_id=user_id, action=action, detail=detail))


def _grant_valid(grant: SubscriptionGrant | None, now: datetime) -> bool:
    if grant is None or not grant.verified_at:
        return False
    if grant.state == "active":
        return grant.expires_at is None or grant.expires_at > now
    return grant.state == "grace" and bool(grant.grace_ends_at and grant.grace_ends_at > now)


def _assign(db: Session, account: BillingAccount, grant: SubscriptionGrant, product: Product, now: datetime) -> None:
    """Point the account at this grant, unless a better live plan already holds it.

    A late event for a Plus subscription must not knock a reader who has since
    moved up to Practitioner back down to Plus.
    """
    current = (
        db.query(PlanAssignment).filter_by(billing_account_id=account.id)
        .order_by(PlanAssignment.revision.desc()).first()
    )
    if current and current.source_grant_id == grant.id and current.access_tier == product.tier:
        return
    if current and current.source_grant_id and current.source_grant_id != grant.id:
        holder = db.get(SubscriptionGrant, current.source_grant_id)
        if _grant_valid(holder, now) and TIER_RANK.get(current.access_tier, 0) > TIER_RANK[product.tier]:
            return
    db.add(PlanAssignment(
        billing_account_id=account.id, access_tier=product.tier, account_topology=account.kind,
        offer_code=product.id, source_grant_id=grant.id, effective_at=now, revision=_bump(account),
    ))


def live_plan_grants(db: Session, account: BillingAccount, now: datetime) -> list[SubscriptionGrant]:
    """Every paid plan this account holds right now, from any store."""
    grants = db.query(SubscriptionGrant).filter(
        SubscriptionGrant.billing_account_id == account.id,
        SubscriptionGrant.state.in_(("active", "grace")),
    ).all()
    return [g for g in grants if _grant_valid(g, now)]


def apply_subscription(db: Session, entity: dict, now: datetime, *, event: str) -> str:
    """Bring our record of one Razorpay subscription in line with `entity`.

    `entity` is a subscription as Razorpay returns it (from the API or a
    signed webhook); its notes say whose it is and which product it sells.
    """
    notes = entity.get("notes") or {}
    user_id = str(notes.get("user_id") or "")
    product = PRODUCTS.get(str(notes.get("product_id") or ""))
    if not user_id or product is None or product.kind != "plan":
        return "ignored"
    status = entity.get("status")
    sub_id = str(entity["id"])
    account = _billing_account(db, user_id)
    grant = db.query(SubscriptionGrant).filter_by(provider=PROVIDER, provider_transaction_id=sub_id).one_or_none()
    if grant is None:
        if status not in LIVE_STATUSES:
            return "ignored_unknown_grant"
        grant = SubscriptionGrant(
            billing_account_id=account.id, provider=PROVIDER,
            provider_product_id=product.id, provider_transaction_id=sub_id,
        )
        db.add(grant)
        db.flush()

    current_end = _ts(entity.get("current_end"))
    grant.last_event_at = now
    if status in LIVE_STATUSES:
        grant.state = "active"
        grant.starts_at = grant.starts_at or _ts(entity.get("start_at")) or now
        # Right after checkout the first cycle may not be stamped yet; the
        # activation webhook replaces this with Razorpay's own date.
        grant.expires_at = (current_end + RENEWAL_SLACK) if current_end else now + timedelta(days=31)
        grant.renews_at = current_end
        grant.grace_ends_at = None
        grant.verified_at = grant.verified_at or now
        _assign(db, account, grant, product, now)
        _bump(account)
        outcome = "activated"
    elif status == "pending":
        # A renewal failed and Razorpay is retrying: keep the plan on meanwhile.
        grant.state = "grace"
        grant.grace_ends_at = (current_end or now) + GRACE
        _bump(account)
        outcome = "grace"
    elif status == "cancelled" and current_end and current_end > now:
        # Cancelled with time left: no more charges, access runs to the end of the paid month.
        grant.renews_at = None
        grant.expires_at = current_end
        _bump(account)
        outcome = "will_not_renew"
    elif status in {"cancelled", "halted", "completed", "expired"}:
        grant.state = "expired"
        grant.renews_at = None
        _bump(account)
        outcome = "expired"
    else:
        return "ignored_status"
    audit(db, account, user_id, f"store.{outcome}", {
        "provider": PROVIDER, "event": event, "subscription_id": sub_id, "product_id": product.id,
    })
    return outcome


def apply_order(db: Session, order: dict, now: datetime, *, event: str) -> str:
    """Credit a paid question-pack order once."""
    notes = order.get("notes") or {}
    user_id = str(notes.get("user_id") or "")
    product = PRODUCTS.get(str(notes.get("product_id") or ""))
    if not user_id or product is None or product.kind != "question_pack" or order.get("status") != "paid":
        return "ignored"
    if int(order.get("amount_paid") or order.get("amount") or 0) < product.price_inr * 100:
        log.warning("razorpay order %s paid less than %s", order.get("id"), product.id)
        return "ignored_amount"
    order_id = str(order["id"])
    if db.query(QuestionCredit.id).filter_by(provider=PROVIDER, provider_transaction_id=order_id).first():
        return "duplicate"
    account = _billing_account(db, user_id)
    db.add(QuestionCredit(
        billing_account_id=account.id, provider=PROVIDER, provider_product_id=product.id,
        provider_transaction_id=order_id, quantity=product.questions, remaining=product.questions,
    ))
    _bump(account)
    audit(db, account, user_id, "store.credited", {
        "provider": PROVIDER, "event": event, "order_id": order_id, "product_id": product.id,
    })
    return "credited"


def apply_refund(db: Session, cfg: Config | None, payment: dict, refund: dict, now: datetime) -> str:
    """A full refund takes back what the payment bought; a partial one changes nothing."""
    if int(refund.get("amount") or 0) < int(payment.get("amount") or 0):
        return "ignored_partial_refund"
    if payment.get("order_id"):
        credit = db.query(QuestionCredit).filter_by(
            provider=PROVIDER, provider_transaction_id=str(payment["order_id"])).one_or_none()
        if credit and credit.revoked_at is None:
            credit.revoked_at = now
            account = db.get(BillingAccount, credit.billing_account_id)
            _bump(account)
            audit(db, account, account.owner_user_id, "store.revoked", {
                "provider": PROVIDER, "order_id": credit.provider_transaction_id, "payment_id": payment.get("id"),
            })
            return "revoked"
    subscription_id = payment.get("subscription_id")
    if not subscription_id and payment.get("invoice_id") and cfg is not None:
        # Subscription payments name their invoice; the invoice names the subscription.
        try:
            subscription_id = _call(cfg, "GET", f"/invoices/{payment['invoice_id']}").get("subscription_id")
        except RazorpayError:
            subscription_id = None
    if subscription_id:
        grant = db.query(SubscriptionGrant).filter_by(
            provider=PROVIDER, provider_transaction_id=str(subscription_id)).one_or_none()
        if grant and grant.state != "revoked":
            grant.state = "revoked"
            grant.renews_at = None
            account = db.get(BillingAccount, grant.billing_account_id)
            _bump(account)
            audit(db, account, account.owner_user_id, "store.revoked", {
                "provider": PROVIDER, "subscription_id": subscription_id, "payment_id": payment.get("id"),
            })
            return "revoked"
    return "ignored"


def apply_webhook(db: Session, payload: dict, now: datetime) -> str:
    event = str(payload.get("event") or "")
    body = payload.get("payload") or {}
    entity = lambda name: (body.get(name) or {}).get("entity") or {}  # noqa: E731
    if event.startswith("subscription.") and entity("subscription"):
        return apply_subscription(db, entity("subscription"), now, event=event)
    if event == "order.paid" and entity("order"):
        return apply_order(db, entity("order"), now, event=event)
    if event in {"refund.processed", "payment.refunded"} and entity("payment"):
        refund = entity("refund") or {"amount": entity("payment").get("amount_refunded")}
        return apply_refund(db, config(), entity("payment"), refund, now)
    return "ignored_event"


def cancel_for_deleted_account(db: Session, user_id: str) -> None:
    """Stop billing a person who deletes their account. Best effort: an outage
    must not block the deletion, and Razorpay's own dashboard can finish it."""
    cfg = config()
    if cfg is None:
        return
    account = db.query(BillingAccount).filter_by(owner_user_id=user_id, kind="individual").one_or_none()
    if account is None:
        return
    grants = db.query(SubscriptionGrant).filter(
        SubscriptionGrant.billing_account_id == account.id,
        SubscriptionGrant.provider == PROVIDER,
        SubscriptionGrant.state.in_(("active", "grace", "pending")),
    ).all()
    for grant in grants:
        try:
            cancel_subscription(cfg, grant.provider_transaction_id, at_cycle_end=False)
        except RazorpayError:
            log.error("could not cancel razorpay subscription %s for a deleted account",
                      grant.provider_transaction_id)
