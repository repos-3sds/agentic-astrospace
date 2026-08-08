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
| Claude | Ask backend Item 1: SSE `fatal_error` contract — **DONE, merged** (PR #3, reviewed by Codex, no blocking findings) | `main` | Done. Next: verifier strengthening (Item 2 of the hardening sequence) | `astrospace/api/ask_stream_routes.py`, `tests/test_domain_agent.py` | 2026-08-08 |
| Codex | Mobile Ask UI renderer + cross-agent backlog docs + Ask thread UX acceptance criteria — PR #4 open, content confirmed intact, diff now clean against `main` | `codex-ask-ui` | Awaiting Codex's own confirmation the frontend actually consumes the now-live `fatal_error` event before merging #4 | `ui/src/app/features/mobile/ask/*`, `ui/src/app/core/models.ts`, `docs/mobile_ask_thread_ux_acceptance_2026-08-08.md` | 2026-08-08 |
| Gemini | Golden-chart VERIFY-flag legwork done (2 docs on `main`); Wealth domain — **DONE, merged** (PR #6, reviewed and 960-test suite independently re-verified by Claude). One process note from review: bundled a `taxonomy.json` keyword edit into the PR instead of flagging it separately per the brief — content was correct and load-bearing for the tests, so it went in, but worth reading the PR #6 comment before the next domain (next up per Phase 6: Children or Health) | `main` | Done. Wealth is now a live, answerable domain — `AGENT_REGISTRY` has career/marriage/wealth | `astrospace/agents/registry.py`, `astrospace/context/taxonomy.json`, tests | 2026-08-08 |
| Qwen | Adversarial paraphrase audit on `safety.py`'s regex gates — **DONE**, 52 findings documented | `qwen-paraphrase-audit` (own environment, not this shared directory) | Tests-only, awaiting a PR; the actual regex fix for the 52 confirmed gaps is separate follow-up work, owner review required | `tests/test_verifier.py` (additive only) | 2026-08-08 |

## Open handoffs / things the next agent in an area should know

- **`AGENTS.md` Rule 3b (branch switches in the shared working directory)
  is confirmed and live** — merged via PR #5, 2026-08-08. Full incident
  history that produced it isn't repeated here anymore (it's fully
  resolved, and it's in `git log`/the merged PRs if anyone needs it) — the
  rule itself is what matters going forward: use `git worktree add <path>
  <branch>` instead of `git checkout`/`git checkout -b` in this directory.
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
