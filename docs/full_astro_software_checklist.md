# AstroSpace Full-Fledged Astrology Software Checklist

This checklist tracks the work needed to move AstroSpace from a strong prototype into a serious, deterministic astrology platform. AI should explain and personalize; the core astrology must be calculated, testable, and auditable.

## 1. Core Calculation Authority

- [x] Move compatibility scoring from frontend approximation to backend engine.
- [x] Implement Ashta Koota / Gun Milan scoring with clear per-koota breakdown.
- [x] Fix audited Gun Milan scoring defects: Tara Janma/Parama Mitra, binary Varna, enemy Yoni pairs, Gana Manushya-Rakshasa, and Graha Maitri lookup.
- [ ] Add compatibility dosha flags and exceptions where rules are verified.
- [x] Add Manglik / Kuja dosha calculation.
- [x] Add first-pass major yoga detection: Raja, Dhana, Neecha Bhanga, Vipareeta Raja, Kemadruma, Gajakesari, Chandra-Mangal, Budhaditya, Kalasarpa flag.
- [x] Add Pancha Mahapurusha yogas and parivartana / graha-drishti association support for Raja and Dhana yoga detection.
- [x] Add structured Vedic rules KB for Yogas/Doshas with rule IDs, source status, implementation status, and source references.
- [ ] Validate Yoga/Dosha KB against external classical sources and upgrade exact rules to `verified_external`.
- [x] Add Shadbala v1 / phased strength system with provenance labels.
- [x] Add combustion, planetary war, avasthas, and retrograde strength handling.
- [x] Add transit aspects and gochara impact engine.
- [ ] Add purpose-based muhurta ranking.
- [ ] Add remedial recommendation engine only after deterministic rules are verified.

## 2. Prediction And Validation Workflow

- [x] Structure AI predictions into dated claims, category, confidence, and validation status.
- [x] Save every prediction version by generated local date.
- [x] Add user validation: accurate, partly accurate, missed, not applicable.
- [x] Track first-pass prediction accuracy over time by profile.
- [ ] Track deeper prediction accuracy over time by category and profile.
- [x] Add deviation reporting between generated reading versions.

## 3. Product Workflows

- [x] Add dashboard intelligence: active dasha, today panchanga, and transit alerts across profiles.
- [x] Add first-pass calendar view for panchanga, dashas, and transits.
- [x] Attach readings to the calendar view.
- [ ] Attach reminders to the calendar view.
- [ ] Add global search across profiles, notes, readings, and predictions.
- [ ] Add profile comparison modes beyond marriage compatibility.
- [ ] Add PDF export for kundli, compatibility, panchanga, and reading reports.
- [x] Add settings for ayanamsha, node type, chart style, timezone, and panchanga place defaults.
- [ ] Add language and deeper regional defaults.

## 4. Trust And Validation

- [ ] Add calculation provenance to each tab.
- [ ] Mark verified vs convention-dependent rules in the UI.
- [ ] Build golden-chart test suite with trusted reference charts.
- [ ] Add regression tests for timezone-sensitive, DST-sensitive, and edge-case births.
- [ ] Add source/convention notes for every major calculation family.
- [ ] Replace pending Yoga/Dosha source placeholders with exact chapter/verse/page references.
- [ ] Validate convention-dependent rules with preferred tradition before stronger UI language.
- [ ] Add audited full 14x14 Yoni matrix and Vashya table from preferred source.
- [ ] Add classical graha drishti layer and expose natal aspect/drishti table.
- [ ] Rework Shadbala v1 into virupa-based classical Shadbala or keep it clearly excluded from interpretive weighting.
- [ ] Add Vedha and Ashtakavarga weighting into Gocharam severity.
- [ ] Add externally verified Gun Milan reference cases.

## 5. UX Polish

- [ ] Keep hero banners data-backed on every major tab.
- [ ] Improve dense table mobile handling.
- [ ] Add user-controlled default panchanga place.
- [ ] Add chart style defaults per user.
- [ ] Add report-friendly print layouts.

## Implementation Progress

- [x] Hero banners added across major tabs.
- [x] Panchanga uses viewer timezone and supports place selection.
- [x] Ashtakavarga includes raw BAV/SAV, Shodhana, Prastara, and Shodhya Pinda.
- [x] Dashas include drilldown and natal/transit chart context.
- [x] Backend compatibility engine.
- [x] UI compatibility consumes backend engine.
- [x] Yogas & Doshas tab added.
- [x] Transit engine and Transits tab added with gochara, aspects, and 7/30 day timeline.
- [x] Calendar Intelligence tab added with panchanga, active dasha, and transit feed.
- [x] Calendar shows saved AI readings on generated dates with version, deviation, and validation status.
- [x] Readings validation uses explicit statuses and period-level accuracy summary.
- [x] Readings generate individual prediction claims with target windows, category, confidence, and claim-level validation.
- [x] Supabase/Postgres schema added for kundlis, readings, and prediction claims.
- [x] Dashboard intelligence added across profiles.
- [x] Settings defaults wired into Vedic calculations, chart style, timezone, and panchanga place.
- [x] Shadbala v1 added to backend and Vedic tab with six components, ranking, and approximation markers.
- [x] Planetary conditions added: combustion, Baladi avastha, retrograde modifiers, planetary war, and adjusted Shadbala scores.
- [x] Vedic rules KB added at `astrospace/knowledge/vedic_rules/` and reflected in Yogas & Doshas UI.
- [x] Chart condition symbols added for exaltation, debilitation, retrograde, combustion, and Vargottama.
- [x] Ashtakavarga SAV/BAV/Shodhana now displayed as South Indian sign-grid number charts.
- [x] External audit received and first concrete correctness pass applied to Gun Milan scoring.
- [x] Audit follow-up: Pancha Mahapurusha yogas added; Raja/Dhana yoga association expanded beyond conjunction/opposition.

## External Validation Needed From User

- [ ] Preferred textual authority order: BPHS only, or BPHS + Phaladeepika + Saravali cross-check.
- [ ] Preferred editions/translations for BPHS, Phaladeepika, and Saravali.
- [ ] Exact chapter/verse/page references for:
  - Gaja Kesari Yoga
  - Chandra-Mangal Yoga
  - Budhaditya Yoga
  - Kemadruma Yoga and cancellation rules
  - Neecha Bhanga Raja Yoga cancellation rules
  - Raja Yoga / Kendra-Trikona lord association
  - Dhana Yoga combinations
  - Vipareeta Raja Yoga
  - Manglik / Kuja Dosha and exception rules
- [ ] Decision on convention-heavy rules:
  - Kala Sarpa Dosha / flag
  - Pitru Dosha
  - Sarpa Dosha
  - Nadi Dosha outside compatibility
- [ ] At least 3 externally verified reference charts with expected:
  - Lagna
  - Moon rashi, nakshatra, pada
  - D1/D9 placements
  - active/inactive yogas
  - active/inactive doshas
  - dasha balance at birth
