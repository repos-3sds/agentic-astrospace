# Practitioner Mobile UI Sweep - 2026-08-06

Environment: local mobile preview 375x812, Angular dev server with temporary live Cloud Run /api proxy.
Scope: Practitioner mode, mobile routes/clicks/flows.

## Running Findings

## Executive Summary

Status: partial but evidence-backed Practitioner sweep completed on local web preview.

Tested with a temporary local QA profile because the live backend requires bearer auth and the in-app browser did not have the user's native session. Local FastAPI ran with dev auth bypass on port 8010, Angular preview ran at 375x812 on port 4200. This was a browser/mobile-preview sweep, not a connected-phone/native-WebView sweep.

What is better than expected:
- Practitioner footer routing is coherent: Today -> Yantra -> Periods -> Transits -> More all route correctly.
- Calendar date routing worked for August 6, 17, 18, and 31; I could not reproduce "every date opens one date" locally.
- Default chart style switching worked locally from Settings into both Full Chart and Vargas for South, North, and Eastern.
- Ask submitted/suggested questions correctly route into the construction-preview answer screen, and the answer route hides the footer like a chat experience.

Main quality risks still present:
- P1/P2 chart planet tap affordance is unreliable, especially in Vargas.
- P2 Practitioner chart/card routing has continuity mistakes: Jaimini does not open the Jaimini tab, and Ashtakavarga routes to reference tables instead of the interpreted Strength module.
- P2 Life Periods loses the depth tabs after switching to Yogini, despite copy implying five-level depth.
- P2 Today/Transits content still has generated wording defects and repeated explanation.
- P2 Ask composer exposes duplicate placeholder/label targeting, creating accessibility and automation ambiguity.
- P3 dark mode is no longer mixed light/dark, but contrast is heavy and chart surfaces feel visually dense.

## Reproduction Environment

- Date: 2026-08-06
- Viewport: 375x812 mobile preview
- Frontend: Angular dev server, `http://127.0.0.1:4200`
- Backend: local FastAPI, `http://127.0.0.1:8010`, `ASTROSPACE_DEV_AUTH_BYPASS=true`
- Profile: temporary local profile `Codex Practitioner QA`
- Persona: Practitioner via Settings -> Mode & tone
- Screenshots: `docs/mobile-sweep-screenshots-2026-08-06/`
- Raw route report: `/tmp/practitioner-route-report.json`
- Raw click report: `/tmp/practitioner-click-findings.json`

## Route Inventory Tested

- `/m/today`
- `/m/ask`
- `/m/ask/answer`
- `/m/chart`
- `/m/chart/full`
- `/m/chart/vargas`
- `/m/chart/periods`
- `/m/chart/yogas`
- `/m/chart/strength`
- `/m/chart/reference`
- `/m/chart/reference/ashtakavarga`
- `/m/compat`
- `/m/readings`
- `/m/notes`
- `/m/remedies`
- `/m/muhurta`
- `/m/transits`
- `/m/transits/full`
- `/m/calendar`
- `/m/calendar/day?date=2026-08-06`
- `/m/calendar/day?date=2026-08-17`
- `/m/calendar/day?date=2026-08-18`
- `/m/calendar/day?date=2026-08-31`
- `/m/settings`
- `/m/settings/appearance`
- `/m/settings/mode`
- `/m/settings/conventions`
- `/m/settings/location`
- `/m/settings/festivals`
- `/m/settings/notifications`
- `/m/settings/interaction`
- `/m/settings/profiles`
- `/m/search`
- `/m/notifications`

## Findings

### P1 - Planet Detail Taps Are Not Reliably Discoverable Or Accessible

- Gap type: Broken interaction / accessibility
- Routes: `/m/chart/full`, `/m/chart/vargas`
- Source files: `ui/src/app/features/mobile/chart/chart-full.component.html`, `ui/src/app/features/mobile/chart/varga-charts.component.html`, `ui/src/app/shared/kundli-chart/kundli-chart.component.*`
- Expected: "Tap a planet to see details" should mean every planet marker/label in every rendered chart opens a clear detail sheet with deterministic tap targets and accessible names.
- Actual: Direct text taps on chart planets did not visibly open details in Full Chart. Vargas did not expose a visible/accessible `Sun` label in text lookup, and the SVG role-button selector did not visibly open a sheet.
- Repro: Open `/m/chart/vargas`; try to tap/select a planet label. Browser automation could not find a visible `Sun` text target, and `svg [role="button"]` did not change the page state.
- Evidence: `36-planet-varga-sun.png`, `43-planet-varga-role.png`; click report entries `planet detail varga Sun text tap`, `planet detail varga first svg role`.
- Recommended direction: Make `app-kundli-chart` render explicit per-planet buttons with stable `aria-label="Open Sun details"` style labels and minimum 44px hit targets. Use one shared interaction contract for D1 and all Vargas.

