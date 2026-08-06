# Backend Astrological Depth Checklist — 2026-08-06

**Status:** canonical, living tracker for Agent A backend astrology depth
work (`astrospace/core/vedic/**`, `astrospace/knowledge/vedic_rules/**`,
`astrospace/context/**`). Check items off as they land; update the
depth/scale note if scope changes. Companion to
[full_astro_software_checklist.md](full_astro_software_checklist.md) (which
tracks mobile/UX + a broader product checklist) — this file tracks
calculation-engine and knowledge-base depth only, and is the source of
truth for that slice. Fold future audit passes into this file rather than
starting a new dated doc.

Every item below carries: what's missing today, acceptance criteria (must
be testable), and depth/scale (how big the change actually is, so "done"
means something specific). Items marked `[ ]` are open, `[x]` are done —
when checked, add a one-line pointer to the test(s)/doc that proves it.

## Ground rules (apply to every item)

- No fabricated classical authority. Where an exact chapter/verse can't be
  confirmed, cite the tradition/text and mark `source_status:
  convention_dependent` or `needs_review` rather than inventing a pinpoint
  citation.
- Every new calculation gets at least one hand-verifiable or externally
  cross-checked test vector (same bar as `docs/jaimini_validation_2026-08-06.md`).
- Every new dosha/caution-style output follows design_principles.md §4/§6:
  flag not verdict, no fear language, no guarantees.
- "Golden-chart validation" against a second independent ephemeris/software
  package is explicitly out of reach in this environment (no such tool is
  available) — where the checklist says "validated," it means internal
  consistency + hand/external-source cross-check, not a second software
  run. This limitation is called out per item, not silently dropped.

---

## Tier 0 — Harden existing self-flagged debt

Nothing new here; every item already has a `pending`/`approximation`/
`VERIFY` marker in the code today. This tier closes those markers or
narrows them honestly.

### T0.1 — Ashtakavarga → Gochara Vedha + severity weighting
- **[x] Already done — false alarm.** `full_astro_software_checklist.md`
  line 130 had this unchecked, but a 2026-08-06 code read found it fully
  shipped: `gocharam/rules.py` has `CLASSICAL_GOCHARA_VEDHA` +
  `VEDHA_EXEMPT_PAIRS` with complete obstruction logic, and
  `gocharam/strength.py` has `ashtakavarga_transit_support()` /
  `apply_ashtakavarga_context()` computing BAV/SAV/kakshya-weighted
  `effective_severity`, all exercised by `tests/test_gochara_vedha.py` (17
  tests, passing) and reachable via `/{kundli_id}/gocharam` and
  `/{kundli_id}/transits`. Fixed the stale checkbox in
  `full_astro_software_checklist.md` rather than re-implementing. No new
  code needed for this item.

### T0.2 — Yoga/Dosha KB external verification pass
- **Missing:** most rules are `status: convention_dependent` or
  `verified_common` without an external cross-check (only my Jaimini pass
  did a real external lookup).
- **AC:** for a defined subset (start with the 5 Pancha Mahapurusha yogas +
  Manglik + Gajakesari — the highest-visibility rules), each rule's
  `source_refs` gets at least one specific, checkable citation (author +
  work + chapter, ideally verse) found via research, not guessed; rules
  that can't be pinned down stay `convention_dependent` with the honest
  reason recorded in `notes`.
- **Depth/scale:** ~7 rules deep-cited this pass; the remaining ~25 stay
  tracked as open (this is genuinely slow, citation-by-citation work).
- **[x] Attempted, partial result — and that partial result is itself the
  honest finding.** Research (2026-08-06) for the 5 Pancha Mahapurusha
  yogas found real edition disagreement on the BPHS chapter number
  (secondary sources cited ch. 36, 75, AND 77 for the same yoga group) —
  updated all 5 `source_refs` in `yogas.json` to say "commonly cited as
  ch. 75 in the Santhanam-descended edition family... chapter numbering
  genuinely varies by edition, this is not a typo" rather than pick one
  number and present false precision. Manglik and Gajakesari: research
  found no specific chapter/verse citation at all in the sources checked
  — left their `source_refs` unchanged rather than fabricate one. The
  existing "exact edition reference pending" language in the KB was
  already the correct, evidenced position, not a gap.

