# Profile Context Ledger Architecture

Date: 2026-08-14

Status: Phase 1 (server ledger + mobile "what Siddha remembers" screen) merged. Phase 2 (deterministic Ask integration) implemented on `claude/profile-context-ledger-phase2`, awaiting review — see "Implementation Update — Phase 2" below. Model extraction, agent-initiated candidate proposal, and offline ledger storage remain unimplemented (Phases 3-4).

Owner: Codex (product/mobile contract)

Required reviewers: Claude (Ask orchestration and persistence), Gemini (astrological domain semantics), Qwen (privacy and contradiction tests)

## Implementation Update — 2026-08-14

Phase 1 server-ledger implementation is complete on
`codex-profile-context-ledger-implementation` and awaiting owner review. It
includes the governed fact registry, Postgres/SQLAlchemy schema, profile-owned
CRUD, optimistic revisions, idempotent mutations, immutable supersession,
deletion scrubbing, domain-filtered projection, logical constraints, export,
account/profile deletion behavior, and adversarial API tests.

The first reader-controlled mobile surface is also implemented: each profile
has a dedicated `What Siddha remembers` screen for reviewing, adding,
correcting, deleting, and exporting allow-listed facts. Writes carry the
server revision, an idempotency key, an explicit reader-consent source, and
discard late responses when the route/profile identity changes. The screen
does not cache sensitive ledger values locally.

This does **not** activate Ask memory, model candidate extraction, agent
retrieval, logical preflight, or offline ledger storage. Those remain Phases
2–4 and must not infer durable facts from model output.

## Implementation Update — Phase 2 (2026-08-14)

Deterministic Ask integration is implemented on
`claude/profile-context-ledger-phase2`, following the sequence below exactly.
Reader-authored facts only — no model extraction, no Ask-derived writes, no
silent inference persistence, no offline ledger cache, and no change to any
deterministic chart calculation. Every claim in this section is backed by a
passing test; see `tests/test_profile_context_ledger_phase2.py` and the new
`TestTenseInvariantParityWithLedgerPreflight` class in `tests/test_verifier.py`.

### 1. Projection builder extracted and shared

