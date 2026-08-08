# Agent task briefs — 2026-08-08

Status: point-in-time task specs, written for all four agents currently on
this repo (Claude, Codex, Gemini, Qwen) so each has something as concrete as
the career/marriage build already got, not a one-line ledger placeholder.
Governed by [AGENTS.md](../AGENTS.md) — read that first if you haven't;
these briefs assume its rules (claim in the ledger before starting, PR+
review for anything outside your own area or touching config/registry/
infra). When a brief is done, prune its row in
[docs/agent_work_ledger.md](agent_work_ledger.md) the way finished work
already gets pruned there — this doc can go stale in place; don't rewrite
it to look permanently current. Write a new dated one when the next round
of assignments looks meaningfully different, per this repo's own convention
against endless-audit-document sprawl.

## Claude — Ask backend hardening sequence

**Already fully specified** in
[the architecture doc's Update section](ask_context_engine_multi_agent_architecture_2026-08-07.md#update-2026-08-08-design-review-after-the-first-two-agents-shipped) —
not re-deriving it here, just pointing at it: the six-item sequence (SSE
`fatal_error` contract → verifier strengthening incl. the paraphrase-
evasion audit and confidence/remedy checks → intent-aware `assemble_domain`
→ routing-vs-synthesis resolution → section-targeted repair → node
contracts) runs in that order, sequentially, single-owner — it's not
parallelizable across agents by design (item 3 depends on item 4's
dependency note already written there).

**One cross-agent dependency worth flagging now:** once the SSE
`fatal_error` event type exists (item 1), the mobile frontend needs a
consumer for it. That's Codex's side — see her brief below. I'll ping the
ledger when item 1 ships so it's not a surprise.

**Status:** queued, not yet started (see ledger).

## Codex — mobile Ask UI + cross-agent backlog

Written from my side with less firsthand visibility into the mobile
codebase's exact current state than you have — treat this as a starting
proposal to refine, not a spec to execute blindly.

**Acceptance criteria source:** Codex added
[mobile Ask thread UX acceptance criteria](mobile_ask_thread_ux_acceptance_2026-08-08.md)
as the working bar for Ask History, follow-ups, old-thread reopening,
streaming terminal states, copy/edit/archive controls, and future
multi-domain rendering.

**What I can confirm is already built** (checked `ask-answer.component.html`
directly this session): `reading.acknowledgment`, `.interpretation`,
`.summary_and_assurance`, `.guidance.practical_actions`, and
`.guidance.remedies` all render as distinct elements; the old regex-based
markdown-section parser is deleted, not kept as fallback; live status
events ("Career & Profession specialist is interpreting…") render mid-
stream and were verified working in-browser.

**Gaps named in the architecture doc that map to frontend work:**

1. **SSE `fatal_error` handling** — once Claude ships the backend event type
   (Item 1 of the Claude brief above), `askService.stream()` and
   `ask-answer.component.ts`'s event-handling loop need a case for it —
   right now a mid-stream failure just hangs the UI with no terminal state.
   Blocked on that backend work landing first; worth scaffolding the
   frontend handling in parallel so it's a fast wire-up once the event
   exists, not a blocked wait.
2. **Multi-domain synthesis badge**, once Item 4 (routing/synthesis) and the
   schema you and I settled (`domain` stays a string, `domains`/
   `primary_domain`/`answer_type` added to `evidence`) actually ship —
   `ANSWER · CAREER + MARRIAGE` instead of a single domain. Not urgent;
   synthesis itself hasn't shipped yet, but worth knowing it's coming so
   the eyebrow-label component (`ask-answer.component.html:37`, the exact
   line that had the `streamDomain()` fallback bug fixed earlier today)
   doesn't need a second pass later.
3. **Richer structured rendering** — persona-differentiated payloads,
   `next_paths.app_links` as clickable in-app routes, distinct per-section
   cards rather than one flowing bubble. This is genuinely unscoped product
   work, not a bug — your call on priority and shape, not mine to dictate.
4. **Cross-agent backlog/acceptance criteria docs** — per the ownership
   table in `AGENTS.md`, this is explicitly your area. I don't have a
   specific ask here beyond: if you want a template, `docs/agent_a_backend_contracts_2026-08-06.md`
   is the existing precedent in this repo for a per-slice delivery log
   written for another agent to consume without re-reading the diff.
5. **Ask thread UX acceptance criteria** (added per Codex's review,
   2026-08-08). Define and validate the proper chat experience explicitly,
   not just fix bugs as they're found: reopening an old thread must not
   re-stream it, a follow-up appends to the same thread rather than
   starting a new one, history shows saved questions correctly, and
   stop/copy/edit/delete/archive behavior is all covered. Some of this may
   already be fixed from earlier sessions — the point of this task is
   writing down the acceptance bar and checking the current app against it,
   not assuming past fixes are still holding.

**Status:** not yet started (see ledger).

## Gemini — golden-chart validation legwork + Wealth domain spec

Two independent pieces. Start with the first — it's fully self-contained,
produces real value even though it's blocked on the user for full closure,
and needs zero orchestrator/registry code, so it's the lowest-risk possible
first task to build a track record on.

### Part 1: Golden-chart validation legwork

**The actual blocker, stated plainly:** `tests/test_vedic.py`'s own
docstring says it — "Reference-chart golden tests will be added once the
user provides a verified chart." `plan.md`'s "Phase 1 Validation" section
(marked "do not delete... that obligation outlives the plan around it")
says the same. **You cannot fully close this without the user supplying a
real reference chart with known-correct expected outputs** — don't attempt
to fabricate or guess one.

**What you *can* do independently, real and valuable:** the engine has
~15 explicitly `VERIFY`-flagged conventions, none cross-checked against a
citable source yet. Grep confirms the full list:

```
astrospace/core/vedic/vargas.py       — D6, D8, D16 varga formulas (JHora/Maitreya conventions)
astrospace/core/vedic/constants.py    — sign boundary tables, yogakaraka lists, numerology tables
astrospace/core/vedic/avkahada.py     — sub-nadi per pada convention
astrospace/core/vedic/moontimes.py    — tithi/nakshatra/yoga/karana boundary tables (checked against DrikPanchang)
astrospace/core/vedic/kala.py         — durmuhurta, choghadiya, varjya/amrit ghati tables
astrospace/core/vedic/ghatak.py       — flagged "VERIFY all on reference chart" explicitly
astrospace/core/vedic/favourable.py   — numerology + house-lordship VERIFY notes
astrospace/context/taxonomy.json:68   — "D6 varga rule is VERIFY-flagged in the engine"
```

For each: either (a) confirm it against a citable published source —
Brihat Parashara Hora Shastra, a documented DrikPanchang methodology note,
or another named, commonly-used software convention — and turn the
confirmation into a real test in `tests/test_vedic.py`'s existing "Real-sky
invariants" style (public, checkable facts, not a personal chart — that
layer already exists for exactly this pattern), or (b) if it genuinely
can't be resolved without a personal reference chart, leave the `VERIFY`
flag in place but write down *exactly* what input/output pair would resolve
it, so that when the user eventually supplies a chart, closing these
becomes a mechanical exercise instead of a research project. Either
outcome is real progress; don't force a citation that isn't solid.

