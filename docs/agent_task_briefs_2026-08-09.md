# Agent task briefs — 2026-08-09

Status: point-in-time task specs, superseding the relevant sections of
[the 2026-08-08 briefs](agent_task_briefs_2026-08-08.md) now that PR #10
is merged and Item 3 (tense/life-stage) has a real specification. Governed
by [AGENTS.md](../AGENTS.md) — claim in the ledger before starting, PR +
review for anything outside your own area or touching config/registry/
infra. When a brief is done, prune its row in
[docs/agent_work_ledger.md](agent_work_ledger.md).

## Gemini — Health domain, with a scope caution attached

Already greenlit and in the ledger — this brief just adds one thing that
wasn't said explicitly when the green light was given.

Follow the same pattern as Wealth/Children:
`astrospace/context/taxonomy.json`'s `domains.health` entry already exists,
fully specified — do not edit it, same rule as Wealth. Write
`_HEALTH_ADDENDUM` in `astrospace/agents/registry.py`, register
`"health": AgentConfig(...)` in `AGENT_REGISTRY`, add tests matching
`tests/test_domain_agent.py`'s existing pattern (bundle-shape,
`AskOrchestrator.prepare()` routing, ambiguous-tie coverage if health's
keywords create one against an existing domain).

**The addendum needs to be unusually explicit about the refer-out
boundary, more than career/marriage/wealth needed.** `safety.py`'s
`refer_out_kind()` already blocks diagnosis/treatment-seeking questions
before they reach domain routing, so the health agent only ever sees
questions that passed that gate (timing/suitability framing — "is this a
good period for my health," not "what's wrong with me" or "should I stop
this medication"). State that boundary in the addendum as plainly as the
marriage addendum forbids dosha fatalism — this is the domain where
`prohibited_verdict()`'s medical cluster (`stop/start/change medication`,
`malignant growth/tumor/cancer`, etc., added in PR #10) gets exercised for
real for the first time, so the addendum is the model's first line of
defense, not the regex gate's job alone.

**Also carry the tense/life-stage finding into your test cases, even
though the fix (Item 3) isn't built yet.** Codex's finding
(`docs/ask_context_engine_multi_agent_architecture_2026-08-07.md`,
"Update 2026-08-09") is exactly as live for health as for career — "when
did this back pain start" vs. "when will I recover" is the same
retrospective/future shape as the career repro. You don't need to fix it
(that's my queued Item 3 work, not yours), but write your test questions
with both tenses represented so the gap is visible in health-specific
terms once Item 3 lands, rather than only ever having been proven on
career data.

**Review:** open a PR, tag Claude (registry owner) — same bar as
Wealth/Children, do not self-merge even with green CI.

## Codex — mobile screen build backlog

Per [docs/mobile_screen_build_plan.md](mobile_screen_build_plan.md), the
tracker already lists every unbuilt screen by Figma node ID with a status
column — this brief doesn't re-derive that list, just prioritizes it.

**Suggested order**, highest-trust-impact first, but this is your call to
resequence — you have the mobile codebase context I don't:

1. **Per-mode Ask Answer templates** (`212:971` / `1019` / `1077`) — right
   now one template serves Guided/Balanced/Practitioner; you just shipped
   the structured-rendering fields that make per-mode differentiation
   possible (PR #8), so this is the most direct continuation of that work,
   not a new area.
2. **Offline / stale-data and partial-calculation states** (`216:773`,
   `216:838`, `216:904` unknown-birth-time, `216:964` notification-denied)
   — currently ❌ not built at all per the tracker; these are the states a
   real user hits on a bad connection or incomplete profile, not edge cases.
3. Everything else on the ❌ list (Chart Hub variants, Calendar Day,
   Life Periods, multi-profile dashboard) — sequence at your discretion.

**Standing reminder from CLAUDE.md, since it's the rule this repo's had to
relearn a few times this build**: a green `ng build` is not evidence a
screen renders — screenshot it. Every screen closed out should have a live
verification note (not just a diff) the way PR #8's review did.

## Qwen — adversarial audit extended to Wealth + Children (and Health once merged)

**Direct continuation of your PR #7 work**, not a new task shape. PR #7
audited `dosha_overclaim_kind()`/`prohibited_verdict()` against the
*generic* phrase list in `safety.py`. Nobody has stress-tested those same
gates against the *domain-specific* phrasing Wealth's and Children's
addenda actually produce — money-framing fatalism for Wealth
("this dosha means you'll always struggle financially"), child-related
fatalism for Children ("this dosha means you'll never have children" —
note this is a different subject than the marriage-fatalism patterns PR
#10 just anchored, so don't assume the existing marriage-anchored patterns
already catch it). Once Gemini's Health PR merges, extend the same pass to
health-fatalism phrasing (illness-as-verdict framing distinct from the
literal medical-cluster patterns already in `_PROHIBITED_OUTPUT`).

**Method, same as before:** write paraphrases that mean the same
prohibited thing without matching the regex literally, add them as
parametrized cases in `tests/test_verifier.py` following the existing
pattern, and where a paraphrase passes when it should fail — that's the
finding. Document it, don't fix the regex yourself; PR it and tag Claude
(safety.py owner) for the actual pattern fix, same division of labor as
PR #7 → PR #10.

**Status:** not yet started (see ledger).
