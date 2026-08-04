# AstroSpace Mobile UI Regression Audit

Audit date: 2026-07-29

Branch: `feat/mobile-app-schema-and-designs`

Scope: `/m/*` routes, `ui/src/app/features/mobile/`, mobile-facing core services, and connected Android native behavior.

Live backend used where relevant: `https://agentic-astrospace-cwuqybpnzq-el.a.run.app`

Evidence folder: `docs/mobile-ui-regression-screenshots-2026-07-29/`

## Executive Summary

The mobile app is usable enough to enter authenticated native Today/Ask/Chart/Settings flows, but it is not regression-clean. The worst defects are not cosmetic: Ask fails against the live backend and hides the error, Calendar fails on native live data, Practitioner navigation generates a bad Periods URL, and Today's Practitioner technical cards overflow their bounds. Chart rendering has improved enough that style switching and exact planet-marker taps work, but chart labels still sit on/outside chart grid boundaries and the hub-to-full-chart visible CTA missed a real native tap.

Auth basics are stronger than the rest: unauthenticated protected routes redirect to `/m/auth`, password sign-in shows a real invalid-credential error, Google launches the real Google OAuth page, and native sign-out returns to `/m/start`. I did not complete Google callback because that requires account interaction.

No fixes were implemented. One new report file was added.

## Reproduction Environment

Local repo: `/Users/vikramaditya/Documents/agentic-astrospace`

Local preview: Angular dev server on `http://127.0.0.1:60323/`

Browser target: Playwright Chromium, mobile viewport `375 x 812`, light and dark media modes.

Backend: Playwright route forwarding to live Cloud Run for browser tests. Native app used its installed live configuration.

Android device: Samsung `SM_S938W`, serial `R5CY11Y5W7L`, WebView `Chrome/150.0.7871.124`, CSS viewport `411 x 891`, DPR `3.5`. Device system night mode reported `yes`.

Also visible but not used for primary native evidence: Android emulator `emulator-5554`.

Build/run verification: local Angular dev server built and served successfully. I did not run the full test suite because this was a manual live regression audit, not a unit/e2e CI pass.

## Route Inventory Tested

Browser, unauthenticated at 375 x 812:

`/m/start`, `/m/auth`, `/m/auth?mode=register`, `/m/today` redirect, `/m/language`, `/m/persona`, `/m/birth-details`.

Native, authenticated on connected Android before logout:

`/m/today`, `/m/ask`, `/m/ask/loading`, `/m/chart`, `/m/chart/full`, `/m/calendar`, `/m/settings`, `/m/settings/mode`, `/m/settings/account`, `/m/start`, `/m/auth`.

Source-reviewed mobile routes not fully manually tapped this pass:

`/m/ask/history`, `/m/ask/answer`, `/m/ask/refer`, `/m/remedies`, `/m/remedies/mantra`, `/m/muhurta`, `/m/muhurta/results`, `/m/chart/vargas`, `/m/chart/reference*`, `/m/chart/periods`, `/m/chart/yogas`, `/m/chart/strength`, `/m/settings/profiles*`, `/m/settings/birth-details`, `/m/settings/appearance`, `/m/settings/language`, `/m/settings/notifications`, `/m/settings/location`, `/m/settings/conventions`, `/m/search`, `/m/notifications`, `/m/subscription`, `/m/calendar/day`, `/m/compat*`, `/m/transits*`, `/m/readings*`, `/m/notes`.

## Persona Coverage

Balanced was tested as the baseline native authenticated mode.

Guided switching was tested from Settings. The tab set changed to `Today / Ask / What to do / Calendar / More`, and Today hid the deeper panchanga/stat sections.

Practitioner switching was tested from Settings. The tab set changed to `Today / Chart / Periods / Transits / More`, and Today exposed `ACTIVE TECHNICAL BASIS`.

Regression: the Settings summary row still says `Balanced · Gentle` after switching to Guided or Practitioner. Source hardcodes that value in `ui/src/app/features/mobile/settings/settings-home.component.ts:73`.

## Flow-by-Flow Findings

### Auth

Password sign-in: verified invalid password against live auth. Expected an inline error; actual was `Invalid login credentials`. Pass.

Google: verified web launch to Google OAuth with Supabase callback. I did not complete callback. Partial.

Protected route: `/m/today` unauthenticated redirects to `/m/auth`. Pass.

Native logout: sign-out from `/m/settings/account` returned to `/m/start`; protected route then redirected to `/m/auth`. Pass.

### Onboarding

Language, persona, and birth-details screens render at 375 x 812.

DOB is native `type=date`; TOB is native `type=time`.

