# Mobile Ask Thread UX Acceptance Criteria

Date: 2026-08-08  
Owner: Codex  
Status: working acceptance criteria for the mobile Ask thread/chat experience

## Purpose

This document defines the mobile Ask thread UX bar. It exists because Ask has
already had user-visible regressions around history, follow-ups, re-opening old
threads, streaming, and chat controls. Future Ask backend work should not be
considered complete unless the mobile thread experience below still passes.

## Scope

Covered screens and services:

- `ui/src/app/features/mobile/ask/ask-home.component.*`
- `ui/src/app/features/mobile/ask/ask-answer.component.*`
- `ui/src/app/features/mobile/ask/ask-history.component.*`
- `ui/src/app/features/mobile/ask/mobile-ask-thread.service.ts`
- `ui/src/app/features/mobile/ask/mobile-ask-state.service.ts`
- `ui/src/app/core/ask.service.ts`
- `ui/src/app/core/models.ts`

## Core Rules

### 1. Opening An Existing Thread Must Never Re-Ask

Acceptance criteria:

- Opening a thread from Ask History loads persisted messages with
  `GET /api/v1/ask/threads/{threadId}`.
- It must not call `POST /api/v1/ask/{kundliId}/stream`.
- It must not resend the old question.
- It must not show a streaming state unless the user submits a new follow-up.
- Persisted structured answers render from `evidence.structured_reading`.
- Old/pre-v2 answers with missing or unparsable structured evidence render
  plainly, not as an error.

Current implementation notes:

- `ask-answer.component.ts` uses `pending=1` as the only route signal that
  starts a stream.
- `thread` without `pending=1` calls `loadThread()`.
- `lastRouteKey` prevents re-streaming after the URL is replaced with the
  saved thread id.

### 2. Follow-Ups Stay In The Same Thread

Acceptance criteria:

- Follow-up composer submissions include the active `thread_id`.
- Backend appends the new user and assistant messages to the same thread.
- UI shows the whole conversation, not only the newest turn.
- Follow-ups should not create a new Ask History card unless there was no
  active thread.
- Pronoun follow-ups such as "Which month is strongest for this?" should
  continue the established backend domain when the backend supports it.

Current implementation notes:

- `askAgain()` navigates to the same answer route with `thread` and
  `pending=1`.
- `startStream()` loads the existing thread first when needed, then appends
  the local follow-up pair.

### 3. Clarification Choices Resolve Once

Acceptance criteria:

- A `clarification_needed` answer renders clear option chips.
- Tapping an option must send the original question plus `domain_override`.
- It must not wrap the question in extra prose.
- It must not trigger the same clarification loop repeatedly.
- The resulting answer must be appended to the same thread when a thread
  exists.

Current implementation notes:

- `askClarification()` uses `firstUser()` and `forceDomain`.
- The backend receives `domain_override`.

### 4. Streaming Must Always Reach A Terminal UI State

Acceptance criteria:

- While streaming, the UI shows current backend status.
- Stop Streaming aborts the request and removes loading affordances.
- `done.status = answered` renders the structured answer.
- `done.status = generation_failed` renders a grounded failure bubble.
- `done.status = verification_failed` renders a grounded failure bubble.
- Future `fatal_error` SSE events must render a terminal error bubble rather
  than leaving the message in a spinner state.
- Network/HTTP errors show an alert/state and stop the local assistant
  loading bubble.

Current implementation notes:

- `AbortController` powers Stop Streaming.
- `generation_failed` and `verification_failed` are already handled.
- `fatal_error` handling is now expected by the frontend contract even before
  the backend event ships.

### 5. Ask History Must Reflect Saved Conversations

Acceptance criteria:

- Ask History lists server-saved threads for the active profile.
- Empty state appears only when the server returns no threads.
- Fetch errors render a retry state.
- Opening a card navigates by `thread`, not by `q`.
- Archiving removes the row locally after the backend confirms.
- Swipe right reveals Archive; swipe left hides it.

Current implementation notes:

- `ask-history.component.ts` uses `MobileAskThreadService.list()`.
- `MobileAskThreadService.archive()` calls the archive endpoint.

### 6. Thread Actions

Acceptance criteria:

- Copy answer copies normalized answer text without markdown control tokens.
- Edit question puts the selected user message into the composer.
- Stop Streaming is visible only during streaming.
- Archive is available for saved threads.
- Delete is not yet implemented; until backend delete exists, the supported
  destructive action is Archive.
- Future delete support must require a confirmation or recoverable archive
  path, not a silent destructive tap.

Current implementation notes:

- `copyAnswer()`, `editQuestion()`, `stopStreaming()`, and `archiveThread()`
  exist on the answer screen.
- Ask History supports archive by swipe action.

### 7. Structured Answer Rendering

Acceptance criteria:

- `acknowledgment` renders as the user's intent being understood.
- `interpretation` renders as the main guidance.
- `summary_and_assurance` renders distinctly from the main guidance.
- `guidance.practical_actions` render under a next-steps section.
- `guidance.remedies` render as traditional supports.
- Technical basis and references are available through Why This.
- Raw markdown headings/bold markers must not leak into the visible answer.
- Long text must scroll naturally and never be clipped behind the composer.

Current implementation notes:

- The old regex section parser is no longer the primary path.
- Persisted structured evidence is reconstructed by `readingFromEvidence()`.

### 8. Persona And Future Multi-Domain Behavior

Acceptance criteria:

- Guided mode should keep technical depth collapsed by default.
- Balanced mode should show plain guidance and make evidence available.
- Practitioner mode should surface stronger provenance and convention context.
- Future multi-domain synthesis must not pretend to be one domain.
- Future synthesis badge should render as `ANSWER · CAREER + MARRIAGE` using
  `evidence.domains` / `evidence.answer_type`, once backend schema ships.

Current implementation notes:

- Single-domain badge rendering exists today.
- Multi-domain schema is not shipped yet.

## Minimum Regression Sweep

Before an Ask release/build is called good:

1. Ask a new career question and wait for answer.
2. Open Ask History and verify the question appears.
3. Open the old thread and verify it does not stream again.
4. Ask a follow-up and verify it appends to the same thread.
5. Reopen the thread again and verify the full conversation appears.
6. Trigger or mock `clarification_needed`; tap a chip and verify no loop.
7. Trigger or mock `domain_not_ready`.
8. Trigger or mock `generation_failed`, `verification_failed`, and
   `fatal_error`.
9. Test Stop Streaming mid-answer.
10. Test Copy, Edit, Archive, and History swipe Archive.

## Open Product Questions

- Whether delete should be a real destructive action or whether Archive is
  the only user-facing removal path for v1.
- How much practitioner provenance should be in the main answer versus the
  Why This sheet.
- Whether multi-domain synthesis should use a combined answer card or
  separate per-domain cards with a final synthesis card.

