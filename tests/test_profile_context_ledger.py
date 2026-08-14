import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from astrospace.api.auth import AuthUser, current_user
from astrospace.db import crud, get_db
from astrospace.db.database import Base
from astrospace.db.models import (
    ProfileContextAuditEvent, ProfileContextFact, ProfileContextLedger,
    ProfileContextMutation,
)

ME = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


@pytest.fixture()
def env():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
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

    db = Session()
    mine = crud.create_kundli(db, {
        "user_id": ME, "name": "Mine", "relation": "self",
        "birth_year": 1960, "birth_month": 1, "birth_day": 1,
        "birth_hour": 8, "birth_minute": 0,
        "birth_city": "Chennai", "birth_nation": "IN",
    }).id
    second = crud.create_kundli(db, {
        "user_id": ME, "name": "Second", "relation": "mother",
        "birth_year": 1950, "birth_month": 2, "birth_day": 2,
        "birth_hour": 8, "birth_minute": 0,
        "birth_city": "Chennai", "birth_nation": "IN",
    }).id
    theirs = crud.create_kundli(db, {
        "user_id": OTHER, "name": "Theirs", "relation": "self",
        "birth_year": 1980, "birth_month": 3, "birth_day": 3,
        "birth_hour": 8, "birth_minute": 0,
        "birth_city": "Delhi", "birth_nation": "IN",
    }).id
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_user] = lambda: AuthUser(id=ME)
    try:
        yield {"client": TestClient(app), "Session": Session,
               "mine": mine, "second": second, "theirs": theirs}
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(current_user, None)


def fact_body(revision=0, *, key="employment_status", value=None):
    return {
        "expected_revision": revision,
        "key": key,
        "value": value or {"code": "retired", "label": "Retired"},
        "valid_from": "2021-03-01",
        "source": {"kind": "profile_form", "channel": "profile_settings"},
        "consent": {"state": "granted", "surface": "profile_memory_v1"},
    }


def test_reader_can_confirm_an_ask_memory_candidate(env):
    body = fact_body()
    body["source"] = {"kind": "reader_statement", "channel": "ask"}
    body["consent"] = {"state": "granted", "surface": "ask_memory_confirmation_v1"}
    response = post_fact(env, env["mine"], body, key="ask-memory-confirm-0001")
    assert response.status_code == 201
    assert response.json()["fact"]["source"] == {
        "kind": "reader_statement", "channel": "ask"
    }


def post_fact(env, profile, body=None, key="create-retired-0001"):
    return env["client"].post(
        f"/api/v1/profiles/{profile}/context/facts",
        json=body or fact_body(), headers={"Idempotency-Key": key},
    )


def test_create_and_domain_projection_are_grounded(env):
    response = post_fact(env, env["mine"])
    assert response.status_code == 201
    assert response.json()["revision"] == 1

    context = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context?domain=career&as_of=2026-08-14"
    ).json()
    assert context["status"] == "ready"
    assert context["facts"][0]["ref"].startswith("profile_fact:")
    assert context["facts"][0]["value"]["code"] == "retired"
    assert "retired" in context["logical_constraints"][0]

    marriage = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context?domain=marriage&as_of=2026-08-14"
    ).json()
    assert marriage["facts"] == []


def test_empty_read_does_not_create_server_state(env):
    response = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context?domain=career"
    )
    assert response.status_code == 200
    assert response.json()["revision"] == 0
    db = env["Session"]()
    assert db.query(ProfileContextLedger).count() == 0
    db.close()


def test_double_submit_is_idempotent_and_does_not_advance_revision(env):
    first = post_fact(env, env["mine"], key="same-create-0001")
    second = post_fact(env, env["mine"], key="same-create-0001")
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context"
    ).json()["revision"] == 1
    db = env["Session"]()
    mutation = db.query(ProfileContextMutation).one()
    assert "fact" not in mutation.response
    assert "retired" not in str(mutation.response)
    db.close()


def test_idempotency_key_cannot_be_reused_for_different_content(env):
    assert post_fact(env, env["mine"], key="reused-key-0001").status_code == 201
    changed = fact_body(value={"code": "employed"})
    response = post_fact(env, env["mine"], changed, key="reused-key-0001")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "idempotency_key_reused"


def test_stale_revision_returns_current_revision(env):
    assert post_fact(env, env["mine"], key="revision-create-1").status_code == 201
    response = post_fact(env, env["mine"], fact_body(0), key="revision-create-2")
    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "stale_revision", "current_revision": 1,
    }


def test_correction_supersedes_history_without_rewriting_it(env):
    created = post_fact(env, env["mine"], key="correct-create-1").json()
    old_id = created["fact"]["id"]
    corrected = fact_body(1, value={"code": "self_employed"})
    corrected["source"]["kind"] = "reader_correction"
    response = env["client"].patch(
        f"/api/v1/profiles/{env['mine']}/context/facts/{old_id}",
        json=corrected, headers={"Idempotency-Key": "correct-fact-0001"},
    )
    assert response.status_code == 200
    assert response.json()["revision"] == 2
    assert response.json()["fact"]["supersedes_id"] == old_id

    history = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context?include_history=true"
    ).json()["facts"]
    assert [item["status"] for item in history] == ["superseded", "active"]