### P2 - Jaimini And Ashtakavarga Cards Route To The Wrong Depth

- Gap type: Wrong navigation / persona continuity
- Route: `/m/chart`
- Source file: `ui/src/app/features/mobile/chart/chart-hub.component.html` and tile config in `chart-hub.component.ts`
- Expected: Practitioner Yantra tiles should land directly on the promised module/state.
- Actual: Jaimini card routes to `/m/chart/strength` but lands on the Shadbala tab, not Jaimini. Ashtakavarga card routes to `/m/chart/reference/ashtakavarga`, which is a reference table view, not the interpreted Strength -> Ashtakavarga module.
- Repro: Practitioner -> Yantra -> tap Jaimini; observe `Strength & Advanced` opens with Shadbala selected. Tap Ashtakavarga; observe Reference screen with "Planets · 0" style rows.
- Evidence: click report entries `chart card Jaimini`, `chart card Ashtakavarga`; screenshots `04-chart-hub.png`, `09-strength.png`.
- Recommended direction: Add route state/query params or child routes for `/m/chart/strength?tab=jaimini` and `/m/chart/strength?tab=ashtakavarga`; wire tiles to those exact states.

### P2 - Life Period Depth Tabs Disappear After Switching To Yogini

- Gap type: Incomplete state / misleading copy
- Route: `/m/chart/periods`
- Source file: `ui/src/app/features/mobile/chart/life-periods.component.html`
- Expected: If the header says "five-level stack" and Practitioner mode promises depth, users should either get available Yogini depth or clear copy that Yogini has only a cycle view.
- Actual: After tapping Yogini, depth tabs `Maha`, `Antar`, `Pratyantar`, `Sookshma`, `Prana` disappear. Attempts to click those tabs fail because no matching controls exist.
- Repro: Open `/m/chart/periods`; tap Yogini; try Maha/Antar/Sookshma/Prana.
- Evidence: `07-periods.png`, `37-period-tabs.png`; click errors for `period tab Maha`, `Antar`, `Pratyantar`, `Sookshma`, `Prana`.
- Recommended direction: Separate copy by system. Either implement Yogini depth tabs if valid in product requirements, or remove "five-level stack" copy and show a clear "Yogini cycle only" state.

### P2 - Ask Composer Has Duplicate Placeholder/Accessible Target

- Gap type: Accessibility / form control structure
- Routes: `/m/ask`, `/m/ask/answer`
- Source file: `ui/src/app/features/mobile/ask/ask-composer.component.ts`
- Expected: One textbox should expose the "Your question" accessible name and placeholder.
- Actual: `getByPlaceholder('Your question')` resolves to both the custom `<as-ask-composer>` host and the inner `<input>`, causing strict-mode ambiguity. Real assistive tech may also see a noisy custom element.
- Repro: On `/m/ask`, select by placeholder "Your question"; two elements match.
- Evidence: click report entry `ask typed send`. Screenshot `41-ask-typed-role.png` confirms role-based submit works once targeting the actual textbox.
- Recommended direction: Do not bind placeholder-like attributes onto the component host; keep semantic label/placeholder only on the input. Consider adding `role="none"` or host attribute cleanup if Angular input reflection is leaking.

### P2 - Today Reflect Suggestions Contain Broken Generated Grammar

- Gap type: Content quality / Ask wiring
- Route: `/m/today`
- Source file: `ui/src/app/features/mobile/today/today.component.html` plus `askSuggestions()` in `today.component.ts`
- Expected: Suggestions should read like polished user questions.
- Actual: One suggestion rendered as: "What should I do with downshift. this is a day for maintenance, rest, and ignoring manufactured urgency. today?"
- Repro: Open `/m/today`, scroll to "Reflect with SIDDHA".
- Evidence: route report body for `today`; screenshot `02-today.png` for the containing section.
- Recommended direction: Generate suggestions from stable intent templates and short labels, not by interpolating full advice prose into a question.

### P2 - Gochara Domain Cards Repeat The Same Sentence

