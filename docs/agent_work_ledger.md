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

Full task specs for the current round: [docs/agent_task_briefs_2026-08-09.md](agent_task_briefs_2026-08-09.md)
(supersedes [the 2026-08-08 briefs](agent_task_briefs_2026-08-08.md) for the
rows below — that doc's Claude/Codex/Gemini/Qwen sections are all now
closed out). This table stays intentionally thin — status only, detail
lives in the brief.

Assigned by Claude 2026-08-09 after PR #10 merged; not yet reviewed/
confirmed by the other three the way the 2026-08-08 round was by Codex —
treat as proposed until each agent claims their row.

| Agent | Task | Branch | Status | Touching | Last updated |
|---|---|---|---|---|---|
| Claude | Ask backend Item 3: tense-aware context (intent tense classification, deterministic profile-facts block, agent prompt updates, verifier invariant) — full spec in the architecture doc's 2026-08-09 update. Not yet started | — | Queued, next up | `astrospace/agents/intent.py`, `astrospace/context/assembler.py`, `astrospace/agents/verifier.py` | 2026-08-09 |
| Codex | Mobile screen build backlog — per-mode Ask Answer templates first, then offline/stale/partial-calculation states, then the rest of the ❌ list in `mobile_screen_build_plan.md`. | `codex-mobile-screen-build` | Claimed, in progress — starting with Ask Answer Figma nodes `212:971`/`212:1019`/`212:1077`; will screenshot 375×812 before PR | `ui/src/app/features/mobile/**`; screenshot evidence/docs if needed | 2026-08-09 |
| Gemini | Health domain (continuing the greenlit work) — same pattern as Wealth/Children, with an explicit refer-out-boundary requirement in `_HEALTH_ADDENDUM` and tense-varied test questions per the new brief. Not yet started | — | Proposed, awaiting claim | `astrospace/agents/registry.py`, `tests/*` | 2026-08-09 |
| Qwen | Adversarial audit extended to Wealth + Children dosha/prohibited-verdict phrasing (Health once Gemini's PR merges) — direct continuation of PR #7's method, new domain-specific paraphrases. Not yet started | — | Proposed, awaiting claim | `tests/test_verifier.py` (additive) | 2026-08-09 |

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
