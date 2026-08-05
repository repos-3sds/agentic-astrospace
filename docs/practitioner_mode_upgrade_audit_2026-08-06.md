# Practitioner Mode Upgrade Audit — 2026-08-06

Scope: mobile Practitioner flows, plus backend/API gaps that directly affect the mobile experience.

## Executive Summary

Practitioner mode currently has a good chart-rendering base, but the product depth is uneven. The biggest issue is that several screens render technical outputs or locally synthesized placeholders instead of using the richer backend contracts that already exist. This creates repeated remedies, incomplete reasoning, shallow reference content, confusing navigation, and avoidable latency.

The next phase should not be a cosmetic patch. It should be a contract pass: define what each Practitioner module must prove, what it must explain, and which backend payload owns the truth. Then update the UI to present that truth with consistent Siddha mobile design.

## Highest Priority Upgrades

### P1 — Remedies Must Use Backend Recommendations

Gap type: backend/UI wiring, safety, personalization

Routes:
- `/m/remedies`
- `/m/explore/what-to-do`
- `/m/remedies/mantra`

Source files:
- `astrospace/api/remedy_routes.py`
- `astrospace/core/vedic/remedies.py`
- `ui/src/app/features/mobile/remedies/remedies.component.ts`
- `ui/src/app/features/mobile/remedies/mantra-tracker.component.ts`

Current state:
- Backend already exposes `/api/v1/remedies/{kundli_id}` with dasha-ranked groups, practice catalog, provenance, convention dependency, cost flags, and disclaimer.
- Mobile remedies screen does not call this endpoint. It reconstructs cards from `dashas()` and `yogasDoshas()`.
- This explains why “Start streak” feels generic and why the same Saturn dasha remedy appears too broadly.
- Manglik appears in Remedies because mobile synthesizes a Manglik card from yogas/doshas. That belongs in Yogas/Doshas or Compatibility caution context, not as a primary remedy module unless explicitly selected by the user.

Expected Practitioner behavior:
- Remedies are populated from the backend remedy recommendation API.
- Each remedy group shows: chart trigger, dasha relevance, why now, traditional source/provenance, optional/cost warning, and “not a guarantee” safety language.
- Manglik is not shown as a general remedy card by default. If present, it should be a contextual flag under Yogas/Doshas or Compatibility with cancellation detail.
- “Start streak” starts the exact selected practice, not a hardcoded Saturn item.
- Reminder settings and haptics connect to practice scheduling and streak milestones.

Upgrade direction:
- Add `VedicService.remedies(kundliId, includeCostly=false)` or a dedicated `RemediesService`.
- Replace mobile local card synthesis with backend `groups`.
- Model streak state by `remedy_slug + kundli_id`.
- Add audio metadata per mantra: title, text, count target, preferred day, language, and source.
- Add two modes:
  - Auto mode: app plays/loops guided japa until 108 count completes.
  - Manual mode: user taps/counts beads; haptics optional.
- Keep gemstones behind “optional, needs qualified review” wording.

### P1 — Muhurtha Needs Real Date Range Input

Gap type: core user story, UI consistency, input contract

Routes:
- `/m/muhurta`
- `/m/muhurta/results`

Source files:
- `astrospace/api/muhurta_routes.py`
- `astrospace/core/vedic/muhurta.py`
- `ui/src/app/features/mobile/muhurta/muhurta-goal.component.ts`
- `ui/src/app/features/mobile/muhurta/muhurta-results.component.ts`

Current state:
- Backend supports `date_from` and `date_to`.
- Mobile “Pick dates” is only a segmented choice and does not collect a date or range.
- Frontend goal IDs do not exactly match backend goal slugs: UI uses `property`, `contract`, etc.; backend expects `buy_property_gold`, `sign_contract`, etc. This can cause wrong or failed requests unless translated later.

Expected Practitioner behavior:
- User can pick a single date or a date range.
- UI shows selected location clearly because muhurta is local, not birth-place based.
- Results explain why a window scored well or poorly: vara, nakshatra, tithi, tarabala, chandrabala, ghatak, clear/trimmed avoid windows.
- CTAs use the same mobile button/icon system as Settings, Calendar, and Chart.

