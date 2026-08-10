"""Ask-AI, streamed — the orchestrator path (v2).

Additive alongside `/api/v1/ask/{kundli_id}` (ask_routes.py), which stays
untouched. Thin by design: this module resolves HTTP/DB concerns (auth,
kundli lookup, thread/history, persistence), and hands everything else to
`AskOrchestrator` (astrospace/agents/orchestrator.py) — routing, safety,
registry gating, context assembly, generation, and verification all live
there, not here.

No silent fallback: a domain the registry doesn't know about never reaches
a model call — see `AskOrchestrator.prepare()`. `prepare()` runs before the
`StreamingResponse` is created, so a bad-birth-data error still comes back
as a normal HTTPException instead of surfacing mid-stream where the status
code can no longer change; only generation, verification, and persistence
happen lazily inside the stream.
"""
import json
import traceback
from typing import Iterator, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..agents.orchestrator import AskOrchestrator, ValidationStore
from ..agents.schema import StructuredReading
from ..agents.validation_agent import ValidationProbeDraft
from ..context.taxonomy import TaxonomyError
from ..db import crud, crud_mobile as cm, get_db
from .ask_routes import MAX_HISTORY, AskRequest, _history_from_thread, _owned_thread
from .auth import CurrentUser
from .context_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/ask", tags=["ask-ai"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _safe_stream(events: Iterator[dict]) -> Iterator[str]:
    """Every SSE stream this route returns goes through here — the
    guarantee is that the stream always ends in a terminal frame, even if
    something inside the generator throws that nothing upstream expected
    (a DB write failure, a bug in event construction). Without this, an
    unhandled exception mid-generator just kills the connection: no `done`,
    no error frame, the client left with no way to know the stream is never
    coming back. `HTTPException`/`TaxonomyError` paths above (still inside
    `prepare()`, before the response starts) aren't affected by this — this
    only covers exceptions raised after streaming has already begun, which
    is the gap that had no contract at all before."""
    try:
        for event in events:
            yield _sse(event)
    except Exception:
        traceback.print_exc()
        yield _sse({
            "type": "fatal_error",
            "message": "Something went wrong while generating this answer. Please try again.",
            "retryable": True,
        })


def _thread_established_domain(db: Session, thread_id: str) -> Optional[str]:
    """The domain the thread most recently actually answered in — the last
    assistant turn with a non-null `domain` field, skipping over
    clarification turns (domain=None) and domain-not-ready turns (domain
    is the *unconfigured* name, which `AskOrchestrator.route()` will
    reject anyway since it only honours a `thread_domain` that's actually
    in the registry). None for a brand-new thread or one that's only ever
    hit clarification/not-ready so far — nothing to continue."""
    messages = cm.get_thread_messages(db, thread_id)
    for message in reversed(messages):
        if message.role == "assistant" and message.domain:
            return message.domain
    return None


def _probe_row(probe) -> dict:
    """A stored probe as the orchestrator and the context engine see it.

    `claim_text`/`confidence` are included because `life_context` scoring needs
    the outcome, not because anything downstream may change them — the only
    write path that touches those columns is the commit itself (see
    crud_mobile.record_validation_answer)."""
    return {
        "slot_id": probe.slot_id,
        "slot_kind": probe.slot_kind,
        "anchor_label": probe.anchor_label,
        "anchor_start": probe.anchor_start,
        "anchor_end": probe.anchor_end,
        "question": probe.question,
        "claim_text": probe.claim_text,
        "claim_candidate": probe.claim_candidate,
        "confidence": probe.confidence,
        "answer_key": probe.answer_key,
        "answer_text": probe.answer_text,
        "status": probe.status,
    }


def _validation_store(db: Session, user_id: str, kundli_id: str,
                      thread_id: Optional[str]) -> ValidationStore:
    """The orchestrator's two callables, closed over this request's session."""

    def probes() -> list[dict]:
        return [_probe_row(row) for row in
                cm.list_validation_probes(db, user_id, kundli_id)]

    def commit(slot: dict, draft: ValidationProbeDraft) -> str:
        probe = cm.commit_validation_probe(
            db, user_id, kundli_id, slot["domain"], slot,
            claim_text=draft.committed_claim,
            claim_candidate=draft.committed_candidate,
            confidence=draft.confidence,
            question=draft.question,
            options=[option.model_dump() for option in draft.options],
            thread_id=thread_id,
        )
        return probe.id

    return ValidationStore(probes=probes, commit=commit)


def _evidence_from_reading(reading: StructuredReading) -> dict:
    """Namespaced, versioned bridge shape for `AskMessage.evidence` — this is
    explicitly a temporary storage decision, not the final one. Wrapping it
    (rather than dumping the raw structured object) makes that obvious to
    the next person who reads a row, and keeps `evidence`'s meaning
    comparable across old rows (`{"tools_used": [...]}` etc., from before
    this build) and new ones."""
    return {
        "schema_version": "ask_structured_v1",
        "structured_reading": reading.model_dump(),
        "references": [item.source for item in reading.technical_basis],
    }


