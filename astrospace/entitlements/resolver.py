"""Resolve immutable entitlement snapshots from persisted authority."""
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.models import (
    BillingAccount,
    EntitlementOverride,
    PlanAssignment,
    SubscriptionGrant,
    UsageBucket,
)
from .registry import CATALOG_REVISION, capability_registry


@dataclass(frozen=True)
class EntitlementDecision:
    allowed: bool
    entitlement: str
    value: Any
    reason: str
    access_tier: str
    remaining: int | None = None
    resets_at: str | None = None

    def denial(self) -> dict:
        return {
            "code": "entitlement_limit_reached" if self.reason == "limit_reached" else "entitlement_required",
            "entitlement": self.entitlement,
            "access_tier": self.access_tier,
            "remaining": self.remaining,
            "resets_at": self.resets_at,
            "upgrade_options": ["plus", "pro"] if self.access_tier == "free" else ["pro"],
        }


class EntitlementDenied(Exception):
    def __init__(self, decision: EntitlementDecision):
        self.decision = decision
        super().__init__(decision.reason)


@dataclass(frozen=True)
class EntitlementSnapshot:
    account_id: str
    access_tier: str
    account_topology: str
    offer_code: str | None
    status: str
    source: str
    effective_at: str
    expires_at: str | None
    grace_ends_at: str | None
    revision: int
    catalog_revision: int
    entitlements: dict[str, Any]
    usage: dict[str, dict]

    def decide(self, key: str) -> EntitlementDecision:
        if key not in capability_registry:
            return EntitlementDecision(False, key, None, "unknown_entitlement", self.access_tier)
        value = self.entitlements[key]
        definition = capability_registry[key]
        if definition.kind == "flag":
            return EntitlementDecision(bool(value), key, value, "available" if value else "plan_required", self.access_tier)
        if value is None:
            return EntitlementDecision(True, key, value, "not_enforced", self.access_tier)
        usage = self.usage.get(key, {})
        remaining = max(0, int(value) - int(usage.get("used", 0)) - int(usage.get("reserved", 0)))
        return EntitlementDecision(
            remaining > 0,
            key,
            value,
            "available" if remaining > 0 else "limit_reached",
            self.access_tier,
            remaining=remaining,
            resets_at=usage.get("resets_at"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


def _billing_account(db: Session, user_id: str) -> BillingAccount:
    account = db.query(BillingAccount).filter(
        BillingAccount.owner_user_id == user_id,
        BillingAccount.kind == "individual",
    ).one_or_none()
    if account:
        return account
    account = BillingAccount(owner_user_id=user_id, kind="individual")
    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        # Two first reads may race. The uniqueness constraint is authoritative;
        # the loser re-reads the row rather than surfacing a false 500.
        db.rollback()
        return db.query(BillingAccount).filter(
            BillingAccount.owner_user_id == user_id,
            BillingAccount.kind == "individual",
        ).one()
    db.refresh(account)
    return account


def resolve_entitlements(db: Session, user_id: str, *, now: datetime | None = None) -> EntitlementSnapshot:
    now = now or datetime.utcnow()
    account = _billing_account(db, user_id)
    assignment = db.query(PlanAssignment).filter(
        PlanAssignment.billing_account_id == account.id,
        PlanAssignment.effective_at <= now,
        or_(PlanAssignment.ends_at.is_(None), PlanAssignment.ends_at > now),
    ).order_by(PlanAssignment.revision.desc()).first()

    grant = None
    if assignment and assignment.access_tier != "free":
        grant = (
            db.query(SubscriptionGrant)
            .filter(SubscriptionGrant.id == assignment.source_grant_id)
            .one_or_none()
        )
        grant_is_valid = bool(
            grant
            and grant.verified_at
            and grant.state in {"active", "grace"}
            and (grant.starts_at is None or grant.starts_at <= now)
            and (
                (grant.state == "active" and (grant.expires_at is None or grant.expires_at > now))
                or (grant.state == "grace" and grant.grace_ends_at and grant.grace_ends_at > now)
            )
        )
        if not grant_is_valid:
            assignment = None
            grant = None

    tier = assignment.access_tier if assignment else "free"
    topology = assignment.account_topology if assignment else account.kind
    revision = max(account.entitlement_revision, assignment.revision if assignment else 0)
    values = {key: definition.value_for(tier) for key, definition in capability_registry.items()}

    overrides = db.query(EntitlementOverride).filter(
        EntitlementOverride.billing_account_id == account.id,
        EntitlementOverride.effective_at <= now,
        or_(EntitlementOverride.expires_at.is_(None), EntitlementOverride.expires_at > now),
    ).order_by(EntitlementOverride.created_at).all()
    for override in overrides:
        definition = capability_registry.get(override.entitlement_key)
        if definition and not definition.protected_baseline:
            values[override.entitlement_key] = override.value.get("value")
            revision = max(revision, override.revision)

    buckets = db.query(UsageBucket).filter(
        UsageBucket.billing_account_id == account.id,
        UsageBucket.period_start <= now,
        UsageBucket.period_end > now,
    ).all()
    usage = {
        bucket.entitlement_key: {
            "used": bucket.consumed,
            "reserved": bucket.reserved,
            "remaining": (
                max(0, int(values[bucket.entitlement_key]) - bucket.consumed - bucket.reserved)
                if isinstance(values.get(bucket.entitlement_key), int)
                else None
            ),
            "resets_at": bucket.period_end.isoformat(),
            "period_id": bucket.period_id,
        }
        for bucket in buckets
        if bucket.entitlement_key in capability_registry
    }
    return EntitlementSnapshot(
        account_id=account.id,
        access_tier=tier,
        account_topology=topology,
        offer_code=assignment.offer_code if assignment else None,
        status=grant.state if grant else ("active" if assignment else "free"),
        source=grant.provider if grant else ("assignment" if assignment else "free_default"),
        effective_at=(
            grant.starts_at if grant and grant.starts_at
            else assignment.effective_at if assignment
            else account.created_at
        ).isoformat(),
        expires_at=(
            grant.expires_at.isoformat() if grant and grant.expires_at
            else assignment.ends_at.isoformat() if assignment and assignment.ends_at
            else None
        ),
        grace_ends_at=grant.grace_ends_at.isoformat() if grant and grant.grace_ends_at else None,
        revision=revision,
        catalog_revision=CATALOG_REVISION,
        entitlements=values,
        usage=usage,
    )


def require_entitlement(snapshot: EntitlementSnapshot, key: str) -> EntitlementDecision:
    decision = snapshot.decide(key)
    if not decision.allowed:
        raise EntitlementDenied(decision)
    return decision
