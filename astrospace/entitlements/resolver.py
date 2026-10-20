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
    QuestionCredit,
    SubscriptionGrant,
    UsageBucket,
)
from .registry import CATALOG_REVISION, capability_registry, free_values, quotas_enforced


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
    # Unspent question-pack credits, used once the monthly Ask allowance runs out.
    question_credits: int = 0
    # Whether a reached limit blocks. Off until store purchases are live.
    quotas_enforced: bool = False

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
        if remaining > 0:
            reason = "available"
        elif key == "ask.answers.period" and self.question_credits > 0:
            reason = "question_credit"
        elif not self.quotas_enforced:
            reason = "not_enforced"
        else:
            reason = "limit_reached"
        return EntitlementDecision(
            reason != "limit_reached",
            key,
            value,
            reason,
            self.access_tier,
            remaining=remaining,
            resets_at=usage.get("resets_at"),
        )

    def decide_capacity(self, key: str, in_use: int) -> EntitlementDecision:
        """A limit on things held rather than used per period (profiles)."""
        value = self.entitlements.get(key)
        if value is None:
            return EntitlementDecision(True, key, value, "not_enforced", self.access_tier)
        remaining = max(0, int(value) - in_use)
        if remaining > 0:
            reason = "available"
        elif not self.quotas_enforced:
            reason = "not_enforced"
        else:
            reason = "limit_reached"
        return EntitlementDecision(
            reason != "limit_reached", key, value, reason, self.access_tier, remaining=remaining,
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


WELCOME_PROVIDER = "welcome"


def _ensure_welcome_question(db: Session, account: BillingAccount) -> None:
    """One free Ask question per account, once, never renewed (Hawk, 2026-10-19).

    Held as a one-question credit so it is spent after any monthly allowance
    and before bought packs, through the same claim as a pack. Keyed by the
    account, so deleting and re-creating the credit row is the only way to
    grant a second one.
    """
    txn = f"welcome:{account.id}"
    exists = db.query(QuestionCredit.id).filter_by(
        provider=WELCOME_PROVIDER, provider_transaction_id=txn,
    ).first()
    if exists:
        return
    db.add(QuestionCredit(
        billing_account_id=account.id, provider=WELCOME_PROVIDER,
        provider_product_id="welcome_question", provider_transaction_id=txn,
        quantity=1, remaining=1,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def resolve_entitlements(db: Session, user_id: str, *, now: datetime | None = None) -> EntitlementSnapshot:
    now = now or datetime.utcnow()
    account = _billing_account(db, user_id)
    _ensure_welcome_question(db, account)
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
    values = (
        free_values() if tier == "free"
        else {key: definition.value_for(tier) for key, definition in capability_registry.items()}
    )

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
        question_credits=sum(
            remaining for (remaining,) in db.query(QuestionCredit.remaining).filter(
                QuestionCredit.billing_account_id == account.id,
                QuestionCredit.revoked_at.is_(None),
            ).all()
        ),
        quotas_enforced=quotas_enforced(),
    )


def require_entitlement(snapshot: EntitlementSnapshot, key: str) -> EntitlementDecision:
    decision = snapshot.decide(key)
    if not decision.allowed:
        raise EntitlementDenied(decision)
    return decision


def plan_lock(db: Session, user_id: str, key: str) -> EntitlementDecision | None:
    """The denial for a plan flag this reader lacks, or None.

    None as well while ASTROSPACE_QUOTAS_ENFORCED is off, so a route and the
    app's PlanGateService agree on when a lock is real.
    """
    snapshot = resolve_entitlements(db, user_id)
    if not snapshot.quotas_enforced:
        return None
    decision = snapshot.decide(key)
    return None if decision.allowed else decision


def require_plan(db: Session, user_id: str, key: str) -> None:
    """Refuse the whole route (402) when `plan_lock` says the plan lacks `key`."""
    denied = plan_lock(db, user_id, key)
    if denied is not None:
        raise EntitlementDenied(denied)


def require_turn(db: Session, user_id: str, key: str, used_this_month: int,
                 *, now: datetime | None = None) -> None:
    """Refuse (402) when a monthly limit `key` is used up, counted by the caller.

    For limits whose count already lives in the caller's own rows (readings
    written this month), so no usage bucket has to mirror them.
    """
    from .usage import month_bounds

    snapshot = resolve_entitlements(db, user_id)
    decision = snapshot.decide_capacity(key, used_this_month)
    if not decision.allowed:
        _, _, period_end = month_bounds(now or datetime.utcnow())
        raise EntitlementDenied(EntitlementDecision(
            False, key, decision.value, decision.reason, decision.access_tier,
            remaining=0, resets_at=period_end.isoformat(),
        ))
