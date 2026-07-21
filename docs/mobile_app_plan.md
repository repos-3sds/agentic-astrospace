# AstroSpace Mobile Application Plan

## 1. Document Control

| Field | Value |
|---|---|
| Product | AstroSpace |
| Document type | Business analysis, product requirements, and delivery checklist |
| Status | Proposed backlog |
| Primary platform | Responsive Angular web application |
| Future platforms | iOS and Android through Capacitor |
| Backend | FastAPI, PostgreSQL/Supabase, Supabase Auth |
| Target audience | Product, design, frontend, backend, QA, and release teams |
| Last updated | 2026-07-21 |

## 2. Purpose

This document defines the work required to make AstroSpace fully usable on mobile browsers and to prepare the same Angular application for eventual distribution as native iOS and Android apps.

The immediate objective is not merely to make the desktop interface smaller. The mobile experience must make charts readable, complex astrology workflows understandable, navigation reachable with one hand, and long-form readings comfortable to consume without horizontal page scrolling.

## 3. Product Goal

AstroSpace users must be able to complete the primary product journeys from a phone:

- Sign in and manage their account.
- Select, create, and edit a Kundli profile.
- Understand what matters today from the dashboard.
- Read and inspect Vedic calculations and charts.
- Navigate Dashas, Gocharam, Calendar, Ashtakavarga, Yogas, and Compatibility.
- Generate and revisit AI readings.
- Receive Context Engine-driven daily guidance and domain-specific answers grounded in the selected profile.
- Change calculation and display preferences.
- Use the product safely on iOS and Android devices without clipped controls, unreadable charts, or accidental horizontal page scrolling.

## 4. Product Principles

- **One product, adaptive presentation:** Desktop, tablet, mobile web, and future native apps use the same Angular application and business rules.
- **Astrology remains inspectable:** Charts and calculated data must not be hidden or oversimplified merely to fit a small screen.
- **Progressive disclosure:** Mobile screens show the most important result first and expose deeper calculations through drill-down, tabs, accordions, sheets, or focused views.
- **Touch-first interaction:** Controls are sized and positioned for fingers rather than mouse pointers.
- **No accidental horizontal page scroll:** Only explicitly identified matrices or comparison surfaces may scroll horizontally inside a clearly bounded container.
- **Accessible by default:** Responsive work must include keyboard, screen-reader, contrast, zoom, and reduced-motion behavior.
- **Native-ready, not native-dependent:** Core workflows continue working in a browser while native capabilities are introduced through replaceable Angular services.

## 5. Scope

### 5.1 In Scope for Mobile Web

- Responsive application shell and navigation.
- Mobile profile selection and Kundli management.
- Responsive behavior for every authenticated product route.
- Mobile-readable Kundli charts in South Indian, North Indian, and Eastern styles.
- Mobile workflows for dense calculations, tables, timelines, and comparisons.
- Responsive dialogs, overlays, notifications, loading states, and errors.
- Mobile integration of the Context Engine for daily guidance, question routing, domain context, source signals, and provenance.
- Accessibility and touch interaction standards.
- Performance improvements needed for mobile networks and devices.
- Installable Progressive Web App behavior.
- Automated and manual responsive test coverage.

### 5.2 In Scope for Native Readiness

- Capacitor integration architecture.
- iOS and Android safe-area handling.
- Supabase authentication callback and deep-link strategy.
- Native back-button and app lifecycle behavior.
- Abstractions for secure storage, notifications, sharing, downloads, and external links.
- App-store readiness checklist.

### 5.3 Out of Scope for the First Mobile Release

- Rewriting the frontend in Flutter, React Native, or a second mobile framework.
- Offline recalculation of the complete astrology engine on the device.
- Push-notification delivery infrastructure, unless separately prioritized.
- App Store and Play Store submission fees and organizational enrollment.
- New astrology calculations unrelated to mobile usability.
- Redesigning backend calculation rules solely for presentation reasons.

## 6. Current-State Findings

- The authenticated shell uses a persistent sidebar at mobile widths. It collapses to a narrow desktop rail instead of becoming a mobile navigation system.
- The top bar wraps profile and profile-management controls, consuming significant vertical space.
- Multiple astrology modules use desktop tables or multi-column panels with horizontal scrolling.
- Responsive breakpoints are implemented independently across feature stylesheets, creating inconsistent behavior.
- Kundli charts scale as square SVGs, but label density and multi-planet houses need mobile-specific handling and focused inspection.
- Several overlays are centered desktop dialogs; mobile requires bottom-sheet or full-screen presentation.
- The Angular project does not currently include Capacitor packages or native projects.
- The Context Engine already exposes authenticated daily guidance and domain-context APIs; mobile presentation must consume these outputs without duplicating routing or astrology logic in the frontend.

## 7. Target Breakpoints and Devices

The UI must be fluid between breakpoints. The following values are test anchors, not device-specific layouts.

| Experience | Width | Expected navigation |
|---|---:|---|
| Small phone | 320-374 px | Mobile top bar and bottom navigation |
| Standard phone | 375-429 px | Mobile top bar and bottom navigation |
| Large phone | 430-599 px | Mobile top bar and bottom navigation |
| Tablet portrait | 600-899 px | Tablet shell or expanded mobile shell |
| Tablet landscape | 900-1199 px | Collapsible desktop sidebar |
| Desktop | 1200 px and above | Full desktop shell |

Mandatory test viewports:

- 360 x 800: small Android reference.
- 390 x 844: standard iPhone reference.
- 430 x 932: large iPhone reference.
- 768 x 1024: tablet portrait reference.
- 1024 x 768: tablet landscape reference.
- 844 x 390: phone landscape reference.

## 8. User Personas

### P1. Everyday Astrology User

Wants a clear explanation of today, important periods, and upcoming changes without needing to understand every technical term.

### P2. Astrology Practitioner

Needs readable charts, exact planetary data, Dashas, Gocharam, Ashtakavarga, and calculation conventions while working with multiple profiles.

### P3. Family Profile Manager

Maintains Kundlis for family and friends and needs fast profile switching, search, comparison, and clear identity context.

### P4. Returning Mobile User

Opens AstroSpace briefly during the day and expects session continuity, the correct active profile, fast loading, and direct access to recent information.

## 9. Priority Definitions

| Priority | Meaning |
|---|---|
| P0 | Release blocker; the mobile product is not usable without it |
| P1 | Required for the first complete mobile release |
| P2 | Valuable enhancement after the primary mobile journeys are stable |
| P3 | Native expansion or later optimization |

---

# Epic M01: Responsive Foundation

## M01-US01: Shared Responsive Design Tokens

**Priority:** P0  
**User story:** As a user, I want spacing, typography, controls, and layouts to behave consistently across mobile screens so that the application feels like one coherent product.

### Acceptance Criteria

1. Given the authenticated app is opened at any supported viewport, when a screen is rendered, then page gutters, section spacing, control heights, and typography follow shared responsive tokens.
2. Given a viewport changes between mobile, tablet, and desktop, when the layout responds, then content does not briefly overlap or require a reload.
3. Given the viewport is 320 px wide, when any primary route is opened, then the document body has no horizontal overflow.
4. Given browser text zoom is set to 200%, when a primary workflow is used, then content remains readable and controls remain reachable.
5. Given the user has enabled reduced motion, when navigation or overlays change state, then non-essential animation is removed or reduced.

### Delivery Checklist

- [ ] Define shared mobile, tablet, and desktop breakpoints.
- [ ] Define responsive page gutters and section gaps.
- [ ] Define compact, standard, and comfortable control heights.
- [ ] Define responsive heading and body type scales without viewport-width font scaling.
- [ ] Add safe-area CSS variables using `env(safe-area-inset-*)`.
- [ ] Add reusable utilities for mobile-only and desktop-only content where semantically necessary.
- [ ] Audit fixed widths and minimum widths across authenticated routes.
- [ ] Remove page-level overflow workarounds that mask layout defects.

### QA Checklist

- [ ] Verify all mandatory viewport sizes.
- [ ] Verify browser zoom at 100%, 150%, and 200%.
- [ ] Verify light and dark themes.
- [ ] Verify reduced-motion preference.
- [ ] Verify no unexpected layout shift during route loading.

## M01-US02: Touch and Interaction Standards

**Priority:** P0  
**User story:** As a mobile user, I want controls to be easy to tap without triggering adjacent actions.

### Acceptance Criteria

1. Given an actionable control is presented on mobile, then its interactive target is at least 44 x 44 CSS pixels, except for non-interactive chart labels.
2. Given two destructive or high-impact actions are adjacent, then sufficient spacing prevents accidental activation.
3. Given a control is icon-only, then it has an accessible name and a visible tooltip where hover or long-press help is appropriate.
4. Given the software keyboard is open, then the focused input and its primary action remain visible.
5. Given a user operates the app with keyboard navigation, then focus order follows the visual order and focus remains visible.

