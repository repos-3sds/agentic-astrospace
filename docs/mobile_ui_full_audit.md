# AstroSpace Mobile UI Full Audit

Audit date: 2026-07-28

Scope: `/m/*` routes, [ui/src/app/features/mobile](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile), existing web features under [ui/src/app/features](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features), Figma file `RRhuTcaKIhqILZW7JUKFzI` page `0:1`.

Evidence: `cd ui && npm run build:dev` passed on 2026-07-28. Figma page inventory was refreshed with the Codex Figma MCP connector on page `0:1`. Source verification was used for the recent footer/search/chart/auth corrections listed below. Existing screenshot evidence remains in [docs/mobile-audit-screenshots](/Users/vikramaditya/Documents/agentic-astrospace/docs/mobile-audit-screenshots); screenshots that only show an auth redirect are called out as redirect evidence, not screen verification.

## Executive Summary

The original audit was directionally right but mixed primary implementation status with overlapping defect flags. This revision reconciles the totals around a canonical inventory: one row per relevant Figma node, one mutually exclusive primary implementation status, and separate reachability, data-wiring, and interaction-completeness flags.

Reconciled status: 112 relevant Figma nodes. 10 are complete under the strict screen definition, 75 are partial, and 27 are missing. These three counts add to 112. The other summary counts intentionally overlap: all 27 missing screens are also unreachable, 31 implemented screens use placeholder/static data, and 18 implemented screens contain broken, inert, or misleading interactions.

The most serious implementation contract is not authentication. Current code supports mobile sign-in, registration, magic link, Google, native callback handling, and check-email messaging. The remaining auth gap is verification/configuration evidence and richer result states. The first remediation slice should instead address Notes and Readings data honesty, because these finished-looking screens make persistence and accuracy claims that are not backed by mobile data wiring.

## Reconciled Counts

| Metric | Count | Derivation |
| --- | ---: | --- |
| Figma top-level nodes returned | 127 | Figma page `0:1` top-level query. |
| Excluded component/helper nodes | 15 | 10 component/component-set nodes plus 5 helper/orphan frames. |
| Relevant Figma screen/native nodes | 112 | Canonical inventory rows. |
| Complete | 10 | Primary status = Complete. |
| Partial | 75 | Primary status = Partial. |
| Missing | 27 | Primary status = Missing. |
| Unreachable | 27 | Reachable? = No. This overlaps the 27 missing nodes; no current implemented route was retained as unreachable after this pass. |
| Placeholder/static data | 31 | Implemented rows where Real data? = No. Missing rows are excluded because no data surface exists yet. |
| Broken/inert interactions | 18 | Implemented rows where Interactions complete? = No. Missing rows are excluded. |
| P0 findings | 0 | No proof that auth is impossible, safety boundary failed, destructive data loss occurs, or materially incorrect backend user data is written. |
| P1 findings | 8 | Listed with evidence below. |

Excluded Figma nodes: components `18:6`, `18:7`, `18:9`, `18:10`, `19:2`, `19:8`, `19:19`, `24:25`, `34:57`, `92:157`; helper/orphan frames `21:32`, `21:41`, `21:50`, `40:113`, `108:390`.

Primary statuses do not overlap. `Complete`, `Partial`, and `Missing` are mutually exclusive. `Unreachable`, `Placeholder/static`, and `Broken/inert` are flags that can overlap a primary status and each other.

## Complete Screens

These are the 10 screens still classified as complete. Each was validated against route reachability, real backend data, loading/error/empty handling where applicable, working primary interactions, active profile/persona context, light/dark rendering, and final-scroll clearance.

| Node | Screen | Route/component | Validation |
| --- | --- | --- | --- |
| `13:2` | `7 · Today` | `/m/today`, `TodayComponent` | Reachable from mobile shell; uses `/context/{id}/daily`; loading/error/empty are implemented; primary sheet/search/profile interactions work; profile/persona context is loaded; shell clearance source-verified. |
| `21:22` | `7c · Day-quality detail` | Today sheet | Opens from Today day-quality action; uses daily payload signals; dismiss works; inherits Today loading/error/profile/theme context. |
| `22:23` | `7d · Why this reading` | Today sheet | Opens from Today; uses daily explanation/provenance; dismiss works; inherits Today state and theme. |
| `25:25` | `8 · Ask — Home` | `/m/ask`, `AskHomeComponent` | Reachable from tab; profile-aware question start; loading handoff exists; error/empty prompts present; source shows no static answer claim on this screen. |
| `26:54` | `10 · Ask — Answer view` | `/m/ask/answer`, `AskAnswerComponent` | Populated by `MobileAskState`; Ask backend call is made from loading screen; primary follow-up/history interactions present. |
| `27:83` | `11 · Ask — Refer-out (safety)` | `/m/ask/refer`, `AskReferOutComponent` | Safety refer-out route exists and is a deliberate boundary state. No P0 safety failure found in source verification. |
| `91:89` | `27 · Gochara (plain transits)` | `/m/transits`, `GocharaComponent` | Uses `/vedic/{id}/gocharam`; loading/error/empty handled; profile/persona context present; remaining date-range depth is P2, not incompletion for the summary screen. |
| `108:417` | `States · Ask — Loading (computing answer)` | `/m/ask/loading`, `AskLoadingComponent` | Calls `/ask/{id}` and redirects to answer/refer state; loading state is the intended screen. |
| `206:223` | `10b · Ask — History` | `/m/ask/history`, `AskHistoryComponent` | Uses `/ask/threads`; loading/error/empty states present; route reachable from Ask. |
| `206:354` | `35 · Notification Center` | `/m/notifications`, `NotificationCenterComponent` | Uses `/me/alerts`; loading/error/empty handled; route reachable from Settings/utility links. Permission-denied is a separate missing state. |

## Recent Fix Recheck

Removed as stale defects:

