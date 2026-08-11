# Siddha Mobile Ask Full Regression Audit

Date: 2026-08-10

Owner: Codex

Status: audit complete; no fixes implemented in this pass

## Executive Summary

Ask is visually much stronger than the previous free-text implementation and its
basic same-profile thread flow works: a new answer saves, a follow-up appends to
the same thread, history reopens persisted messages without re-streaming, and the
three persona templates render distinct levels of evidence.

It is **not release-ready**. The sweep found one P0 safety-path failure, five P1
trust or context failures, and multiple P2 interaction and readability defects.
The most serious problems are:

1. Three of four safety refer-out categories cannot persist against the configured
   Postgres constraint, so a prohibited question can show a generic generation
   error instead of the mandatory safety response.
2. The cached Ask Answer component retains a thread across profile switches. A
   question for profile B can be submitted with profile A's thread, and stale
   profile-B content remains visible when profile A's thread is reopened.
3. Ask's topic selection and the global gentle/direct tone setting are not sent to
   the backend. Both controls promise behavior they do not currently provide.
4. The streamed answer experience duplicates status text, does not reliably bring
   the newest turn or Stop control into view, and presents long readings as dense
   walls of text.
5. Archive has no user-accessible archive, restore, or delete flow; the history
   `ACTIVE` badge is simply the first row, not an actual state.

## Environment And Method

| Target | Configuration | Result |
|---|---|---|
| Android native | Samsung SM-S938W, package `app.astrospace.mobile`, 1440x3120 at density 560, connected over ADB | Tested with a signed-in account and real profiles |
| Local mobile web | Angular dev server, 375x812, Chromium 151 | Tested in light and dark themes |
| Local backend | FastAPI from current `main`, dev auth bypass, configured Postgres | Tested terminal SSE paths and persisted threads |
| Personas | Guided, Balanced, Practitioner | All three rendered and captured |
| Profiles | Srinath, Lalitha Kumari | Switch and thread isolation tested on Android |

Evidence labels used below:

- **Device**: reproduced in the installed Android app.
- **Browser**: reproduced in the 375x812 local mobile preview.
- **Database**: checked directly against configured Postgres metadata/logs.
- **Source**: deterministic behavior confirmed from the named code path.

The installed Android state was restored to **Srinath / Balanced / Direct** after
testing. One test conversation was archived while verifying the real archive
flow. No production code was changed.

## Coverage Matrix

| Area | Coverage | Outcome |
|---|---|---|
| New typed question | Device | Answer completed and saved |
| Suggested question | Device | Answer completed and saved |
| Follow-up | Device | Same-profile continuation works; latest turn positioning is poor |
| Reopen old thread | Device + Browser | Persisted thread does not re-stream |
| Structured rendering | Guided / Balanced / Practitioner | Distinct templates render; content hygiene and density issues remain |
| Tone switch | Gentle / Direct | UI preference persists, but is not sent to Ask backend |
| Profile switch | Two real profiles | Failed isolation; stale thread and draft cross profile boundary |
| History | Device | List, open, swipe, archive tested |
| Archive / delete | Device + Source | Archive removes access; no archive view, restore, or delete |
| Clarification | Browser | Terminal state and domain choice tested |
| Domain not ready | Browser | Terminal state works |
| Safety refer-out | Browser + Database | Broken by database constraint mismatch |
| Generation failure | Browser | Terminal bubble renders |
| Fatal SSE consumer | Unit/source | Consumer exists; live fault injection not performed |
| Voice | Source + visible UI | Listening UI is a fixed placeholder, not speech recognition |
| Copy / edit | Browser | Both work; copy strips markdown tokens |
| Light / dark | Browser + Device | No horizontal overflow; hierarchy/readability issues remain |
| Offline | Not injected | Not marked verified in this audit |

## Findings

### ASK-001 - Safety refer-outs fail database persistence

- **Priority:** P0
- **Gap type:** Safety / backend schema contract
- **Route:** `/m/ask/answer`, `POST /api/v1/ask/{kundliId}/stream`
- **Component/source:** `astrospace/api/ask_stream_routes.py:113-153`,
  `astrospace/agents/safety.py:183-271`, configured Postgres
- **Expected:** A prohibited lifespan, medical, legal, or directive financial
  question returns the deterministic refer-out copy and navigates to the safety
  screen without invoking a domain reading.
- **Actual:** `Will I die this year?` reaches the death refer-out, then the
  assistant insert violates `ask_messages_refer_out_kind_check`. `_safe_stream`
  emits `fatal_error`; the UI says “Something went wrong while generating this
  answer.”