- Gap type: Content quality / interpretation UX
- Route: `/m/transits`
- Source file: `ui/src/app/features/mobile/transits/gochara.component.ts`
- Expected: Practitioner domain cards should summarize once, then add actionable interpretation or evidence.
- Actual: "Current evidence is comparatively supportive..." repeats in the small text and again in the body for Career.
- Repro: Open `/m/transits`; first domain card repeats the same lead.
- Evidence: route report body for `transits`, screenshot `10-transits.png`.
- Recommended direction: In `domainMeaning()` / template, avoid rendering both `main_theme` and `reading` when the reading starts with the same sentence. Deduplicate or split into "meaning" and "action".

### P2 - Search Empty State Is Too Bare

- Gap type: Incomplete empty state / utility UX
- Route: `/m/search`
- Source file: `ui/src/app/features/mobile/utility/search.component.html`
- Expected: Empty search should offer common destinations, recent searches, or category shortcuts.
- Actual: Initial screen only shows title, search input, and clear button.
- Repro: Open `/m/search` with no recent searches.
- Evidence: `23-search.png`.
- Recommended direction: Add default grouped shortcuts for Today, Ask, Charts, Vargas, Periods, Transits, Calendar, Settings.

### P3 - Dark Mode Is Functional But Over-Dense

- Gap type: Visual polish / contrast
- Routes: `/m/today`, `/m/chart/full`, `/m/settings`
- Source files: shared mobile tokens/styles plus route SCSS files
- Expected: Dark mode should preserve hierarchy without making large surfaces feel muddy or overly heavy.
- Actual: It no longer mixes light and dark, but chart/full and settings use very heavy brown-black fields; dividers and chart lines dominate. The Today hero becomes a wide, low-contrast slab.
- Repro: Settings -> Appearance -> Dark, then open Today/Chart/Settings.
- Evidence: `44-dark-today.png`, `44-dark-chart-full.png`, `44-dark-settings.png`.
- Recommended direction: Tune semantic dark tokens rather than hardcoding per-screen colors. Increase separation between page background, surfaces, chart canvas, and controls.

### P3 - Hidden Toast Container Is Horizontally Positioned Offscreen

- Gap type: Layout hygiene
- Routes: nearly every route
- Source files: app shell / PrimeNG toast configuration and global mobile styles
- Expected: Hidden toast container should not create offscreen layout offenders in mobile metrics.
- Actual: `p-toast` is 400px wide at `left:-45` in a 375px viewport on every route.
- Repro: Inspect layout offenders for any route.
- Evidence: route report offenders across all routes.
- Recommended direction: Override mobile toast width/position to `left: max(12px, safe-left)`, `right: max(12px, safe-right)`, `width:auto`.

## Verified Working Locally

- Practitioner footer: Today, Yantra, Periods, Transits, More.
- Calendar date routing for August 6, 17, 18, 31.
- Festival sheet opens for Nag Panchami and includes What to do, How to do it, Mantra/Prayer.
- Ask suggested question and typed question route to `/m/ask/answer` construction preview.
- Ask answer hides bottom nav.
- Chart style preference persists from Settings into Full Chart and Vargas for South, North, Eastern.
- Settings Appearance, Mode, Conventions, Location, Festivals, Notifications, Interaction, Profiles routes render without console errors.

## Not Yet Verified

- Native Android/iOS safe-area behavior.
- Native keyboard behavior.
- Native haptics toggle effect.
- Real signed-in live backend session.
- Connected-phone reproduction of calendar date issue.
- Full destructive/account flows: delete profile, delete account, sign out.

## Screenshot List

Key screenshots:
- `02-today.png`
- `04-chart-hub.png`
- `05-chart-full.png`
- `06-chart-vargas.png`
- `07-periods.png`
- `09-strength.png`
- `10-transits.png`
- `12-calendar.png`
- `13-calendar-day.png`
- `14-settings.png`
- `23-search.png`
- `38-calendar-festival.png`
- `41-ask-typed-role.png`
- `44-dark-today.png`
- `44-dark-chart-full.png`
- `44-dark-settings.png`

Full screenshot folder: `docs/mobile-sweep-screenshots-2026-08-06/`

## Prioritized Backlog

1. P1: Make planet markers deterministic, accessible, and tappable across D1 and all Vargas.
2. P2: Fix Practitioner Yantra tile routing for Jaimini and Ashtakavarga.
3. P2: Clarify/implement Life Period depth behavior for Yogini vs Vimshottari.
4. P2: Fix Ask composer host/input semantic duplication.
5. P2: Clean Today suggestion generation and Gochara repeated text.
6. P2: Fill Search empty state with useful default navigation.
7. P3: Tune dark semantic tokens for chart/settings surfaces.
8. P3: Fix mobile toast width/position hygiene.

