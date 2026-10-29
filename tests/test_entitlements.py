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
    QuestionCredit,
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


def test_plan_limits_follow_hawks_2026_10_19_prices():
    ask = capability_registry["ask.answers.period"]
    assert (ask.value_for("free"), ask.value_for("plus"), ask.value_for("pro")) == (0, 5, 15)
    profiles = capability_registry["profiles.max"]
    assert (profiles.value_for("free"), profiles.value_for("plus"), profiles.value_for("pro")) == (1, 3, 10)
    # Not part of D2: represented, never enforced.
    saved = capability_registry["compatibility.saved.max"]
    assert all(saved.value_for(tier) is None for tier in ("free", "plus", "pro"))


def test_free_snapshot_is_created_server_side_and_unknown_keys_fail_closed(env):
    _, Session = env
    db = Session()
    snapshot = resolve_entitlements(db, USER)
    assert snapshot.access_tier == "free"
    assert snapshot.source == "free_default"
    assert snapshot.entitlements["today.core"] is True
    assert snapshot.entitlements["reports.detailed"] is False
    # No monthly allowance on Free, only the one welcome question.
    assert snapshot.question_credits == 1
    assert snapshot.decide("ask.answers.period").reason == "question_credit"
    assert snapshot.decide("ask.answers.period").remaining == 0
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


def test_usage_decision_includes_authoritative_period(env, monkeypatch):
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
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
    db.query(QuestionCredit).filter_by(billing_account_id=account.id).update({"remaining": 0})
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


def test_divisional_charts_beyond_d1_and_d9_are_held_back_only_when_locks_are_on(env, monkeypatch):
    from astrospace.api.vedic_routes import _varga_decision, _without_locked_vargas

    _, Session = env
    db = Session()
    payload = lambda: {"vargas": {"D1": 1, "D9": 9, "D10": 10, "D60": 60}}

    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED", raising=False)
    assert _varga_decision(db, USER) is None
    assert set(_without_locked_vargas(payload(), db, USER)["vargas"]) == {"D1", "D9", "D10", "D60"}

    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    assert _varga_decision(db, USER).entitlement == "vargas.full"
    assert set(_without_locked_vargas(payload(), db, USER)["vargas"]) == {"D1", "D9"}

    _paid_assignment(db, "practitioner-reader", "pro", datetime.utcnow())
    assert _varga_decision(db, "practitioner-reader") is None
    assert set(_without_locked_vargas(payload(), db, "practitioner-reader")["vargas"]) == {"D1", "D9", "D10", "D60"}
    db.close()


def test_free_keeps_the_first_two_yogas_once_locks_are_on(env, monkeypatch):
    from astrospace.api.vedic_routes import _without_locked_yogas

    _, Session = env
    db = Session()
    yogas = [{"name": f"Yoga {n}", "active": True} for n in range(5)]
    inactive = {"name": "Dormant", "active": False}
    summary = lambda: {"active_count": 5, "active": list(yogas), "all": [*yogas, inactive]}

    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED", raising=False)
    assert len(_without_locked_yogas(summary(), db, USER)["active"]) == 5

    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    trimmed = _without_locked_yogas(summary(), db, USER)
    assert [y["name"] for y in trimmed["active"]] == ["Yoga 0", "Yoga 1"]
    assert [y["name"] for y in trimmed["all"]] == ["Yoga 0", "Yoga 1", "Dormant"]
    assert trimmed["locked_count"] == 3
    assert trimmed["active_count"] == 5

    _paid_assignment(db, "plus-reader", "plus", datetime.utcnow())
    assert len(_without_locked_yogas(summary(), db, "plus-reader")["active"]) == 5
    db.close()


def test_free_never_trims_a_caution_yoga(env, monkeypatch):
    """A caution yoga is a flag, like a dosha: shown on every plan.
    One-way Raja/Dhana links never take one of Free's two places."""
    from astrospace.api.vedic_routes import _without_locked_yogas

    _, Session = env
    db = Session()
    yogas = [
        {"name": "Raja one-way", "category": "Power / Career", "active": True, "partial": True},
        {"name": "Gajakesari", "category": "Mind / Wisdom", "active": True},
        {"name": "Budhaditya", "category": "Intellect / Status", "active": True},
        {"name": "Amala", "category": "Reputation / Career", "active": True},
        {"name": "Kemadruma", "category": "Caution / Mind", "active": True},
        {"name": "Vosi (hard form)", "category": "Caution / Effort", "active": True},
    ]
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    trimmed = _without_locked_yogas({"active": list(yogas), "all": list(yogas)}, db, USER)
    assert [y["name"] for y in trimmed["active"]] == [
        "Gajakesari", "Budhaditya", "Kemadruma", "Vosi (hard form)"]
    assert trimmed["locked_count"] == 2
    db.close()


def test_free_remedy_plan_keeps_the_first_practice_and_every_dosha():
    from astrospace.api.remedy_routes import _free_plan

    plan = {
        "groups": [
            {"trigger": {"kind": "dasha"}, "practices": ["a1", "a2"]},
            {"trigger": {"kind": "life_area"}, "practices": ["b1"]},
            {"trigger": {"kind": "dosha", "dosha": "manglik"}, "practices": ["c1", "c2"]},
        ],
        "count": 3,
    }
    free = _free_plan(plan)
    assert [g["practices"] for g in free["groups"]] == [["a1"], ["c1"]]
    assert free["count"] == 2
    assert free["locked_practices"] == 3