- Mobile footer floats above content. Source: [mobile-shell.component.scss](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/shell/mobile-shell.component.scss:31) uses an absolutely positioned glass tabbar above the safe area.
- `.content` reserves bottom clearance. Source: [mobile-shell.component.scss](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/shell/mobile-shell.component.scss:20) sets `padding-bottom` and `scroll-padding-bottom`.
- Search was removed from mobile Settings. Source grep found no Settings search row; only route declaration and Today link remain.
- Global Search remains accessible from Today. Source: [today.component.html](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/today/today.component.html:11).
- Expanded-chart planet markers are independently tappable. Source: [east-chart.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/chart/east-chart.component.ts:66) renders one button per glyph.
- Sun and Mercury in Gemini open separate details. Source: [chart-full.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/chart/chart-full.component.ts:11) has separate `Su` and `Me` placement records.
- Eastern, South, and North charts support individual markers. Source: [chart-full.component.html](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/chart/chart-full.component.html:24), [regional-chart.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/chart/regional-chart.component.ts:15).

## Authentication Reclassification

Auth is no longer classified as P0. Current mobile registration already supports sign-in/register tabs, password registration, magic link, Google, check-email notice when Supabase returns no session, native callback handling, and stored mobile destination routing.

| Gap type | What is missing | Evidence |
| --- | --- | --- |
| Missing visual state | Dedicated mobile confirmation/auth-result screen for register, magic link, password reset, and callback errors. Current register shows inline notice only. | [mobile-auth.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/onboarding/mobile-auth.component.ts:69), [mobile-auth.component.html](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/onboarding/mobile-auth.component.html:39). |
| Verification/configuration gap | Hosted Supabase redirect allowlist for `app.astrospace.mobile://auth/callback` and web return URLs was not proven in this audit. | Auth redirect code exists at [auth.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/auth.service.ts:176), but project-hosted config was not inspected. |
| Verification/configuration gap | Real-device callback verification for PKCE, fragment token, Google, magic link, and password reset was not completed. | Native callback code exists at [auth.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/auth.service.ts:215). |
| Verification/configuration gap | Test-inbox verification for email confirmation and reset delivery was not available. | No test inbox credentials were provided. |
| Missing loading/error/empty/offline state | Auth-result states need non-enumerating error/result copy and retry paths after hosted callbacks. | Inline errors exist, but no dedicated callback result route is declared under `/m` in [app.routes.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/app.routes.ts:226). |

## P0/P1 Findings

There are no P0 findings after reclassification. P1 findings are below; every item has one gap type.

| Priority | Gap type | Figma node | Route | Source | Expected | Actual | Verification | Screenshot | Backend |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Placeholder/static data | `115:124` | `/m/notes` | [notes.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/notes/notes.component.ts:20) | Notes persist or are labelled local draft. | Text edits only update a signal while UI says `Saved` and account-stored. | Source + prior browser smoke. | `bypass-m-notes.png` | No mobile notes endpoint; only kundli notes field observed. |
| P1 | Placeholder/static data | `113:122`, `114:124` | `/m/readings`, `/m/readings/accuracy` | [readings.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/readings/readings.component.ts:13), [accuracy.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/readings/accuracy.component.ts:25) | Readings and claim totals derive from `ReadingService`. | Fixed `18 of 24`, fixed claims, local-only review state. | Source + prior browser smoke. | `bypass-m-readings.png`, `bypass-m-readings-accuracy.png` | Existing `/readings/{id}` and `/readings/{id}/claims` in [reading.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/reading.service.ts:21). |
| P1 | Placeholder/static data | `93:89`, `94:118`, `116:124` | `/m/calendar`, `/m/calendar/day` | [calendar.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/calendar/calendar.component.ts:12) | Month/day/festival results reflect active profile, selected date, and filters. | July 2026 fixture; month arrows have no handlers; day/festival content fixed. | Source + prior browser smoke. | `bypass-m-calendar.png`, `bypass-m-calendar-day.png` | Existing `/vedic/{id}/calendar-intelligence` in [vedic.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/vedic.service.ts:102). |
| P1 | Placeholder/static data | `97:119`, `97:144`, `98:119`, `215:805` | `/m/compat`, `/m/compat/add`, `/m/compat/results` | [add-prospect.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/compat/add-prospect.component.ts:24) | Add/select person affects computed compatibility and detail. | Submitted values are ignored; result remains fixed; full detail screen missing. | Source + prior browser smoke. | `bypass-m-compat.png`, `bypass-m-compat-results.png` | Existing `/vedic/{id}/compatibility/{partner_id}` in [vedic.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/vedic.service.ts:107). |
| P1 | Missing route/navigation | `216:415`, `216:483`, `216:543`, `216:615` | Expected `/m/settings/profiles/*` | [settings-home.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/settings/settings-home.component.ts:120) | Manage profiles opens create/switch/edit/delete lifecycle. | Settings `Manage profiles` routes to active birth-details edit screen. | Source verification. | none; route inspected in source | `/kundlis` exists in [kundli.store.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/kundli.store.ts:70). |
| P1 | Placeholder/static data | `35:57`, `36:86`, `36:201`, `36:247`, `39:87`, `40:87`, `41:87`, `41:149` | `/m/chart*` | [chart-full.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/chart/chart-full.component.ts:10) | Chart modules use active kundli calculations. | Full chart/detail and deeper chart modules render fixed placements/text. | Source + prior browser smoke. | `bypass-m-chart-full.png` | Existing `/vedic/{id}/all`, dashas, yogas, ashtakavarga, jaimini endpoints in [vedic.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/vedic.service.ts:32). |
| P1 | Placeholder/static data | `30:56`, `31:57` | `/m/muhurta`, `/m/muhurta/results` | [muhurta-results.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/muhurta/muhurta-results.component.ts:1) | Goal/date range drives computed windows and saved/reminder actions. | Results are fixture windows; add/remind controls do not persist. | Source + prior browser smoke. | `bypass-m-muhurta-results.png` | Backend capability not wired; muhurta endpoints referenced in docs/contracts. |
| P1 | Placeholder/static data | `29:55`, `29:109` | `/m/remedies`, `/m/remedies/mantra` | [remedies.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/remedies/remedies.component.ts:1) | Remedies and practice progress reflect recommendations/completions. | Cards and mantra tracker are static/local, but look personalized. | Source + prior browser smoke. | `bypass-m-remedies.png` | Backend capability not wired; remedy/practice endpoints referenced in docs/contracts. |

## Persona Coverage