`build_profile_context_projection(db, user_id=, profile_id=, domain=, as_of=,
include_history=)` (`astrospace/db/crud_profile_context.py`) is now the one
function both `profile_context_routes.py`'s `GET .../context` and
`AskOrchestrator` call — the route was refactored to call it rather than
duplicate the projection logic Phase 1 built inline. Ownership is NOT checked
inside this function (filtering by both `user_id` and `profile_id` makes a
mismatched pair return an empty, revision-0 projection rather than another
account's data); the uniform-404 behaviour stays the caller's job, exactly as
it already was for `list_facts`. `resolve_fact_ref()` (same file) resolves one
`profile_fact:<id>@<revision>` ref against the real ledger for future
audit/admin tooling; the verifier itself does not use it (see below — it
checks bundle membership only, never a live query).

### 2. Frozen per-turn snapshot

`AskOrchestrator` gained `ProfileContextStore` (`astrospace/agents/orchestrator.py`),
the same DB-free-closure pattern as `ValidationStore`/`chart_loader`. Its
`projection(domain, as_of_iso) -> dict` callable is invoked exactly once per
turn, inside `check_profile_context()`, called from `assemble_context()`
during `prepare()` — before `AgentRun`, and never again during the one repair
attempt or verification. `PreparedRun.profile_context_revision`/
`profile_context_as_of` carry the exact snapshot identity forward to
persistence, so a later correction/deletion never retroactively changes what
an already-answered turn is understood to have been grounded in.
`tests/test_profile_context_ledger_phase2.py::TestFrozenSnapshot` proves the
store is called exactly once even across a repair, and that a "concurrent"
correction committed after `prepare()` cannot reach the same turn's bundle.

### 3. Logical preflight

`build_logical_preflight()` (`astrospace/context/profile_context.py`) combines
the assembler's own `profile_facts` (age/birth_year/as_of), the frozen
projection's active facts, `detect_tense()`'s tense, and the routed domain
into a `LogicalPreflight`: `blocked_frames`, `required_frames`,
`context_notes`, `missing_or_conflicting_context`, `applicable_fact_refs` —
deterministic, regex/rule-based, zero model calls, same discipline as
`logical_constraints()` and `detect_tense()` before it. Covers exactly the
five named examples: retired -> blocks future first-career-inception;
married -> blocks first-marriage framing (unless the question is genuinely
retrospective); existing children -> requires existing-children framing and
blocks first-child framing when the question asks "will I have children";
disclosed health constraint -> blocks medical prognosis/recovery guarantees;
age/life-stage mismatch -> blocks implausible first-job or biological-
pregnancy framing at wide, conservative age margins (70+/55+).

### 4. CE bundle extension

`assemble_domain()` (`astrospace/context/assembler.py`) gained an optional
`profile_context` parameter and always returns a `profile_context` top-level
bundle section (an empty stub when no store is configured, so every existing
caller — including the `/context/{kundli_id}` POST route, untouched — keeps
working identically). It is populated by the orchestrator AFTER
`assemble_domain()` returns (not threaded through assembler internals), kept
structurally separate from every chart-derived section, and
`astrospace/context/profile_context.py` imports nothing from
`astrospace.core.vedic` — there is no code path by which a ledger fact can
reach a chart calculation. `domain_agent.py`'s system prompt renders this
section as prose (`_format_profile_context_block`) positioned BEFORE the
astrological grounding rules, and instructs the model never to present a
disclosed fact as a chart discovery, citing the fact's exact `ref` instead.

### 5. Deterministic verification extended

`verifier.py`'s `_valid_sources()` now includes the frozen bundle's own
`profile_context.facts[].ref` values — the SAME evidence-resolution function
KB citations already went through, not a second one. A `profile_fact:` ref
that is deleted, superseded, expired outside `as_of`, or belongs to a
different profile is simply absent from that list (it was never included
when the projection was built), so citing it fails exactly like an invented
KB citation always has. `verify()` gained `_blocked_frame_violations()`
(safety severity — the reading is discarded, same tier as a prohibited
verdict) and `_discovery_violations()` (a disclosed fact handed back as
"your chart reveals..."). `verify_coverage()` gained
`_required_frame_shortfall()` (quality severity, matching the existing
varga-coverage check's discipline — a missed required frame is a worse
reading, not a dangerous one).

### 6. Tense invariant absorption — additive, not a replacement

`detect_tense()` and the existing verifier tense-conflict invariant are
**unchanged**. The new checks are pure `violations.extend(...)` calls
alongside it in the same `verify()` function — structurally incapable of
suppressing an old violation, since nothing removes or filters the old
check's output. `TestTenseInvariantParityWithLedgerPreflight`
(`tests/test_verifier.py`) proves this from the outside rather than by
inspection: every existing `TestTenseConflictInvariant` case still produces
byte-identical violations with an empty ledger, and a case with both an
invented future year AND a blocked ledger frame proves both violations
surface together, with `old_violations ⊆ combined_violations` asserted as a
literal subset check. Per this doc's release gate 7, the old path has not
been removed or delegated — that only happens after this parity evidence is
accepted, which is what this section documents.

### CE/SSE contract for mobile rendering (handoff to Codex)

Every SSE `done` frame from `POST /api/v1/ask/{kundli_id}/stream` with
`status: "answered"` now additionally carries:

```json
{
  "profile_context_revision": 1,
  "profile_context_as_of": "2026-08-14"
}
```

`profile_context_revision` is the ledger's `revision` counter at the moment
this turn's snapshot was frozen (0 when the reader has no ledger facts or no
store was configured). `profile_context_as_of` is the ISO date the snapshot
was evaluated as-of. Both are also persisted into the assistant `AskMessage`
row's `evidence` JSON (`{"profile_context_revision": ..., "profile_context_as_of": ...}`,
alongside the existing `structured_reading`/`references` keys) via
`_evidence_from_reading()` (`astrospace/api/ask_routes.py`) — reopening an old
thread can show what ledger state an answer was actually grounded in, without
re-querying the live ledger.

`evidence_refs` (already on the `done` envelope, and already used by mobile)
now legitimately contains `profile_fact:<id>@<revision>` entries whenever the
model cited a ledger fact — no shape change, same array of strings.

No new SSE event type was added. `blocked_frames`/`required_frames`/etc. are
NOT exposed on the wire — they're an internal generation/verification
contract between the orchestrator, the prompt, and the verifier, not
something the client renders. If a reading is discarded for a ledger-related
reason, the client sees the existing `status: "verification_failed"` frame,
identical in shape to every other verification failure — no ledger-specific
error UI is required.

