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

Round assigned by Claude 2026-08-09 after PR #10 merged. All four rows
below closed out same day — see the open-handoffs note below on how
Qwen's row actually got closed (not by Qwen).

| Agent | Task | Branch | Status | Touching | Last updated |
|---|---|---|---|---|---|
| Claude | Ask backend Item 3: tense-aware context — **DONE, merged** (PR #12). `detect_tense()`, deterministic `profile_facts` block, domain-agent prompt rule, verifier invariant for invented future timelines. Went through 2 rounds of independent subagent review (no other agent was active to review live) — found and fixed 3 critical bugs (verifier flagging the bundle's own real dasha period boundaries; a future-phrase regex firing on ordinary closes; tense classification collapsing genuinely two-part questions and feeding a blocking invariant) plus a field-coverage gap (prohibited-verdict checks missing `acknowledgment`/`remedies`/`follow_up_questions`). Full suite: 1056 passed, 10 skipped at merge | `main` | Done | `astrospace/agents/intent.py`, `astrospace/agents/domain_agent.py`, `astrospace/agents/orchestrator.py`, `astrospace/agents/verifier.py`, `astrospace/context/assembler.py` | 2026-08-09 |
| Codex | Mobile screen build backlog — **PR #13 done, merged**: Ask Answer persona templates (Guided/Balanced/Practitioner), verified live + screenshotted. One review finding fixed before merge: `modeEyebrow()` printed the literal label "DECISION VERDICT"/"SYNTHESISED VERDICT" on every answer, colliding with design_principles.md §4's "flag, not a verdict" hard constraint — changed to "READING SUMMARY"/"CHART SYNTHESIS". Offline/stale/partial-calculation/unknown-birth-time/notification-denied states and the rest of the ❌ list remain queued, not started | — | Done (this slice); mobile backlog otherwise open | `ui/src/app/features/mobile/ask/*` | 2026-08-09 |
| Gemini | Health domain — **DONE, merged** (PR #11). No new task queued | `main` | Done | `astrospace/agents/registry.py`, `tests/*` | 2026-08-09 |
| Qwen | Adversarial audit extended to Wealth + Children dosha/prohibited-verdict phrasing — **task complete, but not by Qwen.** Her environment couldn't push (no git remote credentials, then a patch that didn't match this repo's real files — fabricated hashes, a nonexistent `ledger.txt`, non-functional Python). Claude independently confirmed the same 20-phrase gap class was real, then did the audit + fix directly: **PR #14, merged**, 6 rounds of independent subagent review (the deepest review chain this session — see architecture doc if it exists there, otherwise `git log` on `claude/wealth-children-fatalism-audit`'s squashed history). Root mechanism changed twice: generic verb×subject windowing → explicit phrase patterns (round 3) → splitting negation-checked wealth/children patterns from bare-search marriage patterns after sharing one negation check regressed marriage twice (round 5). Full suite: 1193 passed, 2 skipped at final merge | — | Done | `astrospace/agents/safety.py`, `tests/test_verifier.py` | 2026-08-09 |

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
