# Siddha Practitioner Upgrade Epics and User Stories — 2026-08-06

Purpose: define the next Practitioner-mode delivery slice without diluting astrology depth. This document splits backend astrology ownership from mobile UX ownership and gives both agents a common contract.

## Product Principle

Backend owns astrological truth. Mobile owns comprehension, navigation, visual hierarchy, and interaction. The UI must not invent astrology meaning from raw numbers except for formatting, grouping, and display labels. If a screen needs reasoning, source status, caution wording, or interpretation, the backend contract must provide it.

## Ownership Split

### Agent A — Astrology Contract, Engine, KB, API

Primary ownership:
- `astrospace/core/vedic/**`
- `astrospace/knowledge/vedic_rules/**`
- `astrospace/api/*vedic*`, `remedy_routes.py`, `muhurta_routes.py`
- backend tests and source validation docs

Responsibilities:
- Calculation correctness.
- Interpretation payloads.
- Source/provenance metadata.
- Convention disclosure.
- Safety framing.
- API contracts consumed by mobile.

### Agent B — Mobile Practitioner UX and Integration

Primary ownership:
- `ui/src/app/features/mobile/**`
- `ui/src/app/shell/mobile-nav.ts`
- `ui/src/app/core/*` mobile-facing services
- mobile screenshots and native/browser QA

Responsibilities:
- Practitioner navigation and flow.
- Figma-consistent mobile UI.
- Rendering backend contracts faithfully.
- Loading/empty/error/offline states.
- Contextual Ask wiring.
- Haptics/reminder/audio UX wiring.

## Epic PR-001 — Practitioner Navigation Contract

Goal: make Practitioner mode feel like a coherent astrologer workbench, not a rearranged Balanced app.

### US-PR-001 — Practitioner Footer Contract

As a Practitioner user, I want the footer to expose only the primary workbench destinations so I can move predictably between daily context, chart work, calendar, and more tools.

Acceptance criteria:
- Practitioner footer does not show Ask as a primary tab.
- Calendar is restored to a primary footer position.
- Transits/Gochara are reachable through Yantra/Chart, not competing with Calendar as a footer tab.
- Deep specialist pages either hide footer or keep the correct parent tab active.
- No route causes the selected footer item to change to “More” unless it is actually a More destination.

Owner: Agent B

Dependencies: none

Routes:
- `/m/today`
- `/m/chart`
- `/m/calendar`
- `/m/settings`
- `/m/transits`
- `/m/transits/full`

### US-PR-002 — Contextual Practitioner Ask

As a Practitioner user, I want Ask to be invoked from the chart object I am studying, so questions carry context instead of starting as generic chat.

Acceptance criteria:
- Ask is available as contextual CTA from Remedies, Yogas, Dashas, Gochara, Strengths, Reference, and Readings.
- Submitted Ask opens a no-footer chat experience.
- Prefill/context includes route, profile id, object type, object id, and evidence ids when available.
- If AI is unavailable, the fallback screen says agents are under construction and preserves the user question.

Owner: Agent B, with backend contract support from Agent A if context schema changes.

## Epic PR-002 — Remedies and Practice System

Goal: remedies become profile-specific traditional practices with reasoning, safe framing, streaks, reminders, and mantra audio support.

### US-PR-003 — Backend Remedy Recommendation Contract

As a mobile client, I need a structured remedy recommendation API so every remedy card can explain why it appears and what it is based on.

Acceptance criteria:
- API returns recommendation groups keyed by stable `recommendation_id`.
- Each group includes:
  - `trigger.kind`: dasha, dosha, dignity, combustion, transit, or other supported type.
  - `trigger.planet` or relevant chart object.
  - `reason_short`.
  - `reason_practitioner`.
  - `evidence`.
  - `source_status`.
  - `tradition_source`.
  - `convention_dependent`.
  - `safety_note`.
  - `priority`.
- Practices include stable `practice_slug`, `remedy_type`, `title`, `instructions`, `cadence`, `target_count`, optional cost flag, preferred weekday, and optional audio metadata.
- Manglik is not emitted as a generic remedy recommendation unless explicitly requested or scoped to compatibility/dosha detail.
- Backend tests cover active dasha, active antardasha, debilitated planet, combust planet, no-remedy profile, and Manglik cancellation behavior.