@pytest.mark.parametrize("method,path", [
    ("POST", "/api/v1/readings/k1/generate"),
    ("GET", "/api/v1/readings/k1"),
    ("GET", "/api/v1/readings/k1/claims"),
    ("GET", "/api/v1/readings/k1/latest/weekly"),
    ("GET", "/api/v1/muhurta/k1?goal=marriage"),
])
def test_readings_and_muhurta_refuse_free_only_once_locks_are_on(env, monkeypatch, method, path):
    client, _ = env
    body = {"period": "weekly"} if method == "POST" else None

    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED", raising=False)
    assert client.request(method, path, json=body).status_code == 404  # no such profile, but not locked

    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    response = client.request(method, path, json=body)
    assert response.status_code == 402
    assert response.json()["code"] == "entitlement_required"


def test_testers_get_plus_but_not_practitioner_with_a_teaser_of_ask_and_readings(env, monkeypatch):
    """Hawk, 2026-10-20: closed testers get Plus, with 3 readings a month (10 questions since 2026-10-22)."""
    _, Session = env
    with Session() as db:
        free = resolve_entitlements(db, USER).entitlements
        assert free["readings.full"] is False and free["profiles.max"] == 1
        monkeypatch.setenv("ASTROSPACE_TESTERS_GET_PLUS", "1")
        tester = resolve_entitlements(db, USER)
    assert tester.access_tier == "free"
    as_free = {"remedies.full", "doshas.detail", "dashas.full", "transits.full", "compatibility.checks.period"}
    for key, definition in capability_registry.items():
        if key in ("ask.answers.period", "readings.period", "muhurta.days_ahead", "profiles.max"):
            continue
        expected = definition.value_for("free" if key in as_free else "plus")
        assert tester.entitlements[key] == expected, key
    assert tester.entitlements["vargas.full"] is False  # Practitioner stays paid
    assert tester.entitlements["compatibility.full"] is True  # the full report, 1 person a month
    assert tester.entitlements["compatibility.checks.period"] == 1
    assert tester.entitlements["muhurta.days_ahead"] == 14
    assert tester.entitlements["ask.answers.period"] == 10
    assert tester.entitlements["readings.period"] == 3
    assert tester.entitlements["profiles.max"] == 5  # own profile plus 4 others (2026-10-27)


def test_tester_readings_stop_after_three_a_month_once_locks_are_on(env, monkeypatch):
    from fastapi import HTTPException

    from astrospace.api import reading_routes
    from astrospace.db import crud
    from astrospace.db.models import Reading

    client, Session = env
    monkeypatch.setenv("ASTROSPACE_TESTERS_GET_PLUS", "1")
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")

    def not_written(*args, **kwargs):
        raise HTTPException(status_code=503, detail="stub")

    monkeypatch.setattr(reading_routes, "_generate_and_save", not_written)
    with Session() as db:
        kundli = crud.create_kundli(db, {
            "user_id": USER, "name": "Me", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14, "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
        for n in range(2):
            db.add(Reading(kundli_id=kundli, reading_type="daily", period_label=f"old-{n}", content="x"))
        db.commit()
    generate = lambda: client.post(f"/api/v1/readings/{kundli}/generate", json={"period": "weekly"})
    assert generate().status_code == 503  # third reading allowed through to the writer
    with Session() as db:
        db.add(Reading(kundli_id=kundli, reading_type="monthly", period_label="old-3", content="x"))
        db.commit()
    denied = generate()
    assert denied.status_code == 402
    assert denied.json()["entitlement"] == "readings.period"
    assert denied.json()["code"] == "entitlement_limit_reached"
    assert denied.json()["resets_at"] and denied.json()["limit"] == 3
    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED")
    assert generate().status_code == 503  # counted, never blocking, while locks are off


def test_tester_muhurta_searches_the_next_two_weeks_only(env, monkeypatch):
    from datetime import date, timedelta

    from astrospace.api import muhurta_routes
    from astrospace.db import crud

    client, Session = env
    monkeypatch.setenv("ASTROSPACE_TESTERS_GET_PLUS", "1")
    monkeypatch.setenv("ASTROSPACE_QUOTAS_ENFORCED", "true")
    seen = {}

    def fake_find(goal, start, end, **kwargs):
        seen["range"] = (start, end)
        seen["look_ahead"] = kwargs.get("look_ahead_days")
        seen["locked_from"] = kwargs.get("locked_from")
        return {"windows": []}

    monkeypatch.setattr(muhurta_routes.muhurta, "find", fake_find)
    with Session() as db:
        kundli = crud.create_kundli(db, {
            "user_id": USER, "name": "Me", "relation": "self",
            "birth_year": 1991, "birth_month": 8, "birth_day": 14, "birth_hour": 6, "birth_minute": 12,
            "birth_city": "Vijayawada", "birth_nation": "IN",
        }).id
    params = {"goal": "griha_pravesha", "timezone": "Asia/Kolkata"}
    body = client.get(f"/api/v1/muhurta/{kundli}", params={**params, "date_to": "2099-01-01"}).json()
    start, end = seen["range"]
    assert (end - start).days == 13 and body["capped_to"] == end.isoformat()
    # The frozen tester matrix: no times past the horizon...
    assert seen["look_ahead"] == 0
    # ...but the first good date past it, without its time (Hawk, 2026-10-21).
    assert seen["locked_from"] == end + timedelta(days=1)
    far = client.get(f"/api/v1/muhurta/{kundli}", params={**params, "date_from": "2099-01-01"})
    assert far.status_code == 400
    monkeypatch.delenv("ASTROSPACE_QUOTAS_ENFORCED")
    client.get(f"/api/v1/muhurta/{kundli}", params={**params, "date_to": "2099-01-01"})
    assert seen["range"][1] == date(2099, 1, 1)
    assert seen["locked_from"] is None
