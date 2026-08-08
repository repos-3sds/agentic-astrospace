# Agent work ledger

Status: living state, not a spec. Changes daily/hourly. The rules that
govern *how* to use this file live in [AGENTS.md](../AGENTS.md) — this file
only records current reality: who's doing what, on what branch, touching
what. Stale rows (no update in a while, work clearly finished/abandoned)
should be pruned, not archived — this isn't a history log, `git log` is.

## How to use this

- **Starting work?** Add or update your row before you start, per AGENTS.md
  Rule 1 — especially the "touching" column if it reaches outside your own
  owned area.
- **Stopping mid-task?** Update status/notes before you stop, per Rule 2 and
  Rule 6 — don't leave a row saying "in progress" for work that's actually
  finished or abandoned.
- **About to touch a file outside your own area?** Check this table first
  for whether someone else's row already claims it.

## Current assignments

| Agent | Task | Branch | Status | Touching | Last updated |
|---|---|---|---|---|---|
| Claude | Ask backend hardening sequence (SSE error contract → verifier strengthening → intent-aware context planner → routing/synthesis split → section-targeted repair) — see [architecture doc's Update section](ask_context_engine_multi_agent_architecture_2026-08-07.md#update-2026-08-08-design-review-after-the-first-two-agents-shipped) | not started | Queued — Claude owner, not started | `astrospace/agents/orchestrator.py`, `astrospace/agents/verifier.py`, `astrospace/api/ask_stream_routes.py` | 2026-08-08 |
| Codex | Mobile Ask UI renderer, cross-agent backlog/acceptance criteria | — | Not yet started | `ui/src/app/features/mobile/ask/*` | 2026-08-08 |
| Gemini | Golden chart validation + Wealth domain spec (data/spec first, not orchestrator code) | — | Not yet assigned in detail | `astrospace/context/taxonomy.json` (new `wealth` spec), no code yet | 2026-08-08 |
| Qwen | Test gap audit + additive tests | — | Not yet started | `tests/*` only | 2026-08-08 |

## Open handoffs / things the next agent in an area should know

- **`astrospace/admin/client.py`** (Codex-owned per AGENTS.md): had a live
  uncommitted-edit collision with Claude's session on 2026-08-08 — already
  resolved (Codex committed the fix, `986963a`), but worth knowing this file
  had a rocky day before touching it again.
- **Ask backend hardening sequence** (Claude-owned): the six-item priority
  list in the architecture doc's Update section is meant to run in order —
  item 3 (verifier) depends on item 4's context-trimming work not shipping
  first, per the dependency note already written there. Don't parallelize
  those items across agents; they're sequential by design.
- **PR #1** (Qwen, merged 2026-08-08): added `CONTEXT_ENGINE_MULTI_AGENT_AUDIT_2026-08-08.md`
  at repo root and rewrote `.gitignore`. The gitignore rewrite dropped three
  exclusions without noticing why they existed; Claude restored them same
  day (`9be8011`). If Qwen's next task touches `.gitignore` again, read the
  restored comments first.
- **`AGENTS.md` is now live (merged via PR #2, 2026-08-08, reviewed and
  approved by Codex).** It's the real operating protocol as of now, not a
  draft — everyone (including Gemini and Qwen, before either gets a first
  task) reads it, claims work here before starting, and treats config/
  registry/infra edits and non-trivial feature work as PR+review by default.
  The one correction from review worth flagging specifically: a new
  `AGENT_REGISTRY` entry is *not* low-risk — it's a production trust
  boundary and needs owner review plus the career/marriage-level test bar,
  not a quick append.
