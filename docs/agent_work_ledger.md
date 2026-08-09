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
| Claude | Ask backend Item 2: fixed the 44 safety.py regex gaps — **PR #10 open**. Root cause was structural (flat literal-phrase lists, same weakness `refer_out_kind()` already fixed once) — added contraction normalization + generalized pattern clusters, not phrase patches. All 44 xfail markers removed, real passes. Caught and fixed one real false-positive before shipping (broadened death pattern was also matching ordinary dasha-period descriptions) — kept as permanent regression tests. Full suite: 1013 passed | `claude/safety-paraphrase-fix` | Awaiting review (own PR, needs a second look before merge per AGENTS.md) | `astrospace/agents/safety.py`, `tests/test_verifier.py` | 2026-08-09 |
| Codex | Mobile Ask richer structured rendering — **DONE, merged** (PR #8). Confidence/context pills, intent/plain-guidance cards, numbered next-steps, remedy rows, technical-basis section, all persona-gated. Claude verified live in-browser (not just build) — asked two real questions end to end, confirmed every section renders correctly and Guided mode genuinely hides context pills + technical basis, not just in the diff | `main` | Done | `ui/src/app/features/mobile/ask/*` | 2026-08-09 |
| Gemini | Children domain — **DONE, merged** (PR #9, no process issues this round — clean diff, no silent taxonomy edit, worktree used correctly). Next up: Health domain, held until PR #10 (safety-regex fix) merges, since Health is the domain most exposed to the `prohibited_verdict()` gaps that fix closes | `main` | Done | `astrospace/agents/registry.py`, `tests/*` | 2026-08-09 |
| Qwen | Adversarial paraphrase audit on `safety.py`'s regex gates — **DONE, merged** (PR #7). Claude independently re-verified all 44 phrases against the real regex before merging, marked each `xfail(strict=True)` so the (real) gap doesn't fail CI, and dropped 2 malformed fragments | `main` | Done. The actual regex fix for the 44 confirmed gaps is Claude's next Ask-hardening item, ahead of anything else in that sequence | `tests/test_verifier.py` (additive, merged) | 2026-08-08 |

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