Upgrade direction:
- Add native date inputs or a small range picker sheet.
- Normalize frontend goal slugs to backend slugs.
- Persist last selected goal/range/location.
- Show “no clean window found” as an honest empty state, not a failure.

### P1 — Practitioner Ask Is in the Wrong Product Position

Gap type: persona flow, navigation

Routes:
- `/m/ask`
- `/m/chart`
- `/m/readings`

Source files:
- `ui/src/app/shell/mobile-nav.ts`
- `ui/src/app/features/mobile/chart/chart-hub.component.ts`
- `ui/src/app/features/mobile/ask/*`

Current state:
- Ask exists as a global mobile tab in some persona/nav contracts and as a tile in Practitioner Yantra.
- User explicitly says Practitioner Ask is not a tab.

Expected Practitioner behavior:
- Practitioner footer should follow the Figma/persona contract.
- Ask should be invoked contextually from readings, chart interpretations, remedies, dashas, yogas, and reference pages.
- Submitted question should open a proper chat experience without footer.

Upgrade direction:
- Remove Ask from Practitioner primary/footer nav if still present in the active contract.
- Keep Ask as contextual action: “Ask about this yoga,” “Ask about this transit,” “Ask about this dasha period.”
- Wire reading cards into Ask with prefilled context and profile/chart metadata.

### P1 — Jaimini Needs Validation Before Trusting Output

Gap type: astrology correctness

Routes:
- `/m/chart/strength`
- `/m/chart/reference`

Source files:
- `astrospace/core/vedic/jaimini.py`
- `ui/src/app/features/mobile/chart/strength-advanced.component.ts`

Current state:
- Implementation covers chara karakas and arudha padas.
- It notes conventions: seven/eight karaka schemes, Rahu reverse count, arudha exceptions, and pending stronger-lord variant for Scorpio/Aquarius.
- UI hides this nuance inside a generic “Strength & Advanced” screen.

Expected Practitioner behavior:
- Practitioner can see selected convention: seven vs eight karaka, Rahu handling, arudha exception, dual-lordship convention.
- Jaimini should not be mixed as a tiny sub-tab if it is a serious module.
- Output should show calculation working and warnings where convention-dependent.

Upgrade direction:
- Add a Jaimini reference/settings section before expanding features.
- Revalidate against trusted chart examples and at least one external reference source.
- Add unit tests for chara karaka ranking, Rahu reverse degree, ties, A1/UL exception behavior, and Scorpio/Aquarius lord convention.

External references checked:
- Paramarsh explains eight-karaka ranking, Rahu reverse count, and seven/eight scheme distinction.
- PanchangBodh describes Jaimini as sign aspects, chara karakas, and Jaimini dashas.
- The current code aligns broadly with the public chara-karaka ranking rule, but needs test vectors before we call it accurate.

### P2 — Reference Must Become a Practitioner Workbench

Gap type: UI depth, information architecture

Routes:
- `/m/chart/reference`
- `/m/chart/reference/avkahada`
- `/m/chart/reference/grahas`
- `/m/chart/reference/ashtakavarga`
- `/m/chart/reference/favourable`

Source files:
- `ui/src/app/features/mobile/chart/reference.component.ts`
- `ui/src/app/features/mobile/chart/reference.component.html`

Current state:
- Reference is mostly flattened JSON rows.
- It is technically dense but not practitioner-useful.
- No charts/tables are used where visual interpretation would help.

Expected Practitioner behavior:
- Reference should be a searchable workbench: Avkahada, Ghatak, Graha table, dignity/motion, Ashtakavarga SAV/BAV, favourable points, calculation conventions.
- Use charts/tables where they reduce cognitive load.
- Each section should include “how to use this” for practitioners, without dumbing down.

Upgrade direction:
- Replace generic flattening with typed renderers.
- Add compact tables, score bars, sign grids, and source badges.
- Add route-level anchors and search integration.