### Delivery Checklist

- [ ] Audit all icon buttons, tabs, toggles, table actions, and chart controls.
- [ ] Standardize pressed, focused, disabled, loading, and destructive states.
- [ ] Ensure sticky controls do not cover the final content row.
- [ ] Add keyboard-safe spacing for forms and AI composer surfaces.
- [ ] Add `aria-label` or visible text to all icon-only actions.

---

# Epic M02: Mobile Application Shell

## M02-US01: Mobile Top App Bar

**Priority:** P0  
**User story:** As a mobile user, I want a compact header that tells me where I am and which profile is active without consuming excessive screen space.

### Acceptance Criteria

1. Given the viewport is below the mobile-shell breakpoint, when an authenticated route loads, then the desktop top bar is replaced by a compact mobile app bar.
2. Given a profile is active, then the app bar shows a truncated profile identity without pushing actions off screen.
3. Given no profile is active, then the app bar clearly prompts the user to choose a profile.
4. Given the current route has a title, then the title remains readable at 320 px width.
5. Given the page scrolls, then the app bar behavior is stable and does not cause content jumps.

### Delivery Checklist

- [ ] Create a mobile app-bar variant.
- [ ] Place current route title and active-profile trigger in a clear hierarchy.
- [ ] Move edit/delete profile actions into a contextual menu on mobile.
- [ ] Keep desktop header behavior unchanged above the mobile breakpoint.
- [ ] Apply safe-area inset padding on iOS.

## M02-US02: Bottom Navigation

**Priority:** P0  
**User story:** As a mobile user, I want the most common destinations within thumb reach so that I can move through AstroSpace quickly.

### Proposed Primary Destinations

- Home
- Vedic
- Calendar
- Ask AI
- More

### Acceptance Criteria

1. Given the user is authenticated on a phone, then a bottom navigation bar is visible on all primary app routes except immersive overlays and full-screen chart mode.
2. Given a destination is active, then its icon and label communicate the selected state using more than color alone.
3. Given the device has a home indicator, then the navigation respects the bottom safe area.
4. Given the user navigates to a route inside the More menu, then More displays an active-context state.
5. Given the screen uses browser or native back navigation, then the previously selected route and scroll behavior follow the route history.
6. Given the bottom navigation is present, then page content includes enough bottom padding to remain unobstructed.

### Delivery Checklist

- [ ] Define the five primary navigation destinations.
- [ ] Reuse the existing Lucide icon system.
- [ ] Add active, focus, pressed, and notification-badge states.
- [ ] Hide the desktop sidebar on mobile.
- [ ] Preserve desktop and tablet sidebar behavior.
- [ ] Add safe-area-aware content padding.
- [ ] Verify deep-linked routes select the correct navigation state.

## M02-US03: More Navigation Sheet

**Priority:** P0  
**User story:** As a mobile user, I want all specialist astrology modules to remain accessible without overcrowding the bottom navigation.

### Acceptance Criteria

1. Given the user taps More, then a full-height sheet or full-screen menu presents all non-primary modules.
2. Given the menu opens, then it includes Chart, Varga Charts, Dashas, Transits, Gocharam, Ashtakavarga, Yogas and Doshas, Compatibility, Notes, Readings, Settings, theme control, and Logout as applicable.
3. Given an item is selected, then the menu closes and the selected route loads.
4. Given the menu is open, then browser/native back closes the menu before leaving the current route.
5. Given the user uses a screen reader, then focus moves into the menu on open and returns to the More trigger on close.

### Delivery Checklist

- [ ] Group navigation into understandable sections.
- [ ] Keep Ask AI visually distinct without overwhelming other actions.
- [ ] Include account, appearance, and logout controls.
- [ ] Add focus trapping and Escape/back dismissal.
- [ ] Prevent background scrolling while the menu is open.

## M02-US04: Tablet Navigation

**Priority:** P1  
**User story:** As a tablet user, I want navigation that uses the available space without inheriting cramped phone behavior or oversized desktop behavior.

### Acceptance Criteria

1. Given the app is opened between 600 px and 899 px, then the selected tablet navigation mode remains usable in portrait and landscape.
2. Given the device rotates, then navigation changes without losing the current route, selected profile, or in-progress read state.
3. Given the sidebar is available in tablet landscape, then it can collapse without introducing horizontal content overflow.

### Delivery Checklist

- [ ] Decide and document the tablet threshold after visual testing.
- [ ] Validate compact sidebar versus bottom navigation at 768 px.
- [ ] Preserve route and feature state during orientation changes.

---

# Epic M03: Profile and Account Journeys

## M03-US01: Mobile Profile Selection

**Priority:** P0  
**User story:** As a family profile manager, I want to search and switch profiles from a mobile-friendly overlay so that I always know whose chart I am viewing.

### Acceptance Criteria

1. Given the user taps the active-profile trigger, then a searchable mobile profile sheet opens.
2. Given a search term matches a name, relationship, sign, or birth city, then matching profiles are shown.
3. Given a profile name is long, then it truncates visually without hiding the profile's distinguishing information.
4. Given a profile is selected, then the sheet closes, all profile-dependent data refreshes, and the active identity is updated globally.
5. Given the profile list is empty, then the user receives a clear Add Kundli action.
6. Given data loading fails, then the overlay shows an actionable error without closing unexpectedly.

### Delivery Checklist

- [ ] Convert the existing centered overlay into a mobile bottom sheet or full-screen picker.
- [ ] Keep search visible while the profile list scrolls.
- [ ] Add active-profile indication.
- [ ] Add empty, loading, and error states.
- [ ] Verify profile switching invalidates stale feature data.

## M03-US02: Add and Edit Kundli on Mobile

**Priority:** P0  
**User story:** As a user, I want to create or edit a Kundli from my phone without struggling with a desktop modal or keyboard obstruction.

### Acceptance Criteria

1. Given the user starts Add Kundli on mobile, then the form opens as a full-screen flow or mobile-appropriate sheet.
2. Given a field has an error, then the message appears next to that field and is announced accessibly.
3. Given the user searches for a birthplace, then search results are readable, selectable, and not covered by the keyboard.
4. Given the user submits valid details, then progress is shown until chart generation completes.
5. Given submission succeeds, then the new or updated profile becomes active and the user reaches its Overview.
6. Given the user attempts to leave with unsaved changes, then the app requests confirmation.

### Delivery Checklist

- [ ] Group birth details into a logical mobile field order.
- [ ] Use mobile-appropriate date and time input behavior.
- [ ] Verify city search and timezone selection on touch devices.
- [ ] Keep submit action reachable above the keyboard and safe area.
- [ ] Add pending, success, validation, and server-error states.

## M03-US03: Mobile Account and Session Management

**Priority:** P1  
**User story:** As a signed-in user, I want secure account and logout controls on mobile so that I can manage my session confidently.

### Acceptance Criteria

1. Given the user opens Settings or More, then account identity, settings, and Logout are available.
2. Given the user taps Logout, then a confirmation appears and logout clears local authenticated state.
3. Given an authenticated session expires, then the user is directed to authentication and returned to the intended route after signing in where possible.
4. Given the user signs in with Google or email on mobile web, then the callback returns to the correct AstroSpace origin.
5. Given the future native app receives an OAuth callback, then a supported deep link can complete the same authentication flow.

### Delivery Checklist

- [ ] Centralize post-login and post-logout navigation.
- [ ] Define web and future native Supabase redirect URLs.
- [ ] Remove sensitive state from ordinary local storage where secure storage is required later.
- [ ] Document session-expiry and refresh-token behavior.

---

# Epic M04: Mobile Content and Component Patterns

## M04-US01: Responsive Page Headers and Hero Sections

**Priority:** P1  
**User story:** As a mobile user, I want each page to explain its current astrological context without forcing the actual content below the first screen.

### Acceptance Criteria

1. Given a major astrology page contains a hero, then mobile presentation shows the key current result and a concise explanation before secondary detail.
2. Given a hero contains multiple metrics, then they wrap or stack without clipping.
3. Given the user opens the page at 390 x 844, then the first viewport shows the beginning of actionable content below the header.
4. Given data is unavailable, then the hero uses an intentional empty or error state instead of collapsing unpredictably.

### Delivery Checklist

- [ ] Define compact mobile hero spacing and typography.
- [ ] Replace wide metric rows with responsive metric groups.
- [ ] Keep data-backed context and provenance accessible.
- [ ] Remove decorative height that delays primary information.

## M04-US02: Mobile Subnavigation

**Priority:** P0  
**User story:** As a user, I want to jump between sections within Vedic, Calendar, Gocharam, and other long pages instead of scrolling through the entire page.

### Acceptance Criteria

