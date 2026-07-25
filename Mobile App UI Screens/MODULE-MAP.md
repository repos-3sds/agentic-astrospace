# Module Map — AstroSpace Native App

> How the whole app divides into design modules, mapped to the native IA. Each module is
> designed as a complete screen flow (like M1 Onboarding). Nothing from the current app is
> dropped — the ~15-tab workbench collapses into 5 nav destinations + out-of-nav flows.

## IA

```
BOTTOM NAV:   Today · Ask · You (Chart) · Calendar · More
OUTSIDE NAV:  Onboarding · Compatibility · Remedies/Muhurta · Settings · Native surfaces
```

## Modules

| # | Module | Absorbs (current tabs) | Mode lean | Status |
|---|--------|------------------------|-----------|--------|
| M0 | Foundations & App Shell (design system, nav, states) | — | all | tokens ✅ |
| M1 | Onboarding & Activation | — | all | ✅ done |
| M2 | Today / Daily Guidance (Home) | Overview | Guided/Balanced | ✅ done |
| M3 | Ask (question-first / CE) | Ask AI, Readings | Guided/Balanced | ✅ done |
| M4 | You / Chart (workbench) | Overview, Vedic, Chart, Varga, Dashas, Jaimini, Ashtakavarga, Yogas & Doshas | Practitioner | ✅ done |
| M5 | Transits & Gochara | Gocharam, Transits | Balanced/Practitioner | ✅ done |
| M6 | Calendar, Panchang & Festivals | Calendar | Guided/Balanced | ✅ done |
| M7 | What to Do — Remedies & Muhurta | *(new)* | all | ✅ done |
| M8 | Compatibility / Matchmaking | Compatibility | Balanced | ✅ done |
| M9 | Profiles, Modes & Settings | Settings, Notes | all | ✅ done |
| M10 | Native Surfaces (widgets, live activities, watch, share) | — | all | ⬜ not started |

**All 9 in-scope modules (M1–M9) are designed and wired.** Only M10 (native platform
surfaces — widgets, Live Activities, watch complications, share cards) remains, and
that's a different deliverable type (platform specs, not Figma screens).

### M4 · You/Chart sub-modules
M4a Chart & Positions · M4b Divisional (varga) charts · M4c Life Periods/Dashas ·
M4d Yogas & Doshas · M4e Strength & Advanced (Shadbala, Ashtakavarga, Jaimini) ·
M4f Learning layer.

## Current-tab → module map
Overview → M2+M4a · Vedic → M4a · Varga Charts → M4b · Dashas → M4c · Jaimini → M4e ·
Gocharam → M5 · Transits → M5 · Calendar → M6 · Ashtakavarga → M4e · Yogas & Doshas → M4d ·
Chart(hub) → M4 nav · Readings → M3 · Compatibility → M8 · Notes → M9 · Ask AI → M3.

## Design sequence
1. **M2 Today** → 2. M3 Ask → 3. M7 Remedies & Muhurta → 4. M4 You/Chart →
5. M6 Calendar & Festivals → 6. M5 Transits & Gochara → 7. M8 Compatibility →
8. M9 Settings/Profiles → 9. M10 Native.

Components are promoted to Figma components/variants as each module is built.

## M2 · Today — screen set  ✅ COMPLETE
1. Today Home (collapsed) — ✅ (node 13:2)
2. Today Home (expanded / full scroll) — almanac, Today-vs-Always, Ask chips — ✅ (20:2)
3. Day-quality detail sheet — ✅ (21:22)
4. "Why this reading?" evidence sheet — ✅ (22:23)
5. Listen / audio player — ✅ (23:25)

**Components created (reused app-wide):** Button (ink/outline variants) · Tag ·
Sheet Handle · Stat Cell · Day Quality Gauge · App Bar/Profile · Bottom Nav/Today.
Placed above the screens on the canvas (y ≈ −1050 to −820).

