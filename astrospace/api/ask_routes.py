"""Ask-AI.

A question is either one-off or part of a server-side thread; both apps use
threads to continue a conversation. A client-supplied `history` is still
accepted for older clients but never replayed to the model (audit S15): only
turns the server stored itself can stand as the model's earlier answers.

Why writes happen only after a successful generation
----------------------------------------------------
The agent loop requires a conversation that starts with a user turn and
alternates cleanly. Writing the user's message before calling the model would
leave a dangling user turn behind whenever generation fails, and the next
request would replay a history with two user messages in a row. So the user
and assistant messages are written together, once there is an answer. A failed
request persists nothing and is safe to retry.

Why the request's transaction is released before generation
------------------------------------------------------------
A model call takes 10–90 s. Under Supabase's transaction pooler an open
transaction pins a server connection for that whole time, so the request
session is committed (`release_connection`) once `prepare()` has read
everything it needs, and the turn is written afterwards through a fresh,
short session (`short_session`) in a single transaction (`add_ask_turn`).
"""
import logging
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator

from ..agents.orchestrator import AskOrchestrator, ProfileContextStore, terminal_turn
from ..agents.schema import StructuredReading
from ..context.taxonomy import TaxonomyError, get_domain
from ..core.vedic.ask_suggestions import ask_suggestions
from ..db import get_db
from ..db import crud, crud_mobile as cm
from ..db.models import AnswerReport, AskMessage
from ..db.crud_profile_context import build_profile_context_projection
from ..db.database import release_connection, short_session
from .. import ratelimit
from ..entitlements.usage import commit_ask_credit, release_ask_credit, reserve_ask_credit
from ..agents.ask_engine import uses_agent
from .auth import CurrentUser
from .context_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/ask", tags=["ask-ai"])
log = logging.getLogger(__name__)

MAX_HISTORY = 12
MAX_QUESTION_CHARS = 2000
# A client-supplied `history` longer than this is refused outright (422). The
# web app sends its whole in-memory conversation, so anything up to this is
# accepted and trimmed to the last MAX_HISTORY turns — the only ones a model
# ever sees — before each turn is validated.
MAX_HISTORY_ACCEPTED = 200


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    # Deprecated (S15): validated for older clients, never sent to the model.
    history: Optional[list[HistoryTurn]] = None

    @field_validator("history", mode="before")
    @classmethod
    def _bound_history(cls, value):
        if isinstance(value, list):
            if len(value) > MAX_HISTORY_ACCEPTED:
                raise ValueError(f"history is limited to {MAX_HISTORY_ACCEPTED} turns")
            return value[-MAX_HISTORY:]
        return value

    thread_id: Optional[str] = Field(
        None,
        description="Continue a saved thread. Its stored messages are used as "
                    "history and `history` in the body is ignored.",
    )
    start_thread: bool = Field(
        False, description="Create and persist a new thread for this question."
    )
    language: Literal["en", "te"] = "en"
    input_mode: Literal["text", "voice"] = "text"
    tone: Literal["gentle", "direct"] = Field(
        "gentle",
        description="The reader's tone preference (PreferencesService's "
                    "ReadingTone). Gentle cushions hard findings with what "
                    "is steady; direct states them first. Delivery only: "
                    "neither changes a claim or the refer-out boundary.",
    )
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
        "archived_at": (row.archived_at.isoformat() if row.archived_at else None),
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


def _usage_fields(usage: Optional[dict]) -> dict:
    """AskMessage columns for the cost of an assistant turn — see
    migration 20261015120000. Empty (all null) when the turn never reached
    a model, e.g. a refer-out."""
    if not usage or not usage.get("calls"):
        return {}
    return {
        "model": usage.get("model"),
        "latency_ms": usage.get("latency_ms"),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "llm_calls": {
            "provider": usage.get("provider"),
            "calls": int(usage.get("calls") or 0),
            "repaired": bool(usage.get("repaired")),
            "breakdown": list(usage.get("breakdown") or []),
        },
    }


