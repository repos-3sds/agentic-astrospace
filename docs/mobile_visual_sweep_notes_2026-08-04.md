# Mobile Visual Sweep Notes - 2026-08-04

Scope: installed Android APK on connected phone, mobile UI only.

Device:
- Samsung SM-S938W via ADB (`R5CY11Y5W7L`)
- App package in focus: `app.astrospace.mobile`
- Date/time: 2026-08-04, Asia/Singapore

Rules for this pass:
- Audit only. No fixes during sweep.
- Do not mark a finding verified unless reproduced on phone.
- Capture screenshots under `docs/mobile-sweep-screenshots-2026-08-04/`.

## Route / Screen Notes

- `/m/today` / Today, light mode, Balanced: loads after relaunch; top status area is visible; main card reads current location `Singapore`; footer overlaps next content at bottom while scrolling.
- `/m/ask` / Ask home, light mode, Balanced: visually coherent at rest; history icon visible in light mode; input suggests live answer flow and needs under-construction behavior validation.
- `/m/chart` / Chart hub, light mode, Balanced: D1 chart visible; selected footer tab remains `Chart`; lower content/cards are partially hidden by floating footer.
- `/m/calendar` / Calendar, light mode, Balanced: month renders; selected date is Aug 4; festival list still displays month-level festivals (17/26/28) below selected date; red dots visible under some dates with unclear meaning.
- `/m/settings` / Settings, light mode, Balanced: icon style is more consistent than previous phone photo; lower rows are hidden behind footer; Settings is a subpage but footer remains visible.
- `/m/settings/appearance`: decorative Siddha wordmark is used inside sentence copy and overlaps the line.
- `/m/settings/mode`: layout is coherent; footer still present on subpage.
- `/m/settings/interaction`: haptic toggle exists and is not dummy at the UI level.
- `/m/settings/notifications`: notification toggles exist, but delivery is explicitly not enabled in this build.
- `/m/calendar` festival sheet: festival detail has what/how/mantra content; reminder CTA is shown even though push delivery is not active.
- Dark mode Today/Ask/Chart/Calendar/Settings: coherent enough to use, but palette hierarchy is weak because most surfaces collapse into near-black/brown/red.
- `/m/chart/full`: full chart renders in dark mode; D-chart selector red dots unexplained; chart contrast borderline.
- `/m/chart` divisional charts: D9 chart renders; tapping Mercury opens planet detail successfully.
- `/m/ask` answer flow: suggested question opened under-construction answer once, but subsequent/follow-up state got stuck on loading for 11+ seconds.
- Guided `/m/explore`: hub exists and contains Your Story, What to Do, Your Chart, Life Chapters.
- Guided `/m/your-story`: has back button and content, but user observed it feels hardcoded and font/design-system consistency is not acceptable. Life-domain explanations are weak and read like placeholders.

## Findings

### F01 - Intermittent Black Native Frame After Navigation Batch
- Priority: P1 until reproduced/isolated; could be P2 if only capture/app-switch artifact.
- Gap type: Native render / WebView blank state.
- Route: observed while batch navigating main tabs after Life Periods/back state.
- Evidence: `01-today.png` through `05-more-settings.png` captured all-black frames; relaunch recovered in `06-relaunch.png`.
- Expected: app should never render a full black screen during normal tab navigation.
- Actual: ADB screenshots captured full black frames while app/phone interaction sequence was running; relaunch recovered.
- Repro status: intermittent, needs deliberate repro.

### F02 - Floating Footer Obscures Scroll Content
- Priority: P2.
- Gap type: Safe area / final scroll clearance.
- Route: `/m/chart`, `/m/calendar`, `/m/settings`.
- Evidence: `08-chart-retry.png`, `09-calendar-retry.png`, `10-more-retry.png`.
- Expected: last rows/cards should scroll above footer and Android gesture/nav bar.
- Actual: cards and rows sit behind the floating footer and home indicator area.

### F03 - Calendar Selected-Day Semantics Are Confusing
- Priority: P2.
- Gap type: Calendar UX / data presentation.
- Route: `/m/calendar`.
- Evidence: `09-calendar-retry.png`.
- Expected: selecting Aug 4 should make it clear whether below content is for Aug 4 or the whole month.
- Actual: selected Aug 4 is highlighted but below content starts with Aug 17, Aug 26, Aug 28 festivals, so it reads like date selection is ignored.

### F04 - Calendar Red Dots Lack Meaning
- Priority: P3.
- Gap type: Visual affordance / calendar legend.
- Route: `/m/calendar`.
- Evidence: `09-calendar-retry.png`.
- Expected: red dots should map clearly to festivals, signals, or selected filters.
- Actual: dots appear under 17/26/28 without a legend or direct explanation on screen.

### F05 - Decorative Siddha Font Used Inline Breaks Text Layout
- Priority: P2.
- Gap type: Typography / brand usage.
- Route: `/m/settings/appearance`.
- Evidence: `11-settings-appearance.png`.
- Expected: Samarkan/Siddha treatment should be reserved for controlled brand marks or sized so it aligns with surrounding text.
- Actual: “Choose how siddha looks on this device.” has the Siddha wordmark colliding with the sentence baseline.

### F06 - Notifications Are Honest But Still Not Functionally Complete
- Priority: P2.
- Gap type: Native feature incompleteness.
- Route: `/m/settings/notifications`, Calendar festival reminder sheet.
- Evidence: `19-settings-notifications-clean.png`, `16-settings-notifications-retarget.png`, `17-settings-location-retarget.png`.
- Expected: toggles and “Remind me” should either schedule real local/push notifications or clearly gate the action.
- Actual: settings explain push is not enabled, but toggles and reminder CTA remain active-looking.

