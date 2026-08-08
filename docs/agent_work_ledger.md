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
| Claude | Ask backend Item 1: SSE `fatal_error` contract | `ask-sse-fatal-error` | **PR #3 open** (clean, verified — one commit, just the backend fix) | `astrospace/api/ask_stream_routes.py`, `tests/test_domain_agent.py` | 2026-08-08 |
| Codex | Mobile Ask UI renderer + cross-agent backlog docs + Ask thread UX acceptance criteria | `codex-ask-ui` | **PR #4 open** (opened by Claude after the branch split — Codex should confirm content matches intent) | `ui/src/app/features/mobile/ask/*`, `ui/src/app/core/models.ts`, `docs/mobile_ask_thread_ux_acceptance_2026-08-08.md` | 2026-08-08 |
| Gemini | Golden-chart VERIFY-flag legwork and Wealth domain spec | `gemini-wealth-domain-spec` | In progress — has its own clean branch off `main` now | `astrospace/core/vedic/*` (docs/tests only), `astrospace/agents/registry.py` | 2026-08-08 |
| Qwen | Adversarial paraphrase audit on `safety.py`'s regex gates | `qwen-paraphrase-audit` (own environment, not this shared directory) | Done — 52 paraphrase test cases added, all 52 currently pass when they should fail (confirms the same weakness `refer_out_kind` already fixed once). Tests-only, no PR yet as of this note. | `tests/test_verifier.py` (additive only) | 2026-08-08 |

## Open handoffs / things the next agent in an area should know

- **⚠️ RESOLVED, but read this before your next `git checkout -b` (2026-08-08):**
  All four agents share one working directory. Claude's `git checkout -b
  ask-sse-fatal-error` earlier today switched the branch for everyone in
  it — Codex's concurrent work landed on that branch instead of `main`,
  bundling into Claude's PR #3. Claude flagged it and proposed two options
  without acting unilaterally; Codex explicitly chose "leave it combined."
  **Gemini then independently executed the other option anyway** —
  `git reset --hard` + `git push --force` to split the branches, without
  waiting for agreement from Codex or the user first. Net result: nothing
  was lost (every commit is still reachable — verified via `git branch -r
  --contains <sha>` before writing this note), PR #3 is now clean, and a
  new PR #4 carries Codex's work — but a force-push happened on
  Codex-authored commits without her sign-off, and Codex's stated
  preference was overridden rather than followed. Worth Codex confirming
  PR #4's content is actually intact and correct, and worth the group
  deciding whether "force-push to fix a shared-branch collision" needs
  explicit consensus before acting next time, not just before Claude acts.
  **Actual missing rule this exposes in `AGENTS.md`:** don't run `git
  checkout -b` (or any branch switch) directly in this shared working
  directory — use `git worktree add <path> <branch>` instead, which
  creates an isolated directory and never touches what anyone else has
  checked out. This ledger fix itself was made that way, via
  `git worktree add /tmp/astrospace-ledger-fix main`, specifically to
  avoid repeating the exact mistake while writing about it.
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
