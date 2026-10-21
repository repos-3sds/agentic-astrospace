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

---

## Deferred backlog — CE enrichment & BPHS validation pass (2026-08-10)

**Status:** open backlog. Appended here rather than as a new dated file,
per this doc's own "fold future audit passes into this file" rule.

Scope note: this file's header scopes it to `core/vedic/**`,
`knowledge/vedic_rules/**` and `context/**`. The Ask/agent-layer items in
§C below sit outside that, and are recorded here anyway so there is **one**
backlog to check rather than three. Cross-referenced from
[context_engine_taxonomy.md](context_engine_taxonomy.md)'s ground-truth
section.

Nothing below is a time-budget skip. Each item is either (a) blocked on a
verified source, or (b) a scoping decision made deliberately at the time.
Every entry carries **why not**, **what unblocks it**, and **where the hook
is** — so picking one up later doesn't mean re-deriving the research.

**Shipped this pass, for context:** `dignity_reasoning`, `dhatu`/`rasa`,
full 8-role Jaimini karaka array, D-60 sign, Vimshopaka precision scores,
Shayanadi Avastha (`shayanadi.py`), Argala/Argala-Bhanga (`argala.py`),
D-60 deity database (`shashtyamsha.py`), naisargika planetary varna
(`PLANET_VARNA`), Abhijit intercalary nakshatra (`abhijit.py`), and base-
prompt rule 4a covering `convention_dependent` fields + Argala outcomes.

### A. Blocked on a verified source

- [ ] **Kalapurusha sign-to-body-part mapping** — zero references anywhere
  in `core/vedic/`. Relevant to Health's "disease location by body part"
  subdomain, currently unsupported. *Unblocks on:* a source giving the
  full 12-sign→body-part table. *Hook:* pinned as the last remaining
  `xfail` in `tests/test_bphs_ground_truth.py::TestConfirmedGapsNotYetBuilt`
  — closing it makes noise (unexpected pass) rather than staying silent.
- [ ] **Abhijit muhurta goal-preference scoring** — `abhijit.py` ships the
  verified arc, but nothing scores it. No source found gives a checkable
  mapping of which undertakings Abhijit favours, and `muhurta.py`'s `GOALS`
  table will not be seeded with a guess (same bar applied to the D-60 deity
  list before it shipped). *Unblocks on:* a source mapping Abhijit to
  specific muhurta goals. *Hook:* `GOALS[...]["prefer_nakshatra"]`.
- [ ] **T0.2 / edition-variance citations** — carried forward from the
  pass above; still only 7 of ~32 yoga/dosha rules have a deeper citation,
  none landing an undisputed chapter/verse.
- [ ] **Nakshatra shakti (the 27 "powers")** — deliberately excluded when
  the nakshatra deity/symbol tables were built. The system is genuine
  (Taittiriya Brahmana I.5.1 with Bhattabhaskara Mishra's commentary), but
  the familiar English "the power to…" renderings are one modern author's
  translation, and a 27-row table of his phrasings would be reproducing his
  work rather than stating a traditional fact — the same line that kept
  interpretive trait-prose out of `NAKSHATRA_DEITY`. *Unblocks on:* the
  Sanskrit shakti terms from the primary text (which are the actual
  traditional data), glossed in our own words. *Hook:*
  `constants.NAKSHATRA_DEITY` / `nakshatra.nakshatra_traits()`.

### B. Real, corroborated, simply not built yet

- [ ] **Ashtottari and Shastihayani dashas** — the only two dasha systems
  that actually consume Abhijit; neither exists here. This is the missing
  consumer that would give `abhijit.py` live value beyond description.
  *Hook:* `abhijit.py` is what either should read from.
- [x] **Karakamsha** — **CLOSED 2026-09-01**. `jaimini.karakamsha()`:
  Atmakaraka's D9 sign, who occupies it, and who occupies the 5th sign
  from it, wired into `VedicChart.jaimini()` and exposed domain-
  independently in the CE bundle (`bundle["karakamsha"]`, same reasoning
  as `jaimini_karaka_array`). Motivated by a real question — "how would
  the model predict a reader's inclination toward astrology without being
  asked" — which turned up two grounded BPHS rules, cross-verified in both
  Santhanam's and Sharma's independent translations: "Effects of
  Karakamsha" (ch.33/35, shlokas 41-45 — Ketu or Rahu there names an
  astrologer) and Matsya Yoga (ch.36/37 — a separate combination with the
  same outcome, flagged `convention_dependent` for a genuine manuscript
  disagreement). Both now in `references.json` under
  career/`field_selection`. Also caught while fixing this: a real
  pre-existing extraction gap — Phaladeepika's Mercury-navamsa sloka names
  "a knowledge of astrology" explicitly, which the already-landed
  `phal5_navamsa_tenth_lord_livelihood` reference had summarized away;
  corrected in place. **Follow-up closed same session:** `spirituality` is
  now registered in `AGENT_REGISTRY` (own addendum in `registry.py`,
  non-directive framing around renunciation/gurus/past-life claims) and the
  Karakamsha reference now carries `spirituality`/`spiritual_inclination`
  alongside `career`/`field_selection`. Matsya Yoga stayed career-only —
  it names a specific profession, not a general inclination.
- [ ] **Argala "contested" tiebreak** — `argala.py` reports `contested`
  when the argala and obstruction houses hold equal planet counts, and
  deliberately does not pick a winner. Sources say to compare relative
  strength, which needs Shadbala; that comparison was out of scope.
  *Unblocks on:* a decision on which Shadbala measure to compare.
  *Hook:* `argala._leg_outcome()`.
- [x] **All 11 taxonomy domains registered — CLOSED 2026-09-04.**
  `education`, `family_property`, and `litigation` (the last 3) now have
  real addenda in `agents/registry.py` and real KB grounding, primarily
  from Uttara Kalamritam's Kanda I Ch. V significations chapter (a single
  chapter covering all three domains, plus BPHS's own 9th-house-father
  chapter). See docs/career_kb_education_family_litigation_domains.md.
- [ ] **Several domains' `source_refs` name books absent from this corpus.**
  Surfaced while closing the item above, and checked all the way through
  for `prasna_marga`: `kn_rao_mercury_education`, `pm_disease_sixth`,
  `prasna_marga_5th_affliction` (all three removed), and
  `prasna_marga_3rd_short_travel` (retargeted to a real Uttara Kalamritam
  citation, `uk_3rd_short_travel`) all cited K.N. Rao's *Planets and
  Education* or *Prasna Marga* — neither book exists anywhere in the KB
  corpus, confirmed by `scripts/audit_kb_sources.py` and a direct filename
  sweep. Every `prasna_marga`-cited reference is now fixed; `raman_htjh`
  and `kn_rao_career` have not been swept the same way yet. `career`,
  `wealth`, `marriage`, and `health` still name `raman_htjh` (Raman's *How
  to Judge a Horoscope*) in their own `taxonomy.json` `source_refs`, and
  `career`/`wealth` also name `kn_rao_career` — neither book is in the
  corpus either. Not every mention has necessarily produced a bad reference
  yet, but each is a latent one. *Hook:* audit every `references.json`
  entry whose `source.text_key` is `raman_htjh` or `kn_rao_career` against
  `scripts/audit_kb_sources.py`'s real output, then correct
  `taxonomy.json`'s `source_refs` for those 5 domains the same way this
  pass corrected `education`'s and `litigation`'s.
- [ ] **Migrate off kerykeion 5.x to 6.x's factory API — deliberately not
  done as part of pinning it, 2026-09-16.** `requirements.txt` had
  `kerykeion>=4.0.0` (no upper bound); kerykeion 6.0 removed
  `AstrologicalSubject`/`NatalAspects` outright in favor of
  `AstrologicalSubjectFactory.from_birth_data(...)`, which broke CI and any
  fresh Docker build the instant it published to PyPI — pinned to `==5.12.9`
  (the verified-good version) to stop that, see the commit pinning it for
  the full incident. The pin is a stopgap, not the fix: v6 also changes
  actual computed results, not just the API surface — default active points
  drop from 18 to 14 (Descendant, Imum Coeli, True South Lunar Node, Mean
  Lilith no longer active unless requested), aspect orbs narrow
  (conjunction/opposition 10°→6°, quintile dropped), transits/returns/
  progressions move to a flat 3° orb, and the default chart style changes
  from 'classic' to 'modern'. Any of those could silently shift dasha/
  aspect/strength output this app has spent many sessions verifying against
  BPHS/Santhanam/Sharma — migrating needs each default reviewed against
  this app's own verified fixtures before adopting, not a version bump.
  *Unblocks on:* deciding, per changed default, whether to adopt v6's new
  default or explicitly pin the old v5 behavior via kerykeion's
  `V5_DEFAULT_ACTIVE_POINTS` (kerykeion's own migration guide names this
  escape hatch) — not a decision to make inside a routine dependency bump.
  *Hook:* `astrospace/core/chart.py`, `astrospace/core/transits.py` (both
  `from kerykeion import AstrologicalSubject`), `astrospace/agents/
  compatibility_agent.py` (`SynastryAspects`, unaffected by the v6 removal
  but built on the same v5-era API surface).

- [ ] **Middle planets of a crowded house are small tap targets (UI)**
  — added 2026-10-15 with the flow-audit tap-target fix. Lone planets and
  the first and last planet of a stack now get 44 px targets in every chart
  style, and each target stays centred on its own label. A planet in the
  middle of a stack of three or more keeps the label spacing, about 45 x 11
  px on a phone, because a taller target there would reach its neighbour's
  label. *Unblocks on:* choosing between spacing stacked labels further
  apart (changes how crowded houses look) or a tap on a crowded house
  opening a small list of its planets. *Hook:* `hitRow()` in
  `ui/src/app/shared/kundli-chart/kundli-chart.component.ts`.

- [ ] **Recorded audio for the remedy mantras** (2026-10-17). The plan
  (`core/vedic/remedy_plan.py`) ships every text, but `audio_url` is null.
  *Why not:* needs original recordings; Vedic verses need a svara-trained
  reciter, not TTS, and label/YouTube audio is copyrighted. *Unblocks on:*
  commissioned recordings. *Hook:* `_practice()["audio"]`; the corpus
  `audio.est_seconds_per_repetition` gives loop lengths.
- [ ] **Full text of the long recitations** (Aditya Hridayam, Hanuman
  Chalisa, Vishnu Sahasranama, Sri Rudram, Durga Saptashati) (2026-10-17).
  *Why not:* the plan counts a short verse and names the long text as the
  "fuller practice"; long texts need proofreading against a licensed
  edition. *Unblocks on:* a proofread text per book. *Hook:* entries with
  `text_in_corpus: false` in `core/vedic/mantra_corpus/mantras.json`,
  `_SHORT_FORM` in `remedy_plan.py`.
- [ ] **Long-vow mode for mantra counts** (2026-10-17). BPHS ch.84 gives
  totals (Sun 7,000 … Saturn 23,000) meant to be spread over weeks; the
  tracker only counts one 108 sitting. *Unblocks on:* a product call that
  it is wanted. *Hook:* `traditional_count` in the corpus, the tracker's
  localStorage record.

### C. Ask/agent layer — one live safety gap, highest priority here