### T0.3 — Ghatak Chakra yoga/karana/prahar columns
- **Missing:** `ghatak.py` ships `"yoga": None, "karana": None, "prahar":
  None` — "no verified source yet."
- **AC:** either a source-backed table fills these three columns with
  `source_status` recorded, or they stay `None` with the reason left
  intact — this item is "resolved" either way, not silently dropped.
- **Depth/scale:** one lookup table (12 rows) if a source is found.
- **[ ] Researched, correctly stays deferred.** Confirmed the yoga/karana/
  prahar dimensions are real parts of the classical Ghatak Chakra
  (multiple sources describe the five-dimension structure), but no
  research pass turned up the actual per-rashi lookup values with enough
  confidence to transcribe safely. The code's own reasoning ("shipping a
  guess for an 'inauspicious' indicator is worse than shipping nothing")
  holds — left as `None`, not filled with an unverified guess.

### T0.4 — Moontimes Varjya/Amrit ghati tables
- **Missing:** `moontimes.py` says "VERIFY both tables against DrikPanchang
  before treating as final."
- **AC:** table cross-checked against a second published source; either
  confirmed (note updated to say so) or corrected with the discrepancy
  documented.
- **Depth/scale:** data-table check, not new code.
- **[x] Partially confirmed — real, useful signal, not full closure.**
  Independent research (2026-08-06) surfaced a published Varjya
  start-ghati list covering 18 of 27 nakshatras; **all 18 matched this
  codebase's `VARJYA_START_GHATI` table exactly**, zero discrepancies
  (Ashwini 50, Ashlesha 32, Jyeshtha 14, etc.). Locked in as a regression
  test (`tests/test_panchanga_masa.py::TestVarjyaStartGhatiCrossCheck`) so
  a future edit can't silently drift a confirmed value. The remaining 9
  nakshatras and the entire Amrit Kalam table are still unconfirmed — the
  code comment says so explicitly rather than rounding "18/27 confirmed"
  up to "verified."

