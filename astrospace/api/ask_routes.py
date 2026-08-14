"""Ask-AI.

Conversations can be stateless (the client supplies `history`, as the web app
does) or persisted server-side as threads, which is what the mobile app needs
so a conversation survives leaving the screen.

Why writes happen only after a successful generation
----------------------------------------------------
The agent loop requires a conversation that starts with a user turn and
alternates cleanly. Writing the user's message before calling the model would
leave a dangling user turn behind whenever generation fails, and the next
request would replay a history with two user messages in a row. So the user
and assistant messages are written together, once there is an answer. A failed
request persists nothing and is safe to retry.
"""
from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..agents.orchestrator import AskOrchestrator
from ..agents.schema import StructuredReading
from ..context.taxonomy import TaxonomyError
from ..db import get_db
from ..db import crud, crud_mobile as cm
from .auth import CurrentUser
from .context_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/ask", tags=["ask-ai"])

MAX_HISTORY = 12
MAX_QUESTION_CHARS = 2000


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    history: Optional[list[HistoryTurn]] = None
    thread_id: Optional[str] = Field(
        None,
        description="Continue a saved thread. Its stored messages are used as "
                    "history and `history` in the body is ignored.",
    )
    start_thread: bool = Field(
        False, description="Create and persist a new thread for this question."
    )
    language: str = "en"
    input_mode: Literal["text", "voice"] = "text"
    domain_override: Optional[str] = Field(
        None,
        description="An explicit domain the reader chose (e.g. tapping a "
                    "clarification chip) — bypasses keyword routing entirely "
                    "rather than being folded back into the question text, "
                    "since repeating a keyword the router already saw once "
                    "does not change its score. Only honoured by the "
                    "streamed v2 orchestrator (ask_stream_routes.py).",
    )
    experience_mode: Literal["guided", "balanced", "practitioner"] = Field(
        "balanced",
        description="The reader's own preference (PreferencesService's "
                    "ExperienceMode), selecting the answer's VOICE — guided "
                    "speaks as a warm counsellor in plain language, "
                    "practitioner speaks peer-to-peer in full technical "
                    "vocabulary. It never changes the facts, the claims "
                    "allowed, or any guardrail: the same verified bundle is "
                    "spoken three ways. Previously this preference existed "
                    "only in the frontend and merely hid technical_basis "
                    "rows, so every reader got word-for-word the same "
                    "analyst-voiced answer.",
    )
    validate_first: bool = Field(
        False,
        description="Opt this turn into the consultation validation loop: "
                    "instead of answering immediately, the agent commits to a "
                    "falsifiable claim about a dated window in the reader's "
                    "chart, stores it, and returns one multiple-choice "
                    "question about that window as a `validation_needed` "
                    "envelope. Answer it via POST /api/v1/ask/validation/"
                    "{probe_id}/answer, then re-send the original question. "
                    "Defaults False because a client that cannot render that "
                    "envelope would show the reader nothing at all; answered "
                    "probes feed back into every reading as `life_context` "
                    "whether or not this flag is set. Only honoured by the "
                    "streamed v2 orchestrator (ask_stream_routes.py).",
    )


# ── Threads ──────────────────────────────────────────────────────────────────
# Declared before /{kundli_id} so "threads" is never read as a kundli id.

