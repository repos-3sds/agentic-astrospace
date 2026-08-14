"""Profile-owned APIs for explicit, consented life-context memory."""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from .auth import CurrentUser
from ..context.profile_context import (
    FACT_REGISTRY,
    fact_is_current,
    logical_constraints,
    relevant_to_domain,
    validate_fact_value,
)
from ..db import Kundli, get_db
from ..db import crud
from ..db.crud_profile_context import (
    IdempotencyConflict,
    InvalidFactMutation,
    RevisionConflict,
    change_fact_status,
    create_fact,
    fact_dict,
    get_or_create_ledger,
    list_facts,
    supersede_fact,
)

router = APIRouter(prefix="/api/v1/profiles", tags=["profile-context"])


class FactSource(BaseModel):
    # Ask extraction is a later phase. Phase 1 cannot persist model-proposed
    # content through this structured profile-form endpoint.
    kind: Literal["profile_form", "reader_correction"]
    channel: Literal["profile_settings", "onboarding"]


class FactConsent(BaseModel):
    state: Literal["granted"]
    surface: str = Field(min_length=3, max_length=80)
    captured_at: datetime | None = None


class FactWrite(BaseModel):
    expected_revision: int = Field(ge=0)
    key: str
    value: dict
    valid_from: date | None = None
    valid_to: date | None = None
    source: FactSource
    consent: FactConsent

    @model_validator(mode="after")
    def validate_dates(self):
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to cannot precede valid_from")
        return self


class FactMutation(BaseModel):
    expected_revision: int = Field(ge=0)


def _owned_profile(db: Session, profile_id: str, user_id: str) -> Kundli:
    profile = crud.get_kundli(db, profile_id, user_id)
    if not profile:
        # Same response for absent and foreign-owned profiles avoids enumeration.
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def _request_hash(action: str, payload: dict) -> str:
    canonical = json.dumps(
        {"action": action, "payload": payload}, sort_keys=True,
        separators=(",", ":"), default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _idempotency_key(value: str | None) -> str:
    if not value or len(value.strip()) < 8 or len(value) > 160:
        raise HTTPException(status_code=400, detail="A valid Idempotency-Key is required")
    return value.strip()


def _write_data(body: FactWrite) -> dict:
    try:
        spec = validate_fact_value(body.key, body.value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    consent = body.consent.model_dump(mode="json")
    consent["captured_at"] = (
        body.consent.captured_at or datetime.now(timezone.utc)
    ).isoformat()
    valid_to = body.valid_to
    if spec.retention == "30_days" and valid_to is None:
        valid_to = (body.valid_from or date.today()) + timedelta(days=30)
    if spec.retention == "target_date" and valid_to is None:
        raise HTTPException(status_code=422, detail="A target-date fact requires valid_to")
    return {
        "category": spec.category,
        "key": spec.key,
        "value": body.value,
        "valid_from": body.valid_from,
        "valid_to": valid_to,
        "status": "active",
        "confidence": "confirmed",
        "sensitivity": spec.sensitivity,
        "retention": spec.retention,
        "source": body.source.model_dump(mode="json", exclude_none=True),
        "consent": consent,
    }


def _run_mutation(call):
    try:
        return call()
    except RevisionConflict as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "stale_revision", "current_revision": exc.revision},
        ) from exc
    except IdempotencyConflict as exc:
        raise HTTPException(
            status_code=409, detail={"code": "idempotency_key_reused"}
        ) from exc
    except InvalidFactMutation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{profile_id}/context")
def get_profile_context(
    profile_id: str,
    user: CurrentUser,
    domain: str | None = Query(default=None),
    as_of: date | None = Query(default=None),
    include_history: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    _owned_profile(db, profile_id, user.id)
    from ..db.models import ProfileContextLedger
    ledger = db.query(ProfileContextLedger).filter_by(
        profile_id=profile_id, user_id=user.id
    ).first()
    revision = ledger.revision if ledger else 0
    effective_date = as_of or date.today()
    rows = list_facts(db, user.id, profile_id, include_history=include_history)
    facts = []
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
    return {
        "profile_id": profile_id,
        "revision": revision,
        "as_of": effective_date.isoformat(),
        "status": "context_confirmation_needed" if contradictions else "ready",
        "contradictions": contradictions,
        "facts": facts,
        "logical_constraints": [] if contradictions else logical_constraints(current),
    }


@router.post("/{profile_id}/context/facts", status_code=201)
def add_profile_fact(
    profile_id: str,
    body: FactWrite,
    user: CurrentUser,
    idempotency: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    _owned_profile(db, profile_id, user.id)
    key = _idempotency_key(idempotency)
    payload = body.model_dump(mode="json")
    data = _write_data(body)
    return _run_mutation(lambda: create_fact(
        db, user_id=user.id, profile_id=profile_id, data=data,
        expected_revision=body.expected_revision, idempotency_key=key,
        request_hash=_request_hash("create", payload),
    ))


@router.patch("/{profile_id}/context/facts/{fact_id}")
def correct_profile_fact(
    profile_id: str,
    fact_id: str,
    body: FactWrite,
    user: CurrentUser,
    idempotency: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    _owned_profile(db, profile_id, user.id)
    key = _idempotency_key(idempotency)
    payload = body.model_dump(mode="json")
    result = _run_mutation(lambda: supersede_fact(
        db, user_id=user.id, profile_id=profile_id, fact_id=fact_id,
        data=_write_data(body), expected_revision=body.expected_revision,
        idempotency_key=key, request_hash=_request_hash(f"correct:{fact_id}", payload),
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return result


def _status_mutation(profile_id: str, fact_id: str, body: FactMutation,
                     user, idempotency: str | None, db: Session, action: str):
    _owned_profile(db, profile_id, user.id)
    key = _idempotency_key(idempotency)
    payload = body.model_dump(mode="json")
    result = _run_mutation(lambda: change_fact_status(
        db, user_id=user.id, profile_id=profile_id, fact_id=fact_id,
        action=action, expected_revision=body.expected_revision,
        idempotency_key=key, request_hash=_request_hash(f"{action}:{fact_id}", payload),
    ))
    if result is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return result


@router.delete("/{profile_id}/context/facts/{fact_id}")
def delete_profile_fact(
    profile_id: str, fact_id: str, body: FactMutation, user: CurrentUser,
    idempotency: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    return _status_mutation(profile_id, fact_id, body, user, idempotency, db, "deleted")


@router.post("/{profile_id}/context/facts/{fact_id}/dispute")
def dispute_profile_fact(
    profile_id: str, fact_id: str, body: FactMutation, user: CurrentUser,
    idempotency: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    return _status_mutation(profile_id, fact_id, body, user, idempotency, db, "disputed")


@router.get("/{profile_id}/context/export")
def export_profile_context(profile_id: str, user: CurrentUser,
                           db: Session = Depends(get_db)):
    _owned_profile(db, profile_id, user.id)
    from ..db.models import ProfileContextLedger
    ledger = db.query(ProfileContextLedger).filter_by(
        profile_id=profile_id, user_id=user.id
    ).first()
    facts = [fact_dict(row) for row in list_facts(
        db, user.id, profile_id, include_history=True
    ) if row.status != "deleted"]
    return {
        "schema_version": "profile_context_export_v1",
        "profile_id": profile_id,
        "revision": ledger.revision if ledger else 0,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "facts": facts,
    }
