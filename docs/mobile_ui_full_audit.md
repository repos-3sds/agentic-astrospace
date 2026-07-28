# AstroSpace Mobile UI Full Audit

Audit date: 2026-07-28

Scope: `/m/*` routes, `ui/src/app/features/mobile/`, existing web features under `ui/src/app/features/`, Figma file `RRhuTcaKIhqILZW7JUKFzI` page `0:1`.

Evidence captured with `cd ui && npm run build:dev`, local FastAPI preview on `127.0.0.1:8010`, Chrome at 375 x 812. Protected-route visual checks used `ASTROSPACE_DEV_AUTH_BYPASS=1` so the documented debug user could enter the mobile shell. Screenshots are in [docs/mobile-audit-screenshots](/Users/vikramaditya/Documents/agentic-astrospace/docs/mobile-audit-screenshots).

## Executive Summary

The mobile app has broad Figma-to-code coverage and the native shell is no longer just a prototype. Core Today, Ask, profile restoration, account deletion, settings appearance, notification center, and Gocharam/transit surfaces touch real APIs. The main completion risk is now workflow truth: many screens look finished but still use hard-coded data, do not persist user actions, or expose controls that silently do nothing.

The most important gap is the new-user and profile lifecycle. Registration can create an account, but there is no mobile verification/auth-result screen, and a Supabase project that requires email confirmation leaves the register path without a complete mobile transition. Profile switching exists, creation and edit exist, but the Figma profile-management screens are absent and settings routes "Manage profiles" to edit the active birth details rather than to a management surface.

Figma has moved beyond the documented 79-frame plan. Live Figma inspection returned 117 top-level frames/sections; 112 are relevant screen-level mobile/native artifacts after excluding 5 helper/orphan frames. The older build plan status is stale: it does not include persona variants, profile-management screens, offline/stale data, partial-calculation, notification-denied, or deeper dasha levels.

## Overall Completion Assessment

| Metric | Count |
| --- | ---: |
| Figma top-level frames/sections returned | 117 |
| Relevant screen-level frames after excluding helpers | 112 |
| Fully implemented and real-data wired | 18 |
| Partially implemented | 61 |
| Missing from code | 27 |
| Unreachable or route-hidden | 13 |
| Using placeholder/static data | 31 |
| Broken or inert interactions verified/found in source | 18 |
| P0 issues | 2 |
| P1 issues | 12 |

Excluded Figma helpers: `108:390` Input Field / States, `21:32`, `21:41`, `21:50`, `40:113`.

## Figma Screen Coverage

