"""Transactional persistence for the Profile Context Ledger."""

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..context.profile_context import (
    FACT_REGISTRY,
    fact_is_current,
    logical_constraints,
    relevant_to_domain,
)
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


def undo_supersede(db: Session, *, user_id: str, profile_id: str, fact_id: str,
                   expected_revision: int, idempotency_key: str,
                   request_hash: str) -> dict | None:
    """Reverses ONE automatic-mode supersede as a single atomic operation.

    `fact_id` is the NEW fact (`supersede_fact`'s replacement). Plain
    deletion of that fact — what the reader-facing "Undo" action used
    before this existed — leaves the key with zero active facts, because
    the OLD value it replaced is still sitting at `status: "superseded"`,
    not `"active"`. This does both halves in one revision bump: the new
    fact is retired (scrubbed the same way an ordinary delete already
    scrubs a fact — see `change_fact_status`), and the fact it superseded
    is restored to `"active"`. Undo only reverses the most recent hop —
    it does not walk further back through a chain of corrections.

    Returns None (same 404-shaped contract as `change_fact_status`) when
    `fact_id` isn't a currently-active fact that actually resulted from a
    supersede, or when the fact it claims to have superseded isn't
    currently in `"superseded"` status — both mean there is nothing valid
    to undo, not a revision conflict."""
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
        if not fact or fact.status != "active" or not fact.supersedes_id:
            db.rollback()
            return None
        previous = get_fact(db, user_id, profile_id, fact.supersedes_id, lock=True)
        if not previous or previous.status != "superseded":
            db.rollback()
            return None
        revision = _advance(ledger, expected_revision)
        fact.status = "deleted"
        fact.value = None
        fact.source = {}
        fact.consent = {}
        fact.deleted_at = datetime.utcnow()
        fact.updated_at = datetime.utcnow()
        previous.status = "active"
        previous.updated_at = datetime.utcnow()
        response = {
            "revision": revision, "removed_fact_id": fact.id,
            "restored_fact": fact_dict(previous),
        }
        _record(db, user_id=user_id, profile_id=profile_id,
                idempotency_key=idempotency_key, request_hash=request_hash,
                action="undone", fact=fact, revision=revision, response=response,
                category=previous.category, key=previous.key)
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


@dataclass(frozen=True)
class FrozenProfileContextProjection:
    """One immutable snapshot of a profile's ledger, as of the moment it was
    built. Both `profile_context_routes.py` (the reader-facing "what Siddha
    remembers" screen) and `AskOrchestrator` (Phase 2) build this through
    the SAME function — one deterministic evidence-resolution boundary, not
    a route-only projection and a second orchestrator-only one.

    "Frozen" is a naming discipline, not a runtime lock: this is a plain
    dataclass built once from one set of queries and then only ever read.
    Nothing in this module re-queries the ledger after construction — an
    Ask turn that builds this once before generation and never rebuilds it
    during repair/verification gets that guarantee for free by simply never
    calling this function a second time for the same turn. See
    `AskOrchestrator.check_profile_context()`."""
    profile_id: str
    revision: int
    as_of: str
    domain: str | None
    status: str
    contradictions: tuple[str, ...] = ()
    facts: tuple[dict, ...] = ()
    logical_constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "revision": self.revision,
            "as_of": self.as_of,
            "domain": self.domain,
            "status": self.status,
            "contradictions": list(self.contradictions),
            "facts": [dict(f) for f in self.facts],
            "logical_constraints": list(self.logical_constraints),
        }


def build_profile_context_projection(
    db: Session, *, user_id: str, profile_id: str,
    domain: str | None = None, as_of: date | None = None,
    include_history: bool = False,
) -> FrozenProfileContextProjection:
    """The one shared projection builder — see `FrozenProfileContextProjection`.

    Does NOT check profile ownership. Every caller already sits behind an
    ownership check that returns 404 for an absent-or-foreign profile before
    this runs: `profile_context_routes.py`'s `_owned_profile()` for the
    mobile surface, and the chart loader's own `crud.get_kundli()` check
    (astrospace/api/ask_routes.py, ask_stream_routes.py) for Ask — by the
    time an Ask turn reaches this function, the profile is already resolved.
    Filtering by BOTH `user_id` and `profile_id` here means a mismatched
    pair simply returns an empty, revision-0 projection rather than another
    account's data, so this stays safe even if a future caller forgot the
    upstream check — but the uniform 404 behaviour itself is the caller's
    job, not this function's, exactly like `list_facts` already works."""
    effective_date = as_of or date.today()
    ledger = db.query(ProfileContextLedger).filter_by(
        profile_id=profile_id, user_id=user_id
    ).first()
    revision = ledger.revision if ledger else 0

    rows = list_facts(db, user_id, profile_id, include_history=include_history)
    facts: list[dict] = []
    for row in rows:
        spec = FACT_REGISTRY.get(row.key)
        if not spec:
            continue
        if include_history or (fact_is_current(row, effective_date) and relevant_to_domain(spec, domain)):
            item = fact_dict(row)
            item["ref"] = f"profile_fact:{row.id}@{row.revision}"
            facts.append(item)

    current_by_key: dict[str, list[dict]] = {}
    for fact in facts:
        if fact["status"] == "active":
            current_by_key.setdefault(fact["key"], []).append(fact)
    contradictions = [key for key, values in current_by_key.items() if len(values) > 1]
    current = [fact for fact in facts if fact["status"] == "active"]

    return FrozenProfileContextProjection(
        profile_id=profile_id,
        revision=revision,
        as_of=effective_date.isoformat(),
        domain=domain,
        status="context_confirmation_needed" if contradictions else "ready",
        contradictions=tuple(contradictions),
        facts=tuple(facts),
        logical_constraints=() if contradictions else tuple(logical_constraints(current)),
    )


def resolve_fact_ref(
    db: Session, *, user_id: str, profile_id: str, ref: str,
) -> ProfileContextFact | None:
    """Resolve one `profile_fact:<id>@<revision>` evidence ref against the
    real ledger — used by the verifier to confirm a citation both exists
    and belongs to this exact profile/revision, not a wrong-profile or
    stale/superseded one. See `astrospace/agents/verifier.py`."""
    if not ref.startswith("profile_fact:") or "@" not in ref:
        return None
    body = ref[len("profile_fact:"):]
    fact_id, _, revision_str = body.partition("@")
    if not fact_id or not revision_str.isdigit():
        return None
    fact = get_fact(db, user_id, profile_id, fact_id)
    if fact is None or fact.revision != int(revision_str):
        return None
    return fact