What Codex owns from here, per the original task split: mobile confirmation/
audit rendering (surfacing `profile_context_revision`/`profile_context_as_of`
somewhere reader-visible, e.g. a "grounded in your saved context as of ..."
line, is a product decision, not specified here), cross-profile and profile-
switch device testing against this new field, any structured status UI the
preflight's existence might motivate, and the final Android regression after
this backend lands.

## Product Purpose

Siddha is a way-of-life guidance product, not a stateless horoscope chatbot.
The Profile Context Ledger lets a reader deliberately teach Siddha durable
facts that materially change future guidance: that they are retired, married,
have children, moved country, changed career, are caring for a parent, or are
currently unwell.

This is not hidden surveillance and it is not permission for a model to turn
an inference into biography. The ledger is an auditable profile-owned record
with provenance, time bounds, confidence, consent, correction, and deletion.
Logical life context must constrain astrological interpretation before the
model predicts. A retired reader must not receive a confident future career
inception in 2049 merely because a dasha supports professional activity.

## Business Objective

- Build trust through continuity across consultations.
- Improve relevance without repeatedly asking the same personal questions.
- Make Family plans meaningfully profile-aware while preserving strict
  separation between family members.
- Support premium longitudinal guidance and reports without selling or
  exploiting sensitive disclosures.
- Reduce implausible answers and expensive regeneration by giving the Context
  Engine verified demographic and life-stage constraints up front.

The ledger is not an advertising profile, a medical record, a credit profile,
or a source for irreversible automated decisions.

## Existing System And Boundary

The current consultation-validation loop already stores `ValidationProbe`
answers and projects answered probes into the CE bundle as `life_context`.
That mechanism is narrow and scientifically useful: the engine commits to a
claim before asking, then measures whether the claim matched.

The repository also contains a narrow protection for the incident that
motivated this epic: `detect_tense()`, a deterministic `profile_facts` bundle
section, and a verifier invariant prevent a known retired profile from being
given an invented future career timeline. The ledger must absorb and
generalize that path through one typed preflight contract; it must not create
a second competing source of life-stage truth. Until parity tests prove the
replacement, the existing controls remain authoritative and the ledger
projection is additive only.

The Profile Context Ledger is different:

| Concern | Validation probe | Profile context fact |
|---|---|---|
| Purpose | Measure a committed chart interpretation | Remember reader-confirmed life reality |
| Initiator | Deterministic ambiguity slot | Reader, explicit profile form, or confirmation prompt |
| Truth status | Answer to one scoped probe | Durable or time-bounded profile fact |
| Mutation | Claim immutable; answer once | Correctable, supersedable, revocable |
| Retrieval | Domain-scoped calibration | Relevance-scoped logical context |
| Retention | Product analytics policy | Sensitive profile-data policy |

Do not merge these tables or semantics. A missed chart claim is calibration;
a reader's statement that they are retired is profile truth until they correct
or revoke it.

## Non-Negotiable Invariants

1. Every fact is scoped by authenticated `user_id` and `profile_id`.
2. A fact from profile A never reaches profile B, even when both belong to the
   same account or thread state races during a profile switch.
3. Model inference alone can never create an active durable fact.
4. The reader sees what may be remembered before it is saved.
5. Sensitive health, relationship, finance, legal, religion, and child facts
   require explicit confirmation; silence is never consent.
6. Every active fact has provenance, confidence, timestamps, and a retention
   class.
7. Corrections supersede prior values; they do not silently rewrite history.
8. Deletion removes the fact from CE retrieval, local projections, exports,
   and future model calls. Audit metadata may retain only the minimum required
   by policy and must not retain the deleted prose.
9. Logical constraints run before astrological interpretation. Astrology may
   explain or guide around reality; it may not contradict a confirmed fact.
10. A reported fact must never be narrated back as if the chart discovered it.
11. Absence of a fact means unknown, not false.
12. Current state and historical state are distinct. “Was married” does not
    imply “is married”; “felt unwell last month” is not permanent health status.
13. Profile memory is excluded from logs, analytics payloads, crash reports,
    and cache keys.