def _persist_ask_turn(db: Session, body: "AskRequest", *, user_id: str, kundli_id: str,
                      thread_id: Optional[str], content: str, domain: Optional[str],
                      refer_out_kind: Optional[str], evidence: Optional[dict],
                      usage: Optional[dict] = None):
    """Write the question and its answer together through a fresh, short
    session; returns the (detached, fully loaded) thread, or None when the
    turn is stateless. Shared with `ask_stream_routes.py` so both surfaces
    persist identically.

    The request session is released first, so no transaction it opened is
    still holding a connection (or, on SQLite, a lock) while this one writes.
    """
    if thread_id is None and not body.start_thread:
        return None
    release_connection(db)
    with short_session(db) as session:
        return cm.add_ask_turn(
            session, thread_id=thread_id, user_id=user_id, kundli_id=kundli_id,
            question=body.question, answer=content,
            user_fields={"language": body.language, "input_mode": body.input_mode},
            assistant_fields={
                "language": body.language, "domain": domain,
                "refer_out_kind": refer_out_kind, "evidence": evidence or {},
                **_usage_fields(usage),
            },
        )


def _settle_credit(db: Session, settle, reservation) -> None:
    """Commit or release an Ask credit after the model call, on a fresh short
    session bound to the request's engine. The reservation carries only row
    ids, so it needs nothing from the (released) request session. Shared
    with `ask_stream_routes.py`."""
    with short_session(db) as session:
        settle(session, reservation)