Personas are `Guided`, `Balanced`, and `Practitioner`, matching [preferences.service.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/preferences.service.ts:10). They are presentation modes, not entitlements.

| Feature | Guided behavior required | Balanced behavior required | Practitioner behavior required | Current coverage |
| --- | --- | --- | --- | --- |
| Navigation | Prioritize Today, Ask, What to do; reduce chart depth. | Standard Today, Ask, Chart, Calendar, Settings. | Surface Chart/Reference/Calendar depth prominently. | Shell tab adaptation exists in [mobile-shell.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/shell/mobile-shell.component.ts:63), but many destinations still expose the same static content. |
| Today | Plain verdicts, collapsed technical reasons, simple actions. | Summary plus one-tap why. | Panchanga, transit, and calculation metadata visible by default. | Separate Figma frames exist; component partly changes copy but not all depth/defaults. |
| Ask | Short answer and safety-forward copy. | Answer plus "why" and next action. | Technical terms, source factors, and provenance visible. | Ask persona answer frames are not separate Angular components; behavior should be data/copy depth, not duplication. |
| Chart | Story-first, limited glyph density. | Hub plus optional sheets. | Technical chart tools, vargas, dashas, doshas, strengths, reference. | Practitioner chart/yantra frames missing; chart modules static. |
| Calendar | Day-level guidance and "what to do". | Month/day with festival details. | Sunrise cutoff, ayanamsha, tithi/nakshatra details, filters. | Practitioner/guided day frames missing as distinct presentation states. |
| Safety | Gentler refer-out language and lower jargon. | Balanced refer-out and boundaries. | Same safety boundary, with precise explanation. | Safety route exists; persona-specific wording not fully implemented. |

Separate Figma frames do not automatically require separate Angular components. The implementation contract is mode-aware navigation, copy/detail depth, default expansion, technical visibility, and safety copy.

## Feature Parity Matrix

| Feature/module | Web route/component | Mobile route/component | Web depth | Mobile depth | Backend/API | Parity | Recommended mobile treatment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Auth/account | `/auth`, settings | `/m/auth`, `/m/settings/account` | Supabase auth and account tools | UI supported; result/config verification incomplete | Supabase auth, `/me` | Partial | Add result-state and real-device/test-inbox verification. |
| Profile lifecycle | Web kundli dialog/settings | switcher, `/m/settings/birth-details` | Create/edit/delete | Create/edit active/switch; manage/delete missing | `/kundlis` | Partial | Build mobile-native manage profiles flow. |
| Today | Web overview/daily | `/m/today` | Rich daily context | Real summary with mobile simplification | `/context/{id}/daily` | Appropriate simplification | Add offline/stale and partial-calculation states. |
| Ask | Web Ask tab | `/m/ask/*` | Threaded Ask | Text Ask and history wired; voice simulated | `/ask/{id}`, `/ask/threads` | Near parity | Add real voice and persona answer depth. |
| Chart foundation | Vedic/overview tabs | `/m/chart`, `/m/chart/full` | Computed chart/tables | Rendered but static | `/vedic/{id}/all` | Partial | Bind cards/planet details to active kundli. |
| Vargas/dashas/yogas/strength | Web Vedic sub-tabs | `/m/chart/*` | Computed endpoints | Mostly static | Vedic endpoints | Partial | Wire as one chart data slice. |
| Transits | Web gocharam/transits | `/m/transits*` | Timeline and domain depth | Real summary/detail; fixed range | `/vedic/{id}/gocharam` | Appropriate simplification | Add date/range controls. |
| Calendar | Web calendar intelligence | `/m/calendar*` | Computed month/day | Static July 2026 | `/vedic/{id}/calendar-intelligence` | Partial | API-backed calendar with filters. |
| Compatibility | Web compatibility | `/m/compat*` | Computed partner comparison | Fixed result | `/vedic/{id}/compatibility/{partner_id}` | Partial | Add/select partner and computed result. |
| Readings/notes | Web reading/notes tabs | `/m/readings*`, `/m/notes` | API-backed readings; notes field | Static/local with persistence claims | `ReadingService`; notes contract unclear | Partial | Data honesty first, persistence second. |
| Remedies/Muhurta | Web/API tools | `/m/remedies*`, `/m/muhurta*` | Backend capability documented | Static | Remedy/muhurta endpoints | Partial | Wire recommendations, saved items, reminders. |
| Notifications | Alerts/devices | `/m/notifications` | Alert APIs | Center wired; permission state missing | `/me/alerts`, devices | Partial | Add native permission denied/recovery state. |
| Subscription | None approved | `/m/subscription` | Not productized | Disabled by design | none | Web-only by design | Keep disabled until billing approved. |

## Missing Screens

Exactly 27 canonical Figma nodes are missing from code:

1. `103:92` `M10 · Home Screen Widget (medium)` - native-platform surface, P2.
2. `104:92` `M10 · Lock Screen (context)` - native-platform surface, P2.
3. `106:92` `M10 · Live Activity (Dynamic Island)` - native-platform surface, P2.
4. `106:102` `M10 · Watch Complication` - native-platform surface, P3.
5. `106:109` `M10 · Push Notification (morning brief)` - native-platform surface, P2.
6. `107:101` `M10 · Share Story Card` - native-platform surface, P2.
7. `212:416` `6c · Aha — Guided` - missing screen, P2.
8. `212:458` `6d · Aha — Balanced` - missing screen, P2.
9. `212:512` `6e · Aha — Practitioner` - missing screen, P2.
10. `214:155` `16P · Yantra (Practitioner)` - missing screen, P2.
11. `215:156` `12G · What to do (Guided)` - missing screen, P2.
12. `215:241` `Profiles · Today Across Profiles` - missing route/navigation, P2.
13. `215:373` `16G · Your Story (Guided)` - missing screen, P2.
14. `215:620` `28G · Calendar Day (Guided)` - missing screen, P2.
15. `215:690` `28P · Calendar Day (Practitioner)` - missing screen, P2.
16. `215:805` `30d · Full Compatibility Detail` - missing screen, P1.
17. `215:1216` `16P · Charts (Practitioner)` - missing screen, P2.
18. `216:160` `21e · Life Periods — Sookshma level` - missing screen, P2.
19. `216:262` `21f · Life Periods — Prana level` - missing screen, P2.
20. `216:543` `screen-3-edit-profile` - missing screen, P1.
21. `216:615` `screen-4-delete-confirmation` - missing screen, P1.
22. `216:415` `37 · Manage Profiles` - missing route/navigation, P1.
23. `216:483` `37b · Add Profile` - missing screen, P1.
24. `216:904` `screen-3-unknown` - native-platform surface, P2.
25. `216:964` `screen-4-denied` - missing permission state, P2.
26. `216:773` `States · Offline / Stale Data` - missing loading/error/empty/offline state, P2.
27. `216:838` `States · Partial Calculation` - missing loading/error/empty/offline state, P2.

