from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Literal

from ..db import get_db
from ..db import crud
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


@router.post("/{kundli_id}")
def ask(kundli_id: str, body: AskRequest, user: CurrentUser, db: Session = Depends(get_db)):
    k = crud.get_kundli(db, kundli_id, user.id)
    if not k:
        raise HTTPException(status_code=404, detail="Kundli not found")

    try:
        agent = VedicQAAgent(k)
    except LocationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, OverflowError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid birth details: {e}")

    messages = [
        {"role": t.role, "content": t.content}
        for t in (body.history or [])[-MAX_HISTORY:]
    ]
    # a valid conversation must start with a user turn
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    messages.append({"role": "user", "content": body.question})

    try:
        answer, tools_used = agent.run_messages(messages)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}")

    return {
        "answer": answer,
        "tools_used": sorted(set(tools_used)),
        "kundli_id": kundli_id,
    }