Owner: Agent A

Routes/API:
- `GET /api/v1/remedies/{kundli_id}`
- `GET /api/v1/remedies/catalog`

### US-PR-004 — Mobile Remedy Cards From Backend

As a user, I want remedies to match my chart and active periods so I trust the practice I am starting.

Acceptance criteria:
- `/m/remedies` consumes backend remedy recommendations.
- No local synthesis from only `dashas()` and `yogasDoshas()` remains.
- Each card shows trigger, reason, practice options, source/safety note, and action.
- Start streak opens the exact selected practice.
- Empty state says no specific practice is currently indicated, without inventing fear.
- Error state has retry and does not show stale wrong remedies as current.

Owner: Agent B

Depends on: US-PR-003

### US-PR-005 — Mantra Tracker Auto and Manual Modes

As a user doing a mantra practice, I want either guided playback or manual counting so the streak reflects what I actually practiced.

Acceptance criteria:
- Tracker route receives selected `kundli_id`, `recommendation_id`, and `practice_slug`.
- Manual mode supports tap count up to target count, usually 108.
- Auto mode plays or loops the associated audio until the target count completes.
- Audio controls include play/pause, restart, count progress, and mode switch.
- Haptics can mark count milestones if haptics are enabled.
- Completion updates streak for that exact practice only.
- Reminder CTA links to notification/remedy reminder settings.

Owner: Agent B

Depends on: US-PR-003

### US-PR-006 — Practice Reminder Contract

As a user, I want remedy reminders to be optional and tied to practices I chose, not generic notifications.

Acceptance criteria:
- Reminder settings can be scoped to selected practice.
- Reminder UI shows cadence, weekday, and notification permission state.
- If native push is unavailable, the UI says preferences are local only.
- No notification toggle appears as a dummy control.

Owner: Agent B for mobile; Agent A only if backend persistence is added.

## Epic PR-003 — Muhurtha Workbench

Goal: muhurtha becomes a purpose-based date/range search with transparent scoring.

### US-PR-007 — Muhurtha Goal and Range Contract

As a user planning an action, I want to choose a purpose and date/range so the windows are computed for the actual decision.

Acceptance criteria:
- Frontend goal ids match backend slugs or are mapped in one explicit table.
- `Pick dates` opens native date/range inputs.
- User can choose single date, this week, this month, or custom range.
- Date range is bounded to backend max range.
- Current/panchanga location is shown before searching.

Owner: Agent B

Backend support: Agent A if goal catalog changes.

### US-PR-008 — Muhurtha Result Explanation

As a Practitioner, I want to see why each muhurtha window ranked where it did.

Acceptance criteria:
- Result card shows score, label, date/time, location, goal, and timezone.
- Result details show positive and negative factors:
  - vara
  - nakshatra
  - tithi
  - tarabala
  - chandrabala
  - ghatak
  - avoid-window trimming
- Empty state distinguishes no usable window from API failure.
- Save/remind CTAs are either wired or visibly unavailable with honest copy.

Owner: Agent A for payload completeness; Agent B for UI.

## Epic PR-004 — Chart and Varga Unified Workbench

Goal: D1 and varga charts are one coherent workbench with consistent chart style and planet detail behavior.

### US-PR-009 — Unified Chart Selector

As a Practitioner, I want D1 and divisional charts in one chart workbench so I do not have to hunt for vargas.

Acceptance criteria:
- `/m/chart/full` can show D1 and supported vargas via selector.
- `/m/chart/vargas` lands in the same workbench state with varga selector open or selected.
- Chart style preference applies to every selected chart.
- Planet taps work in every chart style and every varga.
- Planet details identify chart name, sign, house where applicable, role, dignity, and source/convention.

Owner: Agent B

Depends on: existing varga payloads.

### US-PR-010 — Chart Workbench Visual QA

As a Practitioner, I need charts large and legible without distorted geometry.