- [x] **`safety.py` third-party death output net** — **CLOSED 2026-08-10**
  (validation-loop branch). `_PROHIBITED_OUTPUT`'s death cluster was
  anchored entirely to "you", so third-party phrasing passed straight
  through. Re-measured on shipped code before fixing: 10 of 12 probes
  missed, against `'you will die young'` and `'your lifespan is short'`
  being caught.

  Fixed by extending the existing detect-and-regenerate path — no new
  mechanism — with a shared `_THIRD_PARTY_SUBJECTS`/`_THIRD_PARTY_REF`
  vocabulary covering relatives and bare pronouns, applied to the death
  verbs, the lifespan nouns, the survival negations, the "will live
  to/until" duration form, and the windowed years-remaining check (which
  still clears "your father has 3 years remaining in his Saturn dasha",
  the third-party form of a sentence that was always legitimate). 18/18
  prohibited phrasings now caught, 0 false positives on the ordinary set;
  both directions pinned in
  `tests/test_refer_out_boundary.py::test_third_party_longevity_verdicts_are_caught`
  and `::test_ordinary_third_party_sentences_pass_the_output_net`.

  Two deliberate scope limits, so the next reviewer doesn't re-litigate
  them: the subject list is **people only** (adding "marriage"/
  "partnership" would flag "the longevity of your marriage", a sentence
  this app may legitimately write), and bare `he`/`she`/`they` are covered
  with explicit death **verbs** only, never the noun cluster, for the same
  reason ("their longevity" is ambiguous, "she will not survive" is not).
  Third-party HEALTH phrasing (e.g. "your father has cancer") was not part
  of this fix and remains open below.

- [ ] **`safety.py` third-party health output net** — the health cluster in
  `_PROHIBITED_OUTPUT` is still anchored to "you" the same way the death
  cluster was ("you have cancer" is caught; "your father has cancer" is
  not). Split out from the item above rather than folded into it because
  the health vocabulary needs its own false-positive pass — a chart-based
  reading legitimately discusses a family member's vitality in a way it
  never discusses their lifespan, so the death cluster's "people-only
  subject plus death noun is always a violation" shortcut does not
  transfer. *Unblocks on:* nothing external; it needs a probe set in both
  directions, same shape as the death one. *Hook:* the same
  `_THIRD_PARTY_REF` constant is already in place and shared.

- [ ] **Validation loop anchor bounds are judgement calls, not sourced
  numbers** — a probe window never starts before age 14, never exceeds 10
  years, and is dropped below 6 months. All three are defensible and none
  is derived from anything: they encode "a stretch the reader can
  actually characterise". Worth revisiting once real answers exist —
  a high `skipped` rate on long windows would be direct evidence the cap
  is too generous. *Hook:* `_MIN_RECALL_AGE`, `_MAX_ANCHOR_YEARS`,
  `_MIN_ANCHOR_YEARS` in `context/validation.py`, all applied in the one
  place every generator builds an anchor (`_anchor_from`) after the
  2026-08-11 review found the age floor had reached only one generator of
  three.

- [ ] **Validation loop is wealth-only, and shipped behind a flag** — the
  consultation validation loop (commit-before-ask probes, `timeline`,
  `life_context`) landed 2026-08-10 for the **wealth** domain only.
  `context/validation.py::validation_slots()` returns `[]` for every other
  domain by design: the handoff's instruction was to make hit rate visible
  on one real domain before generalising, and the slot generators are
  wealth-shaped (`_WEALTH_HOUSE_SENSE` is a money-sense projection of the
  house significations). *Unblocks on:* enough answered probes on wealth to
  see whether the committed claims are any good — that number does not
  exist yet for any reading this app produces, which is the whole point of
  building it. *Hook:* the domain check at the top of `validation_slots()`;
  a second domain needs its own house-sense table and its own generators,
  not a widened wealth one.

- [ ] **The validation turn defaults OFF** (`AskRequest.validate_first`,
  default `False`). Not a scoping compromise in the engine — the backend
  loop is complete and tested end to end — but a `validation_needed`
  envelope that no client can render is a wealth question that silently
  returns nothing to the reader. Answered probes already flow into every
  reading as `life_context` regardless of the flag, so nothing is waiting
  on the UI except the asking itself. *Unblocks on:* the mobile Ask
  renderer handling `validation_needed` (Codex's area — options as chips,
  a skip affordance, then re-send the original question). *Hook:* flip the
  default in `api/ask_routes.py::AskRequest.validate_first`; no other code
  changes.

- [ ] **Birth-time rectification** — the reason the probe data is worth
  storing at all, and explicitly deferred to a later pass by the handoff
  that scoped this one. Known events plus dasha math can refine a birth
  time; a *persistent* miss on a house-sensitive slot is the signal. The
  store already carries what this needs (committed claim, confidence,
  answer, and `slot_kind`, with `yoga_tension` slots flagged in their own
  `why_it_changes_the_reading` as house-sensitive and therefore
  birth-time-sensitive). *Unblocks on:* a body of answered probes per chart
  — one miss is noise. *Hook:* `validation_probes` rows keyed by
  `kundli_id`; `Kundli.birth_time_accuracy` already distinguishes
  exact/approximate/unknown and is the field a rectification pass would
  act on.

- [ ] **`safety.py`: the lifespan patterns are object-anchored, and that
  bound is lexical** — the 2026-08-11 review found `live (?:until|to|for|
  past|beyond)` swallowing "live to see", "live to enjoy" and "live beyond
  one's means", each of which replaced a whole reading with the longevity
  refer-out. Fixed by requiring a lifespan OBJECT (an age, a year, "a ripe
  old age") rather than trusting the verb, and by making polarity decide the
  one genuinely ambiguous pair ("will not live to see X" is a death verdict,
  "will live to see X" is not). What remains open is the general shape:
  distinguishing "live" the lifespan verb from "live" the reside/conduct verb
  is a semantic judgement a regex approximates. The current approximation is
  measured — 33/33 prohibited phrasings caught, 0 false positives over 36
  app-realistic negatives plus 552 sentences of real shipped prompt/KB prose —
  but a construction outside both sets is an accepted residual limitation of a
  lexical approach, in the same category as the documented immigration ones.
  *Hook:* `_LIFESPAN_OBJECT` / `_LIFE_SUBJECT` in `agents/safety.py`; the probe
  sets are `tests/test_refer_out_boundary.py`'s
  `test_lifespan_verdicts_are_caught_in_both_persons` and
  `test_ordinary_third_party_sentences_pass_the_output_net`.
- [ ] **Ask-by-voice on iOS** (mobile audit item 15, 2026-10-15). Android
  and browsers recognise speech through `ui/src/app/core/speech.service.ts`;
  iOS does not, because `@capacitor-community/speech-recognition` 7.0.1
  ships no `Package.swift` and the iOS project is SPM-only, so the plugin
  is never linked and the composer hides its microphone there. *Why not:*
  adding CocoaPods back for one plugin would split the iOS build.
  *Unblocks on:* a plugin release with SPM support (then `npx cap update`
  links it; the usage strings are already in `Info.plist`). *Hook:*
  `SpeechService` constructor, where `available()` decides `supported()`.
- [ ] **Natural voice: overnight pre-generation of the morning brief**
  (2026-10-15). Chirp 3 HD took 8–13 s for an ~870-character brief, so the
  Listen sheet asks for audio one section at a time, prefetches the first
  section when the sheet opens and the next while one plays. Making the
  whole brief overnight would make play instant, but the brief script is
  built on the device (`audio-reading-script.ts`), so the server has no
  text to synthesise yet. *Unblocks on:* a server-side copy of the brief
  script; the daily notification job (`agentic-astrospace-notifications`,
  every 15 minutes) is already running and can do the warming. *Hook:*
  `natural_speech()` in `astrospace/voice/tts.py` already caches by text
  hash, so a worker that warms the same text makes the app's request a hit.
- [ ] **Natural voice: real metered limit and durable cache.** The speech
  route caps fresh synthesis at 120k characters per reader per day *per
  Cloud Run instance*, which stops a runaway client but is not a quota.
  Durable caching needs a GCS bucket named in `ASTROSPACE_TTS_BUCKET`; with
  none set, only the per-instance memory cache and the device's Cache
  Storage are used. *Unblocks on:* CE-1 setting a reviewed
  `audio.natural_voice` limit, and creating the bucket with object
  read/write for the Cloud Run service account. *Hook:* `DAILY_CHAR_BUDGET`
  in `astrospace/api/voice_routes.py`; `_BucketCache` in
  `astrospace/voice/tts.py`.
- [x] **Natural voice: Telugu morning brief.** Built 2026-10-15: the Listen
  sheet's Telugu chip asks `POST /api/v1/voice/translate` for a simple-Telugu
  rendering of the brief's sections (same model and register as Telugu Ask
  answers, same output safety checks), then Chirp's te-IN voice reads it.
  Still open: the rendering is cached per server instance only, and the
  phone-voice fallback drops back to English because device Telugu voices
  are unreliable.
- [ ] **Readings: in-flight guard is per process.** Since 2026-10-15 a
  second generate request for the same (kundli, period, label) waits for
  the one already running and returns its reading, and new versions are
  capped at `MAX_NEW_VERSIONS_PER_DAY` (3) per kundli, period and
  kundli-local day (429). The cap counts saved rows, so it holds across
  workers; the in-flight registry is a module dict, so two Cloud Run
  instances can still each start one generation for the same period. *Why
  not now:* a cross-instance lock needs shared state (a Postgres advisory
  lock or a `generation_jobs` row) and the cap already bounds the cost.
  *Unblocks on:* choosing that lock. *Hook:* `_IN_FLIGHT` /
  `generate_reading` in `astrospace/api/reading_routes.py`.
- [ ] **Readings: legacy weekly labels are not rewritten.** Rows written
  before 2026-10-15 carry "Week of <day written>" labels. They now list
  under past weeks titled by their Monday–Sunday range (computed from
  `generated_local_date`), and the current week's lookup simply misses
  them, costing at most one regeneration per profile after deploy. *Why
  not now:* rewriting labels in production would merge several "version 1"
  rows into one label with clashing version numbers. *Unblocks on:* a
  migration that renumbers versions within the merged label. *Hook:*
  `_reading_range` / `_period_label` in `astrospace/api/reading_routes.py`.

- [ ] **Paid reports (D2: ₹199–499; Plus gets one a month)** (2026-10-15).
  The hybrid pricing layer shipped without them: a report is a new
  product (Kundli, marriage timing, career, year-ahead, matching PDFs) with
  its own generation, review and convention notes, not a gate on something
  that exists. *Unblocks on:* the report content spec per type and a
  `reports.monthly` limit. *Hook:* add the products to
  `astrospace/entitlements/products.py`; `_apply_pack` in
  `astrospace/api/store_routes.py` is the pattern for a one-off purchase,
  and `ask-report.ts` already builds a PDF on the device.
- [ ] **Ask credit reservations that never settle.** A reservation is a
  counter on the month's `usage_buckets` row (or a decrement on a
  `question_credits` row), released in a `finally` on every route path. A
  process killed between reserve and release leaves one credit held until
  the month rolls over. *Unblocks on:* evidence it happens (watch
  `reserved > 0` on old buckets). *Hook:* `reserve_ask_credit()` in
  `astrospace/entitlements/usage.py`; a per-reservation row with an expiry
  would let a sweeper return it.