1. Given a page has multiple major sections, then a page-level tab or section navigator is available near the top.
2. Given tabs exceed available width, then the control scrolls horizontally within itself and clearly indicates additional options.
3. Given a tab is selected, then its content is shown without resetting unrelated page state.
4. Given the tab row becomes sticky, then it does not overlap the mobile app bar or obscure section content.
5. Given the user navigates with keyboard or assistive technology, then tab semantics and selected state are correctly exposed.

### Delivery Checklist

- [ ] Inventory pages requiring subnavigation.
- [ ] Use route query/state where a section must be deep-linkable.
- [ ] Preserve selected section when returning from a detail view.
- [ ] Avoid nested sticky elements competing for vertical space.

## M04-US03: Dense Data Presentation

**Priority:** P0  
**User story:** As an astrology practitioner, I want exact calculated data to remain readable on mobile without losing important fields.

### Acceptance Criteria

1. Given a desktop table contains many columns, then mobile uses one of the approved patterns: stacked row cards, primary columns plus expandable detail, focused column selection, or an explicitly bounded matrix.
2. Given fields are hidden from the first view, then the user can reveal every original field.
3. Given a table has sorting or filtering, then equivalent controls remain available on mobile.
4. Given horizontal scrolling is necessary for a matrix, then only the matrix container scrolls and row/column context remains understandable.
5. Given values are copied or inspected, then abbreviations have accessible full labels or supporting detail.

### Delivery Checklist

- [ ] Classify every table as record list, comparison, timeline, or matrix.
- [ ] Build a reusable mobile data-row component.
- [ ] Build expandable detail rows for secondary columns.
- [ ] Add compact labels for degree, Rashi, Nakshatra, Paada, RL, NL, SL, and SSL.
- [ ] Keep complete values available to practitioners.
- [ ] Remove document-level horizontal scroll.

## M04-US04: Mobile Overlay and Dialog System

**Priority:** P0  
**User story:** As a mobile user, I want dialogs and pickers to fit my screen and respond naturally to touch and back navigation.

### Acceptance Criteria

1. Given a dialog opens on a phone, then it uses a full-screen or bottom-sheet layout according to task complexity.
2. Given content exceeds available height, then only the intended dialog content area scrolls.
3. Given the keyboard opens, then focused inputs and primary actions remain reachable.
4. Given browser/native back is activated, then the topmost dismissible overlay closes first.
5. Given a destructive confirmation opens, then the destructive and cancel actions are clearly differentiated.

### Delivery Checklist

- [ ] Define when to use bottom sheet, full-screen form, menu, confirmation, and toast.
- [ ] Standardize overlay z-index layers.
- [ ] Add safe-area padding.
- [ ] Add focus trap and focus return.
- [ ] Verify background scroll lock.

---

# Epic M05: Kundli Chart Experience

## M05-US01: Readable Full-Width Charts

**Priority:** P0  
**User story:** As a user, I want South Indian, North Indian, and Eastern charts to fill the available mobile width and remain legible.

### Acceptance Criteria

1. Given any supported chart style is selected, when viewed at 360 px width, then the chart uses the available content width while retaining its intended geometry.
2. Given a chart contains house numbers, signs, planets, and condition symbols, then labels do not overlap under normal supported chart density.
3. Given a house contains multiple planets, then every planet name is shown using an approved abbreviation without a `+N` summary.
4. Given the chart style is South Indian, then house numbers and sign labels remain in their designated corners.
5. Given the chart style is Eastern, then the Ascendant is placed in the actual rising-sign compartment according to the Eastern chart convention.
6. Given the user changes chart style, then the preference is retained according to the user's settings.

### Delivery Checklist

- [ ] Add mobile-specific SVG typography and spacing rules.
- [ ] Add density handling for houses containing several planets.
- [ ] Preserve Exaltation, Debilitation, Retrograde, Combustion, and Vargottama symbols.
- [ ] Test long and dense representative charts in all three styles.
- [ ] Verify chart legend wrapping and contrast.

## M05-US02: House Inspection Mode

**Priority:** P1  
**User story:** As a mobile user, I want to tap a chart house and inspect its details without deciphering crowded labels.

### Acceptance Criteria

1. Given a chart is visible, when the user taps a house or sign compartment, then a detail sheet identifies the house, sign, lord, occupants, and planetary conditions available in the current dataset.
2. Given multiple planets occupy the selected compartment, then all planets are listed individually.
3. Given the user selects another compartment, then the detail updates without leaving the chart page.
4. Given the chart is used with keyboard or screen reader, then each selectable compartment has a meaningful accessible name.

### Delivery Checklist

- [ ] Add selectable SVG regions without changing chart geometry.
- [ ] Add house-detail sheet component.
- [ ] Provide full text for abbreviations and symbols.
- [ ] Add selected-house visual state using more than color alone.

## M05-US03: Focused Chart Mode

**Priority:** P1  
**User story:** As a practitioner, I want to open a chart in a focused view so that I can inspect it at the largest practical size.

### Acceptance Criteria

1. Given a chart is shown in a dense module, when the user selects Expand, then a focused chart view opens above surrounding content.
2. Given the device rotates to landscape, then the focused chart uses the additional width without losing the current chart or style.
3. Given the focused view is closed, then the user returns to the same position in the originating module.
4. Given pinch zoom is supported, then zoom affects the focused chart surface without scaling the entire page.

### Delivery Checklist

- [ ] Add Expand control with accessible label.
- [ ] Support portrait and landscape focused layouts.
- [ ] Decide whether controlled pinch zoom is needed after usability testing.
- [ ] Preserve source-module state on close.

---

# Epic M06: Core Mobile Feature Journeys

## M06-US01: Mobile Home and Intelligence Dashboard

**Priority:** P0  
**User story:** As a returning user, I want to understand what matters today for the selected profile within the first screen.

### Acceptance Criteria

1. Given an active profile exists, then the mobile dashboard shows the highest-priority current intelligence before secondary summaries.
2. Given Today, 7 Days, and 30 Days filters apply only to the intelligence feed, then they are visually attached to that feed.
3. Given dashboard cards stack, then their reading order reflects importance and does not create nested card styling.
4. Given there are no alerts or current events, then the page shows a meaningful quiet-state message.
5. Given the user taps an item, then it opens the relevant detail route or date context.

### Delivery Checklist

- [ ] Prioritize current transit, active Dasha, Panchanga, and upcoming event content.
- [ ] Keep feed filters scoped to the intelligence feed.
- [ ] Use a single-column mobile hierarchy.
- [ ] Add skeleton, empty, and error states.

## M06-US02: Mobile Overview and Vedic Workspace

**Priority:** P0  
**User story:** As a user, I want the selected profile's essential birth and Vedic details presented in a clear mobile sequence.

### Acceptance Criteria

1. Given Overview loads on mobile, then Birth Details and AI Reading appear before Planetary Positions.
2. Given the Vedic page contains several calculation groups, then page subnavigation provides quick access to each group.
3. Given planetary positions are displayed, then all required fields remain accessible without document-level horizontal scrolling.
4. Given calculation conventions apply, then ayanamsha, node type, house system, and timezone provenance can be opened from the page.

### Delivery Checklist

- [ ] Validate Overview content order.
- [ ] Create mobile planetary-position row cards or expandable records.
- [ ] Make provenance compact but visible.
- [ ] Preserve direct access to exact degree and Nakshatra data.

## M06-US03: Mobile Varga Charts

**Priority:** P0  
**User story:** As a practitioner, I want to choose D1-D60 and inspect its chart and planetary positions comfortably on a phone.

### Acceptance Criteria

1. Given the Varga Charts page loads on mobile, then the varga selector and chart-style selector remain visible and reachable.
2. Given a varga is selected, then its chart appears at full content width before supporting planetary data.
3. Given planetary positions are opened, then Planet, Degree, Rashi, Nakshatra, Paada, RL, NL, SL, and SSL are all available.
4. Given the user changes varga, then loading feedback appears and stale data is not presented as current.
5. Given the user returns to the page, then the last selected varga may be restored within the current session.

### Delivery Checklist

- [ ] Use a searchable/selectable D1-D60 control suited to touch.
- [ ] Keep chart-style control compact.
- [ ] Stack chart and position details on phones.
- [ ] Add focused chart mode.
- [ ] Preserve complete column detail through expandable records.

## M06-US04: Mobile Dasha Drill-Down

**Priority:** P0  
**User story:** As a user, I want to drill from Mahadasha to Antardasha to Pratyantardasha without three compressed desktop columns.

### Acceptance Criteria

1. Given the Dasha page opens on mobile, then the active Mahadasha and current period context are visible first.
2. Given the user selects a Mahadasha, then the next view presents its Antardashas.
3. Given the user selects an Antardasha, then the next view presents its Pratyantardashas.
4. Given the user enters a deeper level, then a breadcrumb or back control communicates the hierarchy.
5. Given period rows are displayed, then lord, start date, end date, duration, and active state are accessible without horizontal page scroll.
6. Given natal/transit chart context is opened, then the user can toggle Natal and Transit and view two readable charts vertically.

