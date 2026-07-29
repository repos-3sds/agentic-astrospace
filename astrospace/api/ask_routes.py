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
from time import perf_counter
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Literal

from ..db import get_db
from ..db import crud, crud_mobile as cm
from ..core.vedic import LocationError
from ..agents.qa_agent import VedicQAAgent
from .auth import CurrentUser

router = APIRouter(prefix="/api/v1/ask", tags=["ask-ai"])

MAX_HISTORY = 12
MAX_QUESTION_CHARS = 2000
# Refer-out matching is deliberately two-part: a prohibited SUBJECT plus a
# VERDICT-SEEKING frame. Matching whole phrasings — the previous approach — let
# 24 of 31 probe questions through, because an allowlist of sentences cannot
# cover paraphrase. "when will i die" was caught; "how many years do i have
# left" was not.
#
# The two-part rule is also what keeps ordinary questions answerable. The app's
# own suggested prompt is "Is this month good for a big purchase?" — money
# subject, timing frame, no verdict sought — and the refer-out screen explicitly
# offers timing for decisions already made. Subject alone must never gate.

_VERDICT_FRAMES = (
    r"\bwill\b", r"\bwhen will\b", r"\bhow long\b", r"\bhow many\b",
    r"\bwhat is my\b", r"\bwhat are my\b", r"\bdo i have\b", r"\bam i\b",
    r"\bshould i\b", r"\bcan i\b", r"\bis it going to\b", r"\bgoing to\b",
    r"\bpredict\b", r"\btell me\b", r"\bcalculate\b", r"\bchances? of\b",
    r"\blikelihood\b", r"\bwhat will\b", r"\bwhen do i\b", r"\bhave left\b",
    r"\bdiagnos", r"\bwhat does .{0,20}mean for my\b",
)

# Subjects the app must never issue a verdict on. Kept as word-stems so
# inflections ("survive"/"survival") are covered without listing each form.
_REFER_OUT_SUBJECTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("death", (
        r"\bdie\b", r"\bdeath\b", r"\bdying\b", r"\bdead\b",
        r"\blifespan\b", r"\blongevity\b", r"\blife expectancy\b",
        r"\bsurviv", r"\bpass away\b", r"\byears (?:do i|i) have\b",
        r"\bhow long .{0,20}\blive\b", r"\bkill", r"\bfatal\b", r"\bterminal\b",
        # Devanagari and Telugu death terms. NOT a substitute for review by a
        # fluent speaker — see docs; these cover the literal words only.
        r"मृत्यु", r"मौत", r"मरण", r"మరణ", r"చనిపో",
    )),
    ("health", (
        r"\bdiagnos", r"\bmedical advice\b", r"\btreatment plan\b",
        r"\bdisease\b", r"\bcancer\b", r"\bchemo", r"\btumou?r\b",
        r"\billness\b", r"\bsick\b", r"\bsymptom", r"\bmedicine\b",
        r"\bmedication\b", r"\binsulin\b", r"\bdose\b", r"\bdosage\b",
        r"\bsurgery\b", r"\boperation\b", r"\brecover\b", r"\brecovery\b",
        r"\bcure\b", r"\bcured\b", r"\bpregnan", r"\bmiscarriage\b",
        r"\bdepress", r"\bsuicid", r"\bmental (?:health|illness)\b",
        r"बीमारी", r"అనారోగ్య", r"వ్యాధి",
    )),
    ("legal", (
        r"\blegal advice\b", r"\bsue\b", r"\blawsuit\b", r"\bcourt\b",
        r"\bjudge\b", r"\bjury\b", r"\bverdict\b", r"\bprison\b",
        r"\bjail\b", r"\bconvict", r"\bacquit", r"\bguilty\b",
        r"\bcase\b.{0,20}\b(?:win|lose|outcome)\b", r"\bbail\b",
        r"\bcustody\b", r"\bdivorce settlement\b", r"\bvisa\b.{0,16}\b(?:approved|rejected)\b",
    )),
    ("money", (
        # Directive-seeking only. "Is this month good to buy property" is a
        # timing question and stays answerable — see the note above.
        r"\b(?:stock|share|crypto|coin|mutual fund|bitcoin)\b",
        r"\bshould i (?:buy|sell|invest|trade)\b",
        r"\bwhich .{0,16}\b(?:invest|fund|stock)\b",
        r"\bmarket\b.{0,24}\b(?:rise|fall|crash|go up|go down)\b",
        r"\bguaranteed (?:return|profit)\b", r"\brisk[- ]free\b",
        r"\bwill i (?:become|be) rich\b", r"\bhow much money will\b",
    )),
)

_REFER_OUT_ANSWERS = {
    "death": "AstroSpace does not predict death or lifespan, for anyone.",
    "health": "AstroSpace cannot diagnose illness, predict medical outcomes, or recommend treatment. Please consult a qualified medical professional.",
    "legal": "AstroSpace cannot predict legal outcomes or provide legal advice. Please consult a qualified legal professional.",
    "money": "AstroSpace cannot recommend investments or predict markets. Please consult a qualified financial professional.",
}