### F07 - Back/State Retargeting Can Be Confusing During Cross-Tab Navigation
- Priority: P2.
- Gap type: Navigation state.
- Route: Settings back flow to Calendar/festival sheet during sweep.
- Evidence: `16-settings-notifications-retarget.png`, `17-settings-location-retarget.png`.
- Expected: after leaving Settings subpages, subsequent taps should be predictable and remain in the intended Settings context.
- Actual: after back navigation during the sweep, taps intended for Settings opened Calendar festival sheets; needs direct repro with video/trace before fixing.

### F08 - Dark Mode Palette Has Weak Hierarchy
- Priority: P2.
- Gap type: Visual design / contrast hierarchy.
- Route: `/m/today`, `/m/ask`, `/m/chart`, `/m/calendar`, `/m/settings`.
- Evidence: `21-dark-today.png` through `25-dark-settings.png`, `26-dark-full-chart.png`, `27-dark-varga-charts.png`.
- Expected: dark mode should preserve content hierarchy with distinct surfaces, accessible contrast, and non-monotone accents.
- Actual: most cards and controls sit in a narrow black/brown/red range; chart grid/labels especially feel muted.

### F09 - Full/Divisional Chart Selector Dots Are Unexplained
- Priority: P3.
- Gap type: Visual affordance / chart navigation.
- Route: `/m/chart/full`, `/m/chart/varga`.
- Evidence: `26-dark-full-chart.png`, `27-dark-varga-charts.png`.
- Expected: dots should have a clear meaning or be replaced by explicit state/availability markers.
- Actual: D2/D3/D4 etc and D8/D11 show small colored dots with no legend.

### F10 - Ask Follow-Up/Typed Flow Can Stick On Loading
- Priority: P1.
- Gap type: Ask loading state / incomplete flow.
- Route: `/m/ask` answer screen.
- Evidence: `31-dark-ask-typed-result.png`, `32-dark-ask-typed-after-wait.png`.
- Expected: typed/follow-up submission should show the same under-construction answer, or a clear disabled state.
- Actual: screen remained on “Reading your chart...” after 11+ seconds and still showed the previous question bubble.

### F11 - Divisional Chart Planet Tap Works In D9 Path
- Priority: Not a defect in this pass.
- Gap type: Verification note.
- Route: `/m/chart/varga`.
- Evidence: `28-varga-planet-tap.png`.
- Result: tapping Mercury in D9 opened a detail sheet.

### F12 - Your Story Feels Hardcoded And Typographically Off-System
- Priority: P1.
- Gap type: Persona content wiring / design-system consistency.
- Route: Guided `/m/your-story`.
- Evidence: `42-guided-your-story.png`; user confirmed during sweep: “UI is hardcoded in Your Story; fonts and all not consistent.”
- Expected: Your Story should use the app design system and be clearly generated/wired from profile/chart data, with typography consistent with the rest of Siddha.
- Actual: broad screen structure is present, but the content and type treatment feel hardcoded and inconsistent.

### F14 - Your Story Life-Domain Explanations Lack Real Interpretive Depth
- Priority: P1.
- Gap type: Content quality / astrology interpretation.
- Route: Guided `/m/your-story`.
- Evidence: `42-guided-your-story.png`; user confirmed life-domain explanations are bad.
- Expected: each life domain should explain what the chart means for the person in plain, specific, useful guidance.
- Actual: cards use generic placement-based phrasing and do not deliver the “Siddha way of life guide” promise.

### F13 - Guided Subpage Footer Label Changes From Explore To Your Story
- Priority: P3.
- Gap type: Navigation consistency.
- Route: Guided `/m/explore` -> `/m/your-story`.
- Evidence: `41-guided-middle-tab.png`, `42-guided-your-story.png`, `43-guided-your-story-back.png`.
- Expected: if Explore is the persona tab, subpages should keep footer mental model stable or intentionally hide footer.
- Actual: footer middle label changes to `Your Story` while inside the subpage, then returns to `Explore` on back.

## Screenshots

- `00-current-state.png`
- `01-today.png` through `05-more-settings.png` - black-frame batch, kept as evidence
- `06-relaunch.png` - Today after clean relaunch
- `07-ask-retry.png`
- `08-chart-retry.png`
- `09-calendar-retry.png`
- `10-more-retry.png`
- `11-settings-appearance.png`
- `12-settings-mode-tone.png`
- `13-settings-notifications.png` - actually Interaction due tap retarget; retained
- `16-settings-notifications-retarget.png` - Calendar festival sheet opened during retarget issue
- `17-settings-location-retarget.png` - Calendar festival sheet opened during retarget issue
- `18-settings-clean-return.png`
- `19-settings-notifications-clean.png`
- `20-dark-appearance-selected.png`
- `21-dark-today.png`
- `22-dark-ask.png`
- `23-dark-chart.png`
- `24-dark-calendar.png`
- `25-dark-settings.png`
- `26-dark-full-chart.png`
- `27-dark-varga-charts.png`
- `28-varga-planet-tap.png`
- `31-dark-ask-typed-result.png`
- `32-dark-ask-typed-after-wait.png`
- `39-guided-mode-selected.png`
- `40-guided-today-footer.png`
- `41-guided-middle-tab.png`
- `42-guided-your-story.png`
- `43-guided-your-story-back.png`
- `44-practitioner-mode-selected.png`
- `45-practitioner-today-footer.png`
- `46-practitioner-chart-footer.png`
