from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import get_db
from astrospace.db.database import Base
from astrospace.db.models import (
    BillingAccount,
    EntitlementOverride,
    PlanAssignment,
    SubscriptionGrant,
    UsageBucket,
)
from astrospace.entitlements.registry import capability_registry
from astrospace.entitlements.resolver import resolve_entitlements

USER = "entitlement-test-user"


@pytest.fixture()
def env(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        return AuthUser(id=USER, email="entitlements@example.test", role="authenticated")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = override_current_user
    monkeypatch.setenv("ASTROSPACE_ENTITLEMENT_PROBES", "true")
    try:
        yield TestClient(app), Session
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def _paid_assignment(db, user_id: str, tier: str, now: datetime, *, state="active"):
    account = BillingAccount(owner_user_id=user_id, kind="individual")
    db.add(account)
    db.flush()
    grant = SubscriptionGrant(
        billing_account_id=account.id,
        provider="test_fixture",
        provider_product_id=f"{tier}_fixture",
        provider_transaction_id=f"transaction-{user_id}-{tier}-{state}",
        state=state,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=30),
        grace_ends_at=now + timedelta(days=5) if state == "grace" else None,
        verified_at=now - timedelta(days=1),
    )
    db.add(grant)
    db.flush()
    db.add(PlanAssignment(
        billing_account_id=account.id,
        access_tier=tier,
        account_topology="individual",
        offer_code=f"{tier}_fixture",
        source_grant_id=grant.id,
        effective_at=now - timedelta(hours=1),
        revision=1,
    ))
    db.commit()
    return account


def test_registry_keeps_truth_safety_and_reliability_in_every_tier():
    protected = [item for item in capability_registry.values() if item.protected_baseline]
    assert protected
    for item in protected:
        assert item.kind == "flag"
        assert all(item.value_for(tier) is True for tier in ("free", "plus", "pro"))


def test_unapproved_limits_are_represented_but_not_enforced():
    for key in ("profiles.max", "ask.answers.period", "compatibility.saved.max"):
        item = capability_registry[key]
        assert item.kind == "limit"
        assert all(item.value_for(tier) is None for tier in ("free", "plus", "pro"))


def test_free_snapshot_is_created_server_side_and_unknown_keys_fail_closed(env):
    _, Session = env
    db = Session()
    snapshot = resolve_entitlements(db, USER)
    assert snapshot.access_tier == "free"
    assert snapshot.source == "free_default"
    assert snapshot.entitlements["today.core"] is True
    assert snapshot.entitlements["reports.detailed"] is False
    assert snapshot.decide("ask.answers.period").reason == "not_enforced"
    assert snapshot.decide("made.up.capability").allowed is False
    assert db.query(BillingAccount).filter_by(owner_user_id=USER).count() == 1
    db.close()


def test_verified_paid_grant_resolves_and_revoked_grant_falls_back(env):
    _, Session = env
    now = datetime.utcnow()
    db = Session()
    _paid_assignment(db, USER, "plus", now)
    paid = resolve_entitlements(db, USER, now=now)
    assert paid.entitlements["reports.detailed"] is True
    assert paid.source == "test_fixture"
    assert paid.offer_code == "plus_fixture"
    assert paid.status == "active"
    assert paid.expires_at
    grant = db.query(SubscriptionGrant).one()
    grant.state = "revoked"
    db.commit()
    snapshot = resolve_entitlements(db, USER, now=now)
    assert snapshot.access_tier == "free"
    assert snapshot.entitlements["reports.detailed"] is False
    db.close()


def test_unverified_paid_assignment_never_unlocks(env):
    _, Session = env
    now = datetime.utcnow()
    db = Session()
    account = _paid_assignment(db, USER, "pro", now)
    grant = db.query(SubscriptionGrant).filter_by(billing_account_id=account.id).one()
    grant.verified_at = None
    db.commit()
    snapshot = resolve_entitlements(db, USER, now=now)
    assert snapshot.access_tier == "free"
    assert snapshot.entitlements["practitioner.workflow"] is False
    db.close()