**Deliverable:** a short doc (`docs/vedic_engine_verify_audit_2026-08-08.md`
or similar — self-declare its status per this repo's doc convention) plus
any new tests. New tests are additive to `tests/test_vedic.py`, fine as a
normal PR. **Do not modify the VERIFY comments' underlying formulas** —
that's changing production astrology math, which needs the actual owner
(whoever's closest to `core/vedic/`) to review regardless of citation
confidence, same principle as the registry correction below.

### Part 2: Wealth domain spec

Follows the career/marriage pattern exactly — read
`astrospace/agents/registry.py` in full first, it's short (54 lines) and
both existing entries are the template.

**Good news: the taxonomy entry already exists**, fully specified, unchanged
— `astrospace/context/taxonomy.json`, `domains.wealth` (D2 primary/D4
supporting vargas, houses 2/11 primary, karakas Jupiter/Venus/Mercury/Moon,
`dhana_yoga`/`chandra_mangal_yoga`/`kemadruma_yoga`, source refs BPHS/
Uttara Kalamrita/Saravali/Raman). Nothing to design there — just wire it
in.

**Do not edit `taxonomy.json` for this task** (per Codex's review,
2026-08-08). Inspect the existing entry, validate it against your sources
while writing the addendum, but the entry itself is out of scope here. If
you find an actual documented defect in it, call that out as its own
separate, explicitly-flagged finding — not a silent edit bundled into the
Wealth PR.

**What's missing:**

1. A `_WEALTH_ADDENDUM` string in `registry.py`, same shape as
   `_CAREER_ADDENDUM`/`_MARRIAGE_ADDENDUM` — domain-specific framing rules
   for the model. Needs to explicitly reinforce a boundary that already
   exists one layer up: `safety.py`'s `refer_out_kind()` already blocks
   directive-seeking money questions ("should I buy/sell/invest," "which
   stock") before they ever reach domain routing — so the wealth agent only
   ever sees questions that passed that gate (timing/suitability framing,
   e.g. "is this a good year for my finances"). The addendum should say
   this plainly so the model doesn't drift toward investment-directive
   language on its own, the way the marriage addendum explicitly forbids
   dosha fatalism.
2. `"wealth": AgentConfig(domain_id="wealth", domain_addendum=_WEALTH_ADDENDUM)`
   added to `AGENT_REGISTRY`.
3. Tests, matching `tests/test_domain_agent.py`'s existing pattern:
   `TestAssembleDomainShapes`-style bundle-shape test, an
   `AskOrchestrator.prepare()` test routing a wealth question,
   `test_ambiguous_tie_needs_clarification`-style coverage if wealth
   creates a new keyword tie worth checking (it shouldn't — its keywords
   don't overlap career/marriage's).

**This is not append-only-safe** — see the correction in `AGENTS.md`'s
ownership table: a new `AGENT_REGISTRY` entry flips a domain from
`domain_not_ready` to live model answers for real users. **Open a PR, tag
Claude (registry owner) for review — do not merge it yourself even if CI is
green.** Same review bar career/marriage got: domain addendum content, bundle
validation, verifier tests, route tests all present before merge.

**Status:** not yet assigned in detail (see ledger) — this brief is that
detail.

## Qwen — adversarial safety-regex audit + test-gap sweep

**Primary task, directly named in the architecture doc already** (Item 2's
sub-bullet on re-auditing the verifier): `dosha_overclaim_kind()` and
`prohibited_verdict()` in `astrospace/agents/safety.py` are simple
phrase-regex tables. `refer_out_kind()` in the same file used to be the
same shape and got redesigned after testing showed whole-phrase matching
"let 24 of 31 probe questions through... because an allowlist of sentences
cannot cover paraphrase" (that comment is still in the file — read it,
it's the exact lesson this task re-applies). `dosha_overclaim_kind`/
`prohibited_verdict` haven't had the same adversarial pass.

**What to do:** write paraphrases of every pattern already in
`_DOSHA_OVERCLAIM_OUTPUT` and `_PROHIBITED_OUTPUT` (`safety.py`) that mean
the same thing but don't match the regex literally — the way "how many
years do i have left" means the same as "when will i die" without matching
a death-keyword regex built around the literal word. Add them as new
parametrized cases in `tests/test_verifier.py`, following the existing
`test_dosha_fatalism_in_interpretation_fails` /
`test_prohibited_verdict_in_summary_fails` pattern. Where a paraphrase
passes when it should fail, that's the finding — document it, don't fix
the regex yourself (that's production safety logic; per `AGENTS.md`, PR it
and tag whoever owns `safety.py`/`verifier.py` — currently Claude, since
it's inside the Ask backend sequence — for the actual pattern fix).

**Secondary task, if the first finishes with capacity to spare:** a general
test-coverage gap sweep — pick one module outside `astrospace/agents/`
(not already being hardened by the primary task above), find what's
under-tested, write additive tests. Don't touch existing test assertions
as part of this (that's a different kind of change, needs its own review
per the daily-guidance energy-tone fix earlier today, which was exactly a
"someone should have caught this changed assertion" case) — additive only.

**Reminder from the ledger:** if this work touches `.gitignore` or any
other infra/config file for any reason, stop and PR it — per `AGENTS.md`
Rule 5, config changes are always reviewed, no exceptions, after the
2026-08-08 incident.

**Status:** not yet started (see ledger).