### Delivery Checklist

- [ ] Replace three-column mobile navigator with progressive drill-down.
- [ ] Preserve selected periods while moving between levels.
- [ ] Add sticky hierarchy context where useful.
- [ ] Stack Rashi and Navamsha charts vertically.
- [ ] Keep desktop Dasha explorer behavior above the selected breakpoint.

## M06-US05: Mobile Gocharam and Transits

**Priority:** P0  
**User story:** As a user, I want to understand what happened, what is active, how long it lasts, and what comes next in plain language.

### Acceptance Criteria

1. Given Gocharam opens on mobile, then Past, Current, and Upcoming sections are reachable through clear subnavigation.
2. Given an event is shown, then start, peak, end, and next-transition dates are visibly marked where available.
3. Given a core reading is shown, then the first paragraph explains the astrological rationale and the next paragraph gives a layperson-friendly interpretation.
4. Given a timeline is displayed, then timestamps or dates have explicit markings and do not rely on relative spacing alone.
5. Given the user taps an event, then its relevant natal/transit chart context and complete explanation are available.

### Delivery Checklist

- [ ] Implement compact Past/Current/Upcoming navigation.
- [ ] Convert timelines into a vertical mobile representation.
- [ ] Keep event dates and status visible while reading.
- [ ] Add chart-detail expansion.
- [ ] Verify readable line lengths for long-form interpretation.

## M06-US06: Mobile Calendar Intelligence

**Priority:** P0  
**User story:** As a user, I want Panchanga, transit events, Dashas, and saved readings organized by date in one mobile calendar experience.

### Acceptance Criteria

1. Given Calendar opens on mobile, then the selected local date and local timezone are clearly visible.
2. Given the user changes place, then Panchanga uses the selected place while the viewer timezone behavior follows saved settings.
3. Given a date contains multiple event types, then the user can distinguish Panchanga, Dasha, transit, and reading items.
4. Given the user selects a date, then its event agenda appears without requiring a wide month grid.
5. Given saved reading versions exist for a date, then versions, deviation score, and feedback status are accessible.
6. Given the Today, 7 Days, and 30 Days controls are shown, then they are associated only with the intelligence feed and not the entire Calendar.

### Delivery Checklist

- [ ] Use a mobile date strip, compact calendar, or agenda-first layout.
- [ ] Keep date selection and place control reachable.
- [ ] Add clear event-type markers with accessible labels.
- [ ] Present reading history and validation inside date details.
- [ ] Test timezone and day-boundary behavior.

## M06-US07: Mobile Ashtakavarga

**Priority:** P1  
**User story:** As a practitioner, I want South Indian Ashtakavarga charts, Shodhana, and Pinda calculations to remain inspectable on mobile.

### Acceptance Criteria

1. Given a SAV or BAV chart is selected, then the South Indian sign-grid chart fills the available mobile width.
2. Given the user selects a planet or calculation type, then the corresponding chart and totals update clearly.
3. Given Prastara or matrix data is displayed, then it uses a bounded scroll or focused matrix mode with understandable row and column context.
4. Given Shodhana or Pinda detail is opened, then all calculation values remain available through progressive disclosure.

### Delivery Checklist

- [ ] Add mobile chart/calculation selectors.
- [ ] Stack summary, chart, and detail sections.
- [ ] Add focused mode for large matrices.
- [ ] Preserve raw BAV/SAV, Shodhana, Prastara, and Shodhya Pinda data.

## M06-US08: Mobile Yogas and Doshas

**Priority:** P1  
**User story:** As a user, I want detected Yogas and Doshas explained clearly, with source and verification status available when I need it.

### Acceptance Criteria

1. Given results exist, then active Yogas and Doshas are prioritized before inactive or informational rules.
2. Given the user opens a result, then its rule rationale, participating planets/houses, strength or status, and source note are available.
3. Given a rule is convention-dependent or awaiting external validation, then the UI communicates that state without presenting it as certain.
4. Given several filters are available, then they fit mobile without squeezing labels.

### Delivery Checklist

- [ ] Create mobile filter and result-list behavior.
- [ ] Use expandable details for rule logic and source notes.
- [ ] Retain verification and convention indicators.
- [ ] Avoid nested cards in result detail.

## M06-US09: Mobile Compatibility

**Priority:** P1  
**User story:** As a user, I want to compare two profiles, understand calculated compatibility points, inspect charts, and then read the AI analysis.

### Acceptance Criteria

1. Given Compatibility opens, then both selected profiles are clearly identified and can be changed.
2. Given calculations complete, then the score and basic details appear before AI analysis.
3. Given profile metrics are compared, then the relationship remains understandable on a 360 px screen.
4. Given charts are displayed, then each person's Rashi and Navamsha charts can be inspected at readable width.
5. Given Dosha flags or exceptions apply, then their calculated status is shown before AI prose.

### Delivery Checklist

- [ ] Create compact dual-profile selector.
- [ ] Stack profile summaries while preserving clear A/B identity.
- [ ] Use comparison rows for calculated points.
- [ ] Add chart toggles or accordions instead of four tiny charts.
- [ ] Keep AI analysis below deterministic calculations.

## M06-US10: Mobile Readings and Ask AI

**Priority:** P0  
**User story:** As a user, I want to ask questions, read long answers, revisit versions, and provide feedback comfortably on my phone.

### Acceptance Criteria

1. Given Ask AI opens on mobile, then the composer is reachable and remains visible above the software keyboard.
2. Given a request is generating, then progress is communicated and duplicate submission is prevented.
3. Given an answer is long, then typography, line length, headings, and lists remain comfortable to read.
4. Given multiple reading versions exist, then the user can select a version and see deviation information.
5. Given feedback is supported, then the user can mark Accurate, Partly Accurate, Missed, or Not Applicable with touch-friendly controls.
6. Given generation fails or connectivity is interrupted, then the user can retry without losing the prompt where possible.

### Delivery Checklist

- [ ] Build keyboard-aware composer behavior.
- [ ] Add safe-area-aware bottom padding.
- [ ] Define streaming/loading/error presentation.
- [ ] Optimize Markdown output for small screens.
- [ ] Add mobile version history and feedback controls.

## M06-US11: Mobile Settings

**Priority:** P1  
**User story:** As a user, I want to configure calculation defaults and appearance from my phone without navigating a dense desktop form.

### Acceptance Criteria

1. Given Settings opens on mobile, then Account, Calculations, Location and Time, Appearance, Regional, and Session sections are independently reachable.
2. Given the user changes ayanamsha, node type, chart style, Panchanga place, timezone, or theme, then the saved value is reflected in dependent views.
3. Given a change affects calculations, then the user receives an appropriate explanation before or after saving.
4. Given the user leaves Settings after saving, then persisted settings remain after refresh and on another authenticated device where supported.

### Delivery Checklist

- [ ] Group settings into mobile sections.
- [ ] Use native-feeling controls for choices and booleans.
- [ ] Add save state and error feedback.
- [ ] Verify Supabase-backed preference persistence.
- [ ] Keep Logout clearly separated from ordinary settings.

---

# Epic M07: Accessibility, Themes, and Content Quality

## M07-US01: Mobile Accessibility

**Priority:** P0  
**User story:** As a user with accessibility needs, I want to navigate and understand AstroSpace using zoom, keyboard controls, or assistive technology.

### Acceptance Criteria

1. All primary workflows meet WCAG 2.2 AA expectations applicable to the product.
2. Text and essential icons meet contrast requirements in light and dark themes.
3. Focus is visible, logical, and not hidden by sticky headers or bottom navigation.
4. Charts have meaningful text alternatives or inspectable structured data.
5. Status is never communicated only by color.
6. Motion respects `prefers-reduced-motion`.

### Delivery Checklist

- [ ] Run automated accessibility checks on primary routes.
- [ ] Conduct keyboard-only workflow testing.
- [ ] Test VoiceOver on iOS/Safari.
- [ ] Test TalkBack on Android/Chrome.
- [ ] Audit accessible names and landmarks.
- [ ] Audit light and dark contrast.

## M07-US02: Mobile Light and Dark Themes

**Priority:** P0  
**User story:** As a user, I want both themes to remain clear and consistent on mobile, including controls, tabs, cards, overlays, and charts.

### Acceptance Criteria

1. Given either theme is active, then all foreground, border, raised-surface, active, destructive, warning, and success states remain distinguishable.
2. Given the public landing page and authenticated app are visited, then theme preference behaves consistently according to the product setting.
3. Given system theme changes and System mode is supported, then the app updates without requiring a reload.
4. Given a chart is displayed, then labels, symbols, and lines remain legible in both themes.

### Delivery Checklist