def _thread(row) -> dict:
    return {
        "id": row.id,
        "kundli_id": row.kundli_id,
        "title": row.title,
        "message_count": row.message_count,
        "last_message_at": (row.last_message_at.isoformat()
                            if row.last_message_at else None),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _message(row) -> dict:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "domain": row.domain,
        "evidence": row.evidence,
        # Present when the answer declined to advise and pointed elsewhere —
        # the client renders that differently from an ordinary reply.
        "refer_out_kind": row.refer_out_kind,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _owned_thread(db: Session, thread_id: str, user_id: str):
    thread = cm.get_ask_thread(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.get("/threads")
def list_threads(user: CurrentUser,
                 kundli_id: Optional[str] = None,
                 limit: int = Query(50, ge=1, le=200),
                 db: Session = Depends(get_db)):
    rows = cm.list_ask_threads(db, user.id, kundli_id=kundli_id, limit=limit)
    return {"count": len(rows), "threads": [_thread(r) for r in rows]}


@router.get("/threads/{thread_id}")
def get_thread(thread_id: str, user: CurrentUser,
               limit: int = Query(200, ge=1, le=500),
               db: Session = Depends(get_db)):
    thread = _owned_thread(db, thread_id, user.id)
    messages = cm.get_thread_messages(db, thread_id, limit=limit)
    return {"thread": _thread(thread), "messages": [_message(m) for m in messages]}


@router.post("/threads/{thread_id}/archive")
def archive_thread(thread_id: str, user: CurrentUser,
                   db: Session = Depends(get_db)):
    if not cm.archive_ask_thread(db, thread_id, user.id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"archived": True}


# ── Ask ──────────────────────────────────────────────────────────────────────

def _history_from_thread(db: Session, thread_id: str) -> list[dict]:
    rows = cm.get_thread_messages(db, thread_id)
    return [{"role": r.role, "content": r.content} for r in rows]


def _thread_established_domain(db: Session, thread_id: str) -> Optional[str]:
    """The domain the thread most recently actually answered in — the last
    assistant turn with a non-null `domain` field, skipping over
    clarification turns (domain=None) and domain-not-ready turns (domain
    is the *unconfigured* name, which `AskOrchestrator.route()` will reject
    anyway since it only honours a `thread_domain` that's actually in the
    registry). None for a brand-new thread or one that's only ever hit
    clarification/not-ready so far — nothing to continue.

    Shared with `ask_stream_routes.py` (imported from here) so both surfaces
    resolve thread continuation identically."""
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
    this build) and new ones.

    Shared with `ask_stream_routes.py` (imported from here) so a thread's
    evidence shape is identical regardless of which endpoint answered a
    given turn."""
    return {
        "schema_version": "ask_structured_v1",
        "structured_reading": reading.model_dump(),
        "references": [item.source for item in reading.technical_basis],
    }


@router.post("/{kundli_id}")
def ask(kundli_id: str, body: AskRequest, user: CurrentUser,
        db: Session = Depends(get_db)):
    """The web app's Ask endpoint — runs through the same `AskOrchestrator`
    pipeline as the native app's streamed `/ask/{kundli_id}/stream`
    (ask_stream_routes.py): registry gate, context assembly, `verify()`/
    `verify_coverage()`, the single repair attempt, and persistence-only-
    after-verification. Previously this route ran `VedicQAAgent` directly —
    a separate, materially weaker code path with only the input refer-out
    gate and a post-hoc `prohibited_verdict()` check, no registry gate, no
    verifier, no `dosha_overclaim_kind()`. That gap was real and live (this
    is what the web app's Ask tab actually calls), not hypothetical — see
    the architecture audit finding this closes.

    Non-streaming by contract (the web app expects one JSON response, not
    SSE), so every terminal state the orchestrator can produce is resolved
    to a single response here rather than yielded as frames. `validate_first`
    is never honoured on this route — same restriction the field's own
    docstring already states ("Only honoured by the streamed v2
    orchestrator") — so `validation_needed` cannot occur here."""
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")

    thread = None
    if body.thread_id:
        thread = _owned_thread(db, body.thread_id, user.id)
        if thread.kundli_id != kundli_id:
            raise HTTPException(
                status_code=400,
                detail="Thread belongs to a different kundli",
            )
        # The stored thread is the source of truth; a client-supplied history
        # could otherwise rewrite the conversation on the way in.
        turns = _history_from_thread(db, thread.id)
    else:
        turns = [{"role": t.role, "content": t.content}
                 for t in (body.history or [])]

    messages = turns[-MAX_HISTORY:]
    # a valid conversation must start with a user turn
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": body.question})

    def persist_turn(content: str, domain: Optional[str],
                     refer_out_kind: Optional[str],
                     evidence: Optional[dict]) -> Optional[str]:
        """Nothing is written until a terminal outcome exists — see the
        module docstring. `nonlocal thread` (not a local shadow) so the
        response built after this call sees the thread this turn actually
        used or created, matching every other terminal branch below."""
        nonlocal thread
        if thread is None and body.start_thread:
            thread = cm.create_ask_thread(db, user.id, kundli_id)
        if thread is None:
            return None
        cm.add_ask_message(db, thread.id, "user", body.question,
                           language=body.language, input_mode=body.input_mode)
        cm.add_ask_message(db, thread.id, "assistant", content,
                           language=body.language, domain=domain,
                           refer_out_kind=refer_out_kind, evidence=evidence or {})
        db.refresh(thread)
        return thread.id

    thread_domain = _thread_established_domain(db, thread.id) if thread else None

    orchestrator = AskOrchestrator(
        chart_loader=lambda: _chart_from_kundli(k, "lahiri", "mean"),
    )
    try:
        outcome = orchestrator.prepare(
            body.question, thread_domain=thread_domain,
            domain_override=body.domain_override,
            experience_mode=body.experience_mode,
            # validate_first intentionally not passed through — see docstring.
        )
    except TaxonomyError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if outcome.terminal_envelope is not None:
        envelope = outcome.terminal_envelope
        status = envelope["type"]
        if envelope["type"] == "refer_out":
            answer = envelope["answer"]
            refer_out = envelope["kind"]
            persist_turn(answer, domain=None, refer_out_kind=refer_out,
                        evidence={"safety_policy": "excluded_verdict"})
        elif envelope["type"] == "clarification_needed":
            answer = (
                f"I can help with: {', '.join(envelope['options'])} right now — "
                "which one is this about?"
            )
            refer_out = None
            persist_turn(answer, domain=None, refer_out_kind=None,
                        evidence={"clarification_options": envelope["options"]})
        else:  # domain_not_ready
            answer = (
                f"{envelope['domain_label']} isn't ready yet. "
                f"I can currently help with: {', '.join(envelope['available'])}."
            )
            refer_out = None
            persist_turn(answer, domain=envelope["domain"], refer_out_kind=None,
                        evidence={"status": "domain_not_ready",
                                  "available": envelope["available"]})
        return {
            "answer": answer,
            "tools_used": [],
            "kundli_id": kundli_id,
            "refer_out_kind": refer_out,
            # Explicit, not left for the client to infer from `answer` text
            # alone: "answered" | "refer_out" | "clarification_needed" |
            # "domain_not_ready". A clarification or an unsupported-domain
            # notice must never be mistaken for a real reading by anything
            # that reads this response — see the module docstring.
            "status": status,
            "thread_id": thread.id if thread else None,
            "thread": _thread(thread) if thread else None,
        }

    prepared = outcome.prepared

    def persist_prepared(reading: Optional[StructuredReading], status: str) -> Optional[str]:
        if reading is None:
            # A failed generation/verification writes nothing new — only
            # report the thread that already existed, if any. Matches the
            # module docstring's "a failed request persists nothing" and
            # ask_stream_routes.py's identical contract.
            return thread.id if thread else None
        return persist_turn(reading.interpretation, domain=prepared.domain,
                            refer_out_kind=None,
                            evidence=_evidence_from_reading(reading))

    done = None
    for event in orchestrator.run(prepared, messages, persist=persist_prepared):
        if event["type"] == "done":
            done = event

    if done["status"] != "answered":
        # Explicit, not a generic 500 — the reader gets a clear signal that
        # generation or verification failed, never a reading that shouldn't
        # have shipped. Matches this route's pre-migration contract (a
        # model-call exception was already a 502) and extends it to the new
        # failure mode `verify()`/`verify_coverage()` can produce that
        # VedicQAAgent never had.
        detail = ("AI generation failed" if done["status"] == "generation_failed"
                  else "The answer did not pass verification")
        raise HTTPException(status_code=502, detail=detail)

    reading = done["reading"]
    return {
        "answer": reading["interpretation"],
        "tools_used": [],
        "kundli_id": kundli_id,
        "refer_out_kind": None,
        "status": "answered",
        "thread_id": done["thread_id"],
        "thread": _thread(thread) if thread else None,
    }