Acceptance criteria:
- 375x812 light/dark screenshots show D1, D9, D10 in East/South/North styles.
- Labels stay inside chart bounds.
- Markers are individually tappable.
- No translucent overlays hide chart details.
- Text size is increased only through reusable chart tokens, not screen-specific hacks.

Owner: Agent B

## Epic PR-005 — Jaimini Validation and Presentation

Goal: Jaimini should be trustworthy, convention-aware, and test-backed before it becomes prominent.

### US-PR-011 — Jaimini Calculation Test Vectors

As a Practitioner, I need Jaimini output to disclose its conventions and match known examples.

Acceptance criteria:
- Tests cover seven-karaka and eight-karaka schemes.
- Tests cover Rahu reverse degree.
- Tests cover arc-second tie handling.
- Tests cover A1/UL arudha exception.
- Tests document Scorpio/Aquarius lord convention and pending stronger-lord variant.
- At least three known chart examples are documented with expected karakas/padas.

Owner: Agent A

### US-PR-012 — Jaimini UI Convention Disclosure

As a Practitioner, I want to see how Jaimini values were calculated so I can judge whether they match my tradition.

Acceptance criteria:
- UI shows selected scheme, Rahu handling, arudha exception rule, and dual-lordship caveat.
- Jaimini section is directly reachable from Yantra.
- If the Jaimini route lands inside Strengths, the Jaimini tab is selected directly.
- Calculation working is visible enough for Practitioner mode.

Owner: Agent B

Depends on: US-PR-011 for confidence.

## Epic PR-006 — Yogas and Doshas Knowledge Depth

Goal: Yogas/Doshas must explain rule, result, strength, source, and practical meaning without repeating generic content.

### US-PR-013 — Yoga/Dosha KB Expansion

As the app, I need each rule to carry enough explanation to support Practitioner and Guided modes differently.

Acceptance criteria:
- Every implemented yoga/dosha rule has:
  - rule id
  - classical name
  - category
  - source status
  - implementation status
  - exact trigger description
  - practitioner explanation
  - lay explanation
  - strength rubric
  - caveats/cancellations where relevant
  - source references
- Mild/moderate/strong tags are computed or justified by explicit rubric.
- Rules lacking sources are marked pending and shown with lower confidence.

Owner: Agent A

### US-PR-014 — Yoga Learning Sheets

As a user, I want “Learn this Yoga” to explain the selected yoga, not a generic yoga.

Acceptance criteria:
- Sheet always receives selected rule id.
- Sheet title, trigger, explanation, strength tag, and source match selected yoga/dosha.
- Gajakesari content only appears for Gajakesari.
- Tags such as mild/moderate/strong are explained inline.
- Dosha sheets use “flag, not verdict” framing.

Owner: Agent B

Depends on: US-PR-013

## Epic PR-007 — Strength, Ashtakavarga, and Advanced Interpretation

Goal: advanced metrics should help a Practitioner read the chart rather than stare at numbers.

### US-PR-015 — Strength Interpretation Payload

As a mobile client, I need strength interpretation fields so the UI can explain what Shadbala and related metrics imply.

Acceptance criteria:
- Payload identifies strongest and weakest planets with reason.
- Each planet includes score, required minimum, sufficiency, and interpretive consequence.
- Payload distinguishes raw measurement from interpretation.
- Source/convention fields are included.

Owner: Agent A

### US-PR-016 — Ashtakavarga Interpretation Payload

As a Practitioner, I want SAV/BAV to tell me where support exists and how to use it with transits.

Acceptance criteria:
- SAV includes total, strongest houses/signs, weakest houses/signs, and interpretation.
- BAV includes per-planet strongest/weakest signs and interpretation.
- Payload explains bindu meaning without overclaiming prediction.
- Gochara/transit payload can reference AV support consistently.

Owner: Agent A

### US-PR-017 — Mobile Advanced Workbench

As a Practitioner, I want Shadbala, Ashtakavarga, and Jaimini presented as readable workbench sections.