- [ ] Audit hard-coded colors.
- [ ] Test every shared component in both themes.
- [ ] Verify status and condition colors against chart backgrounds.
- [ ] Verify browser theme color and future native status-bar appearance.

## M07-US03: Plain-Language Mobile Content

**Priority:** P1  
**User story:** As an everyday user, I want technical astrology to be explained in readable language without losing access to the calculation rationale.

### Acceptance Criteria

1. Given a core interpretation is shown, then the rationale and plain-language reading are visually separable.
2. Given a technical abbreviation appears, then its meaning is accessible through expanded detail, label, or glossary behavior.
3. Given a paragraph is shown on a phone, then line length and spacing support comfortable reading.
4. Given a result is uncertain or convention-dependent, then wording reflects that uncertainty.

### Delivery Checklist

- [ ] Audit mobile content hierarchy and paragraph length.
- [ ] Add reusable technical-term help behavior.
- [ ] Keep provenance available without interrupting the main reading.

---

# Epic M08: Performance and Reliability

## M08-US01: Mobile Loading Performance

**Priority:** P1  
**User story:** As a user on a mobile connection, I want AstroSpace to become usable quickly and avoid downloading feature code I have not opened.

### Acceptance Criteria

1. Given the user opens the authenticated app on a typical mobile connection, then the shell and current-route loading state appear promptly.
2. Given a feature route is not visited, then its heavy code and data are lazy-loaded where practical.
3. Given chart or timeline data is loading, then stable skeletons prevent major layout shifts.
4. Given the user returns to recently loaded data, then appropriate cached state reduces unnecessary calls without showing stale profile data.

### Delivery Checklist

- [ ] Establish performance baselines before changes.
- [ ] Audit Angular route lazy loading and bundle composition.
- [ ] Audit icon and UI-library imports.
- [ ] Avoid rendering hidden heavy charts or long lists.
- [ ] Add virtual scrolling only where measured list size requires it.
- [ ] Add stable skeleton dimensions.

## M08-US02: Mobile Network Resilience

**Priority:** P1  
**User story:** As a user on an unreliable connection, I want clear feedback and safe retry behavior rather than blank or inconsistent screens.

### Acceptance Criteria

1. Given a request times out or fails, then the affected section shows an error and retry action without destroying unrelated page state.
2. Given connectivity is lost during a form or AI prompt, then user-entered text is preserved where practical.
3. Given the active profile changes while requests are in flight, then stale responses do not overwrite the newly selected profile's data.
4. Given the app resumes after being backgrounded, then authentication and time-sensitive data are refreshed appropriately.

### Delivery Checklist

- [ ] Standardize loading, empty, partial, and error components.
- [ ] Cancel or ignore stale profile-dependent requests.
- [ ] Define retry behavior for reads versus writes.
- [ ] Add online/offline awareness for future PWA/native use.

---

# Epic M09: Context Engine Mobile Integration

## M09-US01: CE-Powered Today for You

**Priority:** P0  
**User story:** As a returning mobile user, I want a concise, personalized daily view assembled by the Context Engine so that I immediately understand the day's tone, supporting signals, cautions, and practical actions for the selected profile.

### Acceptance Criteria

1. Given an authenticated user has selected a profile, when Home or Overview loads for the current date, then the UI requests daily guidance from the authenticated Context Engine endpoint for that profile.
2. Given daily guidance is returned, then the UI presents the CE verdict, tone, day score, star of the day, do-today items, avoid-today items, and relevant timing windows without inventing replacement calculations in the frontend.
3. Given the selected profile represents the user, then guidance uses second-person wording; given it represents another relation, then wording preserves the subject's correct identity and pronoun context.
4. Given the user changes profile, calculation settings, Panchanga place, timezone, or selected date, then CE guidance is refreshed using the new context and stale guidance is not shown under the new identity.
5. Given the guidance contains active Dasha and Gocharam context, then those signals can open the relevant Dasha or Gocharam detail while preserving profile and date.
6. Given no major supportive or challenging transit rule is active, then the UI presents the CE quiet-state conclusion rather than manufacturing urgency.
7. Given CE daily guidance fails, then the rest of the dashboard remains usable and the CE section provides a retry action.

### Delivery Checklist

- [ ] Create a typed mobile view model for the full CE daily-guidance payload.
- [ ] Place “Today for You” prominently on Home and provide a compact version on Overview where appropriate.
- [ ] Display tone, headline, rationale, practical reading, do, avoid, color, number, Tarabala, Chandrabala, and lucky signature through progressive disclosure.
- [ ] Deep-link active Dasha and Gocharam signals to their source modules.
- [ ] Apply saved ayanamsha, node type, Panchanga place, and viewer timezone consistently.
- [ ] Add skeleton, partial, empty, error, and retry states.
- [ ] Prevent stale CE responses after profile or date changes.
- [ ] Keep CE wording and deterministic values server-authored.

### QA Checklist

- [ ] Verify self and family-relation wording.
- [ ] Verify two profiles with different natal charts produce different context.
- [ ] Verify consecutive dates update star, windows, and daily context.
- [ ] Verify timezone day-boundary behavior.
- [ ] Verify CE section failure does not blank the dashboard.
- [ ] Verify provenance expansion names the Context Engine.

## M09-US02: CE Question Routing for Ask AI

**Priority:** P0  
**User story:** As a user asking an astrology question, I want the Context Engine to identify the relevant life domains and assemble the correct chart evidence before an AI agent explains the answer.

### Supported CE Domains

- Career and profession.
- Wealth and finance.
- Marriage and relationships.
- Health and longevity, subject to product safety exclusions.
- Education and intellect.
- Children and progeny.
- Family, home, and property.
- Foreign travel and settlement.
- Spirituality and Moksha.
- Litigation, enemies, and obstacles, using advisory language.

### Acceptance Criteria

1. Given the user submits a question in Ask AI, then the question and selected Kundli ID are sent to the authenticated CE endpoint before interpretive generation begins.
2. Given the question maps to one life domain, then CE returns that domain as primary and assembles its relevant houses, natural and Jaimini karakas, Vargas, Yogas/Doshas, Dasha relevance, Gocharam, references, and convention flags.
3. Given the question spans multiple domains, such as foreign settlement after marriage, then CE returns a primary and one or more secondary domains and the UI preserves that routing context.
4. Given routing confidence is low or the question is ambiguous, then the user can review or adjust the selected domain before a costly AI generation when product rules require confirmation.
5. Given a request contains an unsupported explicit domain, then the UI shows a clear validation message and does not silently route it to an unrelated domain.
6. Given an AI agent produces an answer, then the agent receives the CE bundle as its calculation context and does not independently recalculate chart facts.
7. Given the answer is displayed, then the user can inspect a compact “Why this answer” section showing routed domains and key evidence without exposing raw internal prompt text.

### Delivery Checklist

- [ ] Add typed CE routing and ContextBundle models to the frontend.
- [ ] Wire Ask AI question submission through `/api/v1/context/{kundli_id}`.
- [ ] Define agent handoff contract for the deterministic CE bundle.
- [ ] Show primary and secondary domain chips during generation and in answer detail.
- [ ] Add domain-review UI for ambiguous routing if enabled by product policy.
- [ ] Add “Why this answer” expansion for houses, karakas, Vargas, Dashas, and Gocharam signals.
- [ ] Keep raw context payload out of the main layperson reading.
- [ ] Preserve the CE taxonomy version and `as_of` timestamp with generated readings.

## M09-US03: CE Context Continuity

**Priority:** P0  
**User story:** As a user moving between routes or reopening the app, I want AstroSpace to preserve the correct person, date, settings, and question context so that guidance never belongs to the wrong profile or calculation convention.

### Acceptance Criteria

1. Given a CE request is in flight and the active profile changes, then the old response is cancelled or discarded and cannot render under the new profile.
2. Given the app is backgrounded and resumed after the CE freshness window or local-date boundary, then time-sensitive context refreshes before being presented as current.
3. Given the user follows a CE signal from Home to Dasha, Gocharam, Calendar, or a chart, then profile ID, `as_of` date, routed domain, and relevant event identity are retained.
4. Given the user returns from a CE-driven detail, then the prior scroll position and expanded context state are restored where practical.
5. Given ayanamsha or node type changes, then cached CE bundles created under the previous convention are invalidated.
6. Given the user logs out, then profile-specific CE bundles, drafts, and local presentation caches are removed.

### Delivery Checklist

- [ ] Define a CE request identity using user, Kundli, date/time, location, ayanamsha, node type, taxonomy version, and requested domains.
- [ ] Add freshness rules for daily and question-specific context.
- [ ] Add route-state contract for CE-driven deep links.
- [ ] Add app-resume refresh behavior for mobile web, PWA, and future native wrappers.
- [ ] Clear CE client state on logout and account changes.
- [ ] Do not share cached CE context between users or profiles.