- [ ] **Turning quotas on.** `ASTROSPACE_QUOTAS_ENFORCED` stays off until the
  store products exist in Play Console and App Store Connect, RevenueCat
  has the app keys (`ui/src/environments/*.ts`, `revenueCat`) and the
  webhook secret (`REVENUECAT_WEBHOOK_AUTH`), and a sandbox purchase has
  round-tripped. Until then usage is counted, never blocked. Hawk's own
  account needs an `entitlement_overrides` row for `ask.answers.period`
  (value null) before enforcement, or testing stops at 3 answers.
- [x] **Muhurta: add the window straight into the calendar on Android.**
  Done 2026-10-17 (PR #151): on Android, `addToCalendar()` in
  `core/calendar-export.ts` opens Google Calendar's add-event form
  (`googleCalendarUrl()`); iOS and the browser still share an .ics file.
- [ ] **Analytics and crash reports are wired but off** (2026-10-15).
  `core/analytics.service.ts` sends to PostHog only when
  `environment.posthog.key` is set, and the reader's "Share usage and crash
  reports" switch (on by default) is respected. *Unblocks on:* a PostHog
  project (EU host assumed) and its public project key in
  `ui/src/environments/environment.prod.ts`, and a line in the privacy
  policy naming PostHog as a processor before launch. Native crashes outside
  the WebView (a plugin's Swift or Kotlin code) are not covered; that needs a
  native crash SDK if they turn up in store reviews.
- [ ] **Two Explore plan gates are still enforced only in the app**
  (2026-10-16; narrowed 2026-10-19). Once `ASTROSPACE_QUOTAS_ENFORCED` is
  on, the API itself refuses readings and Muhurta to Free (402), and trims
  yogas past the first two, the remedy plan to its free practice, and
  vargas beyond D1/D9 (`plan_lock()` / `require_plan()` in
  `entitlements/resolver.py`). Still app-only: dosha detail (the meaning
  text is the public `/vedic/rules` catalogue anyway) and compatibility,
  where the full report and the one-person-a-month count live in
  `core/plan-gate.service.ts`, the count on the device. *Why not built:*
  the Gun Milan rows carry Nadi and Bhakoot dosha, and trimming them
  server-side would hide a dosha, so the free payload needs deciding first.
  *Unblocks on:* a decision on which compatibility fields Free gets (keep
  `safety_checks` and any dosha row). *Hook:* `compatibility()` in
  `api/vedic_routes.py`, and a `UsageBucket` keyed
  `compatibility.checks.period` with the distinct partner ids, like Ask's.

- [ ] **Native app micro-interactions left after the 2026-10-15 pass**
  (production audit §5). Scroll memory, sheet drag and exit, press states,
  haptics, motion tokens, expand/collapse and selectable prose shipped.
  Still open:
  - pull-to-refresh, because `overscroll-behavior: contain` swallows the
    gesture and it needs a directive on Today, Readings, Notifications and
    Calendar;
  - Ask history swipe, which should follow the finger and reveal leftward,
    and should close the reveal on tap rather than open the row
    (`ask/ask-history.*`);
  - the Android exit prompt, which is still a PrimeNG web dialog
    (`app.ts`, NATIVE_EXIT_ROUTES);
  - one skeleton component sized to the final layout, to replace the mix of
    text cards and spinners;
  - `.m-pressable` on the remaining tappables (only cards and rows have it);
  - `warning()` on the profile-delete and account-deletion screens;
  - haptics on reading generation;
  - forgot/reset-password back links, which still use `routerLink`.

  *Why not:* these were outside the pass's scope. *Unblocks on:* nothing;
  each one is ready to build. *Hook:* `styles-mobile.scss` (`.m-pressable`,
  `.m-collapse`), `shared/select-haptic.directive.ts`,
  `shell/scroll-memory.directive.ts`.

### D. Docs pending a decision

- [ ] **`docs/marriage-agent-kb.md`, `marriage-ce-payload-v1.md`,
  `marriage-agent-prompt-v1.md`, `career-agent-kb.md`** — all four are
  user-added, untracked in git, and none is wired into any addendum or the
  KB pipeline. The payload/prompt docs were each audited and found to carry
  fabricated specifics (a wrong Jaimini karaka scheme, self-contradicting
  Avastha arithmetic, mismatched Vimshopaka scores, 2/3 wrong D-60 signs,
  and the non-existent terms "Pratargala" and "Karakaksha"); the two KB
  docs are largely standard prose the retrieval pipeline doesn't ingest
  from `docs/` anyway. *Decision needed:* commit, relocate into the real KB
  ingestion path, or delete.

### E. Production hardening left open (2026-10-15)

Follow-ups from the server-hardening pass on the 2026-10-15 production audit
(section 3). The Ask/stream/voice routes, pool, logging, audit middleware,
worker and deletion fixes shipped; these did not.

- [ ] **Readings hold a transaction through generation.** *Why not:*
  `reading_routes.py` was owned by a parallel change (force_refresh limits,
  labels) and was left alone to avoid a conflicting rewrite. *Unblocks on:*
  that change landing. *Hook:* call `release_connection(db)` from
  `astrospace/db/database.py` before the agent call in `reading_routes.py`,
  then persist through `short_session(db)`, as `ask_routes.py` does.
- [ ] **Content-Security-Policy.** *Why not:* the other security headers are
  safe everywhere; a CSP has to be verified against the running SPA, the
  Supabase auth flow and the Capacitor WebView, and a wrong one is a blank
  screen in production. *Unblocks on:* a report-only rollout read for a week.
  *Hook:* `astrospace/api/security_headers.py`.
- [ ] **Legacy Anthropic clients without limits.** `astrospace/ai/client.py`
  (`AstroClient`) and `astrospace/knowledge/ingestion/analyzer.py` still use
  the SDK defaults (600 s, 2 retries). *Why not:* neither is on a reader's
  request path. *Hook:* reuse `anthropic_client()` from
  `astrospace/agents/base.py`.
- [ ] **`BirthInfo` (api/models.py) has no length limits.** *Why not:* it
  backs the four legacy routes in `routes.py`, which a parallel change
  rewrote. *Hook:* the same `Field(max_length=...)` bounds as
  `KundliCreate` in `kundli_routes.py`.

### F. Native startup and offline (Tier 1 items 1, 2, 6, 8 of the 2026-10-15 production audit)

Shipped 2026-10-15: cache-first `/auth/config`, bounded session refresh,
`/settings` off the boot path, `timeout(8s)` + one retry on API GETs
(`core/http-resilience.interceptor.ts`), native splash held until the web
intro paints, cached profile list and chart bundle in `ResourceCacheService`,
sign-out teardown of retained tabs (`core/session-teardown.ts`), the web shell
and PrimeNG behind a lazy route (initial bundle 1.36 MB → 0.70 MB raw, with an
`angular.json` budget that errors at 1.2 MB), `@capacitor/keyboard`, and real
system insets in place of the hard-coded 48 px Android bottom.

- [ ] **Lazy SQLCipher open.** The audit asked for it; it is still an app
  initializer. *Why not:* the cached profile list and Today are read from
  that cache before first render, so opening it later only moves the wait.
  It is ~6 local bridge calls, not network. *Unblocks on:* a device trace
  showing the open is a meaningful share of cold start. *Hook:*
  `provideAppInitializer` in `ui/src/app/app.config.ts`.
- [ ] **Slimmer Supabase client** (~80 KB of realtime/phoenix/storage still in
  the initial bundle). *Why not:* needs `@supabase/auth-js` used directly and
  every `SupabaseClient` call site re-checked. *Hook:* `buildClient` in
  `ui/src/app/core/auth.service.ts`.
- [ ] **Device-only data on sign-out.** Mobile notes, the mantra tracker and
  recent searches live in plain localStorage and are not cleared on sign-out.
  *Why not:* they are the only copy (no server sync), so clearing is data
  loss. *Unblocks on:* a product decision — sync them, or warn and clear.
  *Hook:* register a hook with `SessionTeardown`.
- [ ] **Keyboard and insets on device.** The 48 px Android bottom was removed
  on the strength of Capacitor 8.4.2's `SystemBars.java` (env() passthrough on
  WebView ≥ 140, `--safe-area-inset-*` injection, WebView padding otherwise).
  *Unblocks on:* an Android 15/16 emulator run with gesture and 3-button nav,
  and an iOS run with the keyboard open in Ask, after `npm run build:native`.
  *Hook:* `--as-safe-*` in `ui/src/styles.scss`; `NativeKeyboardService`.
- [ ] **Auth config rotation applies on the next launch.** A revalidated
  `/auth/config` that differs is stored, not applied, because rebuilding the
  Supabase client under a live session is riskier. *Hook:* `loadConfig` in
  `ui/src/app/core/auth.service.ts`.
- [ ] **First tap after closing a sheet or going back is sometimes ignored**
  (regression 2026-10-17, M5). Seen on the phone reopening Listen, opening
  Past questions, and after leaving a Settings sub-page; a second tap works.
  *Why not:* it is intermittent and does not reproduce in desktop Chromium,
  and nothing in the code holds input: the sheet sets `pointer-events: none`
  only while sliding out and is removed after. *Unblocks on:* a trace on the
  device (chrome://inspect over adb, Performance panel with touch events) to
  see whether the tap reaches the WebView. *Hook:* `slideOut()` and
  `restoreFocus()` in `features/mobile/sheet/sheet.component.ts`, and the
  touch listeners in `installNativeInteractionGuards()` in `app.ts`.

---

## Live evaluation pass (2026-08-12)

**Status:** point-in-time evaluation, folded in per this file's own rule. Real
`AskOrchestrator` runs against a real Gemini call (`.venv`'s live
`GEMINI_API_KEY`), bypassing HTTP/auth/DB so the agent's actual behaviour
could be inspected directly — not the plumbing around it, which the existing
test suite already covers. This is the "does grounding actually change
behaviour" question the career/health/marriage/children/Phaladeepika passes
had not yet been checked against.

Setup: a local, disposable merge of `main` + the three open KB PRs at the
time (`claude/marriage-kb`, `claude/children-kb`,
`claude/phaladeepika-crosscheck`) in a scratch worktree, giving the full
75-reference grounded state those PRs together produce. Never pushed; the
worktree was deleted after this entry was written. Five live generations
across marriage, children and career.

### It works — marriage cited real grounded verses

Asked "Will my marriage be happy? What should I know about my spouse's
nature?" The reading passed verification and its `technical_basis` cited
`bphs24_79_seventh_lord_in_seventh` and `bphs18_16_malefic_on_seventh` by
`ref_id` — both landed in the marriage KB pass, both correctly matched to the
actual chart (7th lord Saturn in the 7th, Rahu conjunct Saturn in the 7th).
The Manglik-adjacent placement (Mars in the 8th) was framed as "a gentle flag
to manage... mindfully" — the flag-not-verdict framing CLAUDE.md requires,
produced without being asked for in the question. Nothing from the excluded
material (exact wife-count, unconditioned spouse-death, the spouse's own
birth-sign prediction) leaked into either this reading or four other live
generations checked the same way.

The **drekkana-emphasis dasha-timing feature is confirmed working in live
output**, not just passing its unit tests: the career reading said "This long
period had its core weight concentrated in its middle phase, from December
2017 to December 2023" — unprompted, and matching the computed emphasis
window exactly.

### It works — the verifier correctly refused a bad generation

The children reading (`"When will I have children, and will it come easily?"`)
returned `verification_failed` on the first live run — both the initial
generation and the one repair attempt failed `verify()`/`verify_coverage()`.
Reproduced the orchestrator's exact repair loop standalone
(`scratch_eval_repair_trace.py`, not committed — see below) to capture the
actual violations rather than the discarded terminal status alone: four
further live generations of the *same question* against the *same bundle*
all passed cleanly on the first try, citing `houses`, `karakas`,
`jaimini_karakas`, `vargas` (D7), `dasha_relevance` and `gochara`, and
correctly framing delay as delay rather than a literal age. Read together as
transient sampling variance (an occasional non-compliant generation, at
roughly the rate LLM structured-output tasks produce them) that the
repair-then-refuse design **correctly caught and declined to serve** —
exactly the failure mode `verification_failed` exists for. Not evidence of a
defect in the newly grounded children material.

### A real, precisely diagnosed gap: verse-level citations are optional, and models take the option

The career reading — 12 references sitting in its bundle, including the
Phaladeepika navamsa-of-10th-lord technique that has no BPHS equivalent —
cited **zero** of them by `ref_id`. `technical_basis` used only generic
section names (`houses`, `jaimini_karakas`, `yogas`, `vargas`,
`dasha_relevance` ×2, `gochara`). The reading's content was directionally
consistent with the navamsa technique (it discussed the D10 lagna lord and a
Venusian professional flavour) without ever citing
`phal5_navamsa_tenth_lord_livelihood` specifically — plausibly reasoning from
the model's own training-data familiarity with the underlying classical
concept rather than from what this project actually grounded.

Root cause, found by reading the prompt rather than guessing: rule 2 in
`domain_agent.py` states a `technical_basis` source "must be either a
reference/passage id from the bundle's `references`... **or** one of the
bundle's own section names" — the two are presented as equally valid, with no
preference for the more specific, independently-checkable citation over the
generic one. A model given two compliant options with no ranking between them
will not reliably reach for the harder-to-produce one.

- [x] **Prefer verse-level citation over bundle-section citation when both
  apply — CLOSED 2026-09-08.** Added rule 2b to `astrospace/agents/
  domain_agent.py`'s `_BASE_SYSTEM`, directly after rule 2a: when a claim is
  grounded in a specific reference/passage id and that section's bare name
  would also technically validate, cite the specific id, never the bare
  name — both were already equally valid against `verifier.valid_sources()`
  and the tool schema's `source` enum (`schema.py`'s
  `reading_tool_schema()`), so nothing before this pushed the model toward
  the harder-to-produce, independently-checkable option. Regression test
  (`test_prompt_prefers_verse_level_citation_over_bare_section_name`)
  pins the rule text in the rendered career prompt and, separately, that
  `phal5_navamsa_tenth_lord_livelihood` still exists in the career bundle's
  `references` — the exact citation the live-eval pass found silently
  unused — so the test fails loudly if that reference is ever renamed
  rather than the preference rule silently having nothing left to prefer.
  Full suite: 2076 passed, 2 skipped, 1 xfailed. **Not yet re-verified live**
  (the finding this fixes was only ever observed via a live model call,
  the 2026-08-12 eval pass) — a prompt instruction is not proof the model
  actually follows it more often; that needs a follow-up live-eval spot
  check, same shape as the original pass, not run this pass.

### What this pass did not do

Five generations across three domains is a sample, not a benchmark — no
health, wealth, personality, family_property or foreign generation was run
live, and no guided/practitioner register variance was checked (only
balanced). The eval harness scripts (`scratch_eval_orchestrator.py`,
`scratch_eval_repair_trace.py`) were written into the scratch worktree and
deliberately not committed; they call the orchestrator directly with a
synthetic chart and no persistence, which is the right shape for a quick
check and the wrong shape for a permanent fixture — a real eval suite would
need seeded charts with known expected citations, not a hand-run script.

---

## KB coverage expansion plan — discovery pass (2026-09-17)

**Status:** open plan + checklist. Folded in per this file's own "one
backlog" rule rather than started as a new dated doc. Measured, not
recalled: every number below came from reading `references.json`,
`taxonomy.json`, `sources.json` and the actual corpus directory in this
pass. Re-derive with the commands in each section rather than trusting
these figures once they age.

### The measured baseline

- **140 references**, but **108 of them (77%) cite BPHS alone.** The rest:
  `uttara_kalamrita` 14, `phaladeepika` 9, `brihat_jataka` 4,
  `jaimini_sutras` 2, `charak_medical` 1, `light_on_relationships` 1,
  `saravali` 1.
- **57 of 74 declared subdomains (77%) have at least one reference.** Per
  domain: career 7/7, wealth 6/7, personality 6/7, spirituality 5/6,
  litigation 5/6, children 4/5, marriage 6/8, family_property 6/8,
  health 5/7, foreign 4/6, **education 3/7 (worst)**.
- **Only 6 of the 24 catalogued sources are physically in the corpus**
  (bphs, brihat_jataka, jataka_parijata, phaladeepika, saravali,
  uttara_kalamrita). The other 18 are catalogue entries with no text behind
  them. Separately, the corpus holds one work that is *not* in the
  catalogue at all (the dokumen.pub nakshatra ebook), so the two lists
  disagree in both directions.
- **`valid_sources()` cannot see any of this.** It validates a citation
  against `sources.json`'s keys, never against corpus presence — so a
  reference citing a book this project does not have passes verification
  looking exactly as grounded as a BPHS citation.

### Finding 1 — Saravali is the cheapest coverage on the table

`saravaliofkalyan01kalyuoft.pdf`'s OCR export is **98,301 words at 94.9%
accuracy — the single most accurate text in the corpus** — and exactly
**one** reference has ever been mined from it. Saravali is encyclopedic on
planets in signs/houses/combinations, which is precisely the material the
thin domains need. No acquisition, no rights question, no OCR work.

### Finding 2 — Jataka Parijata is owned but unreadable

Two copies (`2015.312156.Jataka-Parijata.epub`, and the Mysore 1933
Subrahmanya Sastri Vol 2 EPUB), **both OCR mush** — the DLI copy embeds its
own warning, "estimated to be only 25.10% accurate". Zero references. Yet
`taxonomy.json` names `jataka_parijata` as a `source_ref` for **marriage**
and **education**. Fix is re-OCR through the same pipeline that produced the
five good `ocr-playground-…/markdown.md` exports, not acquisition.
Same treatment needed for BPHS Santhanam Vol 2 (56.1%) and BPHS Sharma
Vol 2 (no text layer at all).

### Finding 3 — three ungrounded subdomains are ones the product refuses

Three of the 17 ungrounded subdomains name things the agents are instructed
not to answer, so "no references" is the correct state and grounding them
would be actively wrong:

- `marriage.divorce` — `registry.py`'s marriage addendum: never say a dosha
  means a marriage "will end in divorce". An explicit, named refusal.
- `health.mental_health` — the personality addendum routes mood/anxiety/
  diagnosis questions to health's refer-out boundary; CLAUDE.md forbids
  medical verdicts. Also explicit.
- `health.hospitalization` — **inference, not an explicit refusal.** No
  instruction names hospitalization; it is read off the general "never
  predict specific medical outcomes" ban. A case exists that the 12th
  house's traditional confinement significations could be described as a
  tendency under the same flag-not-verdict rule the app already applies to
  doshas. Needs a human call before it is treated like the other two.

**Scope check, measured before recommending anything here:** taxonomy
subdomains are consumed *only* by KB retrieval —
`assembler.py` passes them to `JsonKnowledgeBase.retrieve()` as a
rank/filter input, and `kb.py` ranks rather than excludes unless
`require_subdomain_match` is set. **They are never rendered into the
prompt; the model never sees this list.** So an entry here is not
"advertising" anything to the model, and removing one changes no agent
behaviour and weakens no refusal — the refusals live in `registry.py`'s
addenda and `safety.py`'s gate, neither of which reads `taxonomy.json`.
This is metrics and catalogue hygiene, not a safety fix, and should not be
sold as one.

**Prefer marking over deleting.** Deleting loses the knowledge that these
are refused *by design* and invites a future pass to re-add them as
"missing coverage". An explicit `answerable: false` plus a reason matches
this file's own rule that anything deliberately unbuilt states why. **The
real coverage gap is 14 subdomains, not 17.**

### Source discovery — availability only (2026-09-17)

Availability confirmed by direct lookup. Rights tiers are a first read for
triage, **not legal advice** — confirm before ingesting. **This section
establishes that a text EXISTS online; it says nothing about whether its OCR
is usable.** Where it disagrees with the measured pass below, the measured
pass wins — it was wrong about two Prasna Marga identifiers and about
Sarvartha Chintamani being findable by title.

**Tier A — pre-1930, almost certainly public domain.** B. Suryanarain Rao
died 1936; his own editions are PD in India (life+60) and the US (pre-1930
publication). All nine titles sit in one Internet Archive item,
[`Astrology_Books_by_B_Suryanarayana_Row`](https://archive.org/details/Astrology_Books_by_B_Suryanarayana_Row):

| Text | Year | Closes |
| --- | --- | --- |
| Sarvartha Chintamani | 1899 | `sarvartha_chintamani` phantom; bhava depth across most domains |
| Jataka Chandrika | 1900 | `laghu_parashari` phantom |
| An Introduction to the Study of Astrology | 1900 | general |
| Brihat Jataka (Row translation) | 1919 | independent cross-check of an owned text |
| Stri Jataka / Female Horoscopy | 1931 | `marriage.second_marriage` |
| The Astrological Self Instructor | 1893 | general |

- **Bhavartha Ratnakara** — DLI scans [`in.ernet.dli.2015.134838`](https://archive.org/details/in.ernet.dli.2015.134838)
  and [`in.ernet.dli.2015.142241`](https://archive.org/details/in.ernet.dli.2015.142241),
  both with `_djvu.txt` full text. Closes the `bhavartha_ratnakara` phantom.
- **Brihat Samhita** — [`archive.org/details/Brihatsamhita`](https://archive.org/details/Brihatsamhita);
  relevant to `foreign` (yatra/journey chapters). Edition/rights unverified.

**Tier B — obtainable but modern and in copyright.** Usable to *confirm a
rule exists and locate its chapter*, never to reproduce prose. This is
already how `references.json` works (our own paraphrase + chapter-level
`location`), and it is the same line the deferred nakshatra-shakti item
drew.

- **Prasna Marga**, B.V. Raman, 2 vols — [`PrasnaMargaBVR`](https://archive.org/details/PrasnaMargaBVR)
  (with `_djvu.txt`), also [`prasnamarga-035823mbp-1`](https://archive.org/details/prasnamarga-035823mbp-1).
  **The canonical text for `litigation.theft_loss`** and strong on disease
  and travel prasna. Currently named as a `source_ref` by health, children
  and foreign while absent from the corpus.
- **Jaimini Sutras**, Row/Raman 1949 & 1955 — [`in.ernet.dli.2015.486584`](https://archive.org/details/in.ernet.dli.2015.486584).
  **Two live references already cite this text and we do not have it.**
  Prefer the earliest Row edition; Raman's annotations are separately in
  copyright.
- **Hora Sara**, Prithuyasas / R. Santhanam — [full text](https://archive.org/stream/HoraSaraRSanthanamEng/Hora%20Sara%20RSanthanam%20Eng_djvu.txt).

**Websites / structured corpora**

- **[wisdomlib.org](https://www.wisdomlib.org/hinduism/book/brihat-jataka-by-varahamihira-sanskrit-english)** —
  the most useful find for the *citation-precision* problem. Brihat Jataka
  is addressable **per chapter and per individual sloka** (27 chapters, one
  URL per verse), and Brihat Samhita is published the same way. Ideal for
  resolving a rule to a real chapter/verse. **The English there is Michael
  D Neely's 2017 translation — copy the citation target, never the prose.**
- **[GRETIL](https://gretil.sub.uni-goettingen.de/gretilbk.htm)** —
  machine-readable plain-text Sanskrit, searchable. Jyotisha holdings not
  confirmed this pass; worth a direct check.
- **[Muktabodha](https://muktabodha.org/digital-library/)** — 3,000+ texts,
  570+ searchable e-texts, but Śaiva/Tantra-weighted; jyotisha holdings
  unconfirmed.
- **[INDOLOGY virtual e-text archive](https://indology.info/virtual-e-text-archive-of-indic-texts/)**,
  **ebharatisampat.in** — secondary aggregators worth a sweep.

### Measured OCR pass — 2026-09-18

**Status:** supersedes the availability lists above wherever the two
disagree.

**Method.** Downloaded each candidate's `_djvu.txt` from archive.org and
scored it with `scripts/audit_kb_sources.py`'s own scoring — median percent
of tokens that are real dictionary words, over prose pages — so every number
here sits on the same scale as `docs/kb_corpus_sources.md`'s table. Sampled
from roughly 40-45% into each file, never the front: title pages and
Devanagari plates are unrepresentative, which is exactly why our own Saravali
reads as mush in its opening pages and still scores 94.9% overall. Bar is the
audit's own: **>=85% readable, 60-85% marginal, <60% mush.**

#### The rule this pass produced: verify SUBJECT, not title and score

The two best-scoring "Jaimini Sutras" items on archive.org — 86.2% and 87.8%,
one titled *"Jaimini Sutras, 1911 Edition"* — are **the wrong book**. They are
the *Purva Mimamsa* sutras, Vedic ritual philosophy by a same-named author.
A subject-vocabulary check returned 452 ritual-philosophy terms against 0
astrology terms. The genuine astrological Jaimini scores **lower** (82.5-84.3%).

Selecting on title and OCR score alone would have ingested Vedic ritual
philosophy as astrological grounding — the same fabricated-citation failure
Phase 1's guard exists to prevent, arriving through a door that guard does not
cover, because the source would have been genuinely present and genuinely
readable. **Every acquisition gets a subject check before ingestion.**

#### Readable (>=85%)

| Text | archive.org item | Acc | Closes |
| --- | --- | ---: | --- |
| Intro to the Study of Astrology 1900 | Row collection | 94.1% | general |
| Prasna Marga Pt 2 | `prasna-marga-part-2-by-bv-raman` | 91.9% | `litigation.theft_loss`, remedies |
| Astrological Self Instructor 1893 | Row collection | 91.7% | general |
| Jataka Chandrika 1900 | Row collection | 90.5% | `laghu_parashari` phantom |
| **Sarvartha Chintamani 1899** | Row collection | 90.3% | education gaps, `sarvartha_chintamani` phantom |
| Chappanna / Prasana Sastra 1946 | Row collection | 90.0% | theft/loss prasna |
| Prasna Marga | `PrasnaMargaBVR` | 89.7% | as above |
| Stri Jataka (alt copy) | `STRIJATAKA` | 89.3% | `marriage.second_marriage` |
| Bhavartha Ratnakara | `BhavarthaRatnakara` | 89.0% | phantom — **only 13 prose pages, sample too small to trust; re-measure before acquiring** |
| Stri Jataka 1931 | Row collection | 87.4% | `marriage.second_marriage` |
| Hora Sara | `HoraSaraRSanthanamEng` | 86.0% | `hora_sara` phantom |
| **BPHS Vol 2** | `pcis_brihat-parasara-hora-sastra-volume-2-by-maharshi-parasara-sanskrit-and-engl` | 85.3% | **half our backbone text, plus the remedial chapters** |

"Row collection" = `Astrology_Books_by_B_Suryanarayana_Row`, a single archive.org
item holding nine titles. **It must be scored file-by-file** — the first pass
scored only its first file and concluded Sarvartha Chintamani was unavailable,
when it is sitting in that item at 90.3%.

#### Marginal (60-85%, spot-check before trusting)

| Text | Item | Acc | Note |
| --- | --- | ---: | --- |
| **Jataka Parijata 1932** | `JatakaParijata1932` | 75.8% | vs **~25%** for both copies we own — a real upgrade, still under the bar |
| Bhavartha Ratnakara | `in.ernet.dli.2015.142241` | 84.4% | 72 prose pages, more trustworthy sample than the 89.0% one |
| **Jaimini Sutras 1955** | Row collection | 84.3% | the *genuine astrological* one — see the subject-check rule above |
| Jaimini Sutras 1949 | Row collection | 82.5% | same work, earlier edition |
| BPHS Vol 1 | `heag_brihat-parasara-hora-sastra-vol-1-by-maharshi-parasara-commentary-editor-tr` | 83.0% | we already hold better (93.6%/93.8%) |
| Brihat Jataka 1919 | Row collection | 79.8% | we already hold better (91.2%) |

#### Negative results — recorded so nobody researches them twice

- **Lal Kitab has no readable copy.** `LALKITAB1941URDUEDITION` 18.0%;
  `lal-kitab-amrit-rohit-sharma-2` 46.2%; `lal-kitab-1952-grammer-portion...`,
  `asli-prachin-lal-kitab`, `beef_asli-pracheen-lal-kitab...` and the Arun
  Samhita copy all have **no text layer at all**. Every one is untranslated
  Urdu or Hindi, and all sit far below the 60% floor. Note what the result
  list itself demonstrates: 1941 Urdu, 1952, two rival "Asli Pracheen"
  editions and Arun Samhita — **that is the edition problem**, which is
  presumably why `knowledge/ingestion/source_policy.py` already gates Lal
  Kitab behind "requires edition-aware human review before publication".
  Leave `lal_kitab_1952` at `corpus_status: absent` and leave that gate
  alone. Two further reasons it is a product decision rather than a cleanup:
  Lal Kitab is the **North Indian (Punjabi)** tradition, so it does not serve
  a South-Indian-weighted reader, and it is the most *prescriptive* remedial
  tradition there is, which sits awkwardly against CLAUDE.md's "traditional
  practice, never pay-to-remove" and `remedies.py`'s own no-fear-leverage rule.
- **Navagraha items are liturgy, not jyotisha.** Ashtottara Shatanamavali
  name-lists, Navagraha Gayatri, puja mantras — 9.9% to 59%, and devotional
  rather than interpretive. They would ground no *rule*.
- **Two Prasna Marga items named in the availability section above are
  unusable** — `prasna-marga-part-i-don` and `prasnamarga-035823mbp-1` return
  zero prose pages, as does the Nilakantha Sharma tippani. The good copies are
  different items entirely, listed above.
- `in.ernet.dli.2015.134838` (Bhavartha Ratnakara) returns HTTP 500.

#### South Indian remedial sources — and a gap underneath them

`remedies.py` is a real engine with careful safety constraints, but **no
reference in `references.json` mentions remedies at all**, and `remedies` is
not one of the 11 taxonomy domains — so remedy content is currently generated
with zero KB grounding. The two texts that would change that are both already
on the acquisition list:

- **Prasna Marga** is the Kerala tradition, so genuinely South Indian, and is
  densely remedial at 87.7-92.4%: it names specific South Indian rites
  (Aghorabali, Kapala Homa, Chakra Homa, Prathikarabali, Bhuthamaranabali,
  Khanga Ravanabali).
- **BPHS Vol 2** carries the remedial chapters — Ashtakavarga remedial
  measures, "he should take appropriate remedial measures to appease the
  planet concerned" — and that scan is explicitly marked **CC-0, public
  domain** (Gurukul Kangri Collection), which settles its rights cleanly.

Grounding remedies needs a design decision first — whether `remedies` becomes
a taxonomy domain or its references attach to the existing eleven — so it is
listed in the checklist as a decision, not a mining task.

### Gap → source mapping

Ordered by cost. **Most of the real gap closes from texts already owned.**

| Ungrounded subdomain | Closes from | Cost |
| --- | --- | --- |
| ~~`personality.intellect_communication`~~ | **DONE** — Saravali ch.4/13/22 | closed 2026-09-19 |
| ~~`children.relationship_with_children`~~ | **DONE** — BPHS ch.18 v.1-3 (supportive half only) | closed 2026-09-19 |
| `family_property.domestic_peace` | ~~Saravali~~ — **not in our Vol 1** (4 hits, all affliction framing); needs Saravali Vol 2 or BPHS 4th bhava | acquire |
| `family_property.relocation` | ~~Saravali~~ — **zero hits in our Vol 1**; needs Saravali Vol 2 or BPHS | acquire |
| ~~`wealth.debts`~~ | **DONE** — Saravali ch.4 (Ketu), ch.15 v.19 | closed 2026-09-19 |
| ~~`education.field_of_study`~~ | **DONE** — Saravali ch.4/22/23 | closed 2026-09-19 |
| `education.breaks` | **attempted, left open on purpose** — not in Saravali Vol 1, and BPHS's only support is one worked example in Sharma's *commentary* for a single ascendant, not a mula sloka | needs a real source |
| ~~`education.research`~~ | **DONE** — BPHS ch.26 v.8 (lagna lord in the 8th) | closed 2026-09-19 |
| `education.competitive_exams` | Sarvartha Chintamani (Tier A) | acquire |
| `foreign.return_home` | BPHS 4th/12th + Brihat Samhita yatra | mine + acquire |
| `foreign.education_abroad` | BPHS 9th/12th + Sarvartha Chintamani | mine + acquire |
| `spirituality.karmic_axis` | **Jaimini Sutras** (already cited, unowned) | acquire |
| `litigation.theft_loss` | **Prasna Marga** (Tier B) | acquire |
| `marriage.second_marriage` | Stri Jataka 1931 (Tier A) + BPHS 7th | acquire |

### Checklist

**Phase 0 — mine what we own (no acquisition, no rights question)**

- [x] **Saravali mining pass — PARTIALLY DONE 2026-09-19, and the original
  AC was not achievable.** 7 references added (Saravali went from 1 to 8),
  closing `personality.intellect_communication`, `education.field_of_study`
  and `wealth.debts`; all three verified retrievable, coverage 57/74 -> 60/74.

  **The finding that matters more than the references:** the copy we hold is
  **Volume 1 — chapters 1-26 only** (planetary characters, karakas, yogas,
  planets-in-rasis). Saravali's **bhava-effect chapters are in Volume 2,
  which we do not have.** This plan assumed 8 subdomains were "mine only"
  from word count and OCR accuracy without checking what the volume actually
  contains. Measured: `family_property.relocation` has **zero** hits,
  `domestic_peace` and `education.research` have four each, and
  `education.breaks` hits are about obstacles in general, never about study.
  Those four need Volume 2 or another text — they are **not** mining work.

  Two more deliberately left ungrounded rather than forced:
  `children.relationship_with_children` has 180 hits but the material is
  bereavement-flavoured (child-loss shlokas the reference store's own
  `_MORTAL` guard exists to keep out), and `spirituality.karmic_axis` would
  have to come from Saravali's Rahu/Ketu significations, which are disease
  and fear vocabulary this product does not surface.

  *Remaining AC:* the other four subdomains move to Phase 2 behind a fuller
  Saravali — see the acquisition item added there.

- [x] **BPHS follow-up pass — DONE 2026-09-19.** Two of the four subdomains
  Saravali could not reach were closed from BPHS Sharma Vol 1 instead
  (214k words, ch.1-46 — it *does* carry the bhava-effect chapters Saravali
  Vol 1 lacks): `children.relationship_with_children` from ch.18 v.1-3 and
  `education.research` from ch.26 v.8. Coverage 60/74 -> **62/74**.

  `education.breaks` was attempted and **deliberately left open**. Saravali
  Vol 1 has nothing, and BPHS's only support is a single worked example in
  Sharma's own *commentary* for one ascendant (debilitated 5th lord in the
  4th) — a modern commentator's illustration, not a mula sloka. Grounding a
  product claim on that is weaker than leaving the subdomain honestly empty.

  Both new references carry an `observance_note` recording what was
  **not** ingested: BPHS ch.18 continues straight into progeny-denial
  material, and ch.26 v.8 pairs its knowledge indication with adverse
  character claims. Only the supportive halves are carried.

  Worth knowing for the next pass: `test_no_reference_asserts_longevity_or_death`
  scans `statement` **plus** `observance_note`, so a note that *describes*
  excluded mortality material trips the guard even when the statement is
  clean. Describe the exclusion without the vocabulary.
- [ ] **Re-OCR Jataka Parijata** (both copies) through the
  `ocr-playground` pipeline; target ≥90% like the other five exports. Then
  mine it for marriage/education, the two domains whose `source_refs`
  already claim it. *AC:* a `markdown.md` export exists and
  `audit_kb_sources.py` reports it readable.
- [ ] **Re-OCR BPHS Santhanam Vol 2 (56.1%) and BPHS Sharma Vol 2 (no text
  layer).** Half the backbone text is currently unreadable.
- [ ] **Identify the two unlabelled corpus files** —
  `EPUBS/7136b975-c819-43ae-8c04-b510504137e2.epub` (180k words, OCR mush)
  and `EPUBS/Unconfirmed 71230.crdownload` (an incomplete download). Name
  them or delete them.

**Phase 1 — stop citing books we do not have**

- [x] **Retarget or drop the 4 live phantom references — DONE 2026-09-18.**
  All four moved onto BPHS, which was confirmed to support each claim in the
  owned text first: "the Karaka or Significator of wife (Venus)", "the 6th
  House, the House of disease" (plus Saturn-as-delay, Mars-as-significator-
  of-wounds), and the chara-karaka degree-ordering passage naming Putra
  Karaka. Every statement is byte-identical; only citations moved. Two
  ref_ids renamed for naming a source they no longer cite.
  ~~Original item:~~
  `charak_6th_chronic_disease` (health) cites `charak_medical`, a modern
  in-copyright book absent from the corpus — its claim (6th bhava, Saturn
  chronic / Mars acute) is well attested in BPHS and Uttara Kalamritam, so
  retarget rather than delete. Same treatment for the 1
  `light_on_relationships` reference. The 2 `jaimini_sutras` references
  become real the moment Phase 2 lands that text.
- [x] **Clean `taxonomy.json` `source_refs` of unowned books — DONE
  2026-09-18.** 8 lines cleaned. `jataka_parijata` deliberately kept on
  marriage/education: we own it, Phase 0 re-OCRs it, and no reference cites
  it. ~~Original item:~~ — `raman_htjh`
  (career, wealth, marriage, personality), `kn_rao_career` (career),
  `prasna_marga` (health, children, foreign — until acquired),
  `charak_medical` (health), `muhurta_chintamani` (marriage),
  `rath_jaimini` (spirituality). Zero references depend on any of these, so
  this is a pure catalogue correction.
- [x] **Make corpus absence visible to the code — DONE 2026-09-18.**
  `sources.json` entries now carry `corpus_status`
  (`readable`/`present_unreadable`/`absent`) — three states, not a boolean,
  because Jataka Parijata is owned *and* unusable. Guarded by
  `test_every_cited_source_is_actually_in_the_corpus` and
  `test_every_catalogued_source_declares_its_corpus_status` in
  `tests/test_kb_references_integrity.py`. The guard was verified to FAIL by
  re-injecting a phantom citation, not just observed passing.
  ~~Original item:~~ *Missing:*
  `valid_sources()` checks `sources.json` keys only, so a phantom citation
  is indistinguishable from a real one. *AC:* `sources.json` entries carry
  an explicit `in_corpus` (or equivalent) field, a test asserts every
  `references.json` `text_key` resolves to a source marked present, and
  that test fails loudly when a reference cites a book the repo does not
  hold. This is the item that stops this whole class of drift recurring —
  **do it before Phase 2, not after.**

**Phase 2 — acquisitions, highest value first**

Reordered 2026-09-18 by measured OCR rather than assumed availability.

- [ ] **Subject-check every acquisition before ingesting it.** Confirm the
  text is astrology and is the work its title claims — the two highest-scoring
  "Jaimini Sutras" are the Purva Mimamsa sutras. Cheap: sample the OCR and
  compare astrology vocabulary against the wrong subject's vocabulary. Do this
  for every item below, not only the Jaimini one.
- [ ] **BPHS Vol 2** (`pcis_...volume-2...`, 85.3%, **CC-0**) — highest value
  of any acquisition and absent from the first draft of this plan. Makes half
  the backbone text readable (ours is 56.1% and no-text-layer) *and* carries
  the remedial chapters.
- [ ] **Prasna Marga** (`prasna-marga-part-2-by-bv-raman` 91.9%,
  `PrasnaMargaBVR` 89.7%) — `litigation.theft_loss`, and the South Indian
  remedial source. Still in copyright: locate chapters, write our own
  paraphrase.
- [ ] **Sarvartha Chintamani 1899** (Row collection, 90.3%) — education gaps
  plus a catalogue phantom. Score the Row item file-by-file, not as a whole.
- [ ] **Stri Jataka** (Row 1931 87.4%, or `STRIJATAKA` 89.3%) —
  `marriage.second_marriage`.
- [ ] **Jaimini Sutras** (Row 1955, 84.3% — *marginal*) — closes 2 retargeted
  citations and `spirituality.karmic_axis`. Demoted from "highest value": the
  only genuine copies are marginal, and the readable-looking ones are the
  wrong book.
- [ ] **Jataka Parijata 1932** (75.8%, *marginal*) — weigh against re-OCR'ing
  the two copies we already own (Phase 0); 75.8% is a large upgrade on ~25%
  but still under the bar either way.
- [ ] **Saravali, fuller text** (`KalyanaVarmasSaravali_201707`, **94.5%**) —
  reaches **chapter 55** where our copy stops at 26. Added 2026-09-19 after
  the mining pass found our copy is Vol 1 and lacks the bhava chapters.
  Confirm at acquisition that it actually carries them (the 80%-through
  sample showed ch.43-55 but no bhava vocabulary), then it closes
  `family_property.domestic_peace`, `family_property.relocation` and likely
  `education.research`.
- [ ] **Hora Sara** (86.0%), **Jataka Chandrika 1900** (90.5%),
  **Bhavartha Ratnakara** (re-measure first — the 89.0% sample is 13 pages) —
  lower priority; each closes a catalogue phantom.
- [ ] **Decide whether `remedies` becomes a taxonomy domain** before grounding
  any remedial material. `remedies.py` ships with zero KB references behind
  it; BPHS Vol 2 and Prasna Marga would fix that, but where those references
  attach is a design call.
- [ ] **Lal Kitab: closed, not acquirable.** No readable copy exists in any
  edition — see the negative results above. Leave `absent` and leave
  `source_policy.py`'s human-review gate in place.
- [ ] **Run `scripts/audit_kb_sources.py` after every acquisition** and let
  it rewrite `docs/kb_corpus_sources.md`. That file is the source of truth
  and this plan is not.

**Phase 3 — taxonomy honesty**

- [ ] **Mark `marriage.divorce` and `health.mental_health` as
  `answerable: false`, with the reason, in `taxonomy.json`.** Marking, not
  deleting — see Finding 3. *AC:* the coverage metric skips refused
  subdomains, and a test asserts no reference is ever tagged to one, so a
  future mining pass cannot quietly ground a refusal.
- [ ] **Decide `health.hospitalization` first.** It is an inference from the
  medical-verdict ban, not a named refusal like the other two — it either
  joins them or gets grounded under flag-not-verdict framing. A human
  decision, not one to make inside a cleanup pass.

**Phase 4 — prove it changed behaviour**

- [ ] **Live-eval the newly grounded domains.** The only end-to-end check
  this project has ever run (2026-08-12) covered marriage, children and
  career — 3 of 11. *AC:* one live generation per newly grounded domain,
  confirming the new references are actually cited by `ref_id` rather than
  the model falling back on bundle-section names. This also finally
  re-verifies rule 2b, which has been shipped-but-unproven since
  2026-09-08.

### Deliberately not in this plan

- **Verse-pinpoint citations as a blanket goal.** Edition variance is real
  (T0.2 found no undisputed chapter/verse across ~32 rules even when
  looking hard). wisdomlib makes per-sloka addressing *possible* for Brihat
  Jataka and Brihat Samhita specifically; it does not make it possible
  corpus-wide, and the chapter-level `location` convention stays.
- **Bulk-ingesting Tier B prose.** The existing paraphrase-and-cite
  discipline is what keeps modern translations usable at all. Nothing here
  proposes relaxing it.

## Deferred backlog — iPhone widgets (2026-10-17)

- [ ] **WidgetKit widgets, lock-screen circular score and the Rahu Kalam
  Live Activity** (Figma M10: medium widget with the score ring and "Rahu
  Kalam in 2h", lock-screen circular 72, Live Activity "RAHU KALAM Ends in
  38 min"). *Why not built:* a widget extension and an App Group need a paid
  Apple developer team to sign, and Hawk's enrollment is still pending
  (Apple case 102999679854). *Unblocks when:* the Team ID exists. *Hook:*
  the app already publishes the same `today`/`calendar`/`subhashita`/`mantra`
  parts through `WidgetBridgeService` (`ui/src/app/core/widget-bridge.service.ts`);
  an iOS `SiddhaWidgets` plugin writes them to the App Group's
  UserDefaults, a SwiftUI `TimelineProvider` reads them, and the Live
  Activity is started by the app from the `today.windows` entry for Rahu
  Kalam (ActivityKit, `Text(timerInterval:)` for the countdown). Listen
  becomes an App Intent (iOS 17) playing AVSpeechSynthesizer audio.

- [ ] **Listen widget audio without opening the app.** The widget plays
  the overnight natural-voice render, but it reaches the phone only when
  Today opens (`WidgetBridgeService.publishListenAudio`); before that, the
  widget reads with the phone voice. *Why not built:* fetching from the
  widget needs a sign-in the native side doesn't hold, and keeping a
  long-lived token outside the app's auth store is a security decision.
  *Unblocks when:* a narrow, per-device read token for
  `/api/v1/voice/speech` (or a signed URL the worker issues with each
  brief) exists. *Hook:* a WorkManager job after the 22:30 brief, writing
  through `WidgetStore.saveListenAudio`.


## Deferred backlog — Tier 0 audit follow-ups (2026-10-18)

From the Tier 0 fixes for `/mnt/project-files/audits/end-to-end-2026-10-18/findings_ranked.md`.

- [ ] **Shared counter for the generation ceilings.** *Why not built:* a
  Postgres counter needs a new table and migration, and a deploy that runs
  before the migration would break Ask. The in-process version is a hard
  bound per Cloud Run instance. *Unblocks when:* a migration-first deploy
  step exists. *Hook:* `astrospace/ratelimit.py` `take()`; the same
  `ASTROSPACE_LIMIT_*` settings would apply.
- [ ] **Release the DB connection during an on-open brief write** (I4,
  second half). *Why not built:* `_write` saves through the request's
  session, and moving it to `short_session` touches the worker path too.
  *Hook:* `astrospace/context/daily_brief_store.py` `_write` / `_save`, the
  same pattern as `release_connection` in `ask_stream_routes.py`.
- [ ] **Drop kerykeion.** *Why not built:* the legacy LLM routes and their
  agents are gone, but the admin-only web app still reads the kerykeion
  `chart_data` payload stored on each profile (`kundli_routes.py`
  `_with_chart_fields`). *Unblocks when:* the web chart and overview tabs
  read `/vedic` instead. Profile big-three columns are already sidereal.
- [ ] **Erase read-aloud audio and processor logs on account deletion**
  (S12, rest). *Why not built:* the TTS cache in `ASTROSPACE_TTS_BUCKET` is
  keyed by content hash, so one person's files can't be found; the fix is a
  30-day lifecycle rule on the bucket, which is a production change
  (`gsutil lifecycle set`). Resend keeps its own message logs. *Unblocks
  when:* Hawk OKs the bucket rule, and the privacy policy lists each
  processor and its retention. *Hook:* `astrospace/voice/tts.py`;
  RevenueCat deletion is already in `me_routes._delete_store_customer`
  (needs `REVENUECAT_SECRET_API_KEY` set on Cloud Run).
- [ ] **Record the verse sources' licences** (D12). *Why not built:* needs
  the terms of each GitHub, GRETIL and SANSKNET e-text read and written
  down, alongside the scholar review. *Hook:* `docs/subhashita_corpus.md`
  "Before launch"; the push stays off by default until both are done.
- [ ] **Widget picker images for Android 11 and below** (D4, second half).
  *Why not built:* `previewImage` needs a PNG per widget rendered from a
  real device; Android 12+ already uses the `*_preview.xml` layouts with
  sample text. *Hook:* `res/xml/widget_*_info.xml`.
- [ ] **Android 12+ widget polish** (D18): `@android:id/background` on each
  widget root and the system corner radius on API 31+. *Why not built:*
  needs a device to check the launch transition and clipping. The
  monochrome `ic_stat_siddha` part is done. *Hook:* `res/layout/widget_*.xml`,
  `res/drawable/widget_card.xml`.
- [ ] **Keep a failed Ask question in history** (U-ask). *Why not built:*
  the stream deliberately persists nothing when generation or verification
  fails, so a failed turn can't be replayed as if it were an answer. The
  failure copy now says the question is still on screen and that a retry
  doesn't use an answer. *Unblock:* store the question with a
  `status='failed'` row that history shows as "Not answered · Try again"
  and that the replay path skips. *Hook:* `astrospace/api/ask_stream_routes.py`
  failure branch, `ask-answer.component.ts` `failureCopy`.
- [ ] **Server gates for `dashas.full`, `transits.full`, `festivals.full`**
  (I-C2, rest). *Why not built:* the app locks nothing behind these flags
  yet, so a server gate would only hide data the app shows on every plan.
  `vargas.full` is enforced on the server (`vedic_routes._varga_decision`).
  *Unblock:* decide what each flag withholds. *Hook:* `vedic_routes.py`,
  `festival_routes.py`, `entitlements/registry.py`.
- [ ] **Keep unsubscribe tokens and auth codes out of Cloud Run request logs**
  (S16, rest). *Why not built:* needs the unsubscribe link moved to a path
  or POST body with old links still honoured, plus a log exclusion set in
  the GCP console. Crash stacks are scrubbed and usage sharing is now
  opt-in. *Hook:* `email_routes.py` unsubscribe, `audit_middleware.py`.
- [ ] **Listen and mantra Auto as native audio** (N5, D10). *Why not built:*
  both play through WebView `<audio>` and speech, so there are no lock-screen
  or Bluetooth controls, no audio focus (they play over calls and music), and
  playback stops when the WebView is suspended. The screen now stays awake
  while either plays (`core/screen-awake.ts`, Screen Wake Lock API), which
  covers the common case of the screen timing out mid-chant. *Unblock:* a
  small Capacitor plugin around Media3 `MediaSessionService` on Android and
  `AVAudioSession` + Now Playing on iOS, checked on a device with the N5
  items of the nativeness audit's on-device checklist. *Hook:*
  `today/listen-sheet.component.ts` `new Audio()`,
  `remedies/mantra-tracker.component.ts` `toggleListen`.
- [ ] **Daily-brief worker throughput: parallel writes and sharding** (I5,
  rest). *Why not built:* briefs are written one at a time, about 25-40 per
  15-minute run, so roughly 150-240 land between 22:30 and midnight. That is
  ample for today's readers. Each run now writes today's briefs before
  anyone's tomorrow and starts at a different reader, so a short budget no
  longer starves the same people. *Unblock:* past about 200 active profiles,
  write with a bounded pool of 4-8 threads, each on its own session; skip
  profiles that already have a brief for the date with one anti-join on
  `daily_guidance_cache` before computing the payload; then shard by
  `CLOUD_RUN_TASK_INDEX`. *Hook:* `notifications/daily_briefs.py`
  `schedule_daily_briefs`.
- [ ] **Sankashti Chaturthi on the Calendar** (U7, rest). *Why not built:*
  it is the Krishna Chaturthi that holds at moonrise, and the year scan
  takes tithis only at sunrise, sunset and the middle of the night.
  Ekadashi, Purnima, Amavasya and Pradosham are on the Calendar
  (`festivals.vrat_days`). *Unblock:* add the tithi at moonrise to
  `_day_facts` from `moontimes`, then a `("sankashti", "Krishna", 4,
  "moonrise")` row with its own note. *Hook:* `core/vedic/festivals.py`
  `_day_facts`, `vrat_days`.
- [ ] **Notes as a synced, dated journal** (U22, rest). *Why not built:*
  it needs a table, CRUD routes, export and deletion coverage, and
  conflict handling for two phones. That is a feature, not an audit fix.
  Notes are now one per profile, on the phone, with input aids on, and
  the copy says they aren't backed up. *Unblock:* a `notes` table
  (user_id, kundli_id, created_at, body), with routes under `/me/notes`.
  Add it to `/me/export` and to account deletion, then move each
  `astrospace.mobile.notes.draft.<profile>` into it on first open.
  *Hook:* `ui/src/app/features/mobile/notes/notes.component.ts`.

## Deferred backlog — Tier 2 audit follow-ups (2026-10-18)

From the end-to-end audit (2026-10-18). Each needs a device, a new
dependency, or is a project rather than a fix. Rechecked 2026-10-21: the
items marked done shipped in the two "Audit follow-ups" batches (#229 and
the batch after it).

- [x] **Worker and Ask layering** (I8), first half. Today's payload and its
  cache are `context/daily_service.py`, the timing-place rule is
  `context/timing_place.py`; both raise domain errors the routers map to 422,
  and no notification job imports `api/` (`tests/test_daily_service_layering.py`).
- [x] **One orchestrator-owned function for Ask's terminal texts** (I8, rest).
  `terminal_turn()` in `agents/orchestrator.py` gives both Ask routes the
  same text for refer-out, validation, clarification, missing context and
  not-ready domains (`tests/test_ask_terminal_turn.py`).
- [x] **Environment check at boot** (I9), warn-only half. `astrospace/config.py`
  lists the variables and logs a warning for a flag that means the opposite
  of what it says (`ASTROSPACE_QUOTAS_ENFORCED=on` is off), a bad number or
  email list, or a missing database or key on Cloud Run. Never raises.
- [x] **One rule per flag** (I9, part of the rest). Every on/off and
  whole-number variable in `VARS` is read through `config.flag()` /
  `config.integer()`; a test fails if a module reads one directly.
- [ ] **Fail fast on a bad environment** (I9, rest). *Why not built:* the
  boot check is still warn-only. *Unblock:* one deploy whose logs show no
  `config:` warnings; then let `check_environment()` refuse to boot, move
  the text keys onto the same table, and stop `load_dotenv()` per agent
  (`agents/base.py`; `cli.py` and `main.py` already load it).
- [x] **Postgres and Docker in CI** (I12). The `postgres-migrations` job
  builds a pgvector Postgres from `scripts/ci/supabase_shim.sql`, the base
  schema and every migration, then `scripts/check_schema_drift.py` checks
  every model table and column exists and every public table has RLS on.
  The `docker` job builds the Cloud Run image and checks it boots.
- [x] **App/server contract check** (I12, rest). `tests/test_frontend_contract.py`
  reads the interfaces in `ui/src/app/core/models.ts` and checks real
  responses from eight routes against them. It found Indu Lagna typed as
  the wrong shape (shown as "Leo undefined"), now fixed. Add a route to
  `ROUTES` when a screen starts reading it.
- [ ] **A real-model prompt set in CI** (I12, rest). *Why not built:* needs
  a model key in CI and a budget. *Hook:* `.github/workflows/ci.yml`.
- [x] **UI translation groundwork** (I13). `core/i18n/`: an English
  dictionary, a `t` pipe and `I18nService`; the tab bar and offline banner
  read from it. No library, no language switch shown.
- [ ] **Telugu UI** (I13, rest). *Why not built:* a Telugu table written by
  machine would read badly; about 120 components still hold English
  strings. *Unblock:* a native Telugu reader to write and check `te.ts`;
  then move screens onto keys, Today first, and add 'te' to
  `UI_LANGUAGES`. *Hook:* `ui/src/app/core/i18n/`.
- [ ] **iOS edge-swipe back** (N2). *Why not built:* needs a
  `CAPBridgeViewController` subclass and iPhone testing; the iOS build waits
  on Apple enrollment. *Unblock:* set `allowsBackForwardNavigationGestures`,
  disabled on `/m/today`. *Hook:* `ui/ios/App/App/Base.lproj/Main.storyboard`.
- [x] **Pull to refresh** (N13) on Today, Calendar and the Calendar day:
  `shell/pull-refresh.directive.ts`, screens register in
  `core/pull-refresh.service.ts`. *Still to do:* tune the resistance on a
  phone; add other screens by registering their reload.
- [ ] **iOS Dynamic Type, WKWebView config, native Apple sign-in, push
  presentation** (N15, N19, N20, N26). *Why not built:* each needs an
  iPhone build and new plugins (`@capacitor/text-zoom`,
  `@capacitor-community/apple-sign-in`). *Hook:* `capacitor.config.ts` `ios`,
  `core/auth.service.ts`.
- [x] **Verified App Links** (N17), Android: `assetlinks.json` with both
  signing keys and the `autoVerify` filter for `https://asksiddha.app/m/*`
  (#203).
- [ ] **Universal Links** (N17, iOS). *Why not built:* needs the Apple Team
  ID for the AASA file. *Hook:* `firebase-public/.well-known/`.
- [x] **App shortcuts** (N24), Android: long-press the icon for Ask, Calendar,
  Today (`res/xml/shortcuts.xml`), through the App Links route allowlist.
  *Still to do:* check on a phone.
- [x] **Native add-to-calendar, in-app review** (N18, N23), Android.
  `NativeCalendarPlugin` opens the phone's calendar with the event filled
  in (Google Calendar link as fallback); `InAppReviewPlugin` uses Play's
  review sheet, asked by `core/rating-prompt.service.ts` only after 5
  active days and 3 good moments, at most once in 120 days. *Still to do:*
  check both on a phone; iOS versions wait on the Apple build.
- [ ] **System splash icon** (N21). *Why not built:* the blank system
  splash is deliberate: the web intro (#173, #175) takes over at once in
  the same colour, and an icon would show two splashes. Revisit only if
  the hand-off is slowed.
- [ ] **Notification actions** (N12, rest). *Why not built:* pushes are
  sent as FCM notification messages, which Android draws itself, so they
  cannot carry action buttons. A "Listen" button means sending data-only
  messages and drawing them in a custom `FirebaseMessagingService`, which
  replaces how every push is shown. *Unblock:* decide that is worth it;
  then add the service and an action receiver. *Hook:*
  `astrospace/notifications/`, `ui/android/app/src/main/`. Window alerts
  already have their own channel.
- [x] **Conventions and Festival calendar controls** (U30). Chart method
  is one-choice groups with round marks, a plain note per choice and the
  default marked; Festivals to show is ticked rows, at least one kept.


## Deferred backlog — place search, remaining coverage (2026-10-21)

Built 2026-10-21: every GeoNames place of 500+ people in the rest of India,
the US, Canada, the UK, Ireland, the Gulf, Singapore, Malaysia, Australia,
New Zealand and Europe (124k rows, `data/world_places.json.gz`, 2.7 MB; about
+105 MB server memory once loaded, ~30-45 ms per search, first search loads
the file in ~2 s).

- [ ] **Village-level India beyond AP/Telangana.** Outside AP/TS, India has
  only cities500 (~6.5k places), because GeoNames leaves most Indian villages
  without a population. *Why not built:* the full `IN.txt` dump is needed and
  download.geonames.org is blocked from the cloud containers. *Unblocks
  when:* `IN.zip` and `admin2Codes.txt` are downloaded on the Mac. *Hook:*
  add admin1 codes to `STATES` in `scripts/build_state_places.py` (labels
  come from `_STATE_NAMES` in `core/cities.py`); watch memory, every state
  is ~15-20k rows.
- [ ] **The rest of the world** (Nepal, Sri Lanka, Bangladesh, Pakistan,
  Africa, the Caribbean, East Asia, the Americas). *Why not built:* not in
  the diaspora-first list. *Hook:* add codes to `COUNTRIES` in
  `scripts/build_world_places.py` (region-name fixes in
  `_REGION_OVERRIDES`) and rebuild; past ~250k rows the linear search scan
  wants a prefix index.
- [ ] **Local-language spellings** (München, Köln). Only GeoNames' main
  name is indexed, because its alternate names are noisy for these
  countries (abbreviations, other places' names). *Hook:* a vetted alias
  list per country in the builder.

## Deferred backlog — festival guidance follow-ups (2026-10-20)

Every festival and vrat kind now carries short to-dos and prayer names
(`core/vedic/festival_guidance.py`). Left out on purpose:

- [ ] **Festivals the Calendar does not list.** Sankashti Chaturthi (monthly,
  Krishna Chaturthi at moonrise), Masik Shivaratri, Bonalu (Telangana, Sundays
  of Ashada), Bengal's Durga Puja days (Shashthi to Dashami), Vat Purnima as
  its own row, Telugu Hanuman Jayanti (Vaishakha Krishna Dashami), Sindhi
  Cheti Chand. *Why not built:* each needs a date rule and an anchor test
  against a published panchangam, and Bonalu and Sankashti need rule types
  the engine lacks (weekday-in-lunar-month; tithi at moonrise). *Unblocks
  when:* one panchangam per region is chosen as the check. *Hook:* `FESTIVALS`
  in `core/vedic/festivals.py` plus a matching `_g(...)` entry; the guidance
  test fails until both exist.
- [ ] **Open a corpus mantra from the festival sheet.** Names that carry a
  `corpus_id` have text, meaning and sometimes audio in
  `mantra_corpus/mantras.json`, but the mantra screen only opens from a
  profile's remedy plan (`/m/remedies/mantra?recommendation=…`). *Why not
  built:* the screen is keyed to a recommendation group and its streak, not
  to a bare mantra. *Unblocks when:* a read-only "mantra by id" view is
  agreed. *Hook:* `mantraFor` in `ui/.../calendar/festival-sheet.component.ts`.
- [ ] **Telugu and Hindi copy.** The guidance is English only; the sheet shows
  it in every language. *Hook:* add per-language lists beside each entry.

## Deferred backlog — festival day rules (2026-10-20)

Vijayadashami 2026 showed on the 21st while India kept the 20th: the engine
took the tithi at sunrise for festivals fixed by a daytime window. Fixed with
`madhyahna` / `aparahna` window rules (Vijayadashami with the Shravana
tie-break, Ganesh Chaturthi, Rama Navami), pradosh for Dhanteras and Holika
Dahan, Holi as the day after Holika Dahan, and one date per vriddhi run.
Anchored against published New Delhi dates 2022-2026 in
`tests/test_festivals.py::TestKalaRules`. Left out on purpose:

- [ ] **Holika Dahan's Bhadra and second-day rules.** When Bhadra covers the
  first evening, or Purnima runs three prahars into the second day without
  reaching dusk, some panchangams move the fire (2026: 2 vs 3 March). *Why not
  built:* needs karana (Bhadra = Vishti) timing in the day scan and a choice
  of authority. *Hook:* `holika_dahan` rule in `core/vedic/festivals.py`.
- [ ] **Janmashtami by nishita and Rohini.** Still the Ashtami at sunrise;
  correct for 2024-2026 but the Smarta date differs in years like 2023 (6 vs 7
  Sep). *Why not built:* Smarta and Vaishnava (ISKCON) dates genuinely
  differ; the note says so. *Unblocks when:* we pick one or show both.
  *Hook:* `krishna_janmashtami`; a `nishita` window like `_KALA_WINDOWS`.
- [ ] **Pradosh as a window, not the sunset instant.** Diwali and Dhanteras
  test the tithi at sunset only; the classical pradosh is about 2 h 24 min
  after sunset, with "covers more of pradosh" tie-breaks when Amavasya holds
  at dusk on both days (2024, 2025). The first day is kept, which matched
  most of India both years. *Hook:* `_day_facts` / `_KALA_WINDOWS`.
- [ ] **Choti Diwali when Chaturdashi and Amavasya share a day** (2026: 8
  Nov). Naraka Chaturdashi follows Chaturdashi at dawn, as the south keeps it;
  North Indian calendars often list Choti Diwali on the day before. *Hook:*
  `naraka_chaturdashi`.
- [ ] **Durga Ashtami and Maha Navami** still use sunrise; Bengal reckons
  Sandhi Puja and Navami by the tithi's span. Not seen wrong for 2026.

## Deferred backlog — Muhurta (2026-10-20)

From the Muhurta audit (batches A–E built; these were left out on purpose).

- [x] **Read the phone's location for timings.** Built 2026-10-21: "Use my
  location" in the shared city picker (onboarding and the Muhurta screen's
  "Where will it happen?"). Approximate only (Android declares
  `ACCESS_COARSE_LOCATION` and nothing finer; iOS
  `NSLocationDefaultAccuracyReduced`), read once on tap, rounded to ~1 km,
  turned into a city by `POST /api/v1/panchanga/cities/nearest`
  (`core/cities.nearest_city`) and not stored. Settings › Location does not
  offer it yet. Store forms: approximate location, processed ephemerally.
- [x] **Goal rules checked against Muhurta Chintamani.** The per-goal weekday,
  nakshatra and tithi lists in `astrospace/core/vedic/muhurta.py` (`GOALS`)
  follow common panchang practice, not a page-cited text. Unblock: a
  machine-readable Muhurta Chintamani (none in the KB yet; check
  `docs/kb_corpus_sources.md`). Hook: add a `source` field per goal.
  *Found 2026-10-21:* a public-domain print exists, Muhurta Chintamani with
  Mahidhara Sharma's Hindi tika, Khemraj Krishnadas (Venkateshwar Press),
  Samvat 1964 / 1907, CC0 scan at archive.org
  `MuhurtaChintamaniVenkateshwarPress1906ShriKrishnaMuseumKurukshetra`. Its
  OCR text layer is garbled, so it must be read as page images like the other
  image-only books. Cloud threads cannot reach archive.org (network policy);
  the PDF (133 MB) has to come in through the Mac or an allowed domain.
  *Built 2026-10-21:* read from the page images; 15 goals now follow and cite
  their verses (`source`, returned as `rules_source`), with `shun_vara`
  (weekdays the book rules out, marked down, not dropped) and `avoid_lagna`
  (Aquarius for a shop). Then wedding (6.13, 6.53), engagement (6.10-6.11)
  and contract (2.42, the alliance verse, the nearest rule the book has).
  Still on common practice because the book has no rule for them: property
  purchase and registration, sadhana. Verses read are listed in
  `docs/kb_corpus_sources.md`. Not expressible yet: upanayana's "first third
  of the dark half" and the journey's "bright first" (tithi sets are 1-15
  without a paksha).
- [x] **Sarvartha Siddhi and Amrit Siddhi by full table.** Only Amrit Siddhi
  (weekday + nakshatra pairs), Guru/Ravi Pushya and Dwi/Tripushkar are marked
  (`_special_days`). Sarvartha Siddhi has regional tables that disagree.
  Unblock: pick one printed table and cite it. Hook: `_special_days`.
  The 1907 Muhurta Chintamani print above is the candidate table; same
  blocker.
  *Built 2026-10-21:* Sarvartha Siddhi from verse 1.28-29 (the Hindi
  commentary differs on Friday and is garbled on Wednesday; the verse is
  followed), shown only when no stronger special day applies. Amrit Siddhi's
  Monday takes Shravana (the print's table) or Mrigashira (most panchangs).
- [x] **A tester teaser for the longer search range.** Testers search 14 days
  and get no "next good time" beyond it. Showing a locked hint was not built
  because the tester access matrix is frozen
  (`/mnt/project-files/plans/access_matrix_2026-10-20.md`). Unblock: Hawk's OK.
  Hook: `look_ahead_days` in `astrospace/api/muhurta_routes.py`.
  *Built 2026-10-21 (Hawk chose "Add the locked hint"):* a capped plan gets
  `locked_next` (date and quality, never the time) for the first good date
  in the 60 days past its horizon, shown as a Plus lock card on results.