14. Account deletion and profile deletion have deterministic cascade behavior.
15. Profile facts never alter deterministic astronomical computation: planetary
    degrees, houses, Vargas, Dashas, transits, Panchanga, strengths, Yogas and
    Doshas are calculated from their declared astronomical inputs only.
16. A profile fact may constrain semantic framing but can never serve as proof
    of a chart placement or cause the model to manufacture astrological
    evidence that confirms the fact.
17. High-severity health, relationship, finance, legal and child facts are
    retrieved only when the routed domain and intent require them. A diagnosis
    blocks astrological diagnosis, treatment, recovery guarantees and medical
    prognosis; it does not automatically suppress unrelated daily guidance.

## Fact Model

```json
{
  "id": "fact_uuid",
  "user_id": "account_uuid",
  "profile_id": "kundli_uuid",
  "category": "life_stage",
  "key": "employment_status",
  "value": { "code": "retired", "label": "Retired" },
  "valid_from": "2021-03-01",
  "valid_to": null,
  "status": "active",
  "confidence": "confirmed",
  "sensitivity": "personal",
  "retention": "until_removed",
  "source": {
    "kind": "reader_statement",
    "channel": "ask",
    "thread_id": "thread_uuid",
    "message_id": "message_uuid"
  },
  "consent": {
    "state": "granted",
    "captured_at": "2026-08-14T08:20:00Z",
    "surface": "ask_memory_confirmation_v1"
  },
  "supersedes_id": null,
  "created_at": "2026-08-14T08:20:00Z",
  "updated_at": "2026-08-14T08:20:00Z",
  "revision": 1
}
```

### Controlled Categories

| Category | Example keys | Default sensitivity | Typical validity |
|---|---|---|---|
| Demographics | preferred_name, pronouns, residence_country | personal | until corrected |
| Life stage | employment_status, retirement_status, education_stage | personal | time-bounded/current |
| Relationship | relationship_status, marriage_date, separation | sensitive | time-bounded/current |
| Family | has_children, child_count, caregiving_role | sensitive | durable/current |
| Career | occupation, industry, career_transition | personal | time-bounded |
| Health context | current_health_constraint, recovery_period | highly sensitive | short expiry by default |
| Location history | moved_to, travel/residence status | personal | time-bounded |
| Goals | looking_for_work, planning_marriage, study_goal | personal | explicit expiry |
| Preferences | remedy constraints, language, consultation style | personal | until corrected |

Free-form keys are not accepted from clients. New keys require registry-like
review because they expand what agents may retrieve and reason about.

### Confidence

- `confirmed`: explicitly saved or confirmed by the reader.
- `reported`: directly stated in a current turn but not approved for durable
  memory; usable only within that turn/thread.
- `derived`: deterministic derivation from confirmed facts, such as age from
  DOB. Never persisted when it can be recomputed.
- `candidate`: proposed by extraction and awaiting confirmation. Never enters
  CE as truth.
- `disputed`: contradicted or challenged; excluded from normal retrieval.

There is deliberately no `model_confident` status.

## Capture Flow

```text
reader message
  -> deterministic/profile-aware extraction candidate
  -> sensitivity + key allow-list check
  -> candidate shown in plain language
  -> Save / Not now / Never remember this kind
  -> server validates ownership and expected revision
  -> append active fact or superseding correction
  -> invalidate profile-context projection
  -> future CE bundle retrieves only relevant active facts
```

Examples:

- “I retired in 2021.” -> propose `employment_status=retired`, valid from 2021.
- “My health is not fine now.” -> propose a short-lived health-context note;
  never diagnose, and ask whether the reader wants it remembered.
- “Tell me about my children.” -> this is a question, not evidence that the
  reader has children. Do not create a fact.
- “Will I get married?” -> a goal/question, not `relationship_status=single`.

Extraction should prefer deterministic patterns and structured UI. If an LLM
is used to propose candidates, its output must validate against the key/value
registry and remain `candidate` until explicit reader action.

## Context Engine Contract

The Context Planner requests facts by domain and intent; agents do not query
the full ledger directly.

```json
{
  "profile_context": {
    "revision": 12,
    "as_of": "2026-08-14T08:30:00Z",
    "facts": [
      {
        "ref": "profile_fact:fact_uuid@1",
        "key": "employment_status",
        "value": { "code": "retired" },
        "valid_from": "2021-03-01",
        "confidence": "confirmed",
        "source_kind": "reader_statement"
      }
    ],
    "logical_constraints": [
      "The reader is retired. Treat career questions as retrospective, legacy, consulting, purpose, or post-retirement activity unless they explicitly ask about re-employment."
    ]
  }
}
```