def _owned_thread(db: Session, thread_id: str, user_id: str):
    thread = cm.get_ask_thread(db, thread_id, user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


@router.get("/threads")
def list_threads(user: CurrentUser,
                 kundli_id: Optional[str] = None,
                 archived: bool = False,
                 limit: int = Query(50, ge=1, le=200),
                 db: Session = Depends(get_db)):
    rows = cm.list_ask_threads(
        db, user.id, kundli_id=kundli_id, limit=limit, archived=archived,
    )
    return {"count": len(rows), "threads": [_thread(r) for r in rows]}


# Reader facts that change how a suggestion is worded (see ask_suggestions.py).
_SUGGESTION_LIFE_KEYS = {
    "relationship_status": "code", "employment_status": "code",
    "has_children": "value", "looking_for_work": "value", "planning_marriage": "value",
}


def _suggestion_life(db: Session, user_id: str, kundli_id: str) -> dict:
    """The reader's own facts, one value per key. A key with two active
    values (an unresolved contradiction) is left out, so the wording falls
    back to the neutral form instead of guessing."""
    projection = build_profile_context_projection(db, user_id=user_id, profile_id=kundli_id)
    life: dict = {}
    for fact in projection.facts:
        field = _SUGGESTION_LIFE_KEYS.get(fact["key"])
        if not field or fact["status"] != "active" or fact["key"] in projection.contradictions:
            continue
        value = (fact.get("value") or {}).get(field)
        if value is not None:
            life[fact["key"]] = value
    return life


@router.get("/{kundli_id}/suggestions")
def suggestions(kundli_id: str, user: CurrentUser,
                mode: Literal["guided", "balanced", "practitioner"] = "balanced",
                db: Session = Depends(get_db)):
    """Questions to offer on Ask home, built from this profile's chart today:
    a short general list and one list per topic chip."""
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")
    chart = _chart_from_kundli(k, *crud.chart_convention(db, user.id))
    return ask_suggestions(chart, mode=mode, life=_suggestion_life(db, user.id, kundli_id))


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


@router.post("/threads/{thread_id}/restore")
def restore_thread(thread_id: str, user: CurrentUser,
                   db: Session = Depends(get_db)):
    if not cm.restore_ask_thread(db, thread_id, user.id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"archived": False}


@router.delete("/threads/{thread_id}")
def delete_thread(thread_id: str, user: CurrentUser,
                  db: Session = Depends(get_db)):
    if not cm.delete_ask_thread(db, thread_id, user.id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"deleted": True}


# ── Report this answer ───────────────────────────────────────────────────────
# Google Play requires apps with AI-generated content to let readers flag an
# answer from inside the app. Declared before /{kundli_id} so "reports" is
# never read as a kundli id. The team hears about each report from the
# notifications worker (notifications/owner_alerts.py) and reads it in /admin.

class AnswerReportRequest(BaseModel):
    reason: Literal["wrong", "harmful", "offensive", "advice", "other"]
    note: Optional[str] = Field(None, max_length=1000)
    # What the reader saw, copied in so the report stays readable after the
    # conversation is deleted.
    answer: str = Field(min_length=1, max_length=20000)
    question: Optional[str] = Field(None, max_length=MAX_QUESTION_CHARS)
    thread_id: Optional[str] = Field(None, max_length=64)
    message_id: Optional[str] = Field(None, max_length=64)
    experience_mode: Optional[Literal["guided", "balanced", "practitioner"]] = None
    language: Optional[Literal["en", "te"]] = None


@router.post("/reports", status_code=201)
def report_answer(body: AnswerReportRequest, user: CurrentUser,
                  db: Session = Depends(get_db)):
    ratelimit.require(user.id, "report")
    # Link the thread and message only when they are the reader's own; a
    # streamed answer the app has not reloaded still carries a local id.
    thread = (cm.get_ask_thread(db, body.thread_id, user.id)
              if body.thread_id and _is_uuid(body.thread_id) else None)
    message_id = None
    if thread and body.message_id:
        message = db.get(AskMessage, body.message_id) if _is_uuid(body.message_id) else None
        if message and message.thread_id == thread.id and message.role == "assistant":
            message_id = message.id
    note = (body.note or "").strip() or None
    report = AnswerReport(
        user_id=user.id, thread_id=thread.id if thread else None, message_id=message_id,
        reason=body.reason, note=note, question=body.question, answer=body.answer,
        experience_mode=body.experience_mode, language=body.language,
    )
    db.add(report)
    db.commit()
    log.info("answer reported: %s (%s)", report.id, body.reason)
    return {"id": report.id, "received": True}


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


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


def _profile_context_store(db: Session, user_id: str, kundli_id: str) -> ProfileContextStore:
    """One profile-scoped `ProfileContextStore` per Ask call, closing over
    exactly one `(db, user_id, kundli_id)` triple — the same isolation
    pattern as `chart_loader`. A single orchestrator instance is bound to
    one profile for its whole lifetime; there is no code path by which a
    profile switch mid-request could redirect this closure at a different
    profile's data. `build_profile_context_projection` does not check
    ownership itself (see its own docstring) — safe here because the route
    already resolved `k = crud.get_kundli(db, kundli_id, user.id)` (a 404 on
    mismatch) before this closure is ever constructed.

    Shared with `ask_stream_routes.py` (imported from here) so both
    surfaces build the profile-context projection identically."""
    def projection(domain: str, as_of_iso: str) -> dict:
        as_of = datetime.fromisoformat(as_of_iso).date() if as_of_iso else None
        return build_profile_context_projection(
            db, user_id=user_id, profile_id=kundli_id, domain=domain, as_of=as_of,
        ).to_dict()
    return ProfileContextStore(projection=projection)


def _evidence_from_reading(
    reading: StructuredReading, *,
    profile_context_revision: int | None = None,
    profile_context_as_of: str | None = None,
) -> dict:
    """Namespaced, versioned bridge shape for `AskMessage.evidence` — this is
    explicitly a temporary storage decision, not the final one. Wrapping it
    (rather than dumping the raw structured object) makes that obvious to
    the next person who reads a row, and keeps `evidence`'s meaning
    comparable across old rows (`{"tools_used": [...]}` etc., from before
    this build) and new ones.

    `profile_context_revision`/`profile_context_as_of` are optional so old
    call sites and old persisted rows are unaffected — present only from
    Phase 2 onward, and only when a `ProfileContextStore` was actually
    wired in. This is the ledger snapshot the answer was generated and
    verified against (`AskOrchestrator.PreparedRun`), frozen at persistence
    time: reopening this thread later must show what the answer was
    actually grounded in, never a value re-read from the ledger's current
    (possibly since-corrected) state.

    Shared with `ask_stream_routes.py` (imported from here) so a thread's
    evidence shape is identical regardless of which endpoint answered a
    given turn."""
    evidence = {
        "schema_version": "ask_structured_v1",
        "structured_reading": reading.model_dump(),
        "references": [item.source for item in reading.technical_basis],
    }
    if profile_context_revision is not None:
        evidence["profile_context_revision"] = profile_context_revision
        evidence["profile_context_as_of"] = profile_context_as_of
    return evidence


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
        # Client `history` is accepted but never replayed: its assistant turns
        # reached the model as its own earlier answers, so a forged one could
        # steer it past the safety gates (audit S15). Both apps now continue
        # a conversation through a server thread.
        turns = []

    messages = turns[-MAX_HISTORY:]
    # a valid conversation must start with a user turn
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": body.question})

    def persist_turn(content: str, domain: Optional[str],
                     refer_out_kind: Optional[str],
                     evidence: Optional[dict],
                     usage: Optional[dict] = None) -> Optional[str]:
        """Nothing is written until a terminal outcome exists — see the
        module docstring. `nonlocal thread` (not a local shadow) so the
        response built after this call sees the thread this turn actually
        used or created, matching every other terminal branch below."""
        nonlocal thread
        saved = _persist_ask_turn(
            db, body, user_id=user.id, kundli_id=kundli_id, thread_id=thread_id,
            content=content, domain=domain, refer_out_kind=refer_out_kind,
            evidence=evidence, usage=usage,
        )
        if saved is None:
            return None
        thread = saved
        return thread.id

    # Read while the request session is still live: after release_connection
    # below, touching `thread` would open a new transaction just to reload it.
    thread_id = thread.id if thread else None
    thread_domain = _thread_established_domain(db, thread.id) if thread else None

    # Read now: the chart may load after the connection is released.
    convention = crud.chart_convention(db, user.id)
    orchestrator = AskOrchestrator(
        chart_loader=lambda: _chart_from_kundli(k, *convention),
        profile_context_store=_profile_context_store(db, user.id, kundli_id),
    )
    try:
        outcome = orchestrator.prepare(
            body.question, thread_domain=thread_domain,
            domain_override=body.domain_override,
            experience_mode=body.experience_mode,
            language=body.language,
            tone=body.tone,
            history=messages,
            explore=uses_agent(user.email),
            # validate_first intentionally not passed through — see docstring.
        )
    except TaxonomyError:
        log.exception("ask prepare failed on taxonomy (kundli=%s)", kundli_id)
        raise HTTPException(status_code=500, detail="Could not prepare this answer")

    if outcome.terminal_envelope is not None:
        envelope = outcome.terminal_envelope
        status = envelope["type"]
        try:
            turn = terminal_turn(envelope)
        except ValueError as e:
            raise HTTPException(status_code=500, detail=str(e))
        answer, refer_out = turn.content, turn.refer_out_kind
        persist_turn(answer, domain=turn.domain, refer_out_kind=refer_out, evidence=turn.evidence)
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
    # Only a real answer attempt holds an Ask credit: every terminal state
    # above (refer-out, clarification, not ready) returned without one. A 402
    # here is the structured limit denial, raised before any model call.
    ratelimit.require(user.id, "ask")  # always on, unlike the plan quota below
    reservation = reserve_ask_credit(db, user.id)

    def persist_prepared(reading: Optional[StructuredReading], status: str) -> Optional[str]:
        if reading is None:
            # A failed generation/verification writes nothing new — only
            # report the thread that already existed, if any. Matches the
            # module docstring's "a failed request persists nothing" and
            # ask_stream_routes.py's identical contract.
            return thread_id
        return persist_turn(reading.interpretation, domain=prepared.domain,
                            refer_out_kind=None,
                            evidence=_evidence_from_reading(
                                reading,
                                profile_context_revision=prepared.profile_context_revision,
                                profile_context_as_of=prepared.profile_context_as_of,
                            ),
                            usage=prepared.usage)

    # Everything the model needs is in `prepared` and `messages`; give the
    # connection back before the 10–90 s generation (see module docstring).
    # The credit was reserved (and committed) above; settling it after the
    # model call goes through a fresh short session like the turn itself.
    release_connection(db)
    done = None
    try:
        for event in orchestrator.run(prepared, messages, persist=persist_prepared):
            if event["type"] == "done":
                done = event
    except BaseException:
        _settle_credit(db, release_ask_credit, reservation)
        raise

    if done is None or done["status"] != "answered":
        # A failed or unverified answer is never charged.
        _settle_credit(db, release_ask_credit, reservation)
        # Explicit, not a generic 500 — the reader gets a clear signal that
        # generation or verification failed, never a reading that shouldn't
        # have shipped. Matches this route's pre-migration contract (a
        # model-call exception was already a 502) and extends it to the new
        # failure mode `verify()`/`verify_coverage()` can produce that
        # VedicQAAgent never had.
        detail = ("AI generation failed"
                  if done is None or done["status"] == "generation_failed"
                  else "The answer did not pass verification")
        raise HTTPException(status_code=502, detail=detail)

    _settle_credit(db, commit_ask_credit, reservation)
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