## M3 · Ask — screen set  ✅ COMPLETE
1. Ask — Home (empty state, domain chips, suggested-from-chart chips, composer) — ✅ (25:25)
2. Ask — Voice listening (full-bleed dark overlay, pulsing mic, live waveform, transcript) — ✅ (25:123)
3. Ask — Answer view (question bubble → verdict → what to do → why → follow-up) — ✅ (26:54)
4. Ask — Refer-out safety state (health/legal/money never gets a verdict) — ✅ (27:83)

Detail screens (Answer view, Refer-out) are pushed sub-flows, not tab roots — back button
in header, **no bottom nav** on those two (removed per review). Ask Home + Voice keep the
Bottom Nav/Ask component (Ask tab active).

**New component:** Bottom Nav / Ask (Ask-tab-active variant of the nav, node 24:25).

## M7 · Remedies & Muhurta — screen set  ✅ COMPLETE
1. Remedies — For You (cards tied to a specific affliction: Saturn dasha friction, Manglik flag; honest "traditional practice · not a guarantee" labelling) — ✅ (29:55)
2. Remedy detail — mantra tracker (streak pill, tap-to-count progress dial 45/108, reminder CTA) — ✅ (29:109)
3. Muhurta finder — goal picker (6 goal cards, date-range chips, location-aware) — ✅ (30:56)
4. Muhurta results — ranked windows (#1 best + why, add-to-calendar/remind actions, honest closing note) — ✅ (31:57)

QA catch + fix: mantra title was clipping (missing textAutoResize/FILL) and a goal card's
2-line label was clipped (fixed-height card) — both fixed. Then a follow-up fix
(adding outer-frame padding) double-padded the content column and broke the 2-col grid
down to 1-col — reverted (ct/ab already carry their own 20px padding; only paddingBottom
needed at the outer frame).

## M4a · Chart Hub — screen set  ✅ COMPLETE (first sub-module of M4 You/Chart)
1. Chart Hub / "Your Chart" tab (big-three, mini D1 preview, provenance strip, 2×2 tool tiles linking to M4b–M4e) — ✅ (35:57)
2. Chart — full render (true merged-center South Indian D1, S/N/E style switcher, legend, tap-a-planet hint) — ✅ (36:86)
3. Planet detail sheet (glyph, sign/house, dignity/nakshatra/retrograde/combustion tags, lordships, "what this placement means") — ✅ (36:201)
4. Provenance sheet ("How this was computed" — ephemeris/ayanamsha/node/house-system/place/confidence, convention-dependent note, link to Settings) — ✅ (36:247)

Hub is the tab root (keeps Bottom Nav/Chart); the other 3 are pushed/overlay detail
screens (back header only, no bottom nav) — same pattern established in M3.

**New component:** Bottom Nav / Chart (Chart-tab-active variant, node 34:57).

## M4b–f · Chart sub-modules — screen set  ✅ COMPLETE (all of M4 now done)
5. Divisional (varga) charts — chip selector (D1/D9/D10/D7/D12), D9-Navamsha rendered
   in the same merged-center South Indian grid, vargottama callout — ✅ (39:87)
6. Life Periods (Dashas) — Vimshottari/Yogini toggle, active-period card
   (Venus→Saturn), expandable maha-dasha tree with antar sub-periods, active period
   highlighted — ✅ (40:87)
7. Yogas & Doshas — All/Yogas/Doshas filter, cards for Gajakesari (strong),
   Raja Yoga (parivartana), Manglik (flagged + cancelled, exception shown),
   Kalasarpa (honestly "not present") — ✅ (41:87)
8. Strength & Advanced — Shadbala/Ashtakavarga/Jaimini segmented control; Shadbala
   view shows per-planet strength bars (meets/below classical minimum, virupa value)
   — ✅ (41:149)
9. Learning sheet (M4f) — tap "Learn this yoga" → classical rule + BPHS verse/citation
   + a worked example from the user's own chart — ✅ (41:210)

All five are pushed detail screens (back header, no bottom nav), reached from the
Chart Hub's tool tiles. **M4 You/Chart is now fully designed end-to-end** (9 screens
total across M4a–f).