Place search for `Mumbai` returns real city options: `Mumbai, IN · Asia/Kolkata` and `Navi Mumbai, IN · Asia/Kolkata`.

### Today

Skeleton code exists. Native live Today loaded with profile-specific values.

`Listen to your day` is present.

Practitioner `ACTIVE TECHNICAL BASIS` overflows fixed-height cards. Verified on device in `native-today-practitioner-technical-basis.png`.

### Chart

Chart hub renders live chart payload values.

Full chart style switching works for Eastern/South/North when tapping exact segmented controls.

Exact planet-marker taps open detail sheets. Verified with Mercury in `native-full-exact-mercury.png`.

Defects remain: chart labels sit on/outside grid boundaries in Eastern/North layouts, and the visible `Open full chart` CTA missed a normal native tap even though programmatic activation routed correctly.

### Calendar

Native `/m/calendar` failed live with `Calendar could not load / Failed to fetch` after a `calendar-intelligence` request entry of about 2.8s. This blocks month, day, festival, filter, and festival-sheet validation in native.

Source confirms the festival sheet has `WHAT TO DO` and `MANTRA / PRAYER`, but no distinct `HOW TO DO` section.

### Ask

Typed Ask routes to `/m/ask/loading`, then the live backend returned:

`AI generation failed: "Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set..."`

The app navigated back to `/m/ask` with the error in the URL query and no visible error. This is a silent core-flow failure.

Voice state is placeholder/canned: it always shows `Is this a good time to change my job`. The voice action controls overlap the bottom navigation area.

### Settings/Profile

Top profile switcher is visible on Today/Chart/Settings.

Mode switching works, but Settings summary does not reflect selected mode.

Theme behavior is inconsistent: after native chart/style/settings interactions, the app rendered light screens while the Android system reported night mode and Appearance said `System`.

`Manage profiles` was not successfully verified by tap in this pass; my attempted tap after scroll hit Subscription. Source route exists, so it is not marked dead.

## Prioritized Findings

### P1 - Ask live answer generation fails and hides the error

Gap type: Backend wiring and error state

Route: `/m/ask`, `/m/ask/loading`

Component/source: `ui/src/app/features/mobile/ask/ask-loading.component.ts:21-25`, `ui/src/app/features/mobile/ask/ask-home.component.ts:116-127`

Expected behavior: typed question shows loading, then answer/refer/error state with a visible recovery path.

Actual behavior: live backend fails with an AI auth/config error; app returns to Ask home with only `?error=...` in the URL and no visible message.

Repro steps: authenticated native app -> Ask -> type `What should I focus on today?` -> Send -> wait.

Evidence: `native-ask-loading-after-close.png`, `native-ask-answer-after-close.png`.

Recommended fix direction: make `/m/ask` consume and display `error` query params or route to a dedicated error state; fix backend AI credential configuration for live Ask.

### P1 - Calendar live native flow fails

Gap type: Backend/native data wiring

Route: `/m/calendar`

Component/source: `ui/src/app/features/mobile/calendar/calendar.component.ts:229-241`

Expected behavior: month grid loads personal signals and festivals from live data.

Actual behavior: native screen shows `Calendar could not load / Failed to fetch`; resource timing showed `/vedic/{id}/calendar-intelligence?...days=45...` around 2.8s.

Repro steps: authenticated native app -> Calendar tab -> wait.

Evidence: `native-calendar-live-loaded.png`, `native-calendar-day-tap.png`.

Recommended fix direction: inspect native fetch/CORS/auth failure for `calendar-intelligence`; preserve useful error detail; add retry telemetry.

### P1 - Practitioner Periods tab is misrouted

Gap type: Wrong navigation

Route: `/m` shell in Practitioner mode

Component/source: `ui/src/app/features/mobile/shell/mobile-shell.component.ts:77-83`, `ui/src/app/features/mobile/shell/mobile-shell.component.html:7-10`

Expected behavior: Practitioner `Periods` tab navigates to `/m/chart/periods`.

Actual behavior: native DOM shows href `/m/chart%2Fperiods`, because `routerLink` receives `['/m', 'chart/periods']`.

Repro steps: Settings -> Mode & tone -> Practitioner -> inspect/tap Periods tab.

Evidence: `native-account-privacy.png` button inventory captured `Periods` href `/m/chart%2Fperiods`.

Recommended fix direction: represent tab paths as router command arrays or split path segments before binding.

### P1 - Today Practitioner technical cards overflow

Gap type: Visual/layout defect

Route: `/m/today`

Component/source: `ui/src/app/features/mobile/today/today.component.scss:188-206`

Expected behavior: long technical basis values wrap within cards without overlapping adjacent content.

