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

Sandbox purchases (Play licence testers, TestFlight) are acknowledged and not
applied, so a test purchase never becomes a real plan, unless
REVENUECAT_ACCEPT_SANDBOX is set for a test deployment. A TRANSFER (a
restore signed in as someone else) moves the store purchases from the old
account to the new one, and the old account drops back to Free.
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


def _accepts(event: dict) -> bool:
    if event.get("environment", "PRODUCTION") == "PRODUCTION":
        return True
    return os.getenv("REVENUECAT_ACCEPT_SANDBOX", "").strip().lower() in {"1", "true", "yes"}


def _existing_account(db: Session, user_id: str) -> BillingAccount | None:
    return db.query(BillingAccount).filter_by(owner_user_id=user_id, kind="individual").one_or_none()


def _apply_transfer(db: Session, event: dict, now: datetime) -> dict:
    """Move every live store purchase from the old app_user_ids to the new one.

    The grant keeps its transaction id, so later renewals for the new owner
    land on it. The old account gets a Free assignment on top: the resolver
    reads the newest assignment, which still points at the moved grant.
    """
    to_ids = [str(u) for u in event.get("transferred_to") or [] if u and not str(u).startswith("$RCAnonymousID")]
    from_ids = [str(u) for u in event.get("transferred_from") or [] if u and not str(u).startswith("$RCAnonymousID")]
    if not to_ids or not from_ids:
        return {"status": "ignored"}
    target = _billing_account(db, to_ids[0])
    moved = 0
    for from_id in from_ids:
        if from_id == to_ids[0]:
            continue
        source = _existing_account(db, from_id)
        if source is None:
            continue
        grants = db.query(SubscriptionGrant).filter(
            SubscriptionGrant.billing_account_id == source.id,
            SubscriptionGrant.provider == PROVIDER,
            SubscriptionGrant.state.in_(("active", "grace")),
        ).all()
        credits = db.query(QuestionCredit).filter(
            QuestionCredit.billing_account_id == source.id,
            QuestionCredit.provider == PROVIDER,
            QuestionCredit.revoked_at.is_(None),
        ).all()
        if not grants and not credits:
            continue
        for credit in credits:
            credit.billing_account_id = target.id
        for grant in grants:
            grant.billing_account_id = target.id
            product = PRODUCTS.get(grant.provider_product_id)
            if product is not None and product.kind == "plan":
                db.add(PlanAssignment(
                    billing_account_id=target.id, access_tier=product.tier,
                    account_topology=target.kind, offer_code=product.id,
                    source_grant_id=grant.id, effective_at=now, revision=_bump(db, target),
                ))
        if grants:
            db.add(PlanAssignment(
                billing_account_id=source.id, access_tier="free", account_topology=source.kind,
                offer_code=None, source_grant_id=None, effective_at=now, revision=_bump(db, source),
            ))
        else:
            _bump(db, source)
        _audit(db, source, from_id, "store.transferred_out", {
            "event_id": event.get("id"), "to": to_ids[0], "grants": len(grants), "credits": len(credits),
        })
        moved += len(grants) + len(credits)
    if moved:
        _bump(db, target)
    _audit(db, target, to_ids[0], "store.transferred_in", {"event_id": event.get("id"), "items": moved})
    db.commit()
    return {"status": "transferred" if moved else "nothing_to_transfer"}


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
    if not _accepts(event):
        log.info("revenuecat %s event not applied: type=%s", event.get("environment"), kind)
        return {"status": "ignored_sandbox"}
    if kind == "TRANSFER":
        return _apply_transfer(db, event, datetime.utcnow())
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
