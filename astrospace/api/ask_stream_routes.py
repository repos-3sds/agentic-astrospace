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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..agents.orchestrator import AskOrchestrator
from ..agents.schema import StructuredReading
from ..context.taxonomy import TaxonomyError
from ..db import crud, crud_mobile as cm, get_db
from .ask_routes import MAX_HISTORY, AskRequest, _history_from_thread, _owned_thread
from .auth import CurrentUser
from .context_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/ask", tags=["ask-ai"])


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


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

    orchestrator = AskOrchestrator(chart_loader=lambda: _chart_from_kundli(k, "lahiri", "mean"))
    try:
        outcome = orchestrator.prepare(
            body.question, thread_domain=thread_domain, domain_override=body.domain_override,
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
            yield _sse({**envelope, "thread_id": thread_id})

        return StreamingResponse(generate_terminal(), media_type="text/event-stream")

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

    def generate():
        for event in orchestrator.run(prepared, messages, persist=persist_prepared):
            yield _sse(event)

    return StreamingResponse(generate(), media_type="text/event-stream")