| Node(s) | Figma screen(s) | Expected route/component | Status | Notes/action |
| --- | --- | --- | --- | --- |
| `4:2`, `5:2`, `62:88`, `206:160` | Landing, auth, register, forgot password | `/m/start`, `/m/auth`, `/m/forgot-password` | Partially wired | Auth UI exists. Missing mobile verification/auth-result state; real email flows not verified without test inbox/Supabase redirect validation. |
| `82:96`, `6:2`, `7:2`, `8:2`, `11:2`, `206:493` | Language, welcome, disclaimers, persona, birth details, edit birth | `/m/language`, `/m/welcome`, `/m/disclaimers`, `/m/persona`, `/m/birth-details`, `/m/settings/birth-details` | Partial | Create/edit call `/kundlis`; no documented preservation of onboarding state on back/exit; city picker is static. |
| `212:416`, `212:458`, `212:512` | Aha guided/balanced/practitioner | Expected after birth details or first insight | Missing | Current `/m/insight` is not these persona-specific aha screens. |
| `13:2`, `20:2`, `21:22`, `22:23`, `23:25`, `108:92`, `212:161`, `212:324`, `212:751` | Today variants, sheets, dark/persona variants | `/m/today` plus sheets | Mostly wired | Daily guidance uses `/context/{id}/daily`; panchang grid is reduced; persona variants are only partially expressed by copy/tabs. |
| `25:25`, `25:123`, `26:54`, `27:83`, `108:186`, `108:417`, `206:223`, `212:971`, `212:1019`, `212:1077` | Ask home/voice/loading/answer/refer/history/persona answers | `/m/ask`, `/m/ask/loading`, `/m/ask/answer`, `/m/ask/refer`, `/m/ask/history` | Mostly wired | Ask uses `/ask/{id}` and thread APIs. Voice UI is simulated transcript; answer detail differs only partly by persona. |
| `35:57`, `36:86`, `56:88`, `57:88`, `36:201`, `36:247`, `214:155`, `215:373`, `215:1216` | Chart hub/full/regional/planet/provenance/yantra/story/charts variants | `/m/chart`, `/m/chart/full` | Partial | Chart hub/full are rendered; most data is static chart text. Yantra, guided story, and practitioner chart variants are absent. |
| `39:87`, `61:88`, `61:195` | Varga charts | `/m/chart/vargas` | Built static | Route exists; no `/vedic/{id}/all` or varga payload binding observed. |
| `40:87`, `59:88`, `59:258`, `59:427`, `216:160`, `216:262` | Life periods/dasha levels | `/m/chart/periods` | Partial/static | Maha, antar, pratyantar, Yogini are static arrays. Sookshma and prana Figma screens are missing. |
| `41:87`, `41:210`, `62:140` | Yogas/doshas and sheets | `/m/chart/yogas`, shared sheets | Built static | API exists at `/vedic/{id}/yogas-doshas`, but UI uses hard-coded combinations. |
| `41:149`, `60:88`, `60:257` | Strength, Ashtakavarga, Jaimini | `/m/chart/strength` | Built static | API exists for ashtakavarga and jaimini; UI hard-codes shadbala, BAV/SAV, karakas, arudhas. |
| `117:124`, `117:175`, `118:124`, `118:239`, `118:383` | Practitioner reference | `/m/chart/reference/*` | Partial/wired | Reference loads `/vedic/{id}/all` or `/vedic/{id}/ashtakavarga` for detail modes; stronger than many chart routes. |
| `91:89`, `92:89`, `206:550` | Gocharam/full transits/detail | `/m/transits`, `/m/transits/full`, sheet | Wired | Uses `/vedic/{id}/gocharam`. Range is fixed at 90 days; no user date/timeline range controls. |
| `93:89`, `94:118`, `116:124`, `215:620`, `215:690` | Calendar, festival, day/persona variants | `/m/calendar`, `/m/calendar/day` | Static/partial | UI is hard-coded July 2026; previous/next month buttons inert; calendar-intelligence API exists but is unused. |
| `97:119`, `97:144`, `98:119`, `215:805` | Compatibility hub/add/results/full detail | `/m/compat`, `/m/compat/add`, `/m/compat/results` | Static/partial | Partner input is ignored; result is fixed Lakshmi x Ravi. Full compatibility detail is missing. |
| `29:55`, `29:109`, `215:156` | Remedies/What to do/mantra | `/m/remedies`, `/m/remedies/mantra` | Static/partial | Remedy and practice APIs exist; UI not wired to recommendations, streaks, or completions. |
| `30:56`, `31:57` | Muhurta goal/results | `/m/muhurta`, `/m/muhurta/results` | Static/partial | Goal selection routes with query params, but results are fixture windows; add/remind chips do nothing. |
| `113:122`, `114:124` | Readings and accuracy | `/m/readings`, `/m/readings/accuracy` | Static/incorrect | Reading service exists, but mobile shows fixed "18 of 24 held up" and fixed claims. |
| `115:124` | Notes | `/m/notes` | Static/local only | Textarea edits local signal only; UI says saved/account-stored without API persistence. |
| `66:89`, `67:89`, `67:147`, `67:173`, `69:89`, `69:117`, `69:180`, `206:641` | Settings and account deletion | `/m/settings/*` | Partial | Theme is real; preferences service can sync but settings screens do not all call `syncCloud`; several row values are hard-coded. |
| `79:89`, `215:241`, `216:415`, `216:483`, `216:543`, `216:615` | Profile switcher/manage/add/edit/delete profile | Sheet, expected `/m/settings/profiles` | Partial/missing | Switcher exists. Manage Profiles/Add Profile/Edit Profile/Delete confirmation screens are missing; settings "Manage profiles" points to edit active birth details. |
| `206:302`, `206:354`, `216:964` | Subscription, notification center, denied permissions | `/m/subscription`, `/m/notifications` | Partial | Subscription intentionally disabled; notification center wired to `/me/alerts`; denied-permission screen missing. |
| `206:591` | Search | `/m/search` | Built static index | Client-side feature index only; no cross-module content search. |
| `216:773`, `216:838`, `206:190`, `110:153`, `110:121` | Offline/stale, partial calculation, chart computing, generic error, empty compat | Mixed reusable states | Partial/missing | Generic/chart-computing exist; offline/stale and partial-calculation state screens are missing. |
| `103:92`, `104:92`, `106:92`, `106:102`, `106:109`, `107:101` | Widgets, live activity, watch, push, share card | Native surfaces, no `/m` route | Missing/deferred | These are native/platform surfaces, not web routes; no implementation found. |