- **Repro:** Open Ask; submit `Will I die this year?`; wait for the terminal state.
- **Evidence:** `ask-safety-persistence-failure-375x812.jpg`; backend traceback
  records `CheckViolation`; database metadata says the allowed values are
  `medical, legal, financial, longevity, emergency`, while application code emits
  `health, legal, money, death`.
- **Recommended fix direction:** Add a reviewed migration that establishes one
  canonical enum/constraint shared by application models, API tests, and deployed
  Postgres. Make the refer-out transaction atomic and add a real-Postgres contract
  test for every safety kind. Do not rely only on SQLite tests.

### ASK-002 - Cached thread state crosses profile boundaries

- **Priority:** P1
- **Gap type:** Profile isolation / conversation integrity
- **Route:** `/m/ask`, `/m/ask/answer`
- **Component/source:** `ui/src/app/core/mobile-route-reuse-strategy.ts:5-29`,
  `ui/src/app/features/mobile/ask/ask-answer.component.ts:401-448,570-625`
- **Expected:** Switching the active profile clears or rebinds all Ask thread,
  draft, and in-memory message state before another question can be submitted.
- **Actual:** Ask Answer falls back from the URL thread to retained
  `activeThreadId`. After switching Srinath to Lalitha, a Lalitha question was
  submitted with Srinath's thread and failed with `Thread belongs to a different
  kundli`. Switching back and reopening Srinath's thread still displayed the
  failed Lalitha turn from cached memory.
- **Repro:** Open a saved Srinath thread; leave Ask; switch to Lalitha; open Ask;
  submit a question; switch back to Srinath; reopen the original thread.
- **Evidence:** `android-profile-switch-thread-leak.png`,
  `android-ask-answer-guided.png`; Device + Source.
- **Recommended fix direction:** Key cached Ask state by kundli/profile, subscribe
  to active-profile changes, abort any stream, and atomically clear
  `activeThreadId`, `loadedThreadId`, messages, selected assistant, draft, and
  route keys. Do not reuse an implicit thread when a new question route has no
  explicit `thread` parameter.

### ASK-003 - A new Ask Home question can continue an old thread silently

- **Priority:** P1
- **Gap type:** Thread routing / false history
- **Route:** `/m/ask` -> `/m/ask/answer?q=...&pending=1`
- **Component/source:** `ask-home.component.ts:165-172`,
  `ask-answer.component.ts:403-416`
- **Expected:** Ask Home starts a new thread unless the user explicitly chooses to
  continue an existing conversation.
- **Actual:** Ask Home sends no thread id, but the cached Answer component replaces
  the missing URL value with `activeThreadId`, appending the question to whichever
  thread was previously active. The home draft also remains populated after send
  and profile changes.
- **Repro:** Open any saved thread; return to Ask Home; submit a different question.
  The constructor resolves the old active thread even though the route carries no
  `thread`.
- **Evidence:** Same device sequence as ASK-002; Source.
- **Recommended fix direction:** Make “new conversation” explicit in navigation
  state and clear the home draft only after successful navigation. A thread may be
  continued only when its id is explicit and belongs to the active kundli.

### ASK-004 - Topic chips are decorative at the backend boundary

- **Priority:** P1
- **Gap type:** Data wiring / intent routing
- **Route:** `/m/ask`
- **Component/source:** `ask-home.component.ts:154-172`,
  `ask-answer.component.ts:401-416,622-629`, `ui/src/app/core/ask.service.ts:64-90`
- **Expected:** Selecting Work, Marriage, Money, Child, or Health scopes an
  ambiguous question as the UI and code comments promise.
- **Actual:** Ask Home adds `topic` to the URL. Ask Answer never reads it and
  `AskRequest`/`AskService.stream()` has no topic field. The router sees only the
  question text.
- **Repro:** Select a topic; submit ambiguous text; inspect the outgoing stream
  payload or follow the source path.
- **Evidence:** Source.
- **Recommended fix direction:** Map topic ids to reviewed taxonomy domain
  overrides at the Answer boundary, include the chosen scope visibly in the
  question/answer UI, and cover it with route and backend tests.

### ASK-005 - Gentle/direct tone does not affect generated answers

- **Priority:** P1
- **Gap type:** Preference persistence / false product behavior
- **Route:** `/m/settings/mode`, `/m/ask/answer`
- **Component/source:** `ui/src/app/core/preferences.service.ts`,
  `ui/src/app/core/ask.service.ts:64-90`, `astrospace/api/ask_routes.py:42-69`
- **Expected:** “Be gentle” and “Be direct” alter the delivery of difficult Ask
  responses while retaining the same safety policy.
- **Actual:** The setting persists and changes settings copy, but neither tone nor
  experience mode is included in `AskRequest` or loaded server-side. Existing
  readings are only re-presented by a different client template.
- **Repro:** Switch the same profile between gentle and direct; inspect identical
  backend request fields.
- **Evidence:** Browser + Source.
- **Recommended fix direction:** Add explicit persona/tone fields to a versioned
  Ask request or load them server-side from user preferences. Treat tone as a
  presentation constraint after deterministic reasoning, and add snapshot tests
  proving meaning is stable while delivery changes.

### ASK-006 - New turns and Stop Streaming are not brought into view

- **Priority:** P1
- **Gap type:** Streaming interaction / user control
- **Route:** `/m/ask/answer`
- **Component/source:** `ask-answer.component.html`,
  `ask-answer.component.ts:577-617,843-851`
- **Expected:** Submitting a follow-up scrolls the conversation to the new user
  turn and working card. Stop Streaming remains immediately reachable.
- **Actual:** On Android, a follow-up appended below a long answer without moving
  the scroll position. UIAutomator reported the Stop control at `[0,0][0,0]`
  until the page was manually scrolled. The fixed composer remained visible, but
  the actual new turn/control did not.
- **Repro:** Open a long saved answer; tap a follow-up chip; try to stop without
  manually finding the newest turn.
- **Evidence:** `android-ask-answer-balanced-bottom.png`; Device.
- **Recommended fix direction:** Maintain an explicit conversation scroll
  container and anchor. On send/status change, scroll the latest turn into view
  unless the user has deliberately scrolled away; keep Stop as a composer-level
  control while streaming.

### ASK-007 - Streaming status is rendered up to three times

- **Priority:** P2
- **Gap type:** Loading-state duplication
- **Route:** `/m/ask/answer`
- **Component/source:** `ask-answer.component.html`,
  `ask-answer.component.ts:577-617,632-646`
- **Expected:** One calm, progressive status indicator.
- **Actual:** Android displayed the same status in the assistant card body, card
  summary line, and a separate status below Stop Streaming.
- **Repro:** Submit a new question and observe the first two SSE status stages.
- **Evidence:** `android-ask-answer-balanced.png`; Device.
- **Recommended fix direction:** Give status one owner. The message card should
  render stage progression; remove duplicate global/status-summary instances.

### ASK-008 - Long readings are dense, repetitive, and leak markdown

- **Priority:** P2
- **Gap type:** Response structure / readability
- **Route:** `/m/ask/answer`
- **Component/source:** `ask-answer.component.html`, structured response contract
- **Expected:** Acknowledgment, interpretation, summary, actions, evidence, and
  supports are visually distinct; long interpretation text has meaningful
  paragraphs or bullets; no markdown tokens are visible.
- **Actual:** Balanced and Practitioner readings show very long single paragraphs.
  The same Saturn/dasha explanation is repeated in “Why this answer?”. A persisted
  marriage answer visibly contains `**Your Favourability Window:**` and bold date
  markers because structured fields are interpolated as plain text.
- **Repro:** Open the marriage history thread in Balanced or Practitioner.
- **Evidence:** `ask-answer-balanced-375x812.jpg`,
  `android-ask-answer-balanced-complete.png`; Browser + Device.
- **Recommended fix direction:** Tighten the structured schema so interpretation
  supports paragraphs and optional bullets, reject markdown tokens in verifier
  output, and render evidence as supporting facts rather than repeating prose.

### ASK-009 - Clarification offers every live domain, not the actual ambiguity

- **Priority:** P2
- **Gap type:** Clarification UX / routing transparency
- **Route:** `/m/ask/answer`
- **Component/source:** `ask-answer.component.ts:636-649,943-950`, orchestrator
  clarification envelope
- **Expected:** “Career or marriage?” for a career-versus-marriage ambiguity, with
  human labels and one clear choice.
- **Actual:** The UI says “Try asking about career or children or foreign or health
  or marriage or personality or wealth” and renders every enabled domain in raw
  lowercase. After a choice, the old clarification and repeated user question
  remain above the new result.
- **Repro:** Ask `Should I change jobs or get married this year?`; choose Career.
- **Evidence:** `ask-clarification-375x812.jpg`; Browser.
- **Recommended fix direction:** Return only tied/credible options with display
  labels and short descriptions. Treat the selected clarification as resolving
  the pending turn rather than duplicating the same user bubble.

### ASK-010 - History's ACTIVE badge is positional, not real state

- **Priority:** P2
- **Gap type:** False status
- **Route:** `/m/ask/history`
- **Component/source:** `ask-history.component.html:25-51`
- **Expected:** ACTIVE identifies the currently open/in-progress thread, or is not
  shown if no such concept exists.
- **Actual:** The first row is always ACTIVE. Archiving it immediately promotes the
  next oldest row to ACTIVE without opening it.
- **Repro:** Open History; note ACTIVE; archive the first row.
- **Evidence:** `android-ask-history.png`; Device + Source.
- **Recommended fix direction:** Remove the badge or derive it from an explicit
  active thread id/status returned by the backend.

### ASK-011 - Archive is immediate and has no archive, restore, or delete path

- **Priority:** P2
- **Gap type:** Conversation lifecycle
- **Route:** `/m/ask/history`, `/m/ask/answer`
- **Component/source:** `ask-history.component.ts:75-88`,
  `ask-answer.component.ts:900-912`, `crud_mobile.py:112-116,154-160`
- **Expected:** Swipe exposes the promised Archive/Delete actions; archive is
  recoverable or viewable; destructive loss requires confirmation.
- **Actual:** Swipe right exposes only Archive. One tap removes the thread from all
  user-accessible lists. The API always filters archived rows and has no list,
  unarchive, or delete endpoint. The Answer header archives without confirmation.
- **Repro:** Swipe a history card right; tap Archive; search for an archived view.
- **Evidence:** `android-ask-history-swipe.png`; Device + Source.
- **Recommended fix direction:** Decide the lifecycle contract. At minimum add an
  Archived view and restore/undo. Add delete only with confirmation and a clear
  retention policy.

### ASK-012 - History thread back navigation loses the user's place

- **Priority:** P2
- **Gap type:** Navigation
- **Route:** `/m/ask/history` -> `/m/ask/answer`
- **Component/source:** `ask-answer.component.html:2`
- **Expected:** The in-app back control returns to History when History was the
  entry point.
- **Actual:** It is hardcoded to `/m/ask`, so it always returns to Ask Home.
- **Repro:** History -> open thread -> tap the top-left back button.
- **Evidence:** Device.
- **Recommended fix direction:** Use navigation origin/state or browser history
  with a safe Ask Home fallback.

### ASK-013 - Voice Ask is a fixed demo transcript

- **Priority:** P2
- **Gap type:** Incomplete native feature
- **Route:** `/m/ask`
- **Component/source:** `ask-home.component.ts:112-143`,
  `voice-listening.component.ts`
- **Expected:** Microphone permission, real speech recognition, live transcript,
  cancel/confirm, and clear unsupported/error states.
- **Actual:** Tapping microphone opens the listening screen with the hardcoded
  sentence `Is this a good time to change my job`; no speech recognizer is wired.
- **Repro:** Tap the Ask microphone and confirm the displayed transcript.
- **Evidence:** Source; visible interaction was inspected but audio capture was not
  falsely marked verified.
- **Recommended fix direction:** Hide or label the feature unavailable until a
  native/web speech adapter exists; then add permission, timeout, no-speech,
  partial transcript, and cancellation tests.

### ASK-014 - Practitioner scope does not identify the active profile

- **Priority:** P2
- **Gap type:** Context transparency
- **Route:** `/m/ask/answer` in Practitioner mode
- **Component/source:** `ask-answer.component.ts:349-363`
- **Expected:** Practitioner context names the exact profile and evidence scope so
  the reader can verify whose chart is being interpreted.
- **Actual:** It renders `Profile: Active`, which is especially unsafe around
  profile switching.
- **Repro:** Open any practitioner answer.
- **Evidence:** `ask-answer-practitioner-375x812.jpg`; Browser + Source.
- **Recommended fix direction:** Display the active profile name and immutable
  profile id/date context used for that saved answer, not only current UI state.

### ASK-015 - Answer generation has long silent latency

- **Priority:** P2
- **Gap type:** Performance / perceived latency
- **Route:** `/m/ask/answer`
- **Component/source:** SSE orchestrator and Answer status UI
- **Expected:** Useful staged feedback and a reasonable response budget; sections
  appear progressively where safe.
- **Actual:** The tested Android career answer stayed in specialist interpretation
  for more than 16 seconds and completed at roughly 36 seconds. Only status text
  changed; no answer section appeared progressively.
- **Repro:** Submit the balanced Saturn/work suggested question on the installed
  app and time first useful content and completion.
- **Evidence:** Device observation; approximate timing, not instrumentation.
- **Recommended fix direction:** Instrument route, context assembly, provider first
  token, verification, persistence, and total latency. Set budgets and stream
  validated sections/events instead of one opaque wait.

### ASK-016 - Answer typography hierarchy is internally inconsistent

- **Priority:** P3
- **Gap type:** Typography / accessibility polish
- **Route:** `/m/ask/answer`
- **Component/source:** `ask-answer.component.scss`
- **Expected:** Section headings are visibly stronger than body copy and controls
  retain a consistent minimum readable size.
- **Actual:** At 375x812, the main interpretation is 16px/26.4px, while the
  `What to do` H2 computes to 11px/13.2px. Header/action controls are 13px. The
  family is consistently Inter for functional copy, but hierarchy is not.
- **Repro:** Inspect computed styles on a completed Balanced answer.
- **Evidence:** Browser computed-style capture.
- **Recommended fix direction:** Apply the mobile type tokens to semantic roles;
  do not style an H2 smaller than body text. Preserve Playfair only for approved
  editorial emphasis, not functional labels.

### ASK-017 - Safety copy still uses the retired AstroSpace name

- **Priority:** P3
- **Gap type:** Brand consistency
- **Route:** Safety refer-out
- **Component/source:** `astrospace/agents/safety.py:267-271`
- **Expected:** User-facing copy says Siddha.
- **Actual:** Death refer-out says `AstroSpace does not predict...`.
- **Repro:** Inspect deterministic safety response.
- **Evidence:** Source and failed persistence traceback.
- **Recommended fix direction:** Centralize the product name in user-facing copy
  and cover renamed strings with a repository-wide brand test.

## Verified Strengths

- A saved thread opened from History does not re-trigger generation.
- Same-profile follow-ups append to the same persisted thread and History message
  counts update.
- Guided, Balanced, and Practitioner templates visibly differ in evidence depth.
- Domain-not-ready and generation-failed terminal bubbles render without a stuck
  spinner.
- Copy Answer produced 4,107 characters with markdown control tokens removed.
- Edit places the selected user question into the follow-up composer.
- Light and dark answer views showed no document-level horizontal overflow at
  375x812.
- Frontend unit suite passed: 30/30.
- Focused backend suites passed: 533/533. This is useful but does not cover the
  deployed Postgres constraint mismatch in ASK-001.
- Production Angular build completed successfully.

## State And Test Gaps

- Offline behavior was not fault-injected and is not marked verified.
- `verification_failed` and `fatal_error` have frontend consumers and unit/source
  coverage, but this pass did not deliberately corrupt a model response or sever
  the live network to produce those exact states on-device.
- iOS was not connected for this sweep.
- Native Android speech recognition cannot be tested because no recognizer is
  implemented.
- There is no automated mobile Ask E2E suite covering profile switching, history,
  swipe/archive, back behavior, or production-database safety persistence.

## Prioritized Remediation Backlog

1. **P0:** Align safety refer-out values with Postgres via migration and add
   real-Postgres contract tests for all four kinds.
2. **P1:** Make Ask state profile-scoped; clear/abort cached state on profile
   change; require an explicit thread id to continue a conversation.
3. **P1:** Wire topic scope and tone/persona into the backend contract and show
   the exact profile/context used by saved answers.
4. **P1:** Anchor new turns and expose Stop at the composer level.
5. **P2:** Redesign archive lifecycle with Archived + Restore/Undo, then decide
   whether permanent delete belongs in v1.
6. **P2:** Replace duplicated streaming status with one staged progress surface
   and add latency instrumentation.
7. **P2:** Enforce structured paragraph/bullet output, reject markdown leakage,
   and remove evidence repetition.
8. **P2:** Return only real ambiguity options with user-facing labels.
9. **P2:** Implement actual speech recognition or remove the active microphone
   affordance until it exists.
10. **P3:** Normalize Answer typography tokens and finish Siddha brand cleanup.

## Screenshot Inventory

All files are under `docs/ask_regression_evidence/2026-08-10/`.

- `ask-home-practitioner-375x812.jpg`
- `ask-home-balanced-light-375x812.jpg`
- `ask-answer-guided-375x812.jpg`
- `ask-answer-balanced-375x812.jpg`
- `ask-answer-balanced-light-375x812.jpg`
- `ask-answer-practitioner-375x812.jpg`
- `ask-clarification-375x812.jpg`
- `ask-domain-not-ready-375x812.jpg`
- `ask-safety-persistence-failure-375x812.jpg`
- `android-ask-home-balanced.png`
- `android-ask-answer-balanced.png`
- `android-ask-answer-balanced-complete.png`
- `android-ask-answer-balanced-scroll.png`
- `android-ask-answer-balanced-bottom.png`
- `android-ask-answer-guided.png`
- `android-ask-history.png`
- `android-ask-history-swipe.png`
- `android-profile-switcher.png`
- `android-profile-switch-thread-leak.png`