## M09-US04: CE Evidence and Provenance

**Priority:** P0  
**User story:** As a user or practitioner, I want to see which deterministic signals support a recommendation so that I can trust, validate, and challenge the interpretation.

### Acceptance Criteria

1. Given a CE-derived recommendation is shown, then an expandable provenance view identifies the selected profile, context date, ayanamsha, house convention, primary and secondary domains, and taxonomy version.
2. Given the CE bundle includes source references, then they are shown as concise source notes linked to the relevant signal where possible.
3. Given a rule has a convention flag or verification limitation, then that limitation is visible before the result is treated as authoritative.
4. Given a domain contains an explicit exclusion, such as death prediction, then the UI and downstream agent respect the exclusion and provide safe alternative framing.
5. Given deterministic context and AI prose disagree, then deterministic values remain the displayed source of truth and the disagreement can be logged for review.
6. Given an everyday user does not open technical detail, then the primary reading remains concise and understandable.

### Delivery Checklist

- [ ] Build a reusable CE provenance drawer or sheet.
- [ ] Separate “Astrological rationale” from “What this means for you.”
- [ ] Display convention and verification badges with accessible text.
- [ ] Surface CE source references without overwhelming the primary view.
- [ ] Preserve CE bundle metadata with saved AI reading versions.
- [ ] Add a diagnostic identifier for reporting mismatched or unexpected context.

## M09-US05: CE Safety and Domain Boundaries

**Priority:** P0  
**User story:** As a user, I want sensitive astrology topics handled carefully so that the mobile experience does not make harmful, absolute, or unsupported claims.

### Acceptance Criteria

1. Given a health question is submitted, then the result avoids diagnosis, treatment instructions, and deterministic medical outcomes and encourages appropriate professional support where relevant.
2. Given a longevity or death-prediction question is submitted, then the CE exclusion is enforced and the experience offers a safer focus such as wellbeing, resilience, or current life periods.
3. Given litigation or imprisonment context is requested, then output uses advisory language and avoids guaranteed outcomes.
4. Given child gender or another low-confidence convention-heavy question is submitted, then the result communicates limitations or declines unsupported certainty.
5. Given a domain uses a VERIFY-flagged calculation, then that dependency is visible and its contribution is not presented as externally verified.

### Delivery Checklist

- [ ] Map CE domain exclusions and convention flags into frontend display rules.
- [ ] Pass safety constraints with the CE bundle to downstream agents.
- [ ] Add mobile-friendly limitation and support messaging.
- [ ] Add test cases for excluded and convention-heavy questions.
- [ ] Ensure analytics do not capture sensitive question or answer text.

## M09-US06: CE Persistence, Caching, and Supabase Isolation

**Priority:** P1  
**User story:** As a returning user, I want CE-backed readings and their evidence to remain available across devices while staying private to my account.

### Acceptance Criteria

1. Given a CE-backed AI reading is saved, then its user ID, Kundli ID, generated local date, context timestamp, taxonomy version, routed domains, calculation conventions, and reading version are persisted where required by the reading-history contract.
2. Given a user opens another account, then no CE context, question history, or generated reading from the previous account is accessible.
3. Given multiple reading versions exist, then each version retains the CE metadata used at generation time and is not silently rebound to current context.
4. Given a fresh deterministic context can be recomputed, then large transient bundles are not duplicated in storage without a defined audit or history need.
5. Given an offline cached view is shown, then it is labeled with its original profile, date, and freshness and cannot be mistaken for current guidance.

### Delivery Checklist

- [ ] Define which CE metadata is persisted with readings versus recomputed.
- [ ] Add or verify Supabase columns and migrations required by the CE reading contract.
- [ ] Verify row-level security for all CE-linked persisted records.
- [ ] Include calculation and taxonomy versions in cache keys.
- [ ] Define retention and cleanup for transient context caches.
- [ ] Add cross-account and cross-profile isolation tests.

## M09-US07: CE Mobile Observability and Regression Tests

**Priority:** P1  
**User story:** As the delivery team, we want to detect routing, context, freshness, and profile-isolation regressions before they reach mobile users.

### Acceptance Criteria

1. Given representative domain questions are tested, then expected primary and secondary routing decisions are asserted.
2. Given a CE bundle is assembled, then required domain sections and provenance metadata are present.
3. Given daily guidance is generated for fixed charts and dates, then tests prove that output references computed signals rather than generic boilerplate.
4. Given profile, date, timezone, ayanamsha, or node type changes, then mobile integration tests verify the correct request identity and refreshed response.
5. Given CE telemetry is recorded, then it contains route, duration, domain IDs, taxonomy version, status, and diagnostic IDs but excludes birth data, question text, and reading content.

### Delivery Checklist

- [ ] Extend backend CE routing and daily-guidance tests.
- [ ] Add typed frontend contract tests for CE payloads.
- [ ] Add end-to-end tests from mobile Ask AI to routed context and displayed answer evidence.
- [ ] Add stale-response tests during rapid profile switching.
- [ ] Add date-boundary and app-resume tests.
- [ ] Add privacy review for CE logs, errors, and analytics.

---

# Epic M10: Progressive Web App

## M10-US01: Installable Mobile Web App

**Priority:** P2  
**User story:** As a mobile-web user, I want to install AstroSpace on my home screen and launch it like an app.

### Acceptance Criteria

1. Given the production site meets browser installability requirements, then supported browsers can install AstroSpace.
2. Given AstroSpace is launched from the home screen, then it opens in standalone display mode with correct icons and theme colors.
3. Given the app version changes, then the update strategy does not leave the user indefinitely on incompatible frontend code.
4. Given the device is offline, then the app shell provides an intentional offline state and does not imply that calculations were refreshed.

### Delivery Checklist

- [ ] Add Angular service worker and web manifest.
- [ ] Add correctly sized app icons and maskable icons.
- [ ] Define cache policy for static assets and API responses.
- [ ] Add offline and update-available messaging.
- [ ] Verify iOS Add to Home Screen and Android installation.
- [ ] Verify Supabase auth behavior in standalone mode.

---

# Epic M11: Capacitor and Native Applications

## M11-US01: Capacitor Foundation

**Priority:** P3  
**User story:** As the product team, we want to package the tested Angular application for iOS and Android without duplicating product logic.

### Acceptance Criteria

1. Given the Angular production build succeeds, then Capacitor can synchronize it into iOS and Android projects.
2. Given the app launches on an iOS simulator and Android emulator, then the authenticated shell renders without safe-area or keyboard overlap defects.
3. Given environment configuration differs by platform, then secrets are not embedded in source-controlled client files beyond intended public keys.
4. Given the native wrapper is unavailable, then ordinary web deployments continue to function.

### Delivery Checklist

- [ ] Add Capacitor core and CLI packages.
- [ ] Initialize iOS and Android projects.
- [ ] Add environment-aware API origin handling.
- [ ] Configure safe areas, status bar, splash screen, and app icons.
- [ ] Document native build and synchronization commands.
- [ ] Add native projects to CI strategy.

## M11-US02: Native Authentication and Deep Links

**Priority:** P3  
**User story:** As a native-app user, I want email and Google authentication to return me securely to AstroSpace.

### Acceptance Criteria

1. Given Google login is initiated from iOS or Android, then authentication completes and returns to the native app.
2. Given a magic link or email confirmation is opened on the device, then the app handles the configured deep link or falls back safely to web.
3. Given authentication is cancelled, then the user returns to a stable signed-out state.
4. Given the app restarts, then a valid session is restored securely.

### Delivery Checklist

- [ ] Register app URL schemes or universal/app links.
- [ ] Add native redirect URLs in Supabase.
- [ ] Create an authentication callback service shared by web and native adapters.
- [ ] Use native secure storage for sensitive session material where required.
- [ ] Test login, logout, expiry, cancellation, and account switching.

## M11-US03: Native Navigation and Lifecycle

**Priority:** P3  
**User story:** As a native-app user, I want platform back behavior, rotation, backgrounding, and reopening to feel predictable.

### Acceptance Criteria

1. Given an Android user presses Back while an overlay is open, then the overlay closes before route navigation or app exit.
2. Given Back is pressed on a nested route, then the previous route is restored.
3. Given the app is backgrounded and resumed, then time-sensitive dashboard, Panchanga, and transit data refresh according to freshness rules.
4. Given device orientation changes in focused chart mode, then the chart adapts without losing selection.

### Delivery Checklist

- [ ] Add a platform-navigation adapter.
- [ ] Define overlay, route, and app-exit back priority.
- [ ] Add app resume and pause handlers.
- [ ] Refresh time-sensitive data on resume without duplicating requests.

## M11-US04: Native Notifications

**Priority:** P3  
**User story:** As a user, I want optional alerts for important transits, Panchanga events, and scheduled readings.