## Mobile Route Inventory

Routes are declared in [app.routes.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/app.routes.ts:153).

| Route group | Routes | Classification |
| --- | --- | --- |
| Onboarding/auth | `/m/start`, `/m/auth`, `/m/forgot-password`, `/m/reset-password`, `/m/language`, `/m/welcome`, `/m/disclaimers`, `/m/persona`, `/m/birth-details`, `/m/insight` | Built; auth result and persona aha variants missing. |
| Shell core | `/m/today`, `/m/ask`, `/m/chart`, `/m/calendar`, `/m/settings` | Reachable after auth; bottom tab adapts by persona in [mobile-shell.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/shell/mobile-shell.component.ts:63). |
| Ask | `/m/ask/history`, `/m/ask/loading`, `/m/ask/answer`, `/m/ask/refer` | Mostly wired; voice capture simulated. |
| Chart | `/m/chart/full`, `/m/chart/vargas`, `/m/chart/reference/*`, `/m/chart/periods`, `/m/chart/yogas`, `/m/chart/strength` | Reachable; many static-data screens. |
| Utility/settings | `/m/search`, `/m/notifications`, `/m/subscription`, `/m/settings/*` | Mixed. Theme/account deletion real; search/subscription partial. |
| Calendar/compat/transits/readings/notes | `/m/calendar/day`, `/m/compat/*`, `/m/transits/full`, `/m/readings/accuracy`, `/m/notes` | Reachable; calendar/compat/readings/notes mostly static. |

Unreachable or wrong destination:

- Figma `216:415` Manage Profiles and `216:483` Add Profile have no route; settings sends Manage profiles to `/m/settings/birth-details` at [settings-home.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/settings/settings-home.component.ts:120).
- Figma `216:543` edit profile and `216:615` delete profile confirmation are missing.
- Figma `216:773` offline/stale, `216:838` partial calculation, and `216:964` notification denied are missing.
- Figma `216:160` and `216:262` sookshma/prana dasha levels are missing from the Life Periods route.
- M10 widget/live/watch/push/share surfaces have no implementation route or native surface.

## Web/Mobile Parity Matrix