## Recommended Execution Order

### 1. Notes and Readings persistence/data honesty

User outcome: users never see false saved, account-stored, or accuracy claims.
Routes/screens: `/m/notes`, `/m/readings`, `/m/readings/accuracy`; nodes `115:124`, `113:122`, `114:124`.
Backend dependency: decide notes persistence contract; use `ReadingService` endpoints for readings and claims.
Acceptance criteria: reload and sign-out/sign-in prove persistence or UI clearly says local draft; reading totals equal displayed backend claims; empty state when no readings.
Loading/error/empty states: loading list, empty readings, no claims, save failure, offline draft.
Browser/native verification: 375 x 812 light/dark, reload, switch profile, throttle/offline.
Size: M. Dependencies: notes API decision.

### 2. Profile management lifecycle

User outcome: create, switch, edit, and delete profiles without editing the wrong profile.
Routes/screens: `/m/settings/profiles`, add/edit/delete confirmation; nodes `216:415`, `216:483`, `216:543`, `216:615`, `79:89`, `215:241`.
Backend dependency: `/kundlis` list/create/update/delete.
Acceptance criteria: active profile persists; delete active profile chooses safe next profile; Today and Ask reload for selected profile.
Loading/error/empty states: loading profiles, zero profile after delete, API failure, delete confirmation, missing birth data.
Browser/native verification: multi-profile flow at 375 x 812, light/dark, protected-route behavior after logout.
Size: M. Dependencies: none beyond existing store.

### 3. Calendar intelligence

User outcome: month/day/festival guidance reflects the active profile and selected date.
Routes/screens: `/m/calendar`, `/m/calendar/day`; nodes `93:89`, `94:118`, `116:124`, `215:620`, `215:690`.
Backend dependency: `/vedic/{id}/calendar-intelligence`.
Acceptance criteria: previous/next month works; selected day changes payload; guided/practitioner depth differs; fixture July 2026 removed.
Loading/error/empty states: month loading, no observances, API error, offline/stale, unsupported convention.
Browser/native verification: July/August 2026, long festival names, light/dark.
Size: L. Dependencies: profile lifecycle preferred.

### 4. Compatibility end to end

User outcome: add/select person and receive a computed, explainable compatibility result.
Routes/screens: `/m/compat`, `/m/compat/add`, `/m/compat/results`, full detail; nodes `97:119`, `97:144`, `98:119`, `110:121`, `215:805`.
Backend dependency: `/vedic/{id}/compatibility/{partner_id}` and partner/profile storage decision.
Acceptance criteria: input changes result; approximate/missing birth time states are honest; full detail exists; share has visible outcome.
Loading/error/empty states: no checks, loading computation, partner missing data, API error, offline.
Browser/native verification: exact and approximate partner, empty hub, light/dark.
Size: L. Dependencies: profile lifecycle.

### 5. Chart real-data wiring

User outcome: chart, planets, vargas, dashas, yogas, doshas, strengths, and references reflect the active kundli.
Routes/screens: `/m/chart`, `/m/chart/full`, `/m/chart/vargas`, `/m/chart/periods`, `/m/chart/yogas`, `/m/chart/strength`, reference routes; nodes `35:57`, `36:86`, `36:201`, `36:247`, `39:87`, `40:87`, `41:87`, `41:149`, `56:88`, `57:88`, `59:*`, `60:*`, `61:*`, `117:*`, `118:*`, `216:160`, `216:262`.
Backend dependency: VedicService endpoints.
Acceptance criteria: displayed placements match endpoint payload; totals agree with displayed values; no static Lakshmi fixture for other profiles.
Loading/error/empty states: chart computing, partial calculation, unsupported convention, API error, offline/stale.
Browser/native verification: all chart styles, individual markers, long labels, dark mode.
Size: L. Dependencies: profile lifecycle.

### 6. Remedies and Muhurta

User outcome: recommended actions and timing windows are computed, saveable, and honest.
Routes/screens: `/m/remedies`, `/m/remedies/mantra`, `/m/muhurta`, `/m/muhurta/results`; nodes `29:55`, `29:109`, `30:56`, `31:57`, `215:156`.
Backend dependency: remedy, practice, muhurta, saved/reminder APIs.
Acceptance criteria: selected goal/range changes results; completions persist; add-to-calendar/remind has success/error feedback.
Loading/error/empty states: no recommendations, no windows, save failure, notification permission denied.
Browser/native verification: light/dark, reload, offline, permission denied.
Size: L. Dependencies: notifications permission work for reminders.

### 7. Missing platform and resilience states

User outcome: native and degraded states are explicit instead of silent or blank.
Routes/screens: widgets, lock screen, live activity, watch, push, share, offline/stale, partial calculation, notification denied; nodes `103:92`, `104:92`, `106:92`, `106:102`, `106:109`, `107:101`, `216:773`, `216:838`, `216:904`, `216:964`.
Backend dependency: native build hooks, device token/alerts APIs.
Acceptance criteria: offline/stale and partial calculation reusable states are wired; notification denied has recovery path; native surfaces are either implemented or explicitly deferred by product flag.
Loading/error/empty states: offline, stale, denied, partial, retry.
Browser/native verification: browser responsive states plus real iOS/Android permission checks.
Size: M/L. Dependencies: native build access.

### 8. Persona-specific presentation refinement