Rules:

1. Retrieve by the routed domain, intent, time frame, and fact registry.
2. Include the smallest relevant set; never dump the whole biography.
3. Return opaque evidence refs so the verifier can prove every referenced fact
   existed in the supplied projection.
4. Run a deterministic plausibility pass before agent generation: age, current
   employment/retirement, relationship state, known children, current country,
   and explicitly dated events.
5. If the question conflicts with a confirmed fact, acknowledge and clarify
   instead of choosing whichever wording gives the easiest prediction.

6. If facts conflict with one another, return `context_confirmation_needed`;
   do not let the model resolve identity truth.
7. Thread messages may carry conversational context, but durable profile facts
   only come from the ledger projection.

### Evidence-reference reconciliation

`profile_fact:fact_uuid@revision` is a namespace inside the existing evidence
contract, not a second verifier. Extend the current evidence resolver so each
citation resolves against the exact frozen request bundle, whether it points
to classical/CE evidence or a profile fact. Verification must reject a fact
reference that belongs to another profile, is superseded or expired, has a
revision mismatch, or was not supplied to the agent. It must not perform a
fresh database read that could observe a different ledger revision. Persist
the answer only after this unified deterministic evidence pass succeeds.

## Logical Reasoning Before Astrology

The orchestrator needs a deterministic preflight result:

```json
{
  "question_timeframe": "retrospective",
  "life_stage": "retired",
  "contradictions": [],
  "clarifications": [],
  "allowed_frames": ["career_history", "retirement_transition", "legacy"],
  "blocked_frames": ["first_career_inception_after_retirement"],
  "blocked_prognoses": []
}
```

This is not an LLM “common sense” prompt. It is a typed node whose output is
testable and available to the verifier. The final answer must fail verification
if it asserts a blocked frame or treats an explicit historical question as a
future prediction.

Blocked frames constrain narration after the chart is computed; they are not
inputs to chart mathematics. Safety routing still evaluates the reader's
question first. When a relevant confirmed fact contains a diagnosed condition,
the preflight adds medical diagnosis/treatment/recovery claims to
`blocked_prognoses`; medical-advice or prognosis questions return the existing
health `refer_out`. The diagnosis itself is not sent to unrelated domain agents
and must not become a prompt for confirmation-biased chart interpretation.

## API Contract

Recommended endpoints:

```text
GET    /api/v1/profiles/{profile_id}/context
POST   /api/v1/profiles/{profile_id}/context/candidates/{candidate_id}/confirm
POST   /api/v1/profiles/{profile_id}/context/facts
PATCH  /api/v1/profiles/{profile_id}/context/facts/{fact_id}
DELETE /api/v1/profiles/{profile_id}/context/facts/{fact_id}
POST   /api/v1/profiles/{profile_id}/context/facts/{fact_id}/dispute
GET    /api/v1/profiles/{profile_id}/context/export
```

Writes require an idempotency key and `expected_revision`. A stale revision
returns `409` with the current projection; clients do not last-write-win over
another device. All reads and writes re-check account ownership server-side.
Candidate confirmation uses the same idempotency and revision contract; a
double-tap on **Save to this profile** cannot activate two facts or advance the
ledger twice.
Optimistic ledger revisions and `409` conflict recovery are new infrastructure
for this repository, not an extension of an existing profile-write contract.
They require schema, API, concurrent-write, and client conflict-state tests
before the endpoint contract can be called implemented.

## Mobile Experience

### Ask capture

After the assistant response, show a compact confirmation sheet only when a
safe allow-listed candidate exists:

> Remember that you retired in 2021 for future readings?

Actions: **Save to this profile**, **Not now**, **Don't ask for this kind**.
The answer never waits for this action.

### Profile settings

Add `What Siddha remembers` under Manage Profile, not global account settings.
It supports category filters, source/date display, edit, delete, and download.
Highly sensitive facts use plain labels and never expose raw Ask prose by
default.

### Cross-profile behavior

Switching profiles immediately clears pending candidates, ledger projections,
Ask drafts, and optimistic writes from the previous profile. A pending save
captured for profile A carries A's identity and must be rejected if submitted
after switching to B.