### Acceptance Criteria

1. Given the user has not granted notification permission, then the app requests it only in context and explains the value.
2. Given permission is denied, then core product workflows remain available.
3. Given a notification is tapped, then the app opens the related profile, date, or event.
4. Given multiple accounts use a device over time, then notification tokens remain associated with the correct authenticated account.

### Delivery Checklist

- [ ] Define notification categories and user preferences.
- [ ] Add APNs/FCM token registration backend support.
- [ ] Add deep-link payload contract.
- [ ] Add opt-in, opt-out, token refresh, and logout cleanup.
- [ ] Add timezone-aware scheduling rules.

## M11-US05: Native Share and Export

**Priority:** P3  
**User story:** As a native-app user, I want to share or save charts and reports using familiar device controls.

### Acceptance Criteria

1. Given a supported report or chart is ready, then Share opens the native share sheet on iOS and Android.
2. Given file generation fails, then the user receives an actionable error.
3. Given a shared artifact contains personal birth data, then the user explicitly initiates the action and understands what will be shared.

### Delivery Checklist

- [ ] Create web and native share adapters.
- [ ] Define chart-image and PDF export formats.
- [ ] Verify temporary-file cleanup.
- [ ] Add privacy confirmation where appropriate.

---

# Epic M12: Quality Assurance and Release Governance

## M12-US01: Automated Responsive Regression Coverage

**Priority:** P0  
**User story:** As the delivery team, we want automated mobile checks so that future desktop changes do not silently break phone layouts.

### Acceptance Criteria

1. Given a pull request changes frontend code, then core mobile smoke tests run at defined phone and tablet viewports.
2. Given a page introduces document-level horizontal overflow, then an automated check fails for covered routes.
3. Given critical visual baselines change, then differences are reviewable rather than automatically accepted.
4. Given the test account has representative chart data, then dense chart and table states are included in regression coverage.

### Delivery Checklist

- [ ] Add browser-based end-to-end test tooling if not already present.
- [ ] Create authenticated mobile smoke-test fixtures.
- [ ] Add overflow assertions for primary routes.
- [ ] Add screenshots for light and dark themes.
- [ ] Add dense South Indian, North Indian, and Eastern chart fixtures.
- [ ] Run tests in CI at standard phone and tablet viewports.

## M12-US02: Device and Browser Validation

**Priority:** P0  
**User story:** As the product team, we want confidence that AstroSpace works on the browsers and devices users actually carry.

### Supported Matrix for First Mobile-Web Release

| Platform | Browser | Level |
|---|---|---|
| iOS current and previous major | Safari | Required |
| Android current and previous major | Chrome | Required |
| iPadOS current | Safari | Required |
| Android tablet current | Chrome | Required |
| Desktop current | Chrome, Safari, Edge | Regression |

### Acceptance Criteria

1. All P0 journeys pass on required browser/platform combinations.
2. No primary action is blocked by browser chrome, safe areas, or the software keyboard.
3. Orientation changes do not lose unsaved form data or selected calculation context.
4. Date, time, timezone, and location controls behave consistently across required platforms.

### QA Checklist

- [ ] Test authentication and session restoration.
- [ ] Test profile search, create, edit, and switch.
- [ ] Test every primary navigation destination.
- [ ] Test all three chart styles with dense houses.
- [ ] Test Dasha drill-down and chart context.
- [ ] Test Calendar date, place, and timezone behavior.
- [ ] Test AI prompt entry with software keyboard.
- [ ] Test theme switching and system theme.
- [ ] Test back navigation and overlay dismissal.
- [ ] Test portrait and landscape.

## M12-US03: Mobile Analytics and Feedback

**Priority:** P2  
**User story:** As the product team, we want to understand where mobile users struggle so that improvements are based on real behavior without exposing sensitive astrology data.

### Acceptance Criteria

1. Given analytics are enabled, then events record navigation and workflow completion without recording birth details, reading text, or sensitive profile content.
2. Given a mobile workflow repeatedly fails, then errors can be grouped by route and release version.
3. Given the user opts out where required, then analytics behavior follows the applicable privacy setting.

### Delivery Checklist

- [ ] Define privacy-safe event taxonomy.
- [ ] Track route visits, workflow starts, success, cancellation, and failure.
- [ ] Track viewport class and app version without collecting sensitive chart data.
- [ ] Add mobile feedback entry point after initial release.

---

# 10. Cross-Cutting Non-Functional Requirements

## 10.1 Layout and Responsiveness

- [ ] No document-level horizontal scrolling from 320 px upward.
- [ ] Content does not render beneath the app bar, bottom navigation, keyboard, or safe areas.
- [ ] Long names, places, signs, and labels wrap or truncate intentionally.
- [ ] Charts preserve geometry and remain centered.
- [ ] Landscape mode remains usable for charts and forms.

## 10.2 Accessibility

- [ ] Target WCAG 2.2 AA.
- [ ] Touch targets are at least 44 x 44 CSS pixels.
- [ ] Focus order and visibility are verified.
- [ ] Screen-reader labels exist for icon controls and chart regions.
- [ ] Color is never the sole status indicator.
- [ ] Reduced motion is respected.

## 10.3 Performance

- [ ] Establish mobile Core Web Vitals baselines before implementation.
- [ ] Define route-level performance budgets after baseline measurement.
- [ ] Lazy-load non-primary features where practical.
- [ ] Avoid rendering hidden charts and large data sets.
- [ ] Use stable loading placeholders to control layout shift.

## 10.4 Security and Privacy

- [ ] Do not log birth details, AI reading bodies, auth tokens, or profile data to client analytics.
- [ ] Enforce Supabase row-level access rules for all user-owned records.
- [ ] Store only public Supabase client keys in the frontend.
- [ ] Use secure native storage for sensitive session material where required.
- [ ] Clear user-specific cached state on logout.
- [ ] Require explicit action before sharing or exporting personal astrology data.

## 10.5 Data and Calculation Integrity

- [ ] Responsive transformations do not alter backend-calculated values.
- [ ] Hidden mobile details remain accessible through drill-down.
- [ ] Active profile identity remains visible or quickly confirmable.
- [ ] Ayanamsha, node type, timezone, chart style, and other conventions remain consistent with saved preferences.
- [ ] Stale responses cannot replace data after a profile switch.

## 10.6 Context Engine Integrity

- [ ] Mobile clients consume CE outputs and do not recreate domain-routing or astrology calculations in TypeScript.
- [ ] Every CE request is scoped to the authenticated user and selected Kundli.
- [ ] CE request identity includes date/time, place/timezone, ayanamsha, node type, domains, and taxonomy version where applicable.
- [ ] Daily guidance refreshes at the relevant local-date boundary and after material settings changes.
- [ ] Ask AI receives a deterministic CE bundle before interpretive generation.
- [ ] Primary and secondary domain routing remains inspectable.
- [ ] CE references, convention flags, exclusions, and provenance remain available on mobile.
- [ ] Saved reading versions retain the CE metadata used when they were generated.
- [ ] CE caches and drafts are isolated by account and cleared on logout.
- [ ] Sensitive CE questions and answer content are excluded from analytics and ordinary logs.

# 11. Delivery Sequence

## Release A: Mobile Foundation

- [ ] M01 shared responsive tokens and touch standards.
- [ ] M02 mobile app bar, bottom navigation, More menu, and safe areas.
- [ ] M03 mobile profile selection and Add/Edit Kundli.
- [ ] M04 shared subnavigation, dense-data, and overlay patterns.
- [ ] M07 theme and baseline accessibility pass.
- [ ] M12 initial automated viewport and overflow checks.

**Exit criterion:** A user can authenticate, choose or create a profile, navigate the complete app, and return Home on a 360 px phone without document-level horizontal scrolling.

## Release B: Primary Astrology Journeys

- [ ] Home and intelligence dashboard.
- [ ] Overview and Vedic workspace.
- [ ] Kundli charts and focused chart mode.
- [ ] Varga Charts.
- [ ] Dasha drill-down.
- [ ] Gocharam and Transits.
- [ ] Calendar Intelligence.
- [ ] Ask AI and Readings.
- [ ] M09 CE-powered Today for You, question routing, context continuity, evidence, and safety.

**Exit criterion:** All primary daily-use and practitioner journeys are complete on required mobile browsers, and their personalized guidance is demonstrably sourced from the correct CE profile, date, domain, and calculation conventions.

## Release C: Complete Feature Coverage

- [ ] Ashtakavarga.
- [ ] Yogas and Doshas.
- [ ] Compatibility.
- [ ] Notes and secondary routes.
- [ ] Settings and account completeness.
- [ ] Performance and reliability pass.
- [ ] Full accessibility and device matrix validation.

**Exit criterion:** Every authenticated route has an intentional mobile layout and passes the agreed P0/P1 acceptance criteria.

## Release D: PWA