### P2 — Yogas/Doshas Need Better Learning and Tags

Gap type: interpretation, education, classical bug risk

Routes:
- `/m/chart/yogas`

Source files:
- `astrospace/core/vedic/yogas.py`
- `astrospace/knowledge/vedic_rules/yogas.json`
- `astrospace/knowledge/vedic_rules/doshas.json`
- `ui/src/app/features/mobile/chart/yogas-doshas.component.ts`
- `ui/src/app/features/mobile/chart/yoga-learning-sheet.component.ts`

Current state:
- Backend returns deterministic rule detections and enriches from rule KB.
- Previous sweep found classical-looking repetition risk: “Learn this Yoga” and details can collapse into generic/repeated content.
- Tags such as mild/moderate are not explained well enough.

Expected Practitioner behavior:
- Each yoga card explains:
  - What the yoga means.
  - Exact trigger.
  - Strength basis.
  - Why tag is mild/moderate/strong.
  - Cancellation/mitigation notes if applicable.
  - Source status: classical, simplified, pending verification.

Upgrade direction:
- Expand KB per rule with practitioner explanation, lay explanation, strength rubric, exceptions, and source.
- In UI, make “moderate/mild” tappable or inline-explained.
- Ensure “Learn this Yoga” loads the selected yoga, never a generic Gajakesari detail.

### P2 — Strength & Advanced Needs Practitioner Meaning

Gap type: interpretation, presentation

Routes:
- `/m/chart/strength`

Source files:
- `astrospace/core/vedic/strength.py`
- `astrospace/core/vedic/ashtakavarga.py`
- `ui/src/app/features/mobile/chart/strength-advanced.component.ts`

Current state:
- Shadbala, Ashtakavarga, and Jaimini are combined.
- Current explanations are improved compared with raw output but still shallow for a Practitioner.

Expected Practitioner behavior:
- Shadbala: show ratio vs required minimum, rank, sufficiency, and interpretive consequence.
- Ashtakavarga: show SAV and BAV, strongest/weakest houses, transit usefulness, and bindu meaning.
- Jaimini: either separate module or clearly labeled sub-module with convention disclosure.

Upgrade direction:
- Use a workbench layout inspired by mature astrology software: table + chart + interpretation + source/convention.
- Add “how to read this” sections for Practitioner without turning it into Guided copy.

External references checked:
- Ashtakavarga sources consistently describe SAV as aggregate house/sign support and BAV as planet-specific support.
- Jagannatha Hora is a useful benchmark for breadth: divisional charts, planets, mathematical points, strengths, dashas, and transits are grouped as practitioner tools rather than scattered single cards.

### P2 — Vargas and Charts Should Merge Without Losing Depth

Gap type: navigation/information architecture

Routes:
- `/m/chart/full`
- `/m/chart/vargas`

Source files:
- `ui/src/app/features/mobile/chart/chart-full.component.ts`
- `ui/src/app/features/mobile/chart/varga-charts.component.ts`
- `ui/src/app/shared/kundli-chart/*`

Current state:
- Chart rendering itself has improved.
- Varga charts are still separated enough that users ask where they are.

Expected Practitioner behavior:
- Full chart and varga chart browsing should feel like one chart workbench.
- D1 is default; D9/D10/etc. are chart selectors, not a hidden separate world.
- Current chart-style preference applies consistently across all vargas.

Upgrade direction:
- Merge the entry experience: chart workbench with chart selector, style selector, planet detail, and varga notes.
- Keep shortcut tile for “Vargas,” but land in the same workbench state.

### P2 — Move Transits Into Yantra; Restore Calendar Position

Gap type: persona nav contract

Routes:
- `/m/chart`
- `/m/transits`
- `/m/transits/full`
- `/m/calendar`

Source files:
- `ui/src/app/shell/mobile-nav.ts`
- `ui/src/app/features/mobile/chart/chart-hub.component.ts`
- `ui/src/app/features/mobile/transits/*`

