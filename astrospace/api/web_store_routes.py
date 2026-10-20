"""Website checkout (asksiddha.app/buy) over Razorpay.

Thin wrapper over `entitlements/razorpay.py`. The page signs the reader in
with Supabase, so every call below except /config and the webhook carries
the same bearer token the app uses; the purchase lands on that account.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..db.models import SubscriptionGrant
from ..entitlements import razorpay, resolve_entitlements
from ..entitlements.products import PRODUCTS
from ..entitlements.resolver import _billing_account
from .auth import CurrentUser, auth_config

log = logging.getLogger("astrospace.web_store")
router = APIRouter(prefix="/api/v1/store", tags=["store"])

TIER_NAMES = {"plus": "Plus", "pro": "Practitioner"}


def _config() -> razorpay.Config:
    cfg = razorpay.config()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Buying on the website is not open yet.")
    return cfg


def _product_row(product) -> dict:
    return {
        "id": product.id, "kind": product.kind, "title": product.title, "price_inr": product.price_inr,
        "tier": product.tier, "questions": product.questions,
    }


@router.get("/web/config")
def web_config() -> dict:
    """What the buy page needs before anyone signs in. All of it is public."""
    cfg = razorpay.config()
    auth = auth_config()
    if cfg is None or not auth["enabled"]:
        return {"enabled": False}
    return {
        "enabled": True,
        "test_mode": cfg.test_mode,
        "razorpay_key_id": cfg.key_id,
        "supabase_url": auth["url"],
        "supabase_anon_key": auth["anon_key"],
        "products": [_product_row(p) for p in razorpay.sellable(cfg)],
    }


def _status(db: Session, user, cfg: razorpay.Config) -> dict:
    now = datetime.utcnow()
    snapshot = resolve_entitlements(db, user.id, now=now)
    account = _billing_account(db, user.id)
    live = razorpay.live_plan_grants(db, account, now)
    web = [g for g in live if g.provider == razorpay.PROVIDER]
    top_rank = max((razorpay.TIER_RANK.get(PRODUCTS[g.provider_product_id].tier, 0)
                    for g in live if g.provider_product_id in PRODUCTS), default=0)
    return {
        "email": user.email,
        "may_buy": razorpay.may_buy(cfg, user.email),
        "access_tier": snapshot.access_tier,
        "question_credits": snapshot.question_credits,
        # The best plan anyone is paying for; the page will not sell that tier or a lower one again.
        "paid_tier_rank": top_rank,
        "store_plans": [
            {"tier": PRODUCTS[g.provider_product_id].tier, "expires_at": g.expires_at.isoformat() if g.expires_at else None}
            for g in live if g.provider != razorpay.PROVIDER and g.provider_product_id in PRODUCTS
        ],
        "web_plans": [
            {
                "subscription_id": g.provider_transaction_id,
                "tier": PRODUCTS[g.provider_product_id].tier if g.provider_product_id in PRODUCTS else None,
                "state": g.state,
                "renews_at": g.renews_at.isoformat() if g.renews_at else None,
                "expires_at": g.expires_at.isoformat() if g.expires_at else None,
            }
            for g in web
        ],
    }


@router.get("/web/me")
def web_me(user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    return _status(db, user, _config())


class CheckoutRequest(BaseModel):
    product_id: str = Field(max_length=64)


@router.post("/web/checkout")
def web_checkout(body: CheckoutRequest, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    cfg = _config()
    product = PRODUCTS.get(body.product_id)
    if product is None or product not in razorpay.sellable(cfg):
        raise HTTPException(status_code=404, detail="That plan is not sold on the website.")
    if not razorpay.may_buy(cfg, user.email):
        raise HTTPException(status_code=403, detail="Buying on the website is open to a few testers for now.")
    if product.kind == "plan":
        status = _status(db, user, cfg)
        if status["paid_tier_rank"] >= razorpay.TIER_RANK[product.tier]:
            raise HTTPException(
                status_code=409,
                detail=f"You already have {TIER_NAMES[product.tier]} or higher, so there is nothing to buy.",
            )
    try:
        if product.kind == "plan":
            created = razorpay.create_subscription(cfg, product, user.id)
            ids = {"subscription_id": created["id"]}
        else:
            created = razorpay.create_order(cfg, product, user.id)
            ids = {"order_id": created["id"], "amount": created["amount"], "currency": created["currency"]}
    except razorpay.RazorpayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "key_id": cfg.key_id, "product": _product_row(product), "email": user.email, **ids,
    }


class ConfirmRequest(BaseModel):
    razorpay_payment_id: str = Field(max_length=64)
    razorpay_signature: str = Field(max_length=128)
    razorpay_subscription_id: str | None = Field(default=None, max_length=64)
    razorpay_order_id: str | None = Field(default=None, max_length=64)


@router.post("/web/confirm")
def web_confirm(body: ConfirmRequest, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    """Apply a purchase the moment checkout closes, instead of waiting for the webhook."""
    cfg = _config()
    if not razorpay.checkout_signature_ok(
        cfg, payment_id=body.razorpay_payment_id, signature=body.razorpay_signature,
        subscription_id=body.razorpay_subscription_id, order_id=body.razorpay_order_id,
    ):
        raise HTTPException(status_code=400, detail="That payment could not be verified.")
    try:
        if body.razorpay_subscription_id:
            entity = razorpay.fetch_subscription(cfg, body.razorpay_subscription_id)
        else:
            entity = razorpay.fetch_order(cfg, body.razorpay_order_id)
    except razorpay.RazorpayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if str((entity.get("notes") or {}).get("user_id")) != user.id:
        raise HTTPException(status_code=403, detail="That payment belongs to another account.")
    now = datetime.utcnow()
    if body.razorpay_subscription_id:
        outcome = razorpay.apply_subscription(db, entity, now, event="checkout")
    else:
        outcome = razorpay.apply_order(db, entity, now, event="checkout")
    db.commit()
    return {"status": outcome, **_status(db, user, cfg)}


class CancelRequest(BaseModel):
    subscription_id: str = Field(max_length=64)


@router.post("/web/cancel")
def web_cancel(body: CancelRequest, user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    """Stop renewing a website plan. It stays on until the end of the month already paid for."""
    cfg = _config()
    account = _billing_account(db, user.id)
    grant = db.query(SubscriptionGrant).filter_by(
        billing_account_id=account.id, provider=razorpay.PROVIDER,
        provider_transaction_id=body.subscription_id,
    ).one_or_none()
    if grant is None:
        raise HTTPException(status_code=404, detail="No such plan on this account.")
    try:
        entity = razorpay.cancel_subscription(cfg, body.subscription_id)
    except razorpay.RazorpayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Razorpay keeps an at-cycle-end cancellation "active" until the cycle ends.
    grant.renews_at = None
    if entity.get("current_end"):
        grant.expires_at = razorpay._ts(entity["current_end"])
    razorpay.audit(db, account, user.id, "store.will_not_renew", {
        "provider": razorpay.PROVIDER, "event": "website_cancel", "subscription_id": body.subscription_id,
    })
    db.commit()
    return _status(db, user, cfg)


@router.post("/razorpay/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    raw = await request.body()
    verified = razorpay.webhook_signature_ok(raw, x_razorpay_signature)
    if verified is None:
        raise HTTPException(status_code=404, detail="Not found")
    if not verified:
        raise HTTPException(status_code=401, detail="Unauthorised")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Not JSON")
    outcome = razorpay.apply_webhook(db, payload, datetime.utcnow())
    db.commit()
    log.info("razorpay webhook %s: %s", payload.get("event"), outcome)
    # Anything that is not a 2xx is retried, so unknown events are acknowledged too.
    return {"status": outcome}
