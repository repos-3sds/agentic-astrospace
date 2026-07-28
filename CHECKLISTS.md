# CHECKLISTS

This file did not exist at the start of the 2026-07-28 mobile UI audit. It was created to hold the requested remediation checklist.

## Mobile UI audit remediation

Gap type legend: Missing screen; Missing route/navigation; Missing interaction; Missing backend capability; Existing backend not wired; Placeholder/static data; Missing loading/error/empty/offline state; Native-platform surface; Visual/accessibility defect; Verification/configuration gap.

### 1. Immediate data-honesty and Readings

- [ ] P1: Placeholder/static data - relabel `/m/notes` as a local draft while Notes remain local.
- [ ] P1: Placeholder/static data - remove `Saved`, account-persistence and cross-device persistence language from Notes unless server persistence succeeds.
- [ ] P1: Existing backend not wired - wire `/m/readings` to `ReadingService.list()` and remove fixed reading history.
- [ ] P1: Existing backend not wired - wire `/m/readings/accuracy` to reading claims APIs and derive totals from returned claims.
- [ ] P1: Missing loading/error/empty/offline state - add readings loading, no-readings, no-claims, API error and retry states.
- [ ] P1: Missing interaction - make saved versions, generate new, and claim review actions real or visibly disabled/local with explanation.

### 2. Profile management lifecycle

- [ ] P1: Missing screen - build `37 · Manage Profiles` (`216:415`) as `/m/settings/profiles`.
- [ ] P1: Missing screen - build `37b · Add Profile` (`216:483`) as `/m/settings/profiles/new`.
- [ ] P1: Missing screen - build `screen-3-edit-profile` (`216:543`) for editing a selected profile.
- [ ] P1: Missing screen - build `screen-4-delete-confirmation` (`216:615`) with destructive confirmation.
- [ ] P1: Missing route/navigation - route Settings > Manage profiles to the profile-management flow, not `/m/settings/birth-details`.
- [ ] P1: Missing interaction - persist active-profile switching and safely handle deletion of the active profile.
- [ ] P1: Missing loading/error/empty/offline state - cover profile loading, zero profiles, API error, missing birth data, auth expired and delete failure.

### 3. Notes persistence follow-up

- [ ] P2: Missing backend capability - decide whether Notes use the existing kundli notes field, a dedicated Notes API, or intentionally local device storage.
- [ ] P2: Missing backend capability - document Notes ownership, profile scope, sync behavior and privacy behavior.
- [ ] P2: Existing backend not wired - implement account persistence only after the storage contract is decided.
- [ ] P2: Missing loading/error/empty/offline state - add save failure, offline draft and conflict behavior where applicable.

### 4. Calendar intelligence

- [ ] P1: Existing backend not wired - wire `/m/calendar`, `/m/calendar/day` and festival detail to `/vedic/{id}/calendar-intelligence`.
- [ ] P1: Placeholder/static data - remove hard-coded July 2026 observances and day content.
- [ ] P1: Missing interaction - make previous/next month, selected day, filters and related actions functional.
- [ ] P2: Missing loading/error/empty/offline state - add month loading, no observances, API error, offline/stale and unsupported convention states.
- [ ] P2: Missing screen - implement Guided and Practitioner calendar-day presentation from `215:620` and `215:690` as mode-aware states.

### 5. Compatibility end to end

- [ ] P1: Existing backend not wired - wire add/select/results to real partner data and `/vedic/{id}/compatibility/{partner_id}`.
- [ ] P1: Placeholder/static data - remove fixed Lakshmi x Ravi result and fixed Gun Milan totals.
- [ ] P1: Missing screen - build full compatibility detail (`215:805`).
- [ ] P1: Missing interaction - make approximate-time, form validation, result detail and share feedback real.
- [ ] P2: Missing loading/error/empty/offline state - add no checks yet, loading computation, partner missing data, API error and offline states.

### 6. Chart real-data wiring

