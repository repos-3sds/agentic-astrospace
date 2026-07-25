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
        "thread_id": thread.id if thread else None,
        "thread": _thread(thread) if thread else None,
    }