| Feature/module | Web reference | Mobile route/component | Web capability depth | Mobile depth | Backend/API | Parity | Recommended mobile treatment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Auth/account | `/auth`, `/settings` | `/m/auth`, `/m/settings/account` | Password, Google, magic link, account tools | Mobile auth UI plus export/signout/delete | Supabase auth, `/me` | Partial | Add auth-result/verification and test hosted email returns. |
| Profile lifecycle | Dashboard/settings profile flows | switcher, birth details, edit active details | Create/edit/delete via store | Switch/create/edit active only; no manage/delete profile UI | `/kundlis` | Partial | Build Manage Profiles slice, preserving active profile and delete confirmation. |
| Today | Web overview/calendar blend | `/m/today` | Daily + panchanga + transit context | Good mobile summary, real daily endpoint | `/context/{id}/daily` | Appropriate simplification | Add offline/stale/partial states and panchanga detail wiring. |
| Ask | `kundli/:id/ask` | `/m/ask/*` | Session history in web service | Persisted mobile thread APIs, safety refer-out | `/ask/{id}`, `/ask/threads` | Near parity | Add real voice, answer persona variants, and empty/error tests. |
| Chart foundation | overview/vedic/chart tabs | `/m/chart`, `/m/chart/full` | Detailed chart, wheel/aspects/tables | Rendered mobile chart; much static summary | `/vedic/{id}/all` partly | Partial | Bind chart cards/planet detail to active kundli payload. |
| Vargas | `/kundli/:id/varga-charts` | `/m/chart/vargas` | Computed divisional charts | Static selector/screens | `/vedic/{id}/all` | Partial | Use the varga payload and show unsupported/partial states. |
| Dashas | `/kundli/:id/dashas` | `/m/chart/periods` | Computed Vimshottari/Yogini, nested periods | Static arrays; no sookshma/prana screens | `/vedic/{id}/dashas`, `/yogini-dashas` | Partial | Wire all levels as one vertical slice. |
| Yogas/doshas | `/kundli/:id/yogas-doshas` | `/m/chart/yogas` | Computed combinations and notes | Static list | `/vedic/{id}/yogas-doshas` | Partial | Bind computed flags/cancellations; preserve "flag, not verdict." |
| Strength/advanced | ashtakavarga/jaimini tabs | `/m/chart/strength` | Ashtakavarga/Jaimini tables | Static values | `/vedic/{id}/ashtakavarga`, `/jaimini` | Partial | Bind real tables and explain totals/invariants. |
| Transits | transits/gocharam web tabs | `/m/transits`, `/m/transits/full` | Rich gocharam domains/timeline | Real gocharam summary and details; fixed 90d | `/vedic/{id}/gocharam` | Appropriate simplification | Add range/date controls and timeline detail. |
| Calendar | `/kundli/:id/calendar` | `/m/calendar`, `/m/calendar/day` | Calendar intelligence/readings markers | Hard-coded July 2026 | `/vedic/{id}/calendar-intelligence` exists | Partial | Replace static month/day with API-backed calendar. |
| Compatibility | `/kundli/:id/compat` | `/m/compat/*` | Computed compatibility route exists | Fixed Lakshmi x Ravi; add form ignored | `/vedic/{id}/compatibility/{partner_id}`, practice checks | Partial | Add/select partner profile and compute real result. |
| Readings/accuracy | readings tab + reading service | `/m/readings`, `/m/readings/accuracy` | Generate/list/feedback/claims APIs | Static copy and counts | `/readings/{id}`, `/claims` | Partial | Build honest empty/list/detail/feedback flow. |
| Notes | notes tab | `/m/notes` | Saved backend notes | Local signal only, says saved | Kundli notes field only | Partial | Persist notes or change copy to local draft until saved. |
| Remedies | remedy API/practice routes | `/m/remedies`, `/m/remedies/mantra` | Engine/API exists | Static cards/tracker | `/remedies/{id}`, `/practice/remedies` | Partial | Wire recommendations and completion streaks. |
| Muhurta | muhurta API | `/m/muhurta/*` | Goal-based backend exists | Static windows and inert chips | `/muhurta/goals`, `/muhurta/find` | Partial | Wire goal catalog/search/saved reminders. |
| Notifications | `/me/alerts`, devices | `/m/notifications`, settings | Alert APIs exist | Center wired; preferences/denied state missing | `/me/alerts`, `/me/devices` | Partial | Add permission denied/OS setting state and preference persistence. |
| Subscription | none approved | `/m/subscription` | Web-only/no product | Explicitly disabled | none/store pending | Web-only by design for now | Keep disabled until billing/entitlements approved. |

## Persona Coverage

The exact third persona/state is not an entitlement; it is the experience mode triad: `guided`, `balanced`, `practitioner`, defined in [PreferencesService](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/core/preferences.service.ts:10) and visible in Figma `8:2`, `212:*`, `214:*`, `215:*`. The shell adapts tabs for guided and practitioner users in [mobile-shell.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/shell/mobile-shell.component.ts:68).

Coverage is partial. The tab bar changes and some Gocharam copy changes by mode, but the dedicated Figma Today/Ask/Chart/Calendar persona variants are not completely represented. Settings rows also hard-code values such as `Balanced · Gentle`, `English · Audio on`, and `Lahiri · Eastern` in [settings-home.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/settings/settings-home.component.ts:70), so state display can drift from actual preferences.