Actual behavior: long values spill outside the fixed `80px` cards and collide with the next card/section.

Repro steps: Settings -> Mode & tone -> Practitioner -> Today -> scroll to `ACTIVE TECHNICAL BASIS`.

Evidence: `native-today-practitioner-technical-basis.png`.

Recommended fix direction: remove fixed card height for this section, use min-height, or switch Practitioner technical basis to a single-column/detail row pattern.

### P2 - Settings mode summary lies after persona switch

Gap type: Persona/persistence UI regression

Route: `/m/settings`

Component/source: `ui/src/app/features/mobile/settings/settings-home.component.ts:69-74`

Expected behavior: Settings row reflects current mode and tone.

Actual behavior: row always displays `Balanced · Gentle` after Guided/Practitioner are selected.

Repro steps: Settings -> Mode & tone -> Guided or Practitioner -> back to Settings.

Evidence: `native-mode-guided-center.png`, `native-mode-practitioner-center.png`, `native-after-practitioner-back.png`.

Recommended fix direction: derive value from `PreferencesService.experienceMode()` and `tone()`.

### P2 - Chart labels are not rigidly bounded

Gap type: Chart rendering/layout defect

Route: `/m/chart/full`

Component/source: `ui/src/app/features/mobile/chart/chart-full.component.html:41-54`, `ui/src/app/features/mobile/chart/regional-chart.component.scss:13-23`

Expected behavior: sign labels and planet labels stay inside chart bounds with deterministic anchor positions.

Actual behavior: North/Eastern labels sit on grid strokes or outside the inner chart grid (`Ge`, `Ta`, `Pi` visible at top boundary; multi-planet clusters crowd diagonals).

Repro steps: Chart -> full chart -> switch Eastern/North.

Evidence: `native-full-style-eastern-tap.png`, `native-full-style-north-tap.png`, `native-dom-open-full-chart.png`.

Recommended fix direction: define per-style cell anchor maps with bounded label boxes, clamp text boxes inside the chart frame, and regression-test with dense multi-planet cells.

### P2 - Chart hub `Open full chart` tap target is unreliable on native

Gap type: Native interaction/hit target

Route: `/m/chart`

Component/source: `ui/src/app/features/mobile/chart/chart-hub.component.html:63-68`

Expected behavior: tapping the visible `Open full chart` button opens `/m/chart/full`.

Actual behavior: physical center tap on the visible CTA left URL at `/m/chart`; programmatic anchor activation then navigated to `/m/chart/full`.

Repro steps: Chart tab -> tap `Open full chart`.

Evidence: `native-chart-current.png`, `native-chart-full-open.png`, `native-dom-open-full-chart.png`.

Recommended fix direction: inspect overlay/scroll/hit-area stacking; add native tap regression around the CTA.

### P2 - Ask voice state is placeholder and action controls overlap tabbar

Gap type: Incomplete state and layout defect

Route: `/m/ask`

Component/source: `ui/src/app/features/mobile/ask/ask-home.component.ts:118-140`, `ui/src/app/features/mobile/ask/voice-listening.component.ts:31-40`, `ui/src/app/features/mobile/ask/voice-listening.component.scss:3-15`

Expected behavior: voice listening captures speech or clearly marks unavailable; Cancel/Done are fully tappable above the tabbar/safe area.

Actual behavior: voice shows canned transcript text; buttons occupy CSS y=787-835 while the tabbar starts around y=811, causing overlap/missed taps.

Repro steps: Ask -> mic button.

Evidence: `native-ask-voice-tap.png`, `native-ask-voice-done.png`, `native-ask-voice-done-exact.png`.

Recommended fix direction: hide shell tabs while voice overlay is open or raise the voice action area above the tabbar; wire real speech recognition or label as unavailable.

### P2 - Calendar festival detail is missing required "how to do" depth

Gap type: Incomplete content state

Route: `/m/calendar` festival sheet

Component/source: `ui/src/app/features/mobile/calendar/festival-sheet.component.ts:20-32`

Expected behavior: festival detail sheet includes what to do, how to do, and mantras.

Actual behavior: source renders `WHAT TO DO` and `MANTRA / PRAYER`; no separate `HOW TO DO` section exists.

Repro steps: not fully reachable in native because Calendar failed live; source-confirmed.

Evidence: source lines above.

Recommended fix direction: add a distinct how-to section backed by festival payload fields, not generic filler.

### P2 - Native theme/system appearance is inconsistent

Gap type: Native/theme persistence

Route: `/m/today`, `/m/chart/full`, `/m/settings/appearance`

Component/source: theme service and settings appearance components, not deeply traced in this pass.

