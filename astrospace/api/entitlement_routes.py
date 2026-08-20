"""Authenticated commercial entitlement read and decision surface."""
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..entitlements.registry import capability_registry, public_registry
from ..entitlements.resolver import require_entitlement, resolve_entitlements
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/entitlements", tags=["entitlements"])


@router.get("")
def get_entitlements(user: CurrentUser, db: Session = Depends(get_db)):
    return resolve_entitlements(db, user.id).to_dict()


@router.get("/catalog")
def get_entitlement_catalog(user: CurrentUser):
    # Authentication is intentional even though the vocabulary is not secret:
    # this is an app contract, not a public pricing or product catalogue.
    return public_registry()


@router.get("/decisions/{entitlement_key:path}")
def get_entitlement_decision(
    entitlement_key: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    if entitlement_key not in capability_registry:
        raise HTTPException(status_code=404, detail="Unknown entitlement")
    decision = resolve_entitlements(db, user.id).decide(entitlement_key)
    return {
        "allowed": decision.allowed,
        "entitlement": decision.entitlement,
        "value": decision.value,
        "reason": decision.reason,
        "access_tier": decision.access_tier,
        "remaining": decision.remaining,
        "resets_at": decision.resets_at,
        "denial": None if decision.allowed else decision.denial(),
    }


@router.post("/_probe/{entitlement_key:path}")
def probe_entitlement_gate(
    entitlement_key: str,
    user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Exercise a real server gate before any store integration is enabled."""
    if os.getenv("ASTROSPACE_ENTITLEMENT_PROBES", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Not found")
    require_entitlement(resolve_entitlements(db, user.id), entitlement_key)
    return {"allowed": True, "entitlement": entitlement_key}