### Offline

The native app may keep an encrypted read-only projection for continuity.
Offline edits enter a profile-scoped pending queue and require conflict review
after reconnect. This depends on the encrypted native repository from the
Reliable Native Core epic; do not put ledger facts in plain `localStorage`.
On reconnect, replace the durable projection from the server's complete current
revision, including deletions and supersessions; never append-merge it. A
tombstoned health or relationship fact must not reappear because an offline
client received additions without removals.

## Retention And Privacy

- Health context defaults to 30 days unless the reader chooses a longer span.
- Goals expire on their target date plus a short grace period.
- Durable demographics/life events remain until corrected or removed.
- Candidate facts expire within 24 hours if unconfirmed.
- “Never remember this kind” stores a category preference, not the rejected
  sensitive content.
- Profile sharing/export excludes ledger facts by default and requires an
  explicit per-category inclusion step.
- Family-plan account owners cannot inspect another adult profile's ledger
  without that adult's explicit sharing grant.
- Deletion emits an opaque audit event but no deleted value.

Export generation, minimal audit storage, retention scheduling/TTL, and
deletion propagation are new platform capabilities. They need explicit jobs,
failure handling, and end-to-end privacy tests; naming them here does not mean
the repository already supplies that infrastructure.

## Failure And Safety States

| Condition | Product behavior |
|---|---|
| Extraction unavailable | Answer normally; do not propose memory |
| Save unavailable | Keep candidate local only for the current screen; retry only on reader action |
| Fact conflict | Ask reader to confirm current truth; exclude both from prediction |
| Stale client revision | Show latest server values and let reader reapply correction |
| Offline, no encrypted store | Do not display or capture durable memory |
| Profile switch during save | Cancel/ignore late response; never apply it to new profile |
| Account deletion | Block completion until server deletion result is known; clear local projection |
| Agent cites unknown fact ref | Verification failure; no answer persistence |

## Delivery Sequence

### Phase 0: Contract and registry

- Approve fact categories/keys, sensitivity, retention, and CE projection.
- Add JSON schema and fixtures for confirmed, candidate, superseded, disputed,
  expired, and conflicting facts.
- Decide policy language and data-export behavior.

### Phase 1: Server ledger

- Add append/supersede schema, RLS/ownership enforcement, revisioning, CRUD,
  export/delete, and audit events.
- Add deterministic profile projection and relevance filtering.
- No model extraction yet; support structured profile forms first.

### Phase 2: Logical preflight and verifier — implemented, see update above

- ~~Add typed life-stage/tense/contradiction node before CE assembly.~~ Done:
  `build_logical_preflight()`.
- ~~Feed the minimal projection to domain agents.~~ Done: `profile_context`
  bundle section + prompt block.
- ~~Verify fact refs and blocked-frame invariants.~~ Done: `_valid_sources()`,
  `_blocked_frame_violations()`, `_discovery_violations()`,
  `_required_frame_shortfall()`.
- ~~Reproduce the retired-career failure as a golden regression.~~ Done:
  `TestRetiredCareerInception`.

### Phase 3: Mobile control surface

- Build `What Siddha remembers`, correction/delete, consent sheets, conflict
  resolution, and profile-switch race protection.
- Add encrypted offline projection after Reliable Native Core native storage
  is approved.

### Phase 4: Candidate extraction

- Start with retirement/employment, relationship status, children, move/current
  country, and explicit dated life events.
- Measure proposal precision and rejection rate before expanding categories.
- Never auto-save.

### Phase 5: Longitudinal guidance

- Use confirmed facts for continuity, retrospective validation, reports, and
  future follow-ups.
- Introduce plan entitlements only after privacy controls and deletion/export
  are proven; memory safety is not a paid-tier feature.

### Commercial and Family dependency