### Revision — Eastern chart style + dasha redesign (post-review)

Checked the actual Angular implementation (`ui/src/app/shared/kundli-chart/`,
`ui/src/app/features/kundli/dashas/`) after user feedback that the mockup charts/dashas
weren't right. Findings + fixes:

- **Eastern chart geometry corrected.** The app's Eastern (Bengali) style is a 3×3 grid
  where the 4 corner cells are each split diagonally into 2 triangles (12 sign zones
  total) with a **blank center** — structurally different from South Indian's merged
  2×2 center. Rebuilt via a single imported SVG (grid lines + diagonals from the real
  400×400 coordinate system) with text overlays per zone — matches the codebase exactly
  (verified: Pisces upper-right / Aries lower-left in the top-left cell, per source).
- **Eastern is now the default/selected style** across the full Chart render (36:86),
  the D9 varga chart (39:87), and the Chart Hub mini preview (35:57) — chip order is
  Eastern, South, North.
- **Chart size increased** — card padding reduced from 16px to 8px, chart itself grown
  from 313px to 337px (near-edge-to-edge on a 393pt device).
- **Life Periods (40:87) rebuilt** to match the app's real navigation model: a sticky
  Maha/Antar/Pratyantar level switcher showing **one flat list at a time** (not a
  nested accordion), a breadcrumb ("Within Venus maha dasha"), and the active period
  highlighted — mirrors `dashas-tab.component` (mobile: current-card → level-switcher
  tabs → single period-list). Dates corrected so "today" falls inside the highlighted
  Venus–Saturn antar (2025–2028).
- Bug caught + fixed mid-revision: an overly-loose node selector on the Hub screen
  placed the new mini chart outside its card; corrected by finding the card via its
  `cornerRadius`+`effectStyleId` signature instead of a text-content search that also
  matched an ancestor frame.
- **Varga chip row corrected to all 20 vargas** (was showing only 5). Verified against
  `astrospace/core/vedic/vargas.py` `VARGA_INFO` — D1–D12, D16, D20, D24, D27, D30,
  D40, D45, D60. D5/D6/D8/D11 carry a small unverified-status dot, matching the
  engine's `UNVERIFIED_VARGAS` set (honest convention-dependent labeling, per
  design_principles.md §6). Row is unfilled-width (overflows 353px) with the parent
  screen clipping content — simulates a real horizontally-scrollable chip carousel
  auto-scrolled to the selected D9 chip (D8/D20 peek in at the clipped edges).

### Revision 2 — Balanced-mode disclosure audit (post-review)

