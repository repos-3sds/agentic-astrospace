"""Transactional persistence for the Profile Context Ledger."""

from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import (
    ProfileContextAuditEvent,
    ProfileContextFact,
    ProfileContextLedger,
    ProfileContextMutation,
)


class RevisionConflict(Exception):
    def __init__(self, revision: int):
        self.revision = revision


class IdempotencyConflict(Exception):
    pass


class InvalidFactMutation(Exception):
    pass


def fact_dict(fact: ProfileContextFact, *, include_value: bool = True) -> dict:
    return {
        "id": fact.id,
        "category": fact.category,
        "key": fact.key,
        "value": fact.value if include_value else None,
        "valid_from": fact.valid_from.isoformat() if fact.valid_from else None,
        "valid_to": fact.valid_to.isoformat() if fact.valid_to else None,
        "status": fact.status,
        "confidence": fact.confidence,
        "sensitivity": fact.sensitivity,
        "retention": fact.retention,
        "source": fact.source,
        "consent": fact.consent,
        "supersedes_id": fact.supersedes_id,
        "revision": fact.revision,
        "created_at": fact.created_at.isoformat() if fact.created_at else None,
        "updated_at": fact.updated_at.isoformat() if fact.updated_at else None,
    }


def get_or_create_ledger(db: Session, user_id: str, profile_id: str) -> ProfileContextLedger:
    # Both supported databases implement this conflict form. Initialising before
    # locking closes the two-first-writes race without a failed transaction.
    db.execute(text("""
        INSERT INTO profile_context_ledgers (profile_id, user_id, revision, created_at, updated_at)
        VALUES (:profile_id, :user_id, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(profile_id) DO NOTHING
    """), {"profile_id": profile_id, "user_id": user_id})
    db.flush()
    ledger = (
        db.query(ProfileContextLedger)
        .filter(ProfileContextLedger.profile_id == profile_id,
                ProfileContextLedger.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not ledger:
        raise RuntimeError("Profile context ledger could not be initialized")
    return ledger


def list_facts(db: Session, user_id: str, profile_id: str,
               *, include_history: bool = False) -> list[ProfileContextFact]:
    query = db.query(ProfileContextFact).filter(
        ProfileContextFact.user_id == user_id,
        ProfileContextFact.profile_id == profile_id,
    )
    if not include_history:
        query = query.filter(ProfileContextFact.status.in_(("active", "disputed")))
    return query.order_by(ProfileContextFact.revision, ProfileContextFact.created_at).all()


def get_fact(db: Session, user_id: str, profile_id: str, fact_id: str,
             *, lock: bool = False) -> ProfileContextFact | None:
    query = db.query(ProfileContextFact).filter(
        ProfileContextFact.id == fact_id,
        ProfileContextFact.user_id == user_id,
        ProfileContextFact.profile_id == profile_id,
    )
    if lock:
        query = query.with_for_update()
    return query.first()


def _replay(db: Session, user_id: str, profile_id: str,
            idempotency_key: str, request_hash: str) -> dict | None:
    mutation = db.query(ProfileContextMutation).filter(
        ProfileContextMutation.user_id == user_id,
        ProfileContextMutation.profile_id == profile_id,
        ProfileContextMutation.idempotency_key == idempotency_key,
    ).first()
    if not mutation:
        return None
    if mutation.request_hash != request_hash:
        raise IdempotencyConflict()
    if mutation.fact_id:
        fact = get_fact(db, user_id, profile_id, mutation.fact_id)
        if fact and fact.status != "deleted":
            return {"revision": mutation.resulting_revision, "fact": fact_dict(fact)}
        if fact:
            return {
                "revision": mutation.resulting_revision,
                "fact_id": fact.id,
                "status": "deleted",
            }
    return mutation.response


def _advance(ledger: ProfileContextLedger, expected_revision: int) -> int:
    if ledger.revision != expected_revision:
        raise RevisionConflict(ledger.revision)
    ledger.revision += 1
    ledger.updated_at = datetime.utcnow()
    return ledger.revision


def _record(db: Session, *, user_id: str, profile_id: str,
            idempotency_key: str, request_hash: str, action: str,
            fact: ProfileContextFact | None, revision: int, response: dict,
            category: str | None = None, key: str | None = None) -> None:
    db.add(ProfileContextMutation(
        user_id=user_id, profile_id=profile_id,
        idempotency_key=idempotency_key, request_hash=request_hash,
        action=action, fact_id=fact.id if fact else None,
        resulting_revision=revision,
        # Idempotency storage deliberately contains no fact value. Replays
        # resolve the owned fact row; after deletion they cannot resurrect prose.
        response={
            "revision": revision,
            "fact_id": fact.id if fact else None,
            "status": fact.status if fact else action,
        },
    ))
    db.add(ProfileContextAuditEvent(
        user_id=user_id, profile_id=profile_id,
        fact_id=fact.id if fact else None, action=action,
        category=category or (fact.category if fact else None),
        key=key or (fact.key if fact else None), revision=revision,
    ))


def create_fact(db: Session, *, user_id: str, profile_id: str, data: dict,
                expected_revision: int, idempotency_key: str,
                request_hash: str) -> dict:
    replay = _replay(db, user_id, profile_id, idempotency_key, request_hash)
    if replay is not None:
        return replay
    try:
        ledger = get_or_create_ledger(db, user_id, profile_id)
        replay = _replay(db, user_id, profile_id, idempotency_key, request_hash)
        if replay is not None:
            db.rollback()
            return replay
        revision = _advance(ledger, expected_revision)
        fact = ProfileContextFact(
            user_id=user_id, profile_id=profile_id, revision=revision, **data
        )
        db.add(fact)
        db.flush()
        response = {"revision": revision, "fact": fact_dict(fact)}
        _record(db, user_id=user_id, profile_id=profile_id,
                idempotency_key=idempotency_key, request_hash=request_hash,
                action="created", fact=fact, revision=revision, response=response)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def supersede_fact(db: Session, *, user_id: str, profile_id: str, fact_id: str,
                   data: dict, expected_revision: int, idempotency_key: str,
                   request_hash: str) -> dict | None:
    replay = _replay(db, user_id, profile_id, idempotency_key, request_hash)
    if replay is not None:
        return replay
    try:
        ledger = get_or_create_ledger(db, user_id, profile_id)
        replay = _replay(db, user_id, profile_id, idempotency_key, request_hash)
        if replay is not None:
            db.rollback()
            return replay
        old = get_fact(db, user_id, profile_id, fact_id, lock=True)
        if not old or old.status not in ("active", "disputed"):
            db.rollback()
            return None
        if data.get("key") != old.key:
            raise InvalidFactMutation("A correction cannot change the fact key")
        revision = _advance(ledger, expected_revision)
        old.status = "superseded"
        old.updated_at = datetime.utcnow()
        fact = ProfileContextFact(
            user_id=user_id, profile_id=profile_id, revision=revision,
            supersedes_id=old.id, **data,
        )
        db.add(fact)
        db.flush()
        response = {"revision": revision, "fact": fact_dict(fact)}
        _record(db, user_id=user_id, profile_id=profile_id,
                idempotency_key=idempotency_key, request_hash=request_hash,
                action="superseded", fact=fact, revision=revision, response=response)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def change_fact_status(db: Session, *, user_id: str, profile_id: str,
                       fact_id: str, action: str, expected_revision: int,
                       idempotency_key: str, request_hash: str) -> dict | None:
    replay = _replay(db, user_id, profile_id, idempotency_key, request_hash)
    if replay is not None:
        return replay
    try:
        ledger = get_or_create_ledger(db, user_id, profile_id)
        replay = _replay(db, user_id, profile_id, idempotency_key, request_hash)
        if replay is not None:
            db.rollback()
            return replay
        fact = get_fact(db, user_id, profile_id, fact_id, lock=True)
        if not fact or fact.status not in ("active", "disputed"):
            db.rollback()
            return None
        revision = _advance(ledger, expected_revision)
        category, key = fact.category, fact.key
        if action == "deleted":
            fact.status = "deleted"
            fact.value = None
            fact.source = {}
            fact.consent = {}
            fact.deleted_at = datetime.utcnow()
        elif action == "disputed":
            fact.status = "disputed"
            fact.confidence = "disputed"
        else:
            raise ValueError("Unsupported fact status action")
        fact.updated_at = datetime.utcnow()
        response = {"revision": revision, "fact_id": fact.id, "status": fact.status}
        _record(db, user_id=user_id, profile_id=profile_id,
                idempotency_key=idempotency_key, request_hash=request_hash,
                action=action, fact=fact, revision=revision, response=response,
                category=category, key=key)
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise
