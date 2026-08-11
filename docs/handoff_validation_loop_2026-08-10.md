# Handoff — consultation validation loop (2026-08-10)

**Status:** point-in-time handoff brief, disposable — **mostly discharged
2026-08-10**, kept only for §4's remaining item. Delete once birth-time
rectification is picked up.

Read this before starting. It exists so you don't re-derive things that cost a
long session to learn, and so you don't repeat two specific mistakes.

## What has since landed (2026-08-10, `claude/wealth-validation-loop-w0g7os`)

Items 1, 2 and 3 of §1's scope are built and tested for the wealth domain, and
§3's blocker is closed. The durable design record now lives in
[ask_context_engine_multi_agent_architecture_2026-08-07.md](ask_context_engine_multi_agent_architecture_2026-08-07.md)'s
"Update 2026-08-10" section, and the remaining work in
[backend_astro_depth_checklist_2026-08-06.md](backend_astro_depth_checklist_2026-08-06.md)'s
Deferred backlog — read those, not this, for current state.

Three things this brief guessed that turned out otherwise, recorded so the
next reader doesn't trust them over the code:

- **§4's "`PredictionClaim` is likely reusable rather than a new table" was
  wrong.** Its `reading_id` is a NOT NULL foreign key into `readings`, and an
  Ask-side probe has no `readings` row to point at; a probe also carries a
  question and its options, which a forward prediction never does. A new
  `validation_probes` table carries them instead. The *mechanism* is reused
  exactly as intended — commit, then score against what happened.
- **§4's `clarification_needed` envelope was reused as a pattern, not as
  code.** `validation_needed` is its own envelope type, because unlike a
  clarification it must persist a commitment before it is emitted and must
  keep that commitment out of both the envelope and the thread history.
- **§1's item 4 (birth-time rectification) is untouched**, as scoped.

Everything below is the original brief, unedited.

---

## 1. What you're building

Real astrologers don't open with predictions. They **validate first** — asking
about the past, traits, family situation, major incidents — and only then answer
what was actually asked. We want the same: the agent asks a small number of
multiple-choice questions (question *and* options generated on the fly), the
answers are stored, and every future reading gets better.

Agreed scope for the first pass:

1. A structured **timeline** (deterministic, server-computed). Today four
   overlapping dated windows are narrated in prose, so a reader cannot scan
   "where am I, what's next".
2. The **validation question turn**, with commit-before-ask (see §2).
3. Life context flowing back into the bundle as a new section.
4. Later: **birth-time rectification** — known events + dasha math to refine
   birth time. This is the real prize and the reason the data is worth storing.

Do this on the **wealth domain only** first, so hit rate is visible on something
real before generalising.

## 2. The one design decision that matters

**A naive implementation of this is a cold-reading machine.** Agent asks "have
you had money trouble?" → user says yes → agent says "yes, your chart shows
that". The agent learned nothing; the user was handed their own disclosure back
as insight. It would feel uncanny and be worth zero. This is not a hypothetical
— it is the actual professional technique, and it is where you land by default.

**The fix is ordering: the agent commits to a falsifiable claim, with a
confidence, BEFORE it sees the answer.** Then it asks. Then both are stored.

That buys honesty (we're testing the chart, not laundering a disclosure),
measurability (hit rate becomes a real number — we currently have no idea
whether our readings are any good), and learning (a persistent miss is signal,
possibly about birth time).

**Which questions are worth asking:** not rapport. Target genuine *chart
ambiguity* — where two readings are equally defensible and the answer
disambiguates. Rahu in the 11th can express as income volatility, an
unconventional career, or foreign connections; learning which actually happened
calibrates every later reading.

**Split of responsibility:** the **engine picks the slots** (it knows where the
ambiguity is — a dasha boundary, a lord with multiple significations), the
**model writes the question and options**. If the model picks slots too, it will
ask about things the chart cannot speak to.

**Fatigue is a real risk.** Few questions, skippable, asked once, and only when
the answer would change the reading.

## 3. Blocker — close this first

`agents/safety.py`'s `_PROHIBITED_OUTPUT` death cluster is anchored entirely to
"you", so **third-party phrasing passes straight through**. Verified 2026-08-10:

```
CAUGHT   | 'you will die young'              MISSED ! | 'your spouse will die young'
CAUGHT   | 'your lifespan is short'          MISSED ! | 'your child will not survive'
```

This is live in shipped code. It matters *here* specifically: once bundles carry
"user reported a family bereavement in 2019", that gap becomes materially more
reachable. **Close it before storing life events, not after.** The fix needs no
new mechanism — extend the existing detect-and-regenerate path to third-party
subjects.

## 4. Don't rebuild these — they already exist

- **`PredictionClaim`** (`db/models.py:103`) already has `claim_text`,
  `confidence`, `status`, `user_feedback`, `reviewed_at`, target dates. Built for
  *forward* predictions; what you need is the same mechanism pointed *backward*.
  Likely reusable rather than a new table.
- **`clarification_needed`** envelope (`agents/orchestrator.py:213`) — an
  interstitial question turn with options already exists; today it only asks
  about routing.
- **`retrospect`** block in `assemble_domain()` — the reader's dated period
  boundaries with their age at each. Deliberately carries dates and ages and
  *nothing about what happened*. Built exactly to make anchored (not cold-read)
  past-validation possible.
- **Registers** (`agents/domain_agent.py`, `REGISTERS`) — guided / balanced /
  practitioner voices over identical verified facts.
- `UserProfile` has **no** life-context fields. That part is genuinely new.

## 5. How we work here — this is the spine

**Verify every claim against the engine before believing it.** This session
caught, by checking rather than trusting: a Vimshopaka weight table wrong three
times running, a wrong 7-karaka Jaimini scheme, self-contradicting Avastha
arithmetic, 2 of 3 wrong D-60 signs, and two invented technical terms
("Pratargala", "Karakaksha") that do not exist in any source.

Concretely: after any model-generated reading, re-check its factual claims
against the bundle. Every enrichment this session was verified that way, and it
repeatedly caught real errors.

**Sourcing bar:** two independent sources that agree, or don't ship it. A D-60
deity build was started and deliberately reverted for failing this, then shipped
later once two agreeing sources were found. Anything unresolved ships flagged
`source_status: "convention_dependent"`.

**Testing:** `.venv/bin/python -m pytest tests/ -q` — 1552 passing, 1 xfailed
(Kalapurusha, a known gap). **The bundle is deterministic; the prose is not** —
so pin the bundle in tests, never the wording.

## 6. Do NOT trust these files

`docs/marriage-agent-kb.md`, `marriage-ce-payload-v1.md`,
`marriage-agent-prompt-v1.md`, `career-agent-kb.md` are user-added, untracked,
and were **audited and found to contain fabricated specifics** — a wrong Jaimini
scheme, self-contradicting arithmetic, mismatched scores, wrong D-60 signs, and
the two invented terms above. They are also the source of a "Semantic
Translation Layer" proposal (intercept a fatalistic prediction, reframe it into
softer words, serve the euphemism) that was **rejected twice** and should stay
rejected: softening a claim does not make it supportable. Guardrails belong at
the output layer, deterministic and tone-independent.

## 7. Audience and voice — learned the hard way

Users are **Indian, primarily South Indian**. Rahu, Shani, Guru, dasha, Sade
Sati are household words. An early "guided" register translated Rahu into "the
shadow planet of ambition and desire" — that is not simplification, it talks
down to a reader who has known the word since childhood, and it reads foreign.

The benchmark, from the user's own consultation: *"You don't need to worry about
money at all, but be careful with savings — your expenditure side is too high
and savings side is null."* Plain, short, confident, zero metaphor. **That
astrologer was warm because he was direct, not because he was lyrical.**

Also settled: confident/declarative tone is fine, remedies (incl. gemstones) are
fine — `core/vedic/remedies.py` already frames them as optional and non-
transactional. The line that stands is narrower than tone: **confidence must
track the chart, not the format**, and no death/longevity/medical verdicts or
directive financial instructions (CLAUDE.md non-negotiables).

## 8. Environment facts that surprise people

- **`AI_PROVIDER=gemini`**, model `gemini-3.5-flash`. Every reading in this
  project is Gemini-generated, not Anthropic. Don't assume otherwise.
- **If you are running in the cloud, you have no API key.** `.env` is not in the
  repo, so a cloud session cannot generate a live reading — attempting one fails
  at auth, which looks like a bug and is not. This is not blocking for most of
  this work: the engine, `assemble_domain()`, the timeline computation, the
  schema/DB work, the `safety.py` fix and the whole test suite are deterministic
  and need no model call. What you cannot do is the final end-to-end check that a
  generated reading uses the new data correctly — flag that for the user to run
  locally, or ask them to add `GEMINI_API_KEY` to the cloud environment. Say
  plainly that you skipped it; do not describe an unrun verification as done.
- The four untrusted files named in §6 are **untracked**, so a cloud clone will
  not contain them. If they are absent, nothing is wrong — but if the user
  uploads them, §6 applies.
- A `done` envelope can legitimately arrive **without a `reading`** (verification
  failure or API error). Clients must handle it; the orchestrator correctly never
  persists an unverified reading.
- AGENTS.md rules apply: work in a git worktree, and config/registry/infra plus
  non-trivial features go through PR + review rather than self-merge.

## 9. Backlog

One place, with reasons and unblock conditions:
[backend_astro_depth_checklist_2026-08-06.md](backend_astro_depth_checklist_2026-08-06.md)
§ "Deferred backlog". Add deferrals there, not in a new file.