def _refer_out_kind(question: str) -> str | None:
    """Return a structured safety boundary before any model is invoked.

    A question is referred out when it names a prohibited SUBJECT *and* seeks a
    VERDICT about it. Both halves are required: "is this month good for a big
    purchase?" names money but asks about timing, and the product explicitly
    answers that. "which stock should i buy?" seeks a directive and does not.

    Death is the exception — it is gated on subject alone. There is no framing
    in which the app answers a question about when someone dies, so requiring a
    verdict frame would only create a gap to phrase around.
    """
    normalized = " ".join(question.casefold().split())
    seeks_verdict = any(re.search(f, normalized) for f in _VERDICT_FRAMES)
    for kind, subjects in _REFER_OUT_SUBJECTS:
        if not any(re.search(pattern, normalized) for pattern in subjects):
            continue
        if kind == "death" or seeks_verdict:
            return kind
    return None


# Output-side net. The input gate cannot catch every phrasing in every language,
# and nothing previously checked what the model actually said — so a longevity
# verdict produced anyway would have been returned verbatim. This is the second
# layer, and it is why the input rules can stay conservative about false
# positives: the boundary does not rest on them alone.
_PROHIBITED_OUTPUT = (
    (r"\byou (?:will|are going to) die\b", "death"),
    (r"\byour (?:death|lifespan|life expectancy)\b", "death"),
    (r"\byou (?:will|are likely to) live (?:until|to|for)\b", "death"),
    (r"\byou have\b.{0,24}\b(?:years|months) (?:left|to live)\b", "death"),
    (r"\byou (?:have|are suffering from)\b.{0,24}\b(?:cancer|disease|tumou?r)\b", "health"),
    (r"\b(?:stop|start|change) (?:taking )?your (?:medication|medicine|insulin)\b", "health"),
    (r"\byou will (?:win|lose) (?:the|your) (?:case|lawsuit|appeal)\b", "legal"),
    (r"\byou (?:will|should) (?:buy|sell|invest in)\b.{0,24}\b(?:stock|share|crypto)\b", "money"),
)


def _prohibited_verdict(answer: str) -> str | None:
    """Which boundary an answer crosses, if any. None means it is clean."""
    normalized = " ".join(answer.casefold().split())
    for pattern, kind in _PROHIBITED_OUTPUT:
        if re.search(pattern, normalized):
            return kind
    return None


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


@router.post("/{kundli_id}")
def ask(kundli_id: str, body: AskRequest, user: CurrentUser,
        db: Session = Depends(get_db)):
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

    refer_out_kind = _refer_out_kind(body.question)
    if refer_out_kind:
        answer = _REFER_OUT_ANSWERS[refer_out_kind]
        if thread is None and body.start_thread:
            thread = cm.create_ask_thread(db, user.id, kundli_id)
        if thread is not None:
            cm.add_ask_message(
                db, thread.id, "user", body.question,
                language=body.language, input_mode=body.input_mode,
                domain=refer_out_kind,
            )
            cm.add_ask_message(
                db, thread.id, "assistant", answer,
                language=body.language,
                domain=refer_out_kind,
                refer_out_kind=refer_out_kind,
                evidence={"safety_policy": "excluded_verdict"},
            )
            db.refresh(thread)
        return {
            "answer": answer,
            "tools_used": [],
            "kundli_id": kundli_id,
            "refer_out_kind": refer_out_kind,
            "thread_id": thread.id if thread else None,
            "thread": _thread(thread) if thread else None,
        }

    try:
        agent = VedicQAAgent(k)
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, OverflowError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid birth details: {e}")

    messages = turns[-MAX_HISTORY:]
    # a valid conversation must start with a user turn
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": body.question})

    started = perf_counter()
    try:
        answer, tools_used = agent.run_messages(messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")
    latency_ms = int((perf_counter() - started) * 1000)

    # Second layer. The input gate runs before the model; this runs after it,
    # because a prompt instruction is probabilistic and nothing previously
    # checked what was actually said. If the model produced a prohibited
    # verdict anyway, it is replaced by the refer-out — the reader gets the
    # boundary rather than the verdict, and the turn is recorded as a refer-out
    # so the rate is visible instead of silent.
    crossed = _prohibited_verdict(answer)
    if crossed:
        answer = _REFER_OUT_ANSWERS[crossed]

    # Nothing is written until here — see the module docstring.
    if thread is None and body.start_thread:
        thread = cm.create_ask_thread(db, user.id, kundli_id)
    if thread is not None:
        cm.add_ask_message(db, thread.id, "user", body.question,
                           language=body.language, input_mode=body.input_mode)
        cm.add_ask_message(db, thread.id, "assistant", answer,
                           language=body.language, model=agent.model,
                           latency_ms=latency_ms,
                           evidence={"tools_used": sorted(set(tools_used))})
        db.refresh(thread)

    return {
        "answer": answer,
        "tools_used": sorted(set(tools_used)),
        "kundli_id": kundli_id,
        "refer_out_kind": crossed,
        "thread_id": thread.id if thread else None,
        "thread": _thread(thread) if thread else None,
    }
