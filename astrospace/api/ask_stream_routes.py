"""Ask-AI, streamed — the orchestrator path.

Additive alongside `/api/v1/ask/{kundli_id}` (ask_routes.py), which stays
untouched. This endpoint routes a question through the Context Engine's
`KeywordRouter` across the full taxonomy, and for domains with a registered
specialist (`astrospace.agents.domain_agent.DOMAIN_AGENTS`) hands the
already-assembled `ContextBundle` to that specialist and streams its answer
token by token. Domains without a specialist yet fall back to the existing
`VedicQAAgent`, sent as a single chunk — every question gets a real answer,
only registered domains get the streamed, bundle-grounded treatment.

Chart construction and context assembly happen before the StreamingResponse
is created (not inside the generator), so a bad-birth-data error still comes
back as a normal HTTP error instead of a broken stream. Only the actual
token generation and DB writes happen inside the generator.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..agents.domain_agent import DOMAIN_AGENTS
from ..agents.qa_agent import VedicQAAgent
from ..agents.safety import REFER_OUT_ANSWERS, prohibited_verdict, refer_out_kind
from ..context import KeywordRouter, assemble_domain
from ..core.vedic import LocationError
from ..db import crud, crud_mobile as cm, get_db
from .ask_routes import MAX_HISTORY, AskRequest, _history_from_thread, _owned_thread
from .auth import CurrentUser
from .context_routes import _chart_from_kundli

router = APIRouter(prefix="/api/v1/ask", tags=["ask-ai"])

AI_UNAVAILABLE_ANSWER = (
    "Siddha's Ask agents are still being prepared. We have saved your question, "
    "and this space will answer with live chart-grounded guidance once the agents are online."
)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _evidence_from_bundle(bundle: dict) -> list[dict]:
    """Condensed citation list for the client's Why-reading sheet — a few
    references, not the whole bundle (positions/vargas/etc. are provenance
    for the model, not something the reader needs echoed back)."""
    out = [
        {"statement": ref["statement"],
         "source_location": f"{ref['source_text_key']} · {ref['source_location']}"}
        for ref in bundle.get("references", [])[:5]
    ]
    out += [
        {"statement": passage["content"][:280],
         "source_location": passage.get("book") or passage.get("source_key", "")}
        for passage in bundle.get("source_passages", [])[:3]
    ]
    return out


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

    referred_out_as = refer_out_kind(body.question)

    # Resolved before streaming starts: a bad-chart error must come back as a
    # normal HTTPException, not surface mid-stream where the status code can
    # no longer change.
    domain = None
    agent = None
    evidence: list[dict] = []
    streams_tokens = False
    if not referred_out_as:
        decision = KeywordRouter().route(body.question)
        domain = decision.primary
        if domain in DOMAIN_AGENTS:
            try:
                chart = _chart_from_kundli(k, "lahiri", "mean")
            except (ValueError, OverflowError) as e:
                raise HTTPException(status_code=422, detail=f"Invalid birth details: {e}")
            bundle = assemble_domain(chart, domain, question=body.question)
            evidence = _evidence_from_bundle(bundle)
            agent = DOMAIN_AGENTS[domain](bundle)
            streams_tokens = True
        else:
            try:
                agent = VedicQAAgent(k)
            except LocationError as e:
                raise HTTPException(status_code=422, detail=str(e))
            except (ValueError, OverflowError) as e:
                raise HTTPException(status_code=422, detail=f"Invalid birth details: {e}")

    def generate():
        # `final_domain` is the CE taxonomy domain the question was routed to
        # (career, health, marriage, ...) or None if routing never ran.
        # `final_refer_out_kind` is the *safety* category (death/health/
        # legal/money) — kept separate because "health" is a legitimate value
        # for both and a client redirecting to the refer-out screen must not
        # confuse an ordinary health-domain answer with a refused one.
        tools_used: list[str] = []
        if referred_out_as:
            answer = REFER_OUT_ANSWERS[referred_out_as]
            yield _sse({"delta": answer})
            final_domain, final_refer_out_kind, final_evidence = None, referred_out_as, []
        elif streams_tokens:
            buffer = []
            crossed = None
            generation_error = None
            try:
                for delta in agent.run_messages_stream(messages):
                    buffer.append(delta)
                    crossed = prohibited_verdict("".join(buffer))
                    if crossed:
                        break
                    yield _sse({"delta": delta})
            except Exception as exc:
                generation_error = exc
            if crossed:
                # Second-layer net tripped mid-stream — the client discards
                # whatever partial text it has rendered and shows this instead.
                answer = REFER_OUT_ANSWERS[crossed]
                yield _sse({"reset": True, "delta": answer})
                final_domain, final_refer_out_kind, final_evidence = domain, crossed, []
            elif generation_error:
                answer = AI_UNAVAILABLE_ANSWER
                yield _sse({"reset": bool(buffer), "delta": answer})
                final_domain, final_refer_out_kind, final_evidence = domain, None, []
            else:
                answer = "".join(buffer)
                final_domain, final_refer_out_kind, final_evidence = domain, None, evidence
        else:
            try:
                answer, tools_used = agent.run_messages(messages)
            except Exception:
                answer, tools_used = AI_UNAVAILABLE_ANSWER, []
            crossed = prohibited_verdict(answer)
            if crossed:
                answer = REFER_OUT_ANSWERS[crossed]
            yield _sse({"delta": answer})
            final_domain, final_refer_out_kind, final_evidence = domain, crossed, []

        # DB persistence keeps ask_routes.py's existing convention: `domain`
        # is the refer_out_kind itself for a refused answer, the CE domain
        # otherwise — analytics on AskMessage.domain stays comparable across
        # both endpoints.
        stored_domain = final_refer_out_kind or final_domain
        stored_evidence = (
            {"safety_policy": "excluded_verdict"} if final_refer_out_kind
            else {"references": final_evidence} if streams_tokens
            else {"tools_used": sorted(set(tools_used))}
        )

        # Nothing is written until here, once there is a final answer — same
        # rule ask_routes.py follows, so a failed/interrupted stream persists
        # nothing and stays safe to retry.
        local_thread = thread
        if local_thread is None and body.start_thread:
            local_thread = cm.create_ask_thread(db, user.id, kundli_id)
        if local_thread is not None:
            cm.add_ask_message(db, local_thread.id, "user", body.question,
                               language=body.language, input_mode=body.input_mode)
            cm.add_ask_message(db, local_thread.id, "assistant", answer,
                               language=body.language, domain=stored_domain,
                               refer_out_kind=final_refer_out_kind,
                               evidence=stored_evidence)
            db.refresh(local_thread)

        yield _sse({
            "done": True,
            "thread_id": local_thread.id if local_thread else None,
            "domain": final_domain,
            "refer_out_kind": final_refer_out_kind,
            "evidence": final_evidence,
        })

    return StreamingResponse(generate(), media_type="text/event-stream")