def test_override_can_unlock_paid_workflow_but_not_remove_protected_baseline(env):
    _, Session = env
    now = datetime.utcnow()
    db = Session()
    snapshot = resolve_entitlements(db, USER, now=now)
    account = db.get(BillingAccount, snapshot.account_id)
    db.add_all([
        EntitlementOverride(
            billing_account_id=account.id,
            entitlement_key="reports.detailed",
            value={"value": True}, reason="support recovery", actor_user_id="support",
            revision=1,
            effective_at=now - timedelta(minutes=1),
        ),
        EntitlementOverride(
            billing_account_id=account.id,
            entitlement_key="safety.guidance",
            value={"value": False}, reason="invalid override", actor_user_id="support",
            revision=2,
            effective_at=now - timedelta(minutes=1),
        ),
    ])
    db.commit()
    resolved = resolve_entitlements(db, USER, now=now)
    assert resolved.entitlements["reports.detailed"] is True
    assert resolved.entitlements["safety.guidance"] is True
    db.close()


def test_usage_decision_includes_authoritative_period(env):
    _, Session = env
    now = datetime.utcnow()
    db = Session()
    snapshot = resolve_entitlements(db, USER, now=now)
    account = db.get(BillingAccount, snapshot.account_id)
    db.add(EntitlementOverride(
        billing_account_id=account.id,
        entitlement_key="ask.answers.period",
        value={"value": 2}, reason="quota fixture", actor_user_id="test",
        revision=1,
        effective_at=now - timedelta(minutes=1),
    ))
    db.add(UsageBucket(
        billing_account_id=account.id,
        entitlement_key="ask.answers.period",
        period_id="fixture-period",
        period_start=now - timedelta(days=1),
        period_end=now + timedelta(days=29),
        reserved=1,
        consumed=1,
    ))
    db.commit()
    decision = resolve_entitlements(db, USER, now=now).decide("ask.answers.period")
    assert decision.allowed is False
    assert decision.reason == "limit_reached"
    assert decision.remaining == 0
    assert decision.resets_at
    db.close()


def test_api_snapshot_catalog_decision_and_structured_probe_denial(env):
    client, _ = env
    snapshot = client.get("/api/v1/entitlements")
    assert snapshot.status_code == 200
    assert snapshot.json()["access_tier"] == "free"

    catalog = client.get("/api/v1/entitlements/catalog").json()
    assert catalog["capabilities"]["safety.guidance"]["protected_baseline"] is True

    decision = client.get("/api/v1/entitlements/decisions/reports.detailed").json()
    assert decision["allowed"] is False
    assert decision["denial"]["code"] == "entitlement_required"
    assert "plus" in decision["denial"]["upgrade_options"]

    probe = client.post("/api/v1/entitlements/_probe/reports.detailed")
    assert probe.status_code == 402
    assert probe.json()["entitlement"] == "reports.detailed"
    assert "detail" not in probe.json()


def test_probe_is_not_exposed_without_explicit_flag(env, monkeypatch):
    client, _ = env
    monkeypatch.delenv("ASTROSPACE_ENTITLEMENT_PROBES")
    assert client.post("/api/v1/entitlements/_probe/today.core").status_code == 404


def test_account_deletion_removes_pre_billing_foundation_records(env):
    client, Session = env
    assert client.get("/api/v1/entitlements").status_code == 200
    db = Session()
    assert db.query(BillingAccount).filter_by(owner_user_id=USER).count() == 1
    db.close()

    response = client.request("DELETE", "/api/v1/me", json={"confirmation": "DELETE"})
    assert response.status_code == 200
    db = Session()
    assert db.query(BillingAccount).filter_by(owner_user_id=USER).count() == 0
    db.close()


def test_migration_contains_every_authority_table():
    sql = open(
        "supabase/migrations/20260818120000_create_commercial_entitlement_foundation.sql",
        encoding="utf-8",
    ).read()
    for table in (
        "billing_accounts", "subscription_grants", "plan_assignments",
        "entitlement_overrides", "usage_buckets", "entitlement_audit_events",
    ):
        assert f"create table if not exists public.{table}" in sql
        assert f"alter table public.{table} enable row level security" in sql
    assert "revoke all" in sql
    assert "authenticated" in sql