User outcome: Guided, Balanced, and Practitioner feel intentionally different without duplicating screens unnecessarily.
Routes/screens: onboarding aha, Today, Ask, Chart, Calendar, What to do; nodes `212:*`, `214:155`, `215:*`.
Backend dependency: preferences sync and existing feature payloads.
Acceptance criteria: mode changes navigation, copy depth, default expansion, technical visibility, and safety copy; separate Figma frames are reconciled into component states where appropriate.
Loading/error/empty states: mode preference loading/sync failure, default fallback.
Browser/native verification: switch modes, reload, sign out/in, light/dark.
Size: M. Dependencies: data slices above.

## Appendix: Canonical Figma Inventory

Legend: Primary status is mutually exclusive. `Reachable?` answers whether a user can reach the screen/surface from current UI navigation; missing native surfaces are `No`. `Real data? = No` is counted as placeholder/static. `Interactions complete? = No` is counted as broken/inert.

| Node ID | Exact Figma title | User story | Persona | Expected route | Existing component | Primary status | Reachable? | Real data? | Interactions complete? | Missing states | Recommended action | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `4:2` | `1 · Landing` | New user start | All | `/m/start` | `LandingComponent` | Partial | Yes | Yes | Yes | auth result | Keep, add verified auth transition | P2 |
| `5:2` | `2 · Login / Register` | Auth | All | `/m/auth` | `MobileAuthComponent` | Partial | Yes | Yes | Yes | result/config verification | Add confirmation/result states | P2 |
| `6:2` | `3 · Welcome` | Onboarding | All | `/m/welcome` | `WelcomeComponent` | Partial | Yes | Yes | Yes | back/restore | Preserve onboarding progress | P2 |
| `7:2` | `4 · Info Carousel · Disclaimers` | Onboarding safety | All | `/m/disclaimers` | `DisclaimersComponent` | Partial | Yes | Yes | Yes | persistence | Verify consent persistence | P2 |
| `8:2` | `5 · Persona Type` | Persona setup | All | `/m/persona` | `PersonaComponent` | Partial | Yes | Yes | Yes | sync error | Wire all persona behavior | P2 |
| `11:2` | `6 · Birth Details` | Profile create | All | `/m/birth-details` | `BirthDetailsComponent` | Partial | Yes | Yes | Yes | city/search/offline | Improve place/fallback states | P2 |
| `13:2` | `7 · Today` | Today | Balanced | `/m/today` | `TodayComponent` | Complete | Yes | Yes | Yes | offline/stale | Keep; add resilience state | P2 |
| `20:2` | `7b · Today (full scroll)` | Today scroll | Balanced | `/m/today` | `TodayComponent` | Partial | Yes | Yes | Yes | offline/stale | Verify long-scroll after each slice | P3 |
| `21:22` | `7c · Day-quality detail` | Today detail | Balanced | Today sheet | `TodayComponent` sheet | Complete | Yes | Yes | Yes | offline/stale | Keep | P3 |
| `22:23` | `7d · Why this reading` | Provenance | Balanced | Today sheet | `TodayComponent` sheet | Complete | Yes | Yes | Yes | offline/stale | Keep | P3 |
| `23:25` | `7e · Listen (audio)` | Audio | Balanced | Today sheet | `TodayComponent` sheet | Partial | Yes | Yes | No | audio unavailable/error | Wire audio or mark unavailable | P2 |
| `25:25` | `8 · Ask — Home` | Ask start | All | `/m/ask` | `AskHomeComponent` | Complete | Yes | Yes | Yes | offline | Keep; add voice entry | P2 |
| `25:123` | `9 · Ask — Voice listening` | Ask voice | All | `/m/ask` | `AskHomeComponent` voice UI | Partial | Yes | Yes | No | mic denied/offline | Replace simulated voice with native flow | P2 |
| `26:54` | `10 · Ask — Answer view` | Ask answer | All | `/m/ask/answer` | `AskAnswerComponent` | Complete | Yes | Yes | Yes | empty expired state | Keep; add persona depth | P2 |
| `27:83` | `11 · Ask — Refer-out (safety)` | Safety | All | `/m/ask/refer` | `AskReferOutComponent` | Complete | Yes | Yes | Yes | none found | Keep; tune persona copy | P2 |
| `29:55` | `12 · Remedies — For You` | Remedies | All | `/m/remedies` | `RemediesComponent` | Partial | Yes | No | No | loading/error/empty/offline | Wire recommendations | P1 |
| `29:109` | `13 · Remedy detail — Mantra tracker` | Practice | All | `/m/remedies/mantra` | `MantraTrackerComponent` | Partial | Yes | No | No | save/error/offline | Persist completions | P1 |
| `30:56` | `14 · Muhurta — Choose a goal` | Muhurta | All | `/m/muhurta` | `MuhurtaGoalComponent` | Partial | Yes | No | No | loading/error/empty | Wire goal catalog | P1 |
| `31:57` | `15 · Muhurta — Results` | Muhurta results | All | `/m/muhurta/results` | `MuhurtaResultsComponent` | Partial | Yes | No | No | save/reminder/error | Wire computed windows | P1 |
| `35:57` | `16 · Chart Hub (You)` | Chart hub | Balanced | `/m/chart` | `ChartHubComponent` | Partial | Yes | No | Yes | loading/error/partial | Bind active chart data | P1 |
| `36:86` | `17 · Chart — Full render` | Chart full | Balanced | `/m/chart/full` | `ChartFullComponent` | Partial | Yes | No | Yes | loading/error/partial | Bind placements to endpoint | P1 |
| `36:201` | `18 · Planet detail sheet` | Planet detail | Balanced | Chart sheet | `PlanetSheetComponent` | Partial | Yes | No | Yes | missing planet data | Bind selected planet detail | P1 |
| `36:247` | `19 · Provenance sheet` | Provenance | Balanced | Chart sheet | `ProvenanceSheetComponent` | Partial | Yes | No | Yes | endpoint error | Bind calculation provenance | P1 |
| `39:87` | `20 · Divisional (Varga) Charts` | Vargas | Practitioner | `/m/chart/vargas` | `VargaChartsComponent` | Partial | Yes | No | Yes | loading/error/unsupported | Wire varga payload | P2 |
| `40:87` | `21 · Life Periods (Dashas)` | Dashas | Practitioner | `/m/chart/periods` | `LifePeriodsComponent` | Partial | Yes | No | Yes | loading/error/unsupported | Wire dasha payload | P2 |
| `41:87` | `22 · Yogas & Doshas` | Yogas | Practitioner | `/m/chart/yogas` | `YogasDoshasComponent` | Partial | Yes | No | Yes | loading/error/empty | Wire computed flags | P2 |
| `41:149` | `23 · Strength & Advanced` | Strength | Practitioner | `/m/chart/strength` | `StrengthAdvancedComponent` | Partial | Yes | No | Yes | loading/error/empty | Wire strength data | P2 |
| `41:210` | `24 · Learning sheet — Gajakesari Yoga` | Learning sheet | Practitioner | Yoga sheet | `YogaLearningSheetComponent` | Partial | Yes | No | Yes | empty explanation | Bind selected yoga | P2 |
| `56:88` | `17b · Chart — Full render (South)` | Chart full | Practitioner | `/m/chart/full` | `RegionalChartComponent` | Partial | Yes | No | Yes | loading/error/partial | Keep markers; bind data | P1 |
| `57:88` | `17c · Chart — Full render (North)` | Chart full | Practitioner | `/m/chart/full` | `RegionalChartComponent` | Partial | Yes | No | Yes | loading/error/partial | Keep markers; bind data | P1 |
| `59:88` | `21b · Life Periods — Maha level` | Dashas | Practitioner | `/m/chart/periods` | `LifePeriodsComponent` | Partial | Yes | No | Yes | loading/error/unsupported | Wire maha/antar navigation | P2 |
| `59:258` | `21c · Life Periods — Pratyantar level` | Dashas | Practitioner | `/m/chart/periods` | `LifePeriodsComponent` | Partial | Yes | No | Yes | deeper levels | Wire pratyantar | P2 |
| `59:427` | `21d · Life Periods — Yogini system` | Dashas | Practitioner | `/m/chart/periods` | `LifePeriodsComponent` | Partial | Yes | No | Yes | unsupported system | Wire yogini endpoint | P2 |
| `60:88` | `23b · Strength & Advanced — Ashtakavarga` | Strength | Practitioner | `/m/chart/strength` | `StrengthAdvancedComponent` | Partial | Yes | No | Yes | loading/error/empty | Wire ashtakavarga | P2 |
| `60:257` | `23c · Strength & Advanced — Jaimini` | Strength | Practitioner | `/m/chart/strength` | `StrengthAdvancedComponent` | Partial | Yes | No | Yes | loading/error/empty | Wire jaimini | P2 |
| `61:88` | `20b · Divisional charts — D1` | Vargas | Practitioner | `/m/chart/vargas` | `VargaChartsComponent` | Partial | Yes | No | Yes | unsupported | Wire D1 detail | P2 |
| `61:195` | `20c · Divisional charts — D10` | Vargas | Practitioner | `/m/chart/vargas` | `VargaChartsComponent` | Partial | Yes | No | Yes | unsupported | Wire D10 detail | P2 |
| `62:88` | `2b · Register` | Auth | All | `/m/auth?mode=register` | `MobileAuthComponent` | Partial | Yes | Yes | Yes | confirmation/result | Add dedicated check-email screen | P2 |
| `62:140` | `12b · Manglik cancellation detail` | Dosha detail | All | chart/remedies sheet | `ManglikCancellationSheetComponent` | Partial | Yes | No | Yes | endpoint error | Bind real cancellation factors | P2 |
| `66:89` | `25 · Settings — Home` | Settings | All | `/m/settings` | `SettingsHomeComponent` | Partial | Yes | Yes | No | sync/error | Fix Manage profiles destination | P1 |
| `67:89` | `25b · Settings — Mode & Tone` | Settings | All | `/m/settings/mode` | `ModeToneComponent` | Partial | Yes | Yes | Yes | cloud sync error | Sync and reflect preferences | P2 |
| `67:147` | `25c · Settings — Language & Audio` | Settings | All | `/m/settings/language` | `LanguageAudioComponent` | Partial | Yes | Yes | Yes | cloud sync error | Persist all values | P2 |
| `67:173` | `25d · Settings — Notifications` | Notifications | All | `/m/settings/notifications` | `NotificationsComponent` | Partial | Yes | Yes | No | denied/offline | Add permission/device states | P2 |
| `69:89` | `25e · Settings — Location` | Settings | All | `/m/settings/location` | `LocationComponent` | Partial | Yes | Yes | No | permission/error | Wire actual location preference | P2 |
| `69:117` | `25f · Settings — Conventions` | Settings | Practitioner | `/m/settings/conventions` | `ConventionsComponent` | Partial | Yes | Yes | No | unsupported convention | Persist and apply convention | P2 |
| `69:180` | `25g · Settings — Account & Privacy` | Account | All | `/m/settings/account` | `AccountPrivacyComponent` | Partial | Yes | Yes | Yes | auth expired | Keep; verify real auth | P2 |
| `79:89` | `26 · Profile switcher sheet` | Profile switch | All | Profile sheet | `ProfileSwitcherComponent` | Partial | Yes | Yes | Yes | empty/error | Add manage/add/delete links | P2 |
| `82:96` | `2c · Choose Your Language` | Onboarding | All | `/m/language` | `LanguageComponent` | Partial | Yes | Yes | Yes | sync error | Persist language/audio fully | P2 |
| `91:89` | `27 · Gochara (plain transits)` | Transits | All | `/m/transits` | `GocharaComponent` | Complete | Yes | Yes | Yes | range/offline | Add timeline controls later | P2 |
| `92:89` | `27b · Full Transits` | Transits detail | Practitioner | `/m/transits/full` | `FullTransitsComponent` | Partial | Yes | Yes | Yes | range/offline | Add range/date controls | P2 |
| `93:89` | `28 · Calendar` | Calendar | Balanced | `/m/calendar` | `CalendarComponent` | Partial | Yes | No | No | loading/error/empty/offline | Wire calendar intelligence | P1 |
| `94:118` | `29 · Festival detail sheet` | Calendar detail | Balanced | Calendar sheet | `FestivalSheetComponent` | Partial | Yes | No | No | empty/error | Bind selected festival/day | P1 |
| `97:119` | `30 · Compatibility Hub` | Compatibility | All | `/m/compat` | `CompatHubComponent` | Partial | Yes | No | Yes | empty/loading/error | Wire partner list | P1 |
| `97:144` | `30b · Add Prospect` | Compatibility add | All | `/m/compat/add` | `AddProspectComponent` | Partial | Yes | No | No | validation/error | Persist/compute partner | P1 |
| `98:119` | `30c · Gun Milan Results` | Compatibility results | All | `/m/compat/results` | `CompatResultsComponent` | Partial | Yes | No | No | loading/error/detail | Use compatibility endpoint | P1 |
| `103:92` | `M10 · Home Screen Widget (medium)` | Native widget | All | Native | none | Missing | No | N/A | N/A | native/offline | Implement or product-defer | P2 |
| `104:92` | `M10 · Lock Screen (context)` | Native lock screen | All | Native | none | Missing | No | N/A | N/A | native/offline | Implement or product-defer | P2 |
| `106:92` | `M10 · Live Activity (Dynamic Island)` | Native live activity | All | Native | none | Missing | No | N/A | N/A | native/offline | Implement or product-defer | P2 |
| `106:102` | `M10 · Watch Complication` | Watch | All | Native | none | Missing | No | N/A | N/A | native/offline | Product-defer or implement | P3 |
| `106:109` | `M10 · Push Notification (morning brief)` | Push | All | Native | none | Missing | No | N/A | N/A | permission denied | Implement with alerts/devices | P2 |
| `107:101` | `M10 · Share Story Card` | Share | All | Native/share | none | Missing | No | N/A | N/A | share failure | Implement native share card | P2 |
| `108:92` | `7-dark · Today (Dark mode)` | Theme | Balanced | `/m/today` | `TodayComponent` | Partial | Yes | Yes | Yes | dark regression | Keep as visual regression target | P3 |
| `108:186` | `8-dark · Ask Home (Dark mode)` | Theme | All | `/m/ask` | `AskHomeComponent` | Partial | Yes | Yes | Yes | dark regression | Keep as visual regression target | P3 |
| `108:246` | `16-dark · Chart Hub (Dark mode)` | Theme | Balanced | `/m/chart` | `ChartHubComponent` | Partial | Yes | Yes | Yes | dark regression | Keep as visual regression target | P3 |
| `108:417` | `States · Ask — Loading (computing answer)` | Ask loading | All | `/m/ask/loading` | `AskLoadingComponent` | Complete | Yes | Yes | Yes | network/offline | Keep | P2 |
| `110:121` | `States · Compatibility — Empty (no checks yet)` | Compatibility empty | All | `/m/compat` | `CompatHubComponent` | Partial | Yes | Yes | Yes | endpoint empty | Wire real no-partner state | P2 |
| `110:153` | `States · Generic — Something went wrong` | Error | All | reusable | scattered errors | Partial | Yes | Yes | Yes | retry/offline | Standardize reusable error | P2 |
| `113:122` | `31 · Readings & Accuracy` | Readings | All | `/m/readings` | `ReadingsComponent` | Partial | Yes | No | No | loading/error/empty | Wire ReadingService | P1 |
| `114:124` | `31b · Prediction Claims (accuracy)` | Claims | All | `/m/readings/accuracy` | `AccuracyComponent` | Partial | Yes | No | No | loading/error/empty | Wire claims API | P1 |
| `115:124` | `32 · Notes` | Notes | All | `/m/notes` | `NotesComponent` | Partial | Yes | No | No | save/error/offline | Persist or label local draft | P1 |
| `116:124` | `28b · Calendar — Day detail (timing feed)` | Calendar day | Balanced | `/m/calendar/day` | `CalendarDayComponent` | Partial | Yes | Yes | Yes | loading/error/offline | Wire selected day payload | P1 |
| `117:124` | `33 · Practitioner Reference` | Reference | Practitioner | `/m/chart/reference` | `ReferenceComponent` | Partial | Yes | Yes | Yes | loading/error/empty | Keep, broaden data states | P2 |
| `117:175` | `33b · Avkahada & Ghatak` | Reference | Practitioner | `/m/chart/reference/avkahada` | `ReferenceComponent` | Partial | Yes | Yes | Yes | loading/error/empty | Keep, verify data mapping | P2 |
| `118:124` | `33c · Graha positions & conditions` | Reference | Practitioner | `/m/chart/reference/grahas` | `ReferenceComponent` | Partial | Yes | Yes | Yes | loading/error/empty | Keep, verify data mapping | P2 |
| `118:239` | `33d · Ashtakavarga tables` | Reference | Practitioner | `/m/chart/reference/ashtakavarga` | `ReferenceComponent` | Partial | Yes | Yes | Yes | loading/error/empty | Keep, verify totals | P2 |
| `118:383` | `33e · Favourable points` | Reference | Practitioner | `/m/chart/reference/favourable` | `ReferenceComponent` | Partial | Yes | Yes | Yes | loading/error/empty | Keep, verify payload | P2 |
| `206:160` | `2d · Forgot Password` | Auth recovery | All | `/m/forgot-password` | `ForgotPasswordComponent` | Partial | Yes | Yes | Yes | inbox/result | Add callback/result verification | P2 |
| `206:190` | `States · Chart Computing` | Chart loading | All | chart routes | partial loading state | Partial | Yes | Yes | Yes | timeout/retry | Standardize chart loading | P2 |
| `206:223` | `10b · Ask — History` | Ask history | All | `/m/ask/history` | `AskHistoryComponent` | Complete | Yes | Yes | Yes | offline | Keep | P2 |
| `206:302` | `34 · Subscription` | Subscription | All | `/m/subscription` | `SubscriptionComponent` | Partial | Yes | Yes | Yes | entitlement/store | Keep disabled by design | P3 |
| `206:354` | `35 · Notification Center` | Notifications | All | `/m/notifications` | `NotificationCenterComponent` | Complete | Yes | Yes | Yes | permission denied | Keep; add denied state | P2 |
| `206:493` | `6b · Edit Birth Details` | Profile edit | All | `/m/settings/birth-details` | `EditBirthDetailsComponent` | Partial | Yes | Yes | Yes | delete/profile context | Move under profile lifecycle | P1 |
| `206:550` | `27c · Transit Detail` | Transit detail | All | transit sheet | `GocharaComponent`/detail | Partial | Yes | Yes | Yes | range/offline | Keep, add range context | P2 |
| `206:591` | `36 · Search` | Search | All | `/m/search` | `SearchComponent` | Partial | Yes | Yes | No | no results/error | Replace static index with real content | P2 |
| `206:641` | `25h · Account Deletion` | Account delete | All | `/m/settings/account/delete` | `AccountDeletionComponent` | Partial | Yes | Yes | Yes | real auth verification | Verify backend deletion | P1 |
| `212:161` | `7G · Today (Guided)` | Today persona | Guided | `/m/today` | `TodayComponent` | Partial | Yes | Yes | Yes | persona copy/depth | Tune guided presentation | P2 |
| `212:324` | `7B · Today (Balanced)` | Today persona | Balanced | `/m/today` | `TodayComponent` | Partial | Yes | Yes | Yes | persona defaults | Tune balanced presentation | P2 |
| `212:416` | `6c · Aha — Guided` | First insight | Guided | expected `/m/insight` variant | none | Missing | No | N/A | N/A | loading/error | Build persona aha state | P2 |
| `212:458` | `6d · Aha — Balanced` | First insight | Balanced | expected `/m/insight` variant | none | Missing | No | N/A | N/A | loading/error | Build persona aha state | P2 |
| `212:512` | `6e · Aha — Practitioner` | First insight | Practitioner | expected `/m/insight` variant | none | Missing | No | N/A | N/A | loading/error | Build persona aha state | P2 |
| `212:751` | `7P · Today (Practitioner)` | Today persona | Practitioner | `/m/today` | `TodayComponent` | Partial | Yes | Yes | Yes | technical defaults | Tune practitioner presentation | P2 |
| `212:971` | `10G · Ask Answer (Guided)` | Ask persona | Guided | `/m/ask/answer` | `AskAnswerComponent` | Partial | Yes | Yes | Yes | persona copy | Tune answer depth | P2 |
| `212:1019` | `10B · Ask Answer (Balanced)` | Ask persona | Balanced | `/m/ask/answer` | `AskAnswerComponent` | Partial | Yes | Yes | Yes | persona copy | Tune answer depth | P2 |
| `212:1077` | `10P · Ask Answer (Practitioner)` | Ask persona | Practitioner | `/m/ask/answer` | `AskAnswerComponent` | Partial | Yes | Yes | Yes | technical provenance | Tune answer depth | P2 |
| `214:155` | `16P · Yantra (Practitioner)` | Practitioner chart | Practitioner | expected chart subroute | none | Missing | No | N/A | N/A | loading/error | Build or defer yantra | P2 |
| `215:156` | `12G · What to do (Guided)` | Guided actions | Guided | expected `/m/remedies` variant | none | Missing | No | N/A | N/A | loading/error/empty | Implement as remedies mode state | P2 |
| `215:241` | `Profiles · Today Across Profiles` | Profile overview | All | expected profile/today view | none | Missing | No | N/A | N/A | empty/error | Consider in profile slice | P2 |
| `215:373` | `16G · Your Story (Guided)` | Guided chart | Guided | expected chart story | none | Missing | No | N/A | N/A | loading/error | Implement as guided chart state | P2 |
| `215:620` | `28G · Calendar Day (Guided)` | Calendar persona | Guided | `/m/calendar/day` variant | none | Missing | No | N/A | N/A | loading/error/empty | Implement via calendar mode state | P2 |
| `215:690` | `28P · Calendar Day (Practitioner)` | Calendar persona | Practitioner | `/m/calendar/day` variant | none | Missing | No | N/A | N/A | loading/error/empty | Implement via calendar mode state | P2 |
| `215:805` | `30d · Full Compatibility Detail` | Compatibility detail | All | expected `/m/compat/results/detail` | none | Missing | No | N/A | N/A | loading/error/empty | Build in compatibility slice | P1 |
| `215:1216` | `16P · Charts (Practitioner)` | Practitioner chart | Practitioner | expected chart mode view | none | Missing | No | N/A | N/A | loading/error/partial | Implement as practitioner chart state | P2 |
| `216:160` | `21e · Life Periods — Sookshma level` | Dashas | Practitioner | `/m/chart/periods` deeper state | none | Missing | No | N/A | N/A | loading/error/unsupported | Add deeper dasha level | P2 |
| `216:262` | `21f · Life Periods — Prana level` | Dashas | Practitioner | `/m/chart/periods` deeper state | none | Missing | No | N/A | N/A | loading/error/unsupported | Add deeper dasha level | P2 |
| `216:543` | `screen-3-edit-profile` | Profile edit | All | expected `/m/settings/profiles/:id/edit` | none | Missing | No | N/A | N/A | loading/error/delete | Build profile edit | P1 |
| `216:615` | `screen-4-delete-confirmation` | Profile delete | All | expected `/m/settings/profiles/:id/delete` | none | Missing | No | N/A | N/A | destructive confirm/error | Build delete confirmation | P1 |
| `216:415` | `37 · Manage Profiles` | Profile management | All | expected `/m/settings/profiles` | none | Missing | No | N/A | N/A | loading/empty/error | Build manage profiles | P1 |
| `216:483` | `37b · Add Profile` | Profile create | All | expected `/m/settings/profiles/new` | none | Missing | No | N/A | N/A | validation/error | Build add profile | P1 |
| `216:904` | `screen-3-unknown` | Notification permission | All | Native/settings state | none | Missing | No | N/A | N/A | permission unknown | Identify and implement/defer | P2 |
| `216:964` | `screen-4-denied` | Notification denied | All | Native/settings state | none | Missing | No | N/A | N/A | permission denied | Build denied recovery state | P2 |
| `216:773` | `States · Offline / Stale Data` | Resilience | All | reusable state | none | Missing | No | N/A | N/A | offline/stale/retry | Build reusable state | P2 |
| `216:838` | `States · Partial Calculation` | Resilience | All | reusable state | none | Missing | No | N/A | N/A | approximate birth data | Build reusable partial state | P2 |