Current state:
- Practitioner Yantra already has a Transits/Gochara tile.
- Footer/nav contract still risks making Transits a primary placement.

Expected Practitioner behavior:
- Calendar returns to primary footer position where Figma/persona expects it.
- Transits/Gochara live inside Yantra/Chart workbench as a specialist tool.

Upgrade direction:
- Update persona nav mapping and route active-state logic.
- Ensure opening Transits keeps Yantra/Chart context selected if footer is visible, or hides footer on deep specialist pages.

## Backend/KB Upgrade Needs

1. Remedies KB needs fuller profile-based reasoning:
   - active dasha lord
   - antardasha/pratyantardasha relevance
   - dignity/combustion/debilitation
   - dosha flag only when contextually relevant
   - source/convention/cost/safety metadata

2. Audio/sloka support needs a real content model:
   - mantra text
   - transliteration
   - audio asset URL
   - one-cycle duration
   - repeat count target
   - loop-safe audio behavior
   - manual count support

3. Muhurta API already supports date ranges; frontend must expose it.

4. Jaimini needs test vectors and convention settings before expanding.

5. Yogas/Doshas KB needs richer per-rule educational payloads.

6. Ashtakavarga/Strengths need interpretation payloads, not only computed numbers.

7. Transits/Gochara should expose domain-level “so what” readings and dasha cross-reference in one payload.

## Proposed Implementation Order

1. Navigation contract cleanup:
   - Practitioner footer: Today, Chart/Yantra, Calendar, More as designed.
   - Ask becomes contextual, not primary tab.
   - Transits/Gochara moves under Yantra.

2. Remedies contract:
   - Wire mobile to `/api/v1/remedies/{kundli_id}`.
   - Remove local synthetic Manglik remedy card.
   - Fix streak identity per selected remedy.
   - Add reminder/haptics hooks.

3. Mantra audio/streak experience:
   - Add auto/manual modes.
   - Add selected-mantra state.
   - Add placeholder audio contract first, then real assets.

4. Muhurta date range:
   - Add date/range picker.
   - Fix goal slug mapping.
   - Improve result cards and empty states.

5. Chart/Varga merge:
   - One chart workbench with D1/varga selector.
   - Ensure style preference applies everywhere.

6. Reference workbench:
   - Replace flattened JSON rendering.
   - Add typed tables and chart visualizations.

7. Strengths/Jaimini/Yogas depth:
   - Add explanations, source badges, and convention disclosure.
   - Add backend tests before trusting more Jaimini output.

8. Full astrologer-eye sweep:
   - Once these contracts are fixed, run a Practitioner pass with real profile data and screenshots.

## Acceptance Criteria

- Remedies never show a generic wrong planet practice after selecting a different remedy.
- Manglik does not appear as a generic remedies card.
- Every remedy has “why this appears,” practice details, source, and safety framing.
- Start streak opens the exact selected remedy.
- Mantra tracker supports auto and manual count modes.
- Muhurta “Pick dates” actually collects single date or range and sends `date_from/date_to`.
- Practitioner Ask is not a footer tab; contextual Ask opens a no-footer chat.
- Reference sections are typed and useful, not flattened JSON.
- Jaimini shows convention and has backend tests for ranking/arudha rules.
- Yogas “Learn this Yoga” opens the selected yoga and explains strength tags.
- Strength/Ashtakavarga explains practical meaning, not just numbers.
- Transits/Gochara is reachable from Yantra and Calendar is restored in primary navigation.
- Vargas and D1 charts share one consistent workbench behavior.

## Source Notes

- Paramarsh: Jaimini chara karakas ranking, seven/eight scheme, Rahu reverse count.
- PanchangBodh: Jaimini overview and SAV/BAV descriptions.
- Prokerala and other Ashtakavarga references: Ashtakavarga as bindu-based support system.
- Jagannatha Hora public overview: useful benchmark for practitioner breadth and grouping.
- Navagraha mantra remedy references: use 108-count mantra practice as traditional framing, but keep “not a guarantee” and “regional variants exist.”