@router.post("/{kundli_id}/stream")
def ask_stream(kundli_id: str, body: AskRequest, user: CurrentUser,
               db: Session = Depends(get_db)):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")

    thread = None
    if body.thread_id:
        thread = _owned_thread(db, body.thread_id, user.id)
        if thread.kundli_id != kundli_id:
            raise HTTPException(status_code=400, detail="Thread belongs to a different kundli")
        turns = _history_from_thread(db, thread.id)
    else:
        turns = [{"role": t.role, "content": t.content} for t in (body.history or [])]

    messages = turns[-MAX_HISTORY:]
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": body.question})

    def persist_turn(content: str, domain: Optional[str], refer_out_kind: Optional[str],
                     evidence: Optional[dict]) -> Optional[str]:
        """Shared by every terminal path (refer-out, clarification,
        domain-not-ready, answered) and by the orchestrator's own
        `persist` callback for the success/failure-after-generation path.
        Nothing is written until there is a final outcome — a failed or
        interrupted turn persists nothing new, matching ask_routes.py's
        existing convention, and never creates a thread on a generation
        failure even if `start_thread` was set."""
        local_thread = thread
        if local_thread is None and body.start_thread:
            local_thread = cm.create_ask_thread(db, user.id, kundli_id)
        if local_thread is None:
            return None
        cm.add_ask_message(db, local_thread.id, "user", body.question,
                           language=body.language, input_mode=body.input_mode)
        cm.add_ask_message(db, local_thread.id, "assistant", content,
                           language=body.language, domain=domain,
                           refer_out_kind=refer_out_kind, evidence=evidence or {})
        db.refresh(local_thread)
        return local_thread.id

    thread_domain = _thread_established_domain(db, thread.id) if thread else None

    orchestrator = AskOrchestrator(
        chart_loader=lambda: _chart_from_kundli(k, "lahiri", "mean"),
        validation_store=_validation_store(db, user.id, kundli_id,
                                           thread.id if thread else None),
    )
    try:
        outcome = orchestrator.prepare(
            body.question, thread_domain=thread_domain, domain_override=body.domain_override,
            experience_mode=body.experience_mode, validate_first=body.validate_first,
        )
    except TaxonomyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if outcome.terminal_envelope is not None:
        envelope = outcome.terminal_envelope

        def generate_terminal():
            if envelope["type"] == "refer_out":
                thread_id = persist_turn(
                    envelope["answer"], domain=None, refer_out_kind=envelope["kind"],
                    evidence={"safety_policy": "excluded_verdict"},
                )
            elif envelope["type"] == "validation_needed":
                # The stored turn carries the question and the options, never
                # the committed claim — thread history is replayed back to the
                # model on later turns, and a claim visible there would let a
                # future reading quietly launder its own prediction as
                # evidence. The commitment lives in validation_probes, which
                # nothing replays.
                thread_id = persist_turn(
                    envelope["question"], domain=envelope["domain"], refer_out_kind=None,
                    evidence={"status": "validation_needed",
                              "probe_id": envelope["probe_id"],
                              "slot_id": envelope["slot_id"],
                              "options": envelope["options"]},
                )
            elif envelope["type"] == "clarification_needed":
                content = (
                    f"I can help with: {', '.join(envelope['options'])} right now — "
                    "which one is this about?"
                )
                thread_id = persist_turn(
                    content, domain=None, refer_out_kind=None,
                    evidence={"clarification_options": envelope["options"]},
                )
            else:  # domain_not_ready
                content = (
                    f"{envelope['domain_label']} isn't ready yet. "
                    f"I can currently help with: {', '.join(envelope['available'])}."
                )
                thread_id = persist_turn(
                    content, domain=envelope["domain"], refer_out_kind=None,
                    evidence={"status": "domain_not_ready", "available": envelope["available"]},
                )
            yield {**envelope, "thread_id": thread_id}

        return StreamingResponse(_safe_stream(generate_terminal()), media_type="text/event-stream")

    prepared = outcome.prepared

    def persist_prepared(reading: Optional[StructuredReading], status: str) -> Optional[str]:
        if reading is None:
            # A failed generation/verification writes nothing new — only
            # report the thread that already existed, if any.
            return thread.id if thread else None
        return persist_turn(
            reading.interpretation, domain=prepared.domain, refer_out_kind=None,
            evidence=_evidence_from_reading(reading),
        )

    return StreamingResponse(
        _safe_stream(orchestrator.run(prepared, messages, persist=persist_prepared)),
        media_type="text/event-stream",
    )


class ValidationAnswer(BaseModel):
    answer_key: str = Field(
        min_length=1,
        description="One of the option keys from the `validation_needed` envelope. "
                    "'skip' is always offered and is recorded without being scored "
                    "either way — a reader declining to answer is not evidence about "
                    "their chart.",
    )
    answer_text: Optional[str] = Field(
        None, max_length=2000,
        description="Optional free-text the reader added alongside the option.",
    )


@router.post("/validation/{probe_id}/answer")
def answer_validation_probe(probe_id: str, body: ValidationAnswer, user: CurrentUser,
                            db: Session = Depends(get_db)):
    """Score a committed claim against what the reader actually said.

    Nothing here can touch the claim, its confidence, or its commit timestamp —
    `record_validation_answer` writes answer columns only, which is what makes
    the resulting hit rate an honest number rather than a self-graded one. A
    probe already answered is refused rather than overwritten: it was one test.
    """
    probe = cm.record_validation_answer(
        db, probe_id, user.id, body.answer_key, body.answer_text,
    )
    if probe is None:
        raise HTTPException(
            status_code=404,
            detail="No unanswered validation probe with that id for this user",
        )
    return {
        "probe_id": probe.id,
        "slot_id": probe.slot_id,
        "status": probe.status,
        # Safe to return now, and only now: the reader has committed their own
        # answer, so showing them what the chart predicted can no longer
        # influence it. This is the moment the loop is worth anything to them.
        "committed_claim": probe.claim_text,
        "confidence": probe.confidence,
        "answered_at": probe.answered_at,
    }