Self-audit against the Balanced contract (`design_principles.md §2–3`: "plain on top,
depth underneath"; Balanced = Guided content + Practitioner access) found M4 had
renamed one label (Dashas → Life Periods) but never actually implemented adaptive
**default disclosure** — the Chart Hub and Planet Detail sheet defaulted to
Practitioner-depth jargon with no plain layer, reproducing the "astrologer's
workbench" anti-pattern the whole redesign exists to fix. Three fixes applied:

1. **Chart Hub (35:57)** — added a "YOUR SIGNATURE" plain-language card
   ("Warm, communicative, and grounded once you commit...") leading *before* the
   raw Sun/Moon/Ascendant stat cells; softened the provenance strip from raw jargon
   ("Lahiri · Whole-sign...") to a plain "Computed transparently — tap to see how."
2. **Planet Detail sheet (36:201)** — fully reordered: a plain meaning paragraph now
   leads ("Your Sun brings a curious, communicative... currently 'combust'..."),
   with the dignity/nakshatra/lordship tags collapsed behind a **"Show technical
   detail"** toggle (collapsed by default), plus a "What does 'combust' mean?"
   link into the learning layer (M4f).
3. **Life Periods (40:87)** — added inline glosses under both the
   Vimshottari/Yogini toggle and the Maha/Antar/Pratyantar level switcher, so the
   Sanskrit terms aren't a wall a Guided/Balanced user hits unexplained.

Note: Full Chart render, Provenance sheet, Divisional charts, and Strength & Advanced
were judged acceptable as-is — they're opt-in destinations reached by an explicit tap
(not tab-root defaults), which is itself correct progressive disclosure.

## M4 dead-end sweep — "complete journey" pass

User explicitly asked that every tab/toggle/chip across the app have a real
destination, not just visual states. Closed all of the following:

- **Chart style switcher** — built South Indian (56:88) and North Indian (57:88) full
  chart views (North Indian = correct diamond geometry: outer square + both
  diagonals + inner diamond connecting side-midpoints; houses fixed, signs rotate
  from lagna, per `kundli-chart.component.ts`). Full Eastern↔South↔North mesh wired.
- **Varga chip row** — D1 (61:88) and D10 (61:195) built as second/third worked
  examples beyond D9, using a reusable `buildVargaScreen()` function; the other 17
  chips reuse the identical pattern (data-swap only, not new design work).
- **Life Periods** — built Maha level (59:88), Pratyantar level (59:258), and Yogini
  system (59:427) views; full drill mesh wired (breadcrumbs, level tabs, system
  toggle). Fixed a date inconsistency: original hero text ("Venus → Saturn →
  Mercury") didn't correspond to a proportionally-plausible date landing on "today" —
  corrected to "Venus → Saturn → Venus" with dates chained consistently across all
  three levels.
- **Strength & Advanced** — built Ashtakavarga (60:88, SAV bar chart by house) and
  Jaimini (60:257, chara karakas + arudha padas) tabs; full 3-way mesh wired.
- **Ashtakavarga chart request** — added an actual SAV bindu chart-grid (not just the
  bar list) using the same Eastern-chart geometry, with a planet selector row
  (SAV/Su/Mo/Ma/Me/Ju/Ve/Sa). First attempt used wrong zone coordinates (invented
  fresh instead of reusing verified ones) — rebuilt correctly.
- **Register form (2b, 62:88)** built as the missing alternate of Login/Register;
  **Manglik cancellation sheet (62:140)** built for the previously-dead "View
  cancellation" link on the Remedies screen.
- **Profile switching was a dead end** — Chart Hub's profile pill and Settings'
  "Manage profiles" row had no destination. Built a Profile Switcher sheet (26,
  79:89 — Lakshmi/Aarav profiles + "Add a profile" → Birth Details) and wired both
  entry points.

## M9 · Settings — screen set  ✅ COMPLETE

7 screens: Home (66:89) grouped rows → Mode & Tone (67:89), Language & Audio
(67:147), Notifications (67:173), Location (69:89), Conventions (69:117, **closes
the Provenance sheet's dead "Change conventions in Settings" link**), Account &
Privacy (69:180, Sign out/Delete → Landing). All back buttons wired Home↔sub-screens.

Bug caught + fixed: 5 of 7 sub-screens had their back-button row appended to the
screen *after* the content column (because `ct` was appended to `S` before the
`header()` helper ran and appended `ab`), so the header floated below the content
instead of above it. Fixed by reordering — `ab` inserted at index 0.

## M5 · Transits & Gochara — screen set  ✅ COMPLETE

1. **Gochara** (91:89) — plain-language transit readings: overall-mood card, 3
   per-planet transit cards (sign/house/tag/plain description). Balanced-mode default.
2. **Full Transits** (92:89) — technical companion: position table with AV (effective
   severity) + vedha flags, key aspects, 30-day timeline. Toggle mesh between the two.

Entry point: new tile "Transits & Gochara" on Chart Hub's explore grid.

## M6 · Calendar & Festivals — screen set  ✅ COMPLETE

1. **Calendar** (93:89) — month grid (July 2026), today highlighted, festival-day
   dots, upcoming-observances list below. Bottom-nav tab root — **this also finally
   gives the long-unwired "Calendar" bottom-nav tab a real destination**, wired from
   every screen that has a bottom nav (Today ×2, Ask, Chart Hub, and Calendar's own).
2. **Festival detail sheet** (94:118) — meaning, how-to-prepare checklist, best time
   window, "Remind me" → links into Notifications settings.

Data-consistency bug caught + fixed: the sample festival was originally dated in the
past relative to the app's "today" (25 Jul) while listed under "Upcoming
Observances" — corrected to a genuinely upcoming date, calendar dot moved to match.

## M8 · Compatibility — screen set  ✅ COMPLETE

1. **Compatibility Hub** (97:119) — honest "how this works" explainer (no fear, no
   upsell), "Check a new match" CTA, recent-checks list.
2. **Add Prospect** (97:144) — lightweight birth-detail entry, no full profile
   required. Bug fixed: CTA wasn't bottom-pinned (missing `SPACE_BETWEEN` on the
   outer frame) — corrected.
3. **Gun Milan Results** (98:119) — score hero (28/36), koota breakdown (Nadi/
   Bhakoot/Graha Maitri/Gana), Manglik dosha flagged as "matched · not a concern"
   (self-cancelling when both charts carry it), Share report / Find a muhurtham
   (routes into the M7 muhurta finder).

Entry point: new tile "Compatibility" on Chart Hub's explore grid.

Bug caught + fixed while adding these tiles: an extra `.parent` walk in the tile
node-search logic had appended the Transits & Gochara tile to the outer content
column instead of the actual 2-column wrap-grid, silently breaking the grid layout.
Found while adding the Compatibility tile; fixed by locating the grid via a
known-good sibling tile and re-parenting the misplaced card.

## Clickable prototype — fully wired

**55 screens, 167 wired interactions, 0 dangling reaction destinations, 0 screens
with no outgoing wiring** (verified via full-file audit). Covers: full onboarding
flow, all bottom-nav cross-linking (incl. the once-dead Calendar tab), every sheet
(handle-tap-to-dismiss via `BACK`), all chart/dasha/strength-tool switcher meshes,
Settings, Profile Switcher, and all three new M5/M6/M8 modules.

**Known API limitation:** `overlayPositionType`/`overlayBackground`/
`overlayBackgroundInteraction` are read-only via the Figma Plugin API — true
`OVERLAY` navigation (background dimming, tap-outside-to-dismiss) can only be
configured through Figma's own Prototype panel, not from a script. Worked around
with `NAVIGATE` + `SLIDE_IN` transitions; since every sheet already has its own
scrim baked into the design, this looks and feels like a rising overlay sheet in
practice. If true overlay behavior is wanted later, it's a one-time manual toggle
per sheet frame (~15) in Figma's UI.

**Post-testing bug fixes** (found via the user clicking through the live prototype):
- **Eastern chart bottom-left misalignment**, present in all 6 places the chart
  appears — root cause: the BL corner's diagonal is a negative-slope line
  (`x+y=const`), but the label-offset pattern used only clears a positive-slope line
  (`y=x`, correct for TL/BR). Capricorn's label sat exactly on the diagonal line.
  Fixed with correct same-direction offsets across Chart Hub preview, full chart,
  D1/D9/D10 vargas, and the Ashtakavarga chart.
- **Today's top-right icon** — a sun/rays shape that visually read as a light-mode
  toggle but actually opened Settings. Replaced with a proper gear icon (same
  destination) on both Today variants; the full-scroll variant had never had this
  button wired at all — fixed.
- **No explicit language choice** — Telugu only ever appeared as a toggle buried in
  Settings/the Listen sheet. Added a "Choose your language" screen (82:96, English
  default, Telugu selectable) inserted after Landing/Register and before Welcome.
  First build had the Telugu card's label set to `FILL`, pushing the romanized
  caption to a stray far-right position — rebuilt with a proper stacked layout.
- **Orphaned duplicate frame** — an earlier `use_figma` call hit
  `ERR_NETWORK_CHANGED` and was retried, but the failed call had already partially
  created a frame server-side before erroring, leaving a dead duplicate of the
  Gochara screen. Found via a full-file duplicate-name scan; deleted.

## M10 · Native Surfaces — ✅ COMPLETE

6 platform-surface mockups (not phone-frame screens — different sizes/contexts):
1. **Home Screen widget** (medium, iOS-style) — day-quality ring, verdict, next-window countdown
2. **Lock Screen widget** (circular) — shown in a dark lock-screen context frame (time/date
   backdrop) so it reads correctly; bug fixed: initially set opacity on the whole frame
   instead of just the background fill, fading the ring/number too — corrected.
3. **Live Activity / Dynamic Island** (expanded) — Rahu Kalam countdown + ring, shown on a
   phone-notch context. Bug fixed: forced a fixed width before setting hug-sizing, causing
   severe content overflow/clipping — rebuilt letting the auto-layout naturally hug content.
4. **Watch complication** — day-quality ring + label on a watch-face context.
5. **Push notification** (morning brief) — app icon, title, body, timestamp.
6. **Share story card** — branded gradient, verdict headline, tagline. Bug fixed: a
   decorative stars layer was appended as a normal (non-absolute) auto-layout child,
   consuming the full 530px height and pushing all real content below the clipped
   bounds — fixed by setting `layoutPositioning = 'ABSOLUTE'`.

## Dark Mode — ✅ INFRASTRUCTURE + 3 REPRESENTATIVE SCREENS

Added a real **"Dark" mode** to the Tokens variable collection (not just duplicated
screens with hardcoded colors) — 21 tokens given dark values sourced from the
codebase's actual `:root.app-dark` block in `styles.scss`. Since every screen was
built with proper variable bindings from the start, flipping a frame's explicit
variable mode via `setExplicitVariableModeForCollection` cascades correctly through
backgrounds, text, borders, and cards automatically.

**What doesn't cascade automatically:** icon SVGs, which use hardcoded hex strokes
(not variable-bound). Built 3 representative dark-mode screens — **Today** (108:92),
**Ask Home** (108:186), **Chart Hub** (108:246) — and manually recolored every icon
that was invisible/low-contrast dark-on-dark (gear, clock, history, domain-chip
icons, provenance checkmark) to variable-bound colors. Confirmed the underlying
layout, cards, and text needed zero manual fixes — proof the token system is sound.

Not built: dark variants of the remaining 58 screens (would be substantial
duplicate-and-fix effort per screen); the pattern is proven and repeatable if wanted.

## Component States — ✅ COMPLETE (representative set)

1. **Button `disabled` variant** added to the Button component set (18:6) — now
   ink/outline/disabled, 3 variants. Bug fixed: the component set's `layoutMode` was
   `NONE` with all variants stacked exactly on top of each other at (0,0) — existed
   since the set was first created but was invisible because instances always
   reference a specific named variant regardless of the master's arrangement; only
   surfaced once 3 variants made the overlap visually obvious. Fixed by explicitly
   positioning each variant in a row.
2. **Input field states** reference (default / focused / error, with error icon +
   message) — a reusable pattern, not yet applied retroactively to existing forms.
3. **Ask — Loading state** (108:417) — thinking indicator, skeleton lines, animated
   dot sequence. Wired into the live prototype: Ask Home's send button → Loading →
   **auto-advances to the real Answer after 1.8s** via an `AFTER_TIMEOUT` trigger.
4. **Compatibility — Empty state** (110:121) — "No checks yet" with icon + copy,
   built by cloning the Hub and removing the recent-checks card.
5. **Generic error state** (110:153) — "Something went wrong" + Try again button,
   reusable pattern for any network/computation failure.

## Final audit (this session)

**61 phone screens, 72 total frames, 197 wired reactions, 0 dangling destinations,
0 unwired screens, 0 unexpected duplicate names** (the "Frame"×4 are generic
component-wrapper containers near the token area — expected, harmless).

## Web-app parity pass — ✅ COMPLETE

Audited the 61 designed screens against the **actual Angular app** (18 routes,
`ui/src/app/features/`) rather than the earlier design doc. Found ~75% of surfaces
covered but only ~65% of content blocks. Closed every real gap:

**Built (9 new screens):**
1. **Readings** (113:122) — period segment (today/week/year), current version + rating,
   saved-version history, earlier readings with hold-rate tags.
2. **Prediction Claims / Track record** (114:124) — the `prediction_claims` table finally
   has a UI. Accuracy %, stacked accurate/partly/missed/n-a bar, per-claim
   Yes/Partly/No validation. Maps 1:1 to the DB's status enum.
3. **Notes** (115:124) — per-profile private notes with autosave state + char count.
4. **Calendar — Day detail** (116:124) — the web Calendar's *dated intelligence feed*:
   personal day check, day timeline (Brahma Muhurta → Varjya), day choghadiya chips,
   active period stack. My original M6 was festival-only and missed this entirely.
5. **Practitioner Reference hub** (117:124) — houses the dense classical tables behind
   an explicit tap, so they exist without reintroducing the 15-tab workbench.
6. **Avkahada & Ghatak** (117:175) — varna, vashya, yoni, gana, nadi, tatwa, vihaga,
   paya, name letter, charan + all 7 ghatak points.
7. **Graha positions & conditions** (118:124) — all 9 grahas with degree,
   nakshatra-pada, dignity/retrograde/combustion tags.
8. **Ashtakavarga tables** (118:239) — Prastara/Shodhana/Pinda tabs + bindu matrix.
9. **Favourable points** (118:383) — lucky number/day/colour/stone/metal/direction,
   yogakaraka, numbers to avoid, labelled as tradition not fact.

**Also fixed:** Jaimini's dead "Special lagnas — tap to view" stub replaced with real
inline Bhava/Hora/Ghati lagna content.

**Entry points:** Chart Hub grid grew to 8 tiles (added Readings, Reference) plus a
Notes row; Calendar's day-25 cell opens Day detail.

### Astrology-accuracy corrections (caught during this pass)

Checked the sample chart's math rather than trusting placeholder values:

- **6 wrong nakshatra padas** on Graha positions — each pada recomputed from the stated
  degree (e.g. Sun 23°14′ Gemini was labelled *Ardra pada 2*, but Ardra ends at 20°00′
  → corrected to *Punarvasu pada 1*; Mars, Mercury, Jupiter, Rahu, Ketu likewise).
- **7 wrong Avkahada values** — they didn't match a Cancer/Pushya-pada-1 Moon.
  Varna Vaishya→Brahmin, Vashya Chatushpada→Jalachara, Yoni Mahish→Mesha,
  Gana Manushya→Deva, Tatwa Prithvi→Jala, name letter Poo/Sha→Hu, Charan 2nd→1st pada.
- **An impossible statement** in the Planet Detail sheet: it described the *Sun* as
  "combust." Combustion means proximity *to* the Sun, so the Sun cannot be combust —
  copy rewritten, and the learning link retargeted to the 3rd house.

These matter because the product's entire positioning is *"Vedic astrology, computed"* —
a practitioner reviewing the mockups would catch wrong padas immediately.

## Final state

**70 phone screens, 81 total frames, 216 wired reactions, 0 dangling destinations,
0 unwired screens, 0 unexpected duplicates.**

Figma file: `RRhuTcaKIhqILZW7JUKFzI` (see memory `figma-hifi-mockups`).