def test_undo_supersede_restores_the_previous_value_as_active(env):
    """PR #66 review: plain DELETE on the replacement fact left the key
    with zero active values, since the fact it replaced was still sitting
    at status "superseded". `undo-supersede` must restore that fact to
    active in the same operation, not just remove the replacement."""
    created = post_fact(env, env["mine"], key="undo-create-1").json()
    old_id = created["fact"]["id"]
    corrected = fact_body(1, value={"code": "self_employed"})
    corrected["source"]["kind"] = "reader_correction"
    correction = env["client"].patch(
        f"/api/v1/profiles/{env['mine']}/context/facts/{old_id}",
        json=corrected, headers={"Idempotency-Key": "undo-correct-0001"},
    ).json()
    new_id = correction["fact"]["id"]

    undo = env["client"].post(
        f"/api/v1/profiles/{env['mine']}/context/facts/{new_id}/undo-supersede",
        json={"expected_revision": 2}, headers={"Idempotency-Key": "undo-0001"},
    )
    assert undo.status_code == 200
    body = undo.json()
    assert body["revision"] == 3
    assert body["restored_fact"]["id"] == old_id
    assert body["restored_fact"]["status"] == "active"
    assert body["restored_fact"]["value"] == {"code": "retired", "label": "Retired"}

    history = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context?include_history=true"
    ).json()["facts"]
    by_id = {item["id"]: item["status"] for item in history}
    assert by_id[old_id] == "active"
    assert by_id[new_id] == "deleted"

    # And a live domain projection has exactly one active value for the
    # key — not zero, which plain delete-the-new-fact would have left.
    projection = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context"
    ).json()
    active_for_key = [f for f in projection["facts"] if f["key"] == "employment_status"]
    assert len(active_for_key) == 1
    assert active_for_key[0]["id"] == old_id


def test_undo_supersede_rejects_a_fact_that_was_never_a_supersede(env):
    """Undoing a plain create (no `supersedes_id`) has nothing to restore
    — 404, not a silent no-op or a crash."""
    created = post_fact(env, env["mine"], key="undo-plain-create").json()
    fact_id = created["fact"]["id"]
    response = env["client"].post(
        f"/api/v1/profiles/{env['mine']}/context/facts/{fact_id}/undo-supersede",
        json={"expected_revision": 1}, headers={"Idempotency-Key": "undo-plain-0001"},
    )
    assert response.status_code == 404


def test_correction_cannot_change_the_governed_key(env):
    created = post_fact(env, env["mine"], key="immutable-key-create").json()
    changed = fact_body(1, key="occupation", value={"text": "Teacher"})
    changed["source"]["kind"] = "reader_correction"
    response = env["client"].patch(
        f"/api/v1/profiles/{env['mine']}/context/facts/{created['fact']['id']}",
        json=changed, headers={"Idempotency-Key": "immutable-key-change"},
    )
    assert response.status_code == 422
    assert "cannot change" in response.json()["detail"]


def test_delete_scrubs_sensitive_value_and_export(env):
    body = fact_body(
        key="current_health_constraint", value={"text": "Recovering after surgery"}
    )
    created = post_fact(env, env["mine"], body, key="health-create-0001").json()
    fact_id = created["fact"]["id"]
    response = env["client"].request(
        "DELETE", f"/api/v1/profiles/{env['mine']}/context/facts/{fact_id}",
        json={"expected_revision": 1},
        headers={"Idempotency-Key": "health-delete-0001"},
    )
    assert response.status_code == 200
    exported = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context/export"
    ).json()
    assert exported["facts"] == []

    db = env["Session"]()
    fact = db.get(ProfileContextFact, fact_id)
    audit = db.query(ProfileContextAuditEvent).filter_by(fact_id=fact_id).all()
    assert fact.status == "deleted"
    assert fact.value is None and fact.source == {} and fact.consent == {}
    assert all(not hasattr(event, "value") for event in audit)
    db.close()


def test_health_context_defaults_to_bounded_retention(env):
    body = fact_body(
        key="current_health_constraint", value={"text": "Limited mobility"}
    )
    body["valid_from"] = "2026-08-14"
    fact = post_fact(env, env["mine"], body, key="health-bounded-create").json()["fact"]
    assert fact["valid_to"] == "2026-09-13"


def test_foreign_profile_is_indistinguishable_from_missing(env):
    foreign = env["client"].get(
        f"/api/v1/profiles/{env['theirs']}/context"
    )
    missing = env["client"].get(
        "/api/v1/profiles/does-not-exist/context"
    )
    assert foreign.status_code == missing.status_code == 404
    assert foreign.json() == missing.json() == {"detail": "Profile not found"}


def test_profile_a_fact_never_reaches_profile_b(env):
    assert post_fact(env, env["mine"], key="profile-a-create").status_code == 201
    other = env["client"].get(
        f"/api/v1/profiles/{env['second']}/context?domain=career"
    ).json()
    assert other["revision"] == 0
    assert other["facts"] == []


@pytest.mark.parametrize("body", [
    fact_body(key="unknown_key", value={"text": "anything"}),
    fact_body(value={"code": "astronaut"}),
    {**fact_body(), "consent": {"state": "granted", "surface": "x"}},
])
def test_unregistered_or_invalid_facts_are_rejected(env, body):
    response = post_fact(env, env["mine"], body, key=f"invalid-{body['key']}-0001")
    assert response.status_code == 422


def test_expired_fact_is_excluded_from_projection(env):
    body = fact_body()
    body["valid_to"] = "2022-01-01"
    assert post_fact(env, env["mine"], body, key="expired-create-1").status_code == 201
    context = env["client"].get(
        f"/api/v1/profiles/{env['mine']}/context?domain=career&as_of=2026-08-14"
    ).json()
    assert context["facts"] == []