- [ ] Installability.
- [ ] Offline shell and intentional offline states.
- [ ] Update management.
- [ ] Standalone-mode authentication validation.

**Exit criterion:** Supported users can install and update the mobile-web app without breaking authenticated workflows.

## Release E: iOS and Android

- [ ] Capacitor foundation.
- [ ] Native authentication and deep links.
- [ ] Native lifecycle and back behavior.
- [ ] Native notification readiness.
- [ ] Share/export integration.
- [ ] Store metadata, privacy, signing, and release builds.

**Exit criterion:** Signed release candidates pass the native device test matrix and are ready for store submission.

# 12. Dependencies and Decisions Required

| ID | Decision or dependency | Owner | Needed by |
|---|---|---|---|
| D01 | Confirm final five bottom-navigation destinations | Product/Design | Release A |
| D02 | Confirm tablet navigation threshold after prototypes | Design/Frontend | Release A |
| D03 | Select bottom-sheet implementation pattern compatible with Angular/PrimeNG | Frontend | Release A |
| D04 | Define representative dense Kundli fixtures for chart QA | Astrology/QA | Release B |
| D05 | Confirm whether controlled pinch zoom is required for charts and matrices | Product/Design | Release B |
| D06 | Confirm supported iOS and Android minimum versions | Product/Engineering | Release E |
| D07 | Configure Supabase web and native OAuth redirect URLs | Backend/Platform | Release E |
| D08 | Decide notification categories and opt-in language | Product/Legal | Release E |
| D09 | Provide app name, bundle identifiers, icons, splash assets, and store accounts | Product | Release E |
| D10 | Confirm privacy policy and account-deletion workflow | Product/Legal | Before store submission |
| D11 | Confirm whether ambiguous CE domain routing requires user confirmation before AI generation | Product/AI | Release B |
| D12 | Define which CE bundle fields are persisted with a reading versus recomputed | Backend/AI | Release B |
| D13 | Confirm CE freshness windows for daily, current transit, and question-specific context | Astrology/Backend | Release B |
| D14 | Define privacy-safe CE telemetry and diagnostic identifiers | Security/Platform | Release B |

# 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Desktop CSS overrides conflict with mobile rules | Inconsistent or fragile layouts | Introduce shared tokens and shell patterns before feature-by-feature fixes |
| Dense astrology data becomes oversimplified | Practitioner trust is reduced | Use progressive disclosure while retaining every calculated field |
| SVG chart labels overlap on small screens | Core product becomes unreadable | Add density fixtures, focused mode, and compartment detail inspection |
| Too many sticky controls reduce viewport height | Reading area becomes cramped | Limit each screen to one coordinated sticky header layer plus bottom navigation |
| Native packaging begins before mobile web stabilizes | Duplicate debugging and slower delivery | Complete Releases A-C before Capacitor production work |
| OAuth redirects differ across web and native | Login failure after app packaging | Design redirect and deep-link contracts before native implementation |
| Profile changes race with API responses | Wrong person's data may appear | Cancel requests or reject stale responses using profile/request identity |
| PWA caching serves outdated application code | Frontend/backend mismatch | Use explicit update strategy and conservative API caching |
| CE response renders after the active profile changes | Guidance may be attributed to the wrong person | Key requests by user/profile/context and reject stale responses |
| Frontend duplicates CE logic for convenience | Web and native interpretations drift from the audited engine | Keep domain routing and context assembly server-authoritative |
| AI prose loses CE provenance | Users cannot validate why a reading was produced | Persist and display routed domains, evidence, versions, flags, and source notes |
| Sensitive CE questions enter logs or analytics | Private life information may be exposed | Use metadata-only telemetry and prohibit question/answer body collection |

# 14. Definition of Ready for a User Story

A story is ready for implementation when:

- [ ] Business value and target user are clear.
- [ ] Acceptance criteria are testable.
- [ ] Required desktop behavior has been inspected.
- [ ] Mobile design or interaction pattern is agreed where needed.
- [ ] API and data dependencies are known.
- [ ] Accessibility behavior is identified.
- [ ] Analytics requirements are identified or marked not applicable.
- [ ] Representative data fixtures are available.
- [ ] No unresolved dependency blocks implementation.

# 15. Definition of Done for a User Story

A story is complete when:

- [ ] All acceptance criteria pass.
- [ ] Desktop behavior remains correct unless the story intentionally changes it.
- [ ] Small phone, standard phone, and tablet layouts are tested.
- [ ] Light and dark themes are tested.
- [ ] Keyboard and screen-reader semantics are checked where applicable.
- [ ] Loading, empty, error, and success states are implemented.
- [ ] No document-level horizontal overflow is introduced.
- [ ] Automated tests are added or updated in proportion to risk.
- [ ] Visual regression evidence is reviewed for layout-heavy changes.
- [ ] User-owned data remains protected by authenticated access controls.
- [ ] CE-powered stories prove correct profile, date, settings, domain routing, provenance, and stale-response handling.
- [ ] Documentation and this checklist are updated.
- [ ] Code is reviewed, built, and passes the relevant test suite.

# 16. Release-Level Acceptance Criteria

The mobile-web initiative is complete when:

1. Every authenticated route has an intentional phone layout from 320 px upward.
2. The desktop sidebar is replaced by mobile navigation at the agreed breakpoint.
3. Users can sign in, select/create a profile, navigate, inspect charts, review Dashas and Gocharam, use Calendar, and Ask AI through the Context Engine on required mobile browsers.
4. There is no unexpected document-level horizontal scroll on covered routes.
5. South Indian, North Indian, and Eastern charts are readable and preserve correct placement rules.
6. Dense calculations remain fully accessible through mobile-appropriate presentation.
7. Bottom navigation, sticky controls, dialogs, keyboards, and safe areas do not obscure content.
8. Light and dark themes pass the agreed accessibility checks.
9. Automated responsive smoke tests and overflow checks run in CI.
10. The production Angular application is ready for PWA work and later Capacitor packaging without a frontend rewrite.
11. “Today for You” and Ask AI demonstrably use authenticated CE output for the correct profile, date, routed domains, and calculation conventions.
12. CE evidence, references, convention flags, exclusions, taxonomy version, and freshness remain available through mobile progressive disclosure.

# 17. Master Progress Checklist

## Foundation

- [ ] Responsive tokens and breakpoints.
- [ ] Safe-area support.
- [ ] Touch target audit.
- [ ] Mobile app bar.
- [ ] Bottom navigation.
- [ ] More menu.
- [ ] Mobile overlays and dialogs.
- [ ] Mobile subnavigation component.
- [ ] Mobile dense-data component.

## Primary Journeys

- [ ] Authentication and session restoration.
- [ ] Profile chooser.
- [ ] Add/Edit Kundli.
- [ ] Home dashboard.
- [ ] Overview.
- [ ] Vedic.
- [ ] Chart.
- [ ] Varga Charts.
- [ ] Dashas.
- [ ] Gocharam.
- [ ] Transits.
- [ ] Calendar.
- [ ] Ask AI.
- [ ] Readings and feedback.

## Context Engine

- [ ] CE-powered Today for You.
- [ ] CE question routing for all ten supported domains.
- [ ] Primary and secondary domain presentation.
- [ ] CE-to-agent deterministic bundle handoff.
- [ ] CE rationale and plain-language reading separation.
- [ ] CE evidence and provenance sheet.
- [ ] CE convention flags and exclusions.
- [ ] CE profile/date/settings continuity.
- [ ] CE stale-response protection.
- [ ] CE app-resume and date-boundary refresh.
- [ ] CE reading-version metadata persistence.
- [ ] CE Supabase row-level isolation.
- [ ] CE safety-domain tests.
- [ ] CE mobile contract and end-to-end tests.

## Secondary Journeys

- [ ] Ashtakavarga.
- [ ] Yogas and Doshas.
- [ ] Compatibility.
- [ ] Notes.
- [ ] Settings.
- [ ] Account management and Logout.

## Quality

- [ ] Light-theme QA.
- [ ] Dark-theme QA.
- [ ] Accessibility audit.
- [ ] Mobile browser matrix.
- [ ] Portrait and landscape QA.
- [ ] Responsive visual regression tests.
- [ ] Horizontal-overflow checks.
- [ ] Mobile performance baseline and optimization.
- [ ] Network resilience and retry behavior.
- [ ] Supabase data isolation verification.

## Distribution Readiness

- [ ] PWA manifest and service worker.
- [ ] Install and update behavior.
- [ ] Capacitor setup.
- [ ] iOS project.
- [ ] Android project.
- [ ] Native OAuth/deep links.
- [ ] Secure session storage.
- [ ] Native lifecycle and back behavior.
- [ ] Push-notification infrastructure.
- [ ] Native sharing/export.
- [ ] Privacy and account deletion.
- [ ] Store signing and submission assets.