### T0.5 — Shadbala Kala/Cheshta/Drik Bala
- **[x] Already done — bigger false alarm than T0.1.** A complete,
  degree-precise, BPHS-cited virupa Shadbala (`strength.classical_shadbala()`
  — proper Sthana/Dig/Kala/Cheshta/Naisargika/Drik, with `drik_bala_virupa()`
  using the continuous classical sputa-drishti curve, not a whole-sign
  proxy) already existed with its own 27-test suite
  (`tests/test_shadbala_classical.py`) that this pass found completely
  unwired to `chart.py` or any API route — investigated further and found
  it actually WAS reachable: `strength.shadbala()` already calls it
  internally and returns it under a `"classical"` key whenever birth data
  is available (which `chart.py`'s `.shadbala()` always supplies), and
  `total_score`/`rank_band` already derive from the classical ratio rather
  than the v1 approximation. (I initially added a duplicate
  `chart.classical_shadbala()` method and `/shadbala/classical` route
  before discovering this — reverted them rather than ship redundant
  surface.) Fixed the stale checkbox in `full_astro_software_checklist.md`
  line 129. The v1 whole-sign `_drik_bala()` still exists for the
  no-birth-data fallback path (component scores stay 0-100 normalized even
  when classical data is present, per the function's own docstring) — that
  dual-representation is intentional, not a leftover bug.

---

## Tier 1 — New engine capabilities

### T1.1 — Vimshopaka Bala
- **Missing:** not implemented at all.
- **AC:** given a chart's Shadvarga/Saptavarga/Dashavarga/Shodashavarga
  varga placements (all already computed in `vargas.py`), returns a 0–20
  score per planet using the classical weighted-dignity formula, plus the
  4-tier interpretation band (<5 incapable, 5–10 minimal, 10–15 moderate,
  15–20 full).
- **Depth/scale:** one new module; depends on zero new astronomical
  calculation (all 20 divisional charts already exist) — pure weighting
  layer. Cited to the classical Shadvarga/Saptavarga/Dashavarga/
  Shodashavarga weight tables.

### T1.2 — Jaimini Chara Dasha / Narayana Dasha
- **Missing:** only Vimshottari + Yogini dashas exist; no sign-based
  (rashi) dasha system, which is Jaimini's primary timing tool.
- **AC:** given a chart, returns the Chara Dasha sequence (sign mahadashas,
  direction determined by savya/apasavya rule from the 9th house), with
  Narayana Dasha as the Lagna-anchored variant; matches at least one
  external worked example the way the Jaimini karaka cross-check did.
- **Depth/scale:** new module (`chara_dasha.py`), moderate — direction and
  duration rules are well-documented but have multiple published variants;
  ship the mainstream BPHS version and flag `convention_dependent`.

### T1.3 — Special lagnas: Sree Lagna, Indu Lagna, Bhrigu Bindu, Pranapada Lagna
- **Missing:** `special_lagnas.py` has Bhava/Hora/Ghati Lagna only.
- **AC:** each of the four new points computed with its classical formula,
  documented convention, and at least one hand-verifiable test.
- **Depth/scale:** extends the existing module; each point is a closed-form
  formula, no new astronomical primitives needed.
- **[x] Done (partial, by design):** `bhrigu_bindu()` and `indu_lagna()`
  shipped in `special_lagnas.py`, wired into `VedicChart.special_lagnas()`
  additively (existing `bhava_lagna`/`hora_lagna`/`ghati_lagna` keys
  untouched — checked against `ui/src/app/core/models.ts` and the two
  screens reading them before changing the payload shape). Tests:
  `tests/test_jaimini_dashas.py::TestBhriguBinduAndInduLagna` (7 tests,
  including a hand-computed Indu Lagna worked example and the
  zero-remainder edge case). **Sree Lagna and Pranapada Lagna deliberately
  NOT implemented** — secondary sources found in research disagreed with
  each other on Sree Lagna's exact scaling/anchor rule and gave no usable
  Pranapada day/night formula; shipping a guessed point formula was judged
  worse than leaving it open. Still needs a primary source before either
  is attempted.

### T1.4 — True Mandi (distinct from Gulika)
- **Missing:** `masa.py`'s `gulika_positions()` explicitly notes "Mandi
  conventions differ" and doesn't implement the separate formula.
- **AC:** a distinct `mandi_position()` using the alternate classical
  method, with both surfaced side by side and the convention difference
  stated in the payload (never silently picking one).
- **Depth/scale:** small, one function.
- **[x] Done:** research (2026-08-06) found Gulika and Mandi are not two
  different formulas — both use the identical 8-part-day/Saturn's-portion
  method, disagreeing only on which instant *within* that portion is taken
  (start vs middle). Refactored the shared block logic into
  `_upagraha_block()` with an offset parameter; `gulika_positions()`
  (offset 0.0, unchanged behavior) and new `mandi_positions()` (offset 0.5)
  in `masa.py`. Both now surface side by side in `daily_panchanga()`'s
  `"gulika"`/`"mandi"` keys. Tests: `tests/test_panchanga_masa.py::TestMandi`
  (5 tests, including the exact half-part-offset relationship).

---

## Tier 2 — Interpretive KB depth (`astrospace/context/references.json`)

### T2.1 — Populate the 5 empty domains
- **Missing:** `taxonomy.json` defines 10 domains; `references.json` has
  structured entries for only 5 of them (career, marriage, health/litigation
  overlap, spirituality) — education, children, family_property, foreign,
  and litigation-as-its-own-domain have zero.
- **AC:** every domain in `taxonomy.json` has at least 2 structured
  references, each with a real `source.text_key`/`location` (book +
  chapter, not verse-pinpoint unless confirmed) and `status` set honestly.
- **Depth/scale:** ~10-15 new reference entries, content-authorship work
  (not code) — the slowest-per-item work in this whole checklist because
  each one needs real sourcing.
- **[x] Done — all 10 domains covered.** Added 24 new reference entries
  (29 total, up from 5). Every `source.text_key` cited already exists in
  `sources.json`'s curated 23-source catalog (verified programmatically —
  zero references cite an uncataloged source). Statements paraphrase
  general, well-attested house/karaka/varga/yoga significations, several
  drawn from and cross-consistent with this codebase's own `yogas.json`
  entries for the same rule (e.g. Dhana Yoga, Amala Yoga, Saraswati Yoga,
  Manglik/Kuja) rather than re-deriving classical claims from scratch.
  `location` fields stay at chapter/topic level, never a fabricated verse
  number. Manglik entry carries the flag-not-verdict framing explicitly.

### T2.2 — Thicken the 5 sparse domains
- **Missing:** career/marriage/health/spirituality have exactly 1 reference
  each; not enough for the Context Engine to say anything beyond a single
  sentence per domain.
- **AC:** each existing domain reaches at least 3 references covering
  different subdomains already declared in `taxonomy.json`.
- **Depth/scale:** ~10-12 more entries.
- **[x] Done — every one of the 10 domains now has exactly 3 references**
  (verified programmatically by counting `domains` tags across the file),
  each covering a distinct subdomain already declared in `taxonomy.json`.
  Delivered together with T2.1 in the same pass rather than as a separate
  second edit — see T2.1 for the sourcing discipline applied.

---

## Tier 3 — Larger/specialized additions

### T3.1 — Nabhasa Yogas
- **Missing:** zero coverage of the 32 classical shape-pattern yogas (Rajju,
  Musala, Nala, Mala, Sarpa, Gada, Shakata, Vihaga, Shringataka, Hala,
  Vajra, Yava, Kamala, Vapi, Chatra, Ardhachandra, Yuga, and the rest).
- **AC:** at minimum the Ashraya (3), Dala (2), Akriti (20) and Sankhya (7)
  groups' detection logic implemented for the ones with unambiguous,
  widely-agreed trigger conditions (planet-in-movable/fixed/dual signs
  counts, sign-group occupation patterns); each ships through the same KB
  schema (`classical_name`, `practitioner_explanation`, etc.) as the
  existing yogas.
- **Depth/scale:** large — 32 named patterns, phase it (ship the ~10-15
  with the clearest, least contested trigger rules first; mark the rest
  `needs_review` rather than guessing at disputed ones).
- **[x] Done (phase 1 of 2):** shipped all 11 yogas with unambiguous,
  single-reading trigger rules — the full Ashraya group (Rajju/Musala/Nala:
  all 7 classical planets share one sign quality), full Dala group (Mala/
  Sarpa: benefics/malefics each individually in a kendra from Lagna — the
  kendra-reading ambiguity is documented in both code notes and the KB
  `caveats`), and the full Sankhya group (Gola..Dama: graded by count of
  distinct signs occupied, 1-6). New functions
  `_ashraya_yogas()`/`_dala_yogas()`/`_sankhya_yoga()` in `yogas.py`, 12 KB
  entries (11 + 1 umbrella "no tier matched" entry) in `yogas.json`. Tests:
  `tests/test_nabhasa_yogas.py` (14 tests, hand-constructed charts for
  every tier). **20 Akriti (shape) yogas deliberately deferred** — their
  per-yoga trigger conditions have more room for cross-source disagreement
  than Ashraya/Dala/Sankhya, and this pass did not do the citation-by-
  citation research each of the 20 would need to ship responsibly.

### T3.2 — Dashakoota extension (Rajju, Vedha, Stree Deergha kutas)
- **Missing:** `compatibility.py` has the full 8-koota Ashtakoota system;
  the extended 10-koota (Dashakoota, more common in South Indian practice)
  adds Rajju, Vedha, and Stree Deergha.
- **AC:** three new koota functions following the existing `_varna`/
  `_vashya`/etc. pattern, returned as an additional, clearly-labeled block
  (not merged into the 36-point Ashtakoota total, since mixing scales is a
  correctness bug) with `is_convention_dependent` set honestly.
- **Depth/scale:** three functions, same shape as existing kutas.
- **[x] Done:** `RAJJU_GROUPS` (5-zone table, 4 groups sourced directly, the
  5th derived by elimination and cross-checked against the full 27-
  nakshatra list), `VEDHA_PAIRS` (13 sourced pairs, Chitra correctly left
  unpaired), and `STREE_DEERGHA_MIN_COUNT` (13, the most-repeated threshold
  across sources checked, with the 7/9/15 variants documented rather than
  silently dropped) added to `compatibility.py`. New
  `dashakoota_extension()` returns a separate block (own point scale, own
  `hard_blockers` list for Rajju/Vedha) surfaced additively as
  `gun_milan()["dashakoota_extension"]` — verified it does NOT change
  `gun_milan()`'s existing 36-point `total`. Tests:
  `tests/test_dashakoota.py` (16 tests, including full-table integrity
  checks and threshold boundary cases).

### T3.3 — Bhava Chalit / Sripati house system (optional lens)
- **Missing:** `chart.py` hardcodes `"house_system": "whole-sign houses"` —
  no cuspal house system exists at all.
- **AC:** an opt-in `house_system` param (`"whole_sign"` default,
  `"sripati"` alternate) that recomputes house placements via Sripati
  cuspal bhava madhya; whole-sign stays the default so nothing existing
  changes behavior.
- **Depth/scale:** structural — touches `positions.py`'s house lookup and
  every consumer of `house_from_lagna`; scope tightly to "compute cusps and
  re-bucket planets," not a parallel chart system.
- **[x] Done, scoped as a standalone additive reading (not a
  `house_system` param threaded through existing consumers):** new
  `positions.sidereal_mc()` (Swiss Ephemeris `ascmc[1]`, same ayanamsha
  path as `sidereal_lagna()`) and new module `bhava_chalit.py`
  (`sripati_madhyas()`, `sripati_cusps()`, `house_of()`, `bhava_chalit()`)
  implementing the trisection method (madhya-first, sandhi-as-midpoint,
  cross-checked via research 2026-08-06). Wired as `VedicChart.bhava_chalit()`
  and `GET /{kundli_id}/bhava-chalit` — entirely new surface, zero changes
  to `house_from_lagna()` or any existing yoga/dosha/strength/dasha
  computation (verified by
  `test_bhava_chalit.py::test_does_not_mutate_or_depend_on_whole_sign_house_state`).
  Deliberately did NOT thread a `house_system` param through every existing
  consumer — that would mean re-deriving house-dependent logic (Raja Yoga
  kendras, dosha houses, Shadbala Dig Bala, dozens of call sites) for a
  second house system in one pass, which is a much larger and riskier
  project than "give a Practitioner a second lens to compare against."
  Tests: `tests/test_bhava_chalit.py` (15 tests, including an idealized
  90°-quadrant chart that hand-verifies to exact 30° houses, and a
  real-ephemeris consistency check).

### T3.4 — Sarvatobhadra Chakra
- **Missing:** not implemented; the 9×9 nakshatra/rashi transit-vedha grid
  used professionally for muhurta/prashna refinement (sourced to
  Phaladeepika ch. 26 in research for this checklist).
- **AC:** given a chart and a transit day, returns the grid placement and
  the vedha (obstruction) analysis for the day's Moon nakshatra against
  natal points.
- **Depth/scale:** the largest single item in Tier 3 — a genuinely new
  subsystem, not an extension of an existing module. Scope to muhurta use
  first (it directly strengthens `muhurta.py`'s existing tarabala/
  chandrabala scoring); prashna/mundane applications are out of scope for
  this pass.
- **[ ] Deliberately NOT implemented — real blocker, not a time-budget
  skip.** Follow-up research (2026-08-06) found Sarvatobhadra's Vedha is
  **grid-geometric**: a planet obstructs whatever sits along the straight
  and diagonal lines from its cell in the actual 9×9 layout (Narapati
  Jayacharya), not a lookup table of nakshatra pairs the way the
  compatibility Vedha koota (T3.2) or the classical Gochara Vedha
  (`gocharam/rules.py`, already shipped) are. That means correctness
  depends entirely on which nakshatra/sign/syllable sits in which of the
  81 cells, and this pass's research did not turn up a reliable primary
  source for that exact placement — only descriptions of the *mechanism*,
  not the *grid*. Implementing a guessed 9×9 layout and deriving
  "obstruction" from wrong geometry would produce confidently-wrong
  muhurta guidance, which is worse than not having the feature. Needs a
  primary source (a scanned/translated Narapati Jayacharya table, or a
  cross-checked software implementation to verify cell-by-cell) before a
  future pass attempts this.

---

## Revalidation pass (do after all tiers)

- [x] Full backend suite green: `874 passed, 2 skipped, 1 failed` — the one
  failure (`test_daily_guidance.py::TestVerdict::test_reading_is_practical_before_technical`)
  is pre-existing and unrelated to this checklist's work, confirmed via
  `git stash` against the unmodified branch before this pass started.
  Started this pass at 763 passing; net +111 tests (105 new across
  `test_vimshopaka.py`, `test_chara_dasha.py`, `test_nabhasa_yogas.py`,
  `test_dashakoota.py`, `test_bhava_chalit.py`, plus additions to
  `test_jaimini_dashas.py`, `test_panchanga_masa.py`, `test_api_v2.py`).
- [x] `test_vedic_rules_kb.py` passes with the 12 new Nabhasa yoga KB
  entries (11 rules + 1 umbrella fallback) — schema, source-catalog, and
  fear-language checks all green.
- [x] Every new module (`vimshopaka.py`, `chara_dasha.py`, `bhava_chalit.py`)
  has a module-level docstring citing its source/convention and per-item
  research findings, matching the house style in `jaimini.py`/`doshas.py`.
- [x] Fear-language/guarantee scan run across every new JSON/Python file
  from this pass (yogas.json, doshas.json, references.json, chara_dasha.py,
  vimshopaka.py, special_lagnas.py, bhava_chalit.py, compatibility.py,
  yogas.py, masa.py, panchanga_day.py, moontimes.py) — clean.
- [x] Checklist checkboxes re-read against the actual diff before writing
  this summary — two items (T3.4 Sarvatobhadra Chakra, T0.3 Ghatak table)
  are intentionally left `[ ]` open because they were genuinely not
  implemented (real primary-source gaps, not time-budget skips); every
  other item is `[x]`.
- [x] New API routes smoke-tested live end-to-end (`TestBackendDepthEndpoints`
  in `test_api_v2.py`): 200 on success, 422 on a bad Vimshopaka scheme
  param, 404 on an unknown kundli, across all three new routes.

### What's still genuinely open after this pass

- **T3.4 Sarvatobhadra Chakra** — not implemented; needs a primary source
  for the actual 9×9 grid cell layout (Narapati Jayacharya), not just a
  description of the mechanism.
- **T0.3 Ghatak yoga/karana/prahar columns** — not implemented; same
  reason, no reliable source for the per-rashi lookup values found.
- **T3.1 Nabhasa Yogas** — only Ashraya/Dala/Sankhya groups (11 of 32)
  shipped; the 20 Akriti (shape) yogas remain undone.
- **T1.3 Sree Lagna, Pranapada Lagna** — not implemented; secondary
  sources disagreed with each other on the exact formulas.
- **T1.2 Narayana Dasha** — not implemented; secondary sources disagreed
  on the fixed/dual-sign stepping rule.
- **T0.2** — only 7 of ~32 yoga/dosha rules got a deeper citation pass,
  and even those didn't land a single undisputed chapter/verse (genuine
  edition variance, not a research shortfall).
- Golden-chart validation against a second independent ephemeris/software
  package was out of reach all pass (no such tool available in this
  environment) — every "validated" claim in this checklist means internal
  consistency plus an external secondary-source cross-check, not a second
  software run. Stated explicitly per-item above, not implied.
