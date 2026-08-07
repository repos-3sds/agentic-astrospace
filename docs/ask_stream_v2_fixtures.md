status: draft — coordination handoff, not implemented behavior yet
source of truth: /Users/vikramaditya/.claude/plans/tingly-weaving-emerson.md

# Ask stream v2 — SSE fixture examples

For the UI owner to wire against while the backend orchestrator is built in
parallel. Frame format unchanged: `data: {json}\n\n`, one frame per event.

## status (0 or more, before `done`)

```json
{ "type": "status", "stage": "understanding_intent", "label": "Understanding your question…" }
{ "type": "status", "stage": "routing", "label": "Routing to the right specialist…" }
{ "type": "status", "stage": "gathering_context", "label": "Gathering your D9, dasha, and transits…" }
{ "type": "status", "stage": "interpreting", "label": "Marriage specialist is interpreting…" }
```

## clarification_needed (terminal — no `done` follows)

```json
{
  "type": "clarification_needed",
  "options": ["career", "marriage"]
}
```

## domain_not_ready (terminal — no `done` follows)

```json
{
  "type": "domain_not_ready",
  "domain": "litigation",
  "domain_label": "Litigation & Legal Matters",
  "available": ["career", "marriage"]
}
```

## refer_out (terminal — no `done` follows)

```json
{
  "type": "refer_out",
  "kind": "death",
  "answer": "AstroSpace does not predict death or lifespan, for anyone."
}
```

## done (terminal, success path)

```json
{
  "type": "done",
  "status": "answered",
  "schema_version": "ask_structured_v1",
  "domain": "marriage",
  "intent": "timing",
  "context_used": ["houses", "vargas", "dasha_relevance", "gochara", "references"],
  "evidence_refs": ["uk_4_marriage_7th", "dasha_relevance", "gochara"],
  "reading": {
    "acknowledgment": "You're asking whether the coming period supports marriage timing, not just compatibility in general.",
    "technical_basis": [
      {
        "factor": "7th lord Venus",
        "reading": "Venus sits in the 7th's trine, well placed for partnership matters.",
        "source": "uk_4_marriage_7th"
      },
      {
        "factor": "Jupiter mahadasha",
        "reading": "Currently running, and Jupiter is a marriage karaka — a naturally supportive period for this question.",
        "source": "dasha_relevance"
      }
    ],
    "interpretation": "The current period leans supportive rather than neutral — Jupiter's influence as both a marriage significator and the active dasha lord gives this window real weight, though timing within it depends on which sub-period is active when a specific proposal or match comes up.",
    "summary_and_assurance": "This is a genuinely favourable stretch, not a guarantee of a specific date — the chart shows readiness, not a fixed outcome.",
    "guidance": {
      "practical_actions": ["Keep the next 6-12 months open for serious conversations, not just casual ones."],
      "remedies": [],
      "follow_up_questions": ["Which month in this window is strongest?", "What does my D9 say about my partner's nature?"]
    },
    "confidence": "medium"
  },
  "thread_id": "8f2b1c40-....-....-....-............"
}
```

## verification_failed / generation_failed (terminal, rare)

```json
{
  "type": "done",
  "status": "verification_failed",
  "schema_version": "ask_structured_v1",
  "domain": "marriage",
  "intent": "timing",
  "thread_id": null
}
```

Added during implementation, not in the original coordination draft:
`status` can also be `"generation_failed"` — same shape, distinct meaning.
`verification_failed` = the model answered but the deterministic checks
rejected it twice (invented citation, wrong domain, prohibited/dosha
language); `generation_failed` = the model call itself errored (network,
provider outage, bad API key) before verification ever ran. Render both the
same way: an honest "couldn't produce a grounded answer" bubble, not a
broken card. (No `reading` on either variant. `thread_id` is non-null only
if a thread already existed before this turn — a failed turn never creates
one, matching "nothing persists on failure.")

## Notes for the UI owner

- `refer_out` is now its own event type, not a field folded into `done` —
  don't check `done.refer_out_kind` anymore.
- `domain` on `done` is the real CE taxonomy domain; there's no more
  `"GUIDANCE"`/`"PREVIEW"` placeholder string to branch on.
- Old (pre-migration) threads reopened from history won't have this shape
  in `AskMessage.evidence` — treat missing/unparseable `evidence` as
  "render `content` plainly, no structured card," not an error.