Expected behavior: with Appearance set to `System` and Android night mode `yes`, mobile screens render dark consistently.

Actual behavior: initial native Today rendered dark, but later Chart/Settings/Today screenshots rendered light while Settings still said `System`.

Repro steps: connected Android in night mode -> navigate Today/Chart full/Settings/Appearance.

Evidence: `native-current-dark.png`, `native-dom-open-full-chart.png`, `native-settings-mode2.png`.

Recommended fix direction: audit native system theme listener, persisted preference, and body/root classes after route changes.

## Broken Navigation / CTA Table

| Priority | Element | Route | Actual | Evidence |
| --- | --- | --- | --- | --- |
| P1 | Practitioner `Periods` tab | `/m` shell | href encoded as `/m/chart%2Fperiods` | `native-account-privacy.png` DOM inventory |
| P2 | `Open full chart` | `/m/chart` | physical tap did not navigate; programmatic click worked | `native-chart-full-open.png`, `native-dom-open-full-chart.png` |
| P2 | Ask voice `Done`/`Cancel` | `/m/ask` | controls overlap tabbar zone | `native-ask-voice-tap.png` |
| Untested | Manage profiles | `/m/settings` | source route exists; my attempted tap hit Subscription after scroll | `native-manage-profiles-tap.png` |

## Loading, Empty, Error, Offline State Gaps

Ask loading exists but live error is not surfaced after redirect.

Calendar loading/error exists, but native failure collapses to generic `Failed to fetch` without actionable diagnosis.

Offline/stale data states were not verified in this pass.

Partial calculation state was not verified.

Voice/listening state is a visual placeholder and not a real capture state.

## Data / Backend Wiring Gaps

Live Ask generation is misconfigured or missing credentials.

Calendar native fetch fails for live `calendar-intelligence`.

Festival detail cannot be validated live because Calendar fails before festival interaction.

Settings persona summary is not wired to preferences.

Chart uses live payload for hub/full chart, but layout still treats labels as decorative positioning rather than bounded chart semantics.

## Native-App-Specific Issues

Connected Android was testable through WebView debugging and physical tap simulation.

Native sign-out/protected-route behavior passed.

Native Calendar failed with live fetch.

Native hit targets are suspect on `Open full chart` and voice sheet actions.

Native theme behavior is inconsistent with system dark mode.

## Screenshots List

Key evidence files:

`native-current-dark.png`

`native-tap-today.png`

`native-tap-ask.png`

`native-tap-chart.png`

`native-tap-calendar.png`

`native-tap-more.png`

`native-calendar-live-loaded.png`

`native-ask-loading-after-close.png`

`native-ask-answer-after-close.png`

`native-ask-voice-tap.png`

`native-dom-open-full-chart.png`

`native-full-style-eastern-tap.png`

`native-full-style-south-tap.png`

`native-full-style-north-tap.png`

`native-full-exact-mercury.png`

`native-mode-guided-center.png`

`native-mode-practitioner-center.png`

`native-today-practitioner-technical-basis.png`

`native-after-signout.png`

`native-protected-after-signout.png`

`web375-light-start.png`

`web375-dark-start.png`

`web375-light-auth.png`

`web375-light-auth-register.png`

`web375-auth-invalid-password.png`

`web375-auth-google-after-click.png`

`web375-protected-today-redirect.png`

`web375-language.png`

`web375-persona.png`

`web375-birth-details-empty.png`

`web375-birth-place-search-mumbai.png`

Additional exploratory screenshots are in the same folder and should be treated as supporting evidence, not individually audited artifacts.

## Prioritized Backlog

1. P1: Fix live Ask backend credential/config failure and show visible mobile error states after `/m/ask/loading` failures.

2. P1: Fix native Calendar live fetch failure; validate month/day/festival flows after data loads.

3. P1: Fix Practitioner `Periods` tab routing by avoiding slash-containing path strings in `routerLink`.

4. P1: Remove fixed-height Today stat cards for Practitioner technical basis.

5. P2: Wire Settings mode/tone summary to real preferences.

6. P2: Rework chart label placement with deterministic bounded anchors per style.

7. P2: Fix native hit target/stacking for `Open full chart`.

8. P2: Make voice state real or clearly unavailable, and keep voice controls above the shell tabbar.

9. P2: Add `HOW TO DO` festival detail content and validate against real festival payloads.

10. P2: Audit native theme persistence/system mode after route/style/preference changes.

11. P2: Retest Manage Profiles, edit birth details, conventions, notifications, readings, notes, transits, compatibility, remedies, and muhurta with exact tap targets after the P1 navigation/data blockers are fixed.

