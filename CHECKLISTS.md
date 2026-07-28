# CHECKLISTS

This file did not exist at the start of the 2026-07-28 mobile UI audit. It was created to hold the requested remediation checklist.

## Mobile UI audit remediation

- [ ] P0: Add and verify a mobile auth verification/auth-result flow for register, magic link, password reset, and Google callback.
- [ ] P0: Remove false persistence claims from Notes/Readings or wire them to real persisted data first.
- [ ] P1: Build Manage Profiles, Add Profile, Edit Profile, and Delete Profile confirmation screens from Figma.
- [ ] P1: Route Settings > Manage profiles to the profile-management flow, not `/m/settings/birth-details`.
- [ ] P1: Wire Calendar month/day/festival surfaces to `/vedic/{id}/calendar-intelligence`.
- [ ] P1: Make Calendar previous/next month controls functional and stateful.
- [ ] P1: Wire Compatibility add/select/results to real partner data and compatibility APIs.
- [ ] P1: Add the missing full compatibility detail screen.
- [ ] P1: Wire Readings list/detail/accuracy to reading and claim APIs, with honest empty states.
- [ ] P2: Wire Life Periods to Vimshottari/Yogini APIs, including Sookshma and Prana levels.
- [ ] P2: Wire Yogas & Doshas to `/vedic/{id}/yogas-doshas`.
- [ ] P2: Wire Strength/Ashtakavarga/Jaimini to real endpoint payloads.
- [ ] P2: Wire Remedies and Mantra tracker to recommendation/practice APIs.
- [ ] P2: Wire Muhurta goal/results to `/muhurta/goals`, `/muhurta/find`, and saved/reminder APIs.
- [ ] P2: Add offline/stale-data, partial-calculation, and notification-permission-denied states.
- [ ] P2: Add Gocharam/full-transit date and range controls.
- [ ] P2: Replace static Search with real recent searches and content/history results.
- [ ] P3: Audit and fix final-scroll clearance under the mobile tab bar.
- [ ] P3: Add visible feedback for share, clipboard, saved versions, add-to-calendar, and reminder actions.
- [ ] P3: Re-check long names, Telugu/mixed-script text, 200% zoom, and dark-mode fixed-color SVGs after each slice.