## End-To-End User-Story Results

| Story | Result | Defects |
| --- | --- | --- |
| New user landing -> registration -> auth result -> onboarding -> first insight -> Today | Partial/fails at verification coverage | No mobile verification/auth-result screen; real email confirmation and password reset delivery unverified. |
| Returning user sign in -> restore profile -> Today -> features -> logout -> sign in | Partial | Redirect guard works; debug bypass verified profile restoration. Real Supabase credentials/test inbox not available. |
| Guided/Balanced/Practitioner persona | Partial | Mode selection exists; tab/copy adaptation partial; Figma persona screens missing. |
| Profile create/switch/edit/delete | Partial | Create/edit/switch exist. Manage/add/edit/delete profile Figma screens missing; settings route is wrong. |
| Theme lifecycle | Mostly passes | System/light/dark implemented and local persistence works; not verified against native OS change event. |
| Today | Mostly passes | Real data, loading/error/empty present; audio sheet is UI only; offline/stale state missing. |
| Ask | Mostly passes | Text Ask and backend safety decision wired; voice is simulated; history shows persisted threads. |
| Chart | Partial | Full chart style toggles work; many details static; missing yantra/story/practitioner variants. |
| Calendar | Fails parity | Static July 2026; selected day fixed; prev/next inert; no filters/API. |
| Compatibility | Fails parity | Add form ignores data; results fixed; share has no visible outcome in headless/browser. |
| Transits | Partial/good | Real Gocharam payload; no date/range controls. |
| Readings/notes | Fails parity | Static readings/claims; notes are local only while claiming saved/account-stored. |
| Remedies/Muhurta | Partial/static | Screens exist; APIs exist; not wired to recommendations/search/saved actions. |
| Notifications/subscription/settings | Partial | Notification center real; subscription intentionally disabled; notification denied state missing. |

## Navigation Defects

1. P1: Settings "Manage profiles" routes to edit active birth details instead of a manage-profiles screen. Source: [settings-home.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/settings/settings-home.component.ts:120).
2. P1: Calendar month arrows are buttons with no handlers. Source: [calendar.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/calendar/calendar.component.ts:12). Verified unchanged after tap.
3. P1: Compatibility add form submits to fixed results and ignores entered values. Source: [add-prospect.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/compat/add-prospect.component.ts:27).
4. P2: `/m/chart/periods` cannot reach sookshma/prana Figma levels.
5. P2: `/m/notifications` has no permission-denied route/sheet despite Figma `216:964`.
6. P2: Search is reachable only from Today/Settings and searches a static feature index, not actual readings/notes/history.

## Data/Backend Wiring Gaps

- Static despite available backend: Life Periods, Yogas/Doshas, Strength/Ashtakavarga/Jaimini, Calendar, Compatibility, Remedies, Muhurta, Readings, Notes.
- Backend capability exists but UI missing: `/vedic/{id}/calendar-intelligence`, `/vedic/{id}/compatibility/{partner_id}`, `/muhurta/find`, `/remedies/{kundli_id}`, `/practice/remedies`, `/practice/saved-muhurtas`, `/readings/{id}`, `/readings/{id}/claims`.
- Backend capability not approved/complete: subscriptions/entitlements and native billing.
- Data integrity risk: notes display "Saved" and "Stored privately on your account" but only update a component signal in [notes.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/notes/notes.component.ts:20).
- Data honesty risk: readings display fixed accuracy totals in [readings.component.ts](/Users/vikramaditya/Documents/agentic-astrospace/ui/src/app/features/mobile/readings/readings.component.ts:13) and fixed review claims in `accuracy.component.ts`.

## Visual And Accessibility Defects