The Family behavior described here depends on the still-separate Commercial
Entitlements proposal (PR #54 at the time of writing). Individual-profile
ledger work may proceed without it. Family membership, adult sharing roles,
dependent profiles, and paid-seat lifecycle behavior must wait for an approved
entitlement contract and must be linked as an explicit delivery dependency.
The core privacy invariants remain mandatory for every plan.
No cross-profile ledger read or sharing endpoint may ship before that contract
defines authenticated membership and explicit grants; temporary organizer or
same-account shortcuts are forbidden.

## Acceptance Matrix

| Scenario | Required result |
|---|---|
| Retired mother asks career inception/retirement dates | Answer is retrospective; no post-retirement “career inception” invented |
| User says “I retired in 2021” | Candidate shown; nothing durable saved without confirmation |
| User asks about children | No `has_children` fact inferred from the question |
| Older reader asks whether they will have children | Clarify whose parenthood is meant and avoid an assumed biological-pregnancy prediction; adoption, grandchildren or creative legacy are offered only when relevant, not inferred as facts |
| Reader with a confirmed diagnosis asks for astrological diagnosis, treatment or recovery certainty | Health `refer_out`; the known diagnosis is not used to invent chart evidence or a medical prognosis |
| Diagnosed health fact exists while reader asks an unrelated career question | Health fact is excluded from the career projection; career answer proceeds without medical contamination |
| Profile A is married, profile B is single/unknown | Each receives only its own facts; no cross-profile flash or retrieval |
| User corrects married to separated | New revision supersedes prior fact; history is auditable; current projection is separated |
| User deletes a health fact | It disappears from CE, device projection, export, and later answers |
| Two devices edit same fact | One receives 409 and explicit conflict resolution; no silent overwrite |
| Agent invents a profile fact | Unknown evidence ref fails verification; turn does not persist |
| Historical and current facts coexist | Query time frame selects the appropriate interval |
| Offline profile switch | Previous profile's projection is removed before target profile renders |
| Caller requests another account's `profile_id` directly | Server returns not-found/forbidden without revealing whether a ledger exists |
| Reader double-taps candidate confirmation | One idempotent activation and one revision advance |
| Ask generation for profile A is in flight when user switches to B | Late result is discarded from the active UI and may persist only to A's authenticated thread; it never enters B's thread, projection or cache |
| Fact is corrected or expires after request projection is frozen | Verification uses the exact frozen request bundle, never a live ledger re-read; later requests use the new revision |
| Reported fact appears in one thread but is never confirmed | It may support that immediate turn only and never appears in another thread's profile projection |
| Offline device reconnects after server-side fact deletion | Full revision replacement removes the local fact; append-only merge is forbidden |

## Release Gates

1. Claude approves schema, orchestrator node placement, and persistence order.
2. Privacy review approves sensitivity, consent, retention, export, and Family
   plan boundaries.
3. Golden tests include the retired-career incident and attacker-side A/B
   profile races. **Engineering-satisfied on `claude/profile-context-ledger-phase2`**
   — `tests/test_profile_context_ledger_phase2.py` covers the retired-career
   scenario plus foreign-profile/cross-domain isolation; broader attacker-side
   device/production testing (Qwen's original scope) is still separate.
5. All fact evidence refs resolve against the exact CE projection used.
   **Engineering-satisfied** — `verifier.py`'s `_valid_sources()` checks
   `profile_fact:` refs against the frozen bundle only, never a live query;
   see `TestVerifierEvidenceResolution`.
6. Golden tests prove profile facts do not alter deterministic chart outputs and
   cannot be cited as astronomical evidence. **Engineering-satisfied** —
   `astrospace/context/profile_context.py` imports nothing from
   `astrospace.core.vedic`; there is no code path from a ledger fact to a
   chart calculation.
7. Phase 2 replaces the narrow tense/profile-fact path only after parity tests
   prove the old behavior is a strict subset with zero disagreement cases; no
   release may run two independently authoritative preflight paths.
   **Parity proven, old path NOT yet removed** — `detect_tense()` and the
   existing verifier tense invariant are unchanged; the new checks are purely
   additive (`violations.extend(...)`, never a filter/override). See
   `TestTenseInvariantParityWithLedgerPreflight`. Whether/when to delegate or
   retire the narrow path is a separate decision this parity evidence enables,
   not one this implementation makes unilaterally.
8. Correction, deletion, account deletion, and offline conflict paths pass on
   Android and iOS.
9. Production telemetry contains counts/status/latency only, never fact values.

## Immediate Dependency Boundary

Implementation beyond this contract touches Claude-owned Ask orchestration,
database models/migrations, and CE assembly. It also depends on an approved
encrypted native repository before offline storage is allowed. Until those
reviews are available, the safe independent work is complete: the product,
data, privacy, API, CE, UI, failure, test, and sequencing contracts are
specified without creating a shadow persistence path.