- [ ] P1: Existing backend not wired - bind chart hub, full chart, planet detail and provenance to active kundli data from VedicService.
- [ ] P2: Existing backend not wired - wire Varga charts to real divisional chart payloads.
- [ ] P2: Existing backend not wired - wire Life Periods to Vimshottari/Yogini APIs.
- [ ] P2: Missing screen - add Sookshma (`216:160`) and Prana (`216:262`) dasha levels.
- [ ] P2: Existing backend not wired - wire Yogas & Doshas to `/vedic/{id}/yogas-doshas`.
- [ ] P2: Existing backend not wired - wire Strength, Ashtakavarga and Jaimini to real endpoint payloads.
- [ ] P2: Missing loading/error/empty/offline state - add chart computing, partial-calculation, unsupported convention, API error and offline/stale states.
- [ ] P2: Missing screen - implement or explicitly defer practitioner Yantra, practitioner Charts and guided Your Story presentation.

### 7. Remedies and Muhurta

- [ ] P1: Existing backend not wired - wire Remedies and Mantra tracker to recommendation/practice APIs.
- [ ] P1: Placeholder/static data - remove fixed remedy cards, local-only mantra progress and personalized-looking static trackers.
- [ ] P1: Existing backend not wired - wire Muhurta goal/results to goal catalog, search, saved windows and reminder APIs.
- [ ] P1: Missing interaction - make add-to-calendar, remind, save and completion actions produce success/error feedback.
- [ ] P2: Missing loading/error/empty/offline state - add no recommendations, no windows, save failure, notification denied and offline states.
- [ ] P2: Missing screen - implement Guided What to do (`215:156`) as the guided-mode remedies presentation.

### 8. Missing platform and resilience states

- [ ] P2: Native-platform surface - implement or product-defer Home Screen Widget (`103:92`).
- [ ] P2: Native-platform surface - implement or product-defer Lock Screen context (`104:92`).
- [ ] P2: Native-platform surface - implement or product-defer Live Activity (`106:92`).
- [ ] P3: Native-platform surface - implement or product-defer Watch Complication (`106:102`).
- [ ] P2: Native-platform surface - implement Push Notification morning brief (`106:109`) with permission recovery.
- [ ] P2: Native-platform surface - implement Share Story Card (`107:101`) or explicitly defer.
- [ ] P2: Missing loading/error/empty/offline state - build reusable Offline/Stale Data (`216:773`).
- [ ] P2: Missing loading/error/empty/offline state - build reusable Partial Calculation (`216:838`).
- [ ] P2: Missing loading/error/empty/offline state - identify and implement/defer `screen-3-unknown` (`216:904`).
- [ ] P2: Missing loading/error/empty/offline state - build notification denied recovery (`216:964`).

### 9. Persona-specific presentation refinement

- [ ] P2: Missing screen - implement Guided, Balanced and Practitioner Aha states (`212:416`, `212:458`, `212:512`) without duplicating unnecessary components.
- [ ] P2: Missing interaction - make persona mode affect navigation, copy/detail depth, default expanded/collapsed state and technical data visibility.
- [ ] P2: Existing backend not wired - make persona presentation consume real feature payloads rather than separate static copies.
- [ ] P2: Missing loading/error/empty/offline state - cover preference loading, cloud sync failure and default mode fallback.
- [ ] P3: Visual/accessibility defect - re-check long names, Telugu/mixed-script text, 200% zoom and dark-mode fixed-color SVGs after each slice.

### Auth verification and configuration follow-up

- [ ] P2: Missing visual state - add dedicated mobile auth confirmation/result states for registration, magic link, password reset and callback errors.
- [ ] P2: Verification/configuration gap - verify hosted Supabase redirect allowlist for mobile custom scheme and web return URLs.
- [ ] P2: Verification/configuration gap - verify real-device PKCE, fragment-token, Google, magic link and password-reset callbacks.
- [ ] P2: Verification/configuration gap - verify email confirmation and reset delivery with a test inbox.