- Many routes with the tab bar have final-scroll overlap risk at the bottom of the viewport; examples: Today, Ask, Chart, Calendar, Settings. Screenshots: `bypass-m-today.png`, `bypass-m-calendar.png`.
- Some icon-only controls lack visible text but have labels; good examples are Today search/profile. Calendar month controls have labels but no function.
- Several controls are reachable and focusable but inert: calendar month arrows, muhurta chips, readings saved versions, compatibility share visible feedback, notes save.
- Dark mode representative screenshots did not reveal invisible core text on Today/Chart, but fixed-color SVGs should still be audited when implementing missing states.
- Long content risk remains for Gocharam/transit fields; current mobile screens place long rule text in cards rather than always pushing narrative to sheets.

## Prioritized Remediation Backlog

### P0

1. Complete mobile auth verification/result flow.
   Outcome: New users never dead-end after register/magic link/reset.
   Routes: `/m/auth`, `/m/forgot-password`, `/m/reset-password`, new auth-result screen.
   Backend: Supabase auth redirect allowlist/test inbox.
   Acceptance: register with email-confirmation project shows non-enumerating confirmation and returns to onboarding/Today after verification.
   Verification: real Supabase test account, password reset, magic link, Google.
   Size: M. Dependencies: test inbox and Supabase redirect configuration.

2. Fix notes/readings false persistence claims.
   Outcome: The app never says account data is saved when it is only local/static.
   Routes: `/m/notes`, `/m/readings`, `/m/readings/accuracy`.
   Backend: `/readings`, claims APIs; notes storage contract.
   Acceptance: notes persist across reload or UI says draft/local; readings totals derive from API rows.
   Verification: reload, switch profile, sign out/in, API payload check.
   Size: M. Dependencies: notes API decision.

### P1

3. Build Profile Management vertical slice.
   Outcome: Users can create, switch, edit, and delete profiles without touching the wrong profile.
   Routes: `/m/settings`, new `/m/settings/profiles`, add/edit/delete confirmation.
   Backend: `/kundlis`.
   Acceptance: active profile persists; delete switches safely; Today reloads for selected profile.
   Verification: multiple profiles, edit birth time, delete active/non-active.
   Size: M.

4. Wire Calendar to calendar intelligence.
   Outcome: Calendar month/day/filter actions reflect real dates and convention notes.
   Routes: `/m/calendar`, `/m/calendar/day`, festival sheet.
   Backend: `/vedic/{id}/calendar-intelligence`.
   Acceptance: prev/next work; selected day changes; empty/API/offline states exist.
   Verification: July/August 2026, practitioner vs guided mode, long festival names.
   Size: L.

5. Wire Compatibility end-to-end.
   Outcome: Add/select person -> computed result -> detailed flags/cancellations.
   Routes: `/m/compat`, `/m/compat/add`, `/m/compat/results`, new detail.
   Backend: `/vedic/{id}/compatibility/{partner_id}`, `/practice/compatibility-checks`.
   Acceptance: input affects result; empty and approximate-time states are honest.
   Verification: exact/approx partner, missing birth time, no partner, share feedback.
   Size: L.

6. Wire Readings and accuracy.
   Outcome: Users see real generated readings and can review claims.
   Routes: `/m/readings`, `/m/readings/accuracy`.
   Backend: `ReadingService`.
   Acceptance: empty state when `/readings/{id}` returns `[]`; totals derive from displayed claims.
   Verification: generate, force refresh, feedback, no-data state.
   Size: M.

### P2

7. Wire dasha/yoga/strength chart modules by endpoint.
8. Wire remedies and muhurta, including saved reminders.
9. Add offline/stale, partial-calculation, notification-denied, and permission states.
10. Add range/date controls to Gocharam/full transits.
11. Replace search static index with real recent/history/content results.

### P3

12. Polish final-scroll clearance under the tab bar.
13. Add visible success/failure feedback for share, clipboard, saved versions, reminders.
14. Tighten long-copy sheets and dark-mode icon audits for missing screens.

## Recommended Execution Order

1. Auth result + profile-management slice.
2. Notes/readings persistence and honesty slice.
3. Calendar intelligence slice.
4. Compatibility slice.
5. Chart endpoint wiring slice: dashas -> yogas/doshas -> strength.
6. Remedies/muhurta practice slice.
7. Missing state screens and native notification permission slice.

Stop here before implementation. This audit is complete enough to start remediation, but the first remediation slice should be approved before code changes begin.
