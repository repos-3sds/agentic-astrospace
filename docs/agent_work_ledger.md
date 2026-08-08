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

Full task specs for all four: [docs/agent_task_briefs_2026-08-08.md](agent_task_briefs_2026-08-08.md).
This table stays intentionally thin — status only, detail lives in the
brief.

All four briefs approved by Codex 2026-08-08, two refinements folded in
(Gemini: no `taxonomy.json` edits; Codex: added Ask thread UX acceptance
criteria to her own brief). Cleared to begin per her kickoff recommendation.

| Agent | Task | Branch | Status | Touching | Last updated |
|---|---|---|---|---|---|
| Claude | Ask backend Item 1: SSE `fatal_error` contract — **PR #3 open** | `ask-sse-fatal-error` | Backend commit done (`93923ad`); PR now also contains Codex's two commits, see warning below | `astrospace/api/ask_stream_routes.py`, `tests/test_domain_agent.py` | 2026-08-08 |
| Codex | Mobile Ask UI renderer + cross-agent backlog docs + Ask thread UX acceptance criteria | `ask-sse-fatal-error` | Two commits pushed (`d4aa5b0`, `a4e1ba8`) — landed on Claude's branch, see warning below | `ui/src/app/features/mobile/ask/*`, `ui/src/app/core/models.ts`, `docs/mobile_ask_thread_ux_acceptance_2026-08-08.md` | 2026-08-08 |
| Gemini | Golden-chart VERIFY-flag legwork and Wealth domain spec PR | unverified — ledger says `main`, but this working directory has been on `ask-sse-fatal-error` since Claude branched; Gemini should confirm | In progress | `astrospace/core/vedic/*` (docs/tests only), `astrospace/agents/registry.py` | 2026-08-08 |
| Qwen | Adversarial paraphrase audit on `safety.py`'s regex gates | — | Cleared to start | `tests/test_verifier.py` (additive only) | 2026-08-08 |

## Open handoffs / things the next agent in an area should know

- **⚠️ NEW, URGENT (2026-08-08): all four agents share one working
  directory, and `git checkout -b` affects everyone in it, not just whoever
  ran it.** Discovered live today: Claude ran `git checkout -b
  ask-sse-fatal-error` to start Item 1. That switched the branch for the
  *entire shared working directory* — Codex and Gemini's concurrent,
  uncommitted work landed on that branch too, not `main`, regardless of
  what their own ledger rows said. Codex has since pushed two real commits
  (`d4aa5b0`, `a4e1ba8`) onto it; they're now bundled into Claude's PR #3
  along with the unrelated backend fix. Nobody is force-pushing or
  resetting to untangle this without explicit go-ahead from the user and
  whoever else's commits are involved — that's a destructive operation on
  another agent's already-pushed work, not a unilateral call. **Until this
  is resolved: before every commit, run `git branch --show-current` and
  actually check it against what you expect — don't trust the ledger's
  "Branch" column, it can be stale the moment someone else switches
  branches.** AGENTS.md doesn't have a rule for this yet; it needs one
  (something like: coordinate before switching branches, or avoid it
  entirely in favor of committing straight from whatever's checked out) —
  flagging here first since fixing it requires everyone's docs update, not
  changing the rules unilaterally mid-collision.
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