Acceptance criteria:
- Tables use mobile-friendly rows, not cramped desktop tables.
- Charts/score bars support scanability.
- “What this means” is not repetitive filler.
- Source/convention badges appear on every advanced section.

Owner: Agent B

Depends on: US-PR-015 and US-PR-016.

## Epic PR-008 — Gochara, Dasha, and Yogini Integration

Goal: Transits/Gochara, Vimshottari, and Yogini should tell one timed story.

### US-PR-018 — Period and Transit Interpretation Bridge

As a Practitioner, I want to see how current gochara interacts with the active dasha and Yogini period.

Acceptance criteria:
- Active dasha stack includes Maha, Antar, Pratyantar, Sookshma, and Prana where backend supports them.
- Yogini is explained separately and not forced into Vimshottari language.
- Gochara cards reference active period lord where relevant.
- Interpretation states whether transit supports, pressures, or contradicts period themes.

Owner: Agent A for interpretation payload; Agent B for UI wiring.

### US-PR-019 — Move Gochara Into Yantra

As a Practitioner, I want Transits/Gochara inside the Yantra workbench so Calendar can remain the daily almanac.

Acceptance criteria:
- Yantra tile opens Gochara.
- Full Transits remains accessible from Gochara.
- Footer parent state is correct.
- Calendar footer opens Calendar, not transits.

Owner: Agent B

## Epic PR-009 — Practitioner Reference Workbench

Goal: Reference becomes a useful astrologer utility instead of flattened payload display.

### US-PR-020 — Typed Reference Renderers

As a Practitioner, I want reference data grouped by meaning so I can consult it during interpretation.

Acceptance criteria:
- Avkahada/Ghatak renderer is typed and grouped.
- Graha positions show planet, sign, degree, nakshatra/pada, dignity, motion, combustion, and house.
- Ashtakavarga tables show SAV/BAV grids and totals.
- Favourable points show colours, numbers, directions, stones, and related reasoning where backend provides it.
- No generic recursive JSON flattening is used for primary reference sections.

Owner: Agent B

Depends on: backend payload shape stability.

### US-PR-021 — Reference Search and Cross-Linking

As a Practitioner, I want to jump from chart objects to reference sections and back.

Acceptance criteria:
- Search indexes Reference sections.
- Chart/yoga/strength screens link to relevant Reference anchors.
- Reference pages provide back behavior to originating chart context where available.

Owner: Agent B

## Epic PR-010 — Practitioner QA and Release Gate

Goal: finish with evidence, not belief.

### US-PR-022 — Full Practitioner Sweep

As the product owner, I want every Practitioner route and CTA swept after implementation so regressions are caught before APK install.

Acceptance criteria:
- 375x812 screenshots for light and dark.
- Routes tested:
  - Today
  - Yantra/Chart
  - Chart full
  - Vargas
  - Periods
  - Yogas/Doshas
  - Strength/Jaimini/Ashtakavarga
  - Reference
  - Remedies
  - Mantra tracker
  - Muhurtha
  - Calendar
  - Gochara/Full Transits
  - Ask contextual flow
  - Settings relevant toggles
- Every footer tab, tile, CTA, sheet action, back button, and chip is tapped.
- Defects are recorded with priority, route, source file, repro, screenshot, and recommendation.

Owner: Agent B

## Cross-Agent Contract Rules

1. Do not hardcode astrology interpretations in mobile components.
2. Do not mark a screen “done” because it renders; it must satisfy its contract.
3. Do not bury convention-dependent details in prose only; expose structured fields.
4. Do not add fear-based remedy copy.
5. Do not present gemstones as required.
6. Do not expose medical, legal, death, lifespan, or financial certainty.
7. Do not replace source validation with generic internet summaries.
8. If backend lacks a field, add the contract first or show an honest pending state.

## Suggested Parallel Work Plan

### Sprint 1

Agent A:
- US-PR-003 Remedy contract.
- US-PR-011 Jaimini test-vector plan.
- US-PR-013 Yoga/Dosha KB schema.

Agent B:
- US-PR-001 Practitioner nav.
- US-PR-002 contextual Ask shell.
- US-PR-004 mobile remedies wire-ready UI.

