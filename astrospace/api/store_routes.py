"""RevenueCat webhook: the only way a store purchase reaches entitlements (D5).

The phone starts a purchase through RevenueCat's SDK; RevenueCat validates
the receipt with Apple or Google and posts the result here. Nothing the app
says about a purchase is trusted. Each event resolves through
`entitlements/products.py` to either a plan (a SubscriptionGrant plus the
PlanAssignment that points at it) or a question pack (a QuestionCredit row).

Disabled (404) until REVENUECAT_WEBHOOK_AUTH is set; RevenueCat sends that
value as the Authorization header on every call, and it is compared in
constant time. Events are idempotent: a retried delivery lands on the same
grant or credit row by its store transaction id.

Refunds: a CANCELLATION whose reason is a refund (CUSTOMER_SUPPORT) revokes
the grant or the unspent credits. Any other cancellation only turns
auto-renew off; the plan runs to its expiry and EXPIRATION ends it.
"""
import hmac
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..db.models import (
    BillingAccount,
    EntitlementAuditEvent,
    PlanAssignment,
    QuestionCredit,
    SubscriptionGrant,
)
from ..entitlements.products import PRODUCTS
from ..entitlements.resolver import _billing_account

log = logging.getLogger("astrospace.store")
router = APIRouter(prefix="/api/v1/store", tags=["store"])

PROVIDER = "revenuecat"
ACTIVATING = {"INITIAL_PURCHASE", "RENEWAL", "UNCANCELLATION", "PRODUCT_CHANGE", "SUBSCRIPTION_EXTENDED"}
REFUND_REASONS = {"CUSTOMER_SUPPORT"}


def _ms(value) -> datetime | None:
    return datetime.utcfromtimestamp(int(value) / 1000) if value else None


def _authorised(header: str | None) -> None:
    secret = os.getenv("REVENUECAT_WEBHOOK_AUTH", "")
    if not secret:
        raise HTTPException(status_code=404, detail="Not found")
    if not header or not hmac.compare_digest(header.encode(), secret.encode()):
        raise HTTPException(status_code=401, detail="Unauthorised")


def _bump(db: Session, account: BillingAccount) -> int:
    account.entitlement_revision += 1
    return account.entitlement_revision


def _audit(db: Session, account: BillingAccount, user_id: str, action: str, detail: dict) -> None:
    db.add(EntitlementAuditEvent(
        billing_account_id=account.id, user_id=user_id, action=action, detail=detail,
    ))


def _apply_plan(db: Session, account: BillingAccount, event: dict, product, now: datetime) -> str:
    kind = event["type"]
    txn = str(event.get("original_transaction_id") or event.get("transaction_id"))
    grant = db.query(SubscriptionGrant).filter_by(provider=PROVIDER, provider_transaction_id=txn).one_or_none()
    if grant is None:
        if kind not in ACTIVATING and kind != "BILLING_ISSUE":
            return "ignored_unknown_grant"
        grant = SubscriptionGrant(
            billing_account_id=account.id, provider=PROVIDER,
            provider_product_id=product.id, provider_transaction_id=txn,
        )
        db.add(grant)
        db.flush()

    grant.last_event_at = now
    grant.provider_product_id = product.id
    if kind in ACTIVATING:
        grant.state = "active"
        grant.starts_at = grant.starts_at or _ms(event.get("purchased_at_ms")) or now
        grant.expires_at = _ms(event.get("expiration_at_ms"))
        grant.renews_at = grant.expires_at
        grant.grace_ends_at = None
        grant.verified_at = now
        current = (
            db.query(PlanAssignment)
            .filter_by(billing_account_id=account.id)
            .order_by(PlanAssignment.revision.desc())
            .first()
        )
        if not current or current.source_grant_id != grant.id or current.access_tier != product.tier:
            revision = _bump(db, account)
            db.add(PlanAssignment(
                billing_account_id=account.id, access_tier=product.tier,
                account_topology=account.kind, offer_code=product.id,
                source_grant_id=grant.id, effective_at=now, revision=revision,
            ))
        return "activated"
    if kind == "BILLING_ISSUE":
        grant.state = "grace"
        grant.grace_ends_at = _ms(event.get("grace_period_expiration_at_ms")) or grant.expires_at
        _bump(db, account)
        return "grace"
    if kind == "CANCELLATION":
        if event.get("cancel_reason") in REFUND_REASONS:
            grant.state = "revoked"
            _bump(db, account)
            return "revoked"
        grant.renews_at = None
        return "will_not_renew"
    if kind == "EXPIRATION":
        grant.state = "expired"
        _bump(db, account)
        return "expired"
    return "ignored_event"


def _apply_pack(db: Session, account: BillingAccount, event: dict, product, now: datetime) -> str:
    kind = event["type"]
    txn = str(event.get("transaction_id"))
    credit = db.query(QuestionCredit).filter_by(provider=PROVIDER, provider_transaction_id=txn).one_or_none()
    if kind in {"NON_RENEWING_PURCHASE", "INITIAL_PURCHASE"}:
        if credit:
            return "duplicate"
        db.add(QuestionCredit(
            billing_account_id=account.id, provider=PROVIDER, provider_product_id=product.id,
            provider_transaction_id=txn, quantity=product.questions, remaining=product.questions,
        ))
        _bump(db, account)
        return "credited"
    if kind == "CANCELLATION" and credit and credit.revoked_at is None:
        # A refunded pack loses whatever is left of it; answers already given stay given.
        credit.revoked_at = now
        _bump(db, account)
        return "revoked"
    return "ignored_event"


@router.post("/revenuecat/webhook")
def revenuecat_webhook(
    payload: dict,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _authorised(authorization)
    event = payload.get("event") or {}
    kind = event.get("type")
    user_id = event.get("app_user_id")
    product = PRODUCTS.get(str(event.get("product_id", "")).split(":")[0])
    if kind == "TEST" or not user_id or product is None or str(user_id).startswith("$RCAnonymousID"):
        # Unknown products and anonymous buyers are acknowledged, never applied:
        # RevenueCat retries anything that is not a 2xx.
        log.info("revenuecat event not applied: type=%s product=%s", kind, event.get("product_id"))
        return {"status": "ignored"}
    now = datetime.utcnow()
    account = _billing_account(db, str(user_id))
    apply = _apply_plan if product.kind == "plan" else _apply_pack
    outcome = apply(db, account, event, product, now)
    _audit(db, account, str(user_id), f"store.{outcome}", {
        "event_id": event.get("id"), "type": kind, "product_id": product.id,
        "environment": event.get("environment"), "store": event.get("store"),
    })
    db.commit()
    return {"status": outcome}