### Sprint 2

Agent A:
- US-PR-015/016 Strength and Ashtakavarga interpretation payloads.
- US-PR-008 Muhurtha result factors audit.

Agent B:
- US-PR-005 mantra tracker modes.
- US-PR-007 Muhurtha date/range UI.
- US-PR-009 chart/varga unified workbench.

### Sprint 3

Agent A:
- US-PR-018 Dasha/Yogini/Gochara bridge.
- Complete Jaimini tests and convention payload.

Agent B:
- US-PR-012 Jaimini UI.
- US-PR-017 advanced workbench.
- US-PR-019 move Gochara into Yantra.
- US-PR-020/021 Reference workbench.

### Release Gate

Agent B:
- US-PR-022 full Practitioner sweep.

Agent A:
- Backend test suite and source validation summary.

Both:
- No open P0/P1.
- P2s triaged explicitly.

## Prompt for Other Agent

Use the prompt below to start the astrology/backend-focused agent.

```text
You are working in /Users/vikramaditya/Documents/agentic-astrospace on the Siddha mobile app.

Your role is Agent A: Astrology Contract, Engine, Knowledge Base, and API depth. Do not work on mobile UI unless a backend contract needs a tiny client type update. Another agent owns mobile UX and Angular integration.

Primary files you may need:
- astrospace/core/vedic/**
- astrospace/knowledge/vedic_rules/**
- astrospace/api/remedy_routes.py
- astrospace/api/muhurta_routes.py
- astrospace/api/vedic_routes.py
- tests/**
- docs/practitioner_mode_upgrade_audit_2026-08-06.md
- docs/practitioner_epics_user_stories_2026-08-06.md

Product principle:
Backend owns astrological truth. Mobile owns comprehension and display. Do not push raw technical numbers without interpretation metadata. Do not let the UI invent astrology meaning.

Critical safety rules:
- Remedies are traditional practice, not guarantees.
- Do not use fear-based copy.
- Do not present gemstones as required.
- Do not provide medical, legal, death/lifespan, or financial certainty.
- A dosha is a flag, not a verdict.
- Convention-dependent calculations must disclose the convention.

Your initial scope:
1. Read docs/practitioner_mode_upgrade_audit_2026-08-06.md and docs/practitioner_epics_user_stories_2026-08-06.md.
2. Implement or refine the backend remedy recommendation contract:
   - GET /api/v1/remedies/{kundli_id}
   - stable recommendation ids
   - trigger object
   - reason_short
   - reason_practitioner
   - evidence
   - source_status
   - tradition_source
   - convention_dependent
   - safety_note
   - priority
   - practices with practice_slug, type, title, instructions, cadence, target_count, preferred day, optional cost, and optional audio metadata.
   - Manglik must not appear as a generic remedy card unless explicitly scoped to compatibility/dosha detail.
3. Add backend tests for remedies:
   - active mahadasha
   - active antardasha
   - debilitated planet
   - combust planet
   - no-remedy profile
   - Manglik cancellation behavior.
4. Start Jaimini validation:
   - document seven/eight karaka scheme
   - Rahu reverse degree
   - arc-second tie behavior
   - A1/UL arudha exception
   - Scorpio/Aquarius dual-lordship caveat
   - add test vectors before expanding UI-facing claims.
5. Expand Yogas/Doshas KB schema so every implemented rule can provide:
   - rule id
   - classical name
   - category
   - source status
   - implementation status
   - exact trigger
   - practitioner explanation
   - lay explanation
   - strength rubric
   - caveats/cancellations
   - source references.

Important:
- Be evidence-based. Use primary/trusted astrology sources where possible and cite them in docs or source metadata.
- Do not fabricate classical authority.
- If a rule is simplified or pending verification, mark it explicitly.
- Preserve unrelated dirty worktree changes.
- Do not overwrite another agent’s UI work.
- Run targeted backend tests and report exactly what passed/failed.

Deliverables:
- Backend/API changes with tests.
- Updated docs section summarizing contracts and source assumptions.
- Clear list of fields the mobile agent can consume.
```
