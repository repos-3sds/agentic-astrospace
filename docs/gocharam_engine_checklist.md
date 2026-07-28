# Gocharam Engine and Interpretation Checklist

## Goal

Deliver one deterministic South Indian Gocharam system that calculates once, explains the result by life domain, and supplies the same evidence to Gocharam, Transits, Calendar, Dashas, Dashboard, CE, and Ask AI.

## Definition of Done

- One canonical calculation module owns transit snapshots, Moon/Lagna houses, named rules, Vedha, Ashtakavarga weighting, and rule timelines.
- Every interpretation identifies its computed evidence, timing, modifiers, convention, and content-library version.
- The non-AI report provides explanatory paragraphs for major life domains and planets.
- LLM or agent layers may explain canonical evidence but cannot recalculate or silently replace it.
- Existing API response fields remain compatible while consumers migrate to the versioned contract.
- Automated tests prove rule consistency across entry points.

## Epic 1: Canonical Calculation Authority

### US-GOC-001 - Single calculation source

As a user, I want every screen to show the same Gocharam result so that I can trust the software.

Acceptance criteria:

- [x] `astrospace/core/vedic/gocharam/` is the canonical engine.
- [x] `vedic/transits.py` delegates its public `gochara_rules` entry point to the canonical engine.
- [x] `VedicChart.transit_context()` consumes the canonical planet and Sade Sati result.
- [x] Daily CE imports canonical `gochara_rules`.
- [x] Calendar and Transits reuse the canonical profile.
- [ ] Remove deprecated private duplicate helpers from `vedic/transits.py` after downstream compatibility monitoring.
- [ ] Add a runtime deprecation warning if an external caller uses a removed private helper.

### US-GOC-002 - Versioned result contract

As a developer, I want a stable evidence contract so that UI, CE, and agents cannot interpret different shapes.

Acceptance criteria:

- [x] Profile includes `schema_version` and `engine_version`.
- [x] Interpretation includes schema and content-library versions.
- [x] Computed evidence and authored interpretation provenance are separated.
- [x] Existing fields remain available during migration.
- [ ] Add JSON Schema/OpenAPI examples for the complete profile response.

## Epic 2: Classical Rules and Modifiers

### US-GOC-003 - Moon-first rules with Lagna cross-check

Acceptance criteria:

- [x] Every planet includes houses from natal Moon and Lagna.
- [x] Sade Sati, Ashtama Shani, Kantaka Shani, Guru Bala, node cautions, and Mars triggers use named rule IDs.
- [x] Moon-first and Lagna-cross-check methodology is visible in provenance.
- [x] All nine planets have one baseline record for every Moon house (108 unique placements).
- [x] Baseline verdicts and special named overlays are separate rule kinds.
- [ ] Externally review the rule catalogue against the preferred South Indian textual authority.

### US-GOC-004 - Vedha

Acceptance criteria:

- [x] Classical favourable houses and Vedha-sthana are calculated per planet.
- [x] Sun-Saturn and Moon-Mercury exceptions are tested.
- [x] Rahu/Ketu use is marked convention-dependent.
- [ ] Attach exact edition/chapter/verse references selected by the astrology reviewer.

### US-GOC-005 - Ashtakavarga and Kakshya

Acceptance criteria:

- [x] BAV, SAV, kakshya lord, and bindu-given state are calculated once in the canonical profile.
- [x] AV changes effective emphasis without changing rule activation.
- [x] Transits reuses canonical AV output.
- [ ] Validate configured BAV/SAV interpretation thresholds with the selected source tradition.

### US-GOC-006 - Retrograde and repeated passes

Acceptance criteria:

- [x] Current retrograde state is included in planet evidence and prose.
- [ ] Calculate exact direct/retrograde station timestamps.
- [ ] Group first entry, retrograde return, and final exit into one multi-pass transit cycle.
- [ ] Show each pass and its exact date range in the UI.

### US-GOC-007 - Dasha alignment

Acceptance criteria:

- [x] Dedicated Gocharam and Transits calls supply the active Dasha stack.
- [x] Calendar supplies the Dasha stack already calculated for its selected date.
- [x] Domain readings identify direct Dasha-lord repetition.
- [ ] Add house ownership and natal dignity of active Dasha lords to the weighting model.

## Epic 3: Deterministic Interpretation

### US-GOC-008 - Domain-wise explanations

As a user, I want substantial explanations for different parts of life instead of generic labels.

Acceptance criteria:

- [x] Career and work reading.
- [x] Money and resources reading.
- [x] Relationships and family reading.
- [x] Health and energy reading with a non-diagnostic boundary.
- [x] Learning, travel, and growth reading.
- [x] Inner life and emotional balance reading.
- [x] Every domain contains main theme, rationale, plain reading, strengths, challenges, actions, timing, and leading planets.
- [x] Every domain reading is generated without an LLM.
- [x] V3 exposes six evidence-backed domain projections from the same placement and modifier witnesses used by the planet explorer.
- [x] Web and native Gocharam surfaces render the domain projection rather than reconstructing it locally.
- [ ] Astrology reviewer approves the authored English clause library.

### US-GOC-009 - Planet-wise explanations

Acceptance criteria:

- [x] All nine transit planets receive an explanatory reading.
- [x] Each reading identifies sign, Moon house, Lagna house, classical status, AV evidence where available, retrograde state, and active named rules.
- [ ] Add planet-sign nuance only after source-backed content review.
- [ ] Add exact natal house lordship and transit aspects to planet readings.

### US-GOC-010 - Contradiction handling

Acceptance criteria:

- [x] Supportive, challenging, obstructed, and mixed states remain distinct.
- [x] Interpretations state that results are combinations rather than binary labels.
- [x] Balance score is labelled as emphasis, not probability.
- [x] Vedha, BAV/SAV, retrograde motion, exact natal contacts, Dasha concordance, and timing are retained as separate evidence-bearing modifiers.
- [x] Base and effective verdicts are both retained; modifiers do not overwrite the base text.
- [ ] Add a formal conflict matrix for Dasha, Gocharam, AV, and natal-promise disagreements.
- [ ] Surface the strongest supporting and contradicting witness separately.

### US-GOC-011 - Source and content governance

Acceptance criteria:

- [x] Interpretation provenance distinguishes a classical verdict from editorial synthesis.
- [x] Calculation evidence retains classical versus convention-dependent status.
- [x] Store interpretation clauses as versioned KB records with source and claim status.
- [x] Rahu/Ketu treatment is explicitly labelled as a configured convention rather than attributed to Phaladeepika.
- [ ] Require reviewer, source reference, language, status, and effective version before publication.
- [ ] Add admin preview, diff, approval, rollback, and audit log for Gocharam content.

## Epic 4: Timing and Validation

### US-GOC-012 - Previous, current, and next

Acceptance criteria:

- [x] Active windows have start and end dates.
- [x] Previous and next named-rule transitions are available.
- [x] Domain readings filter timing to relevant planets.
- [x] UI retains active/next/earlier validation views.
- [x] Every requested 30/90/365/1095-day horizon returns its own event count, first/last change, previous count, highlights, and stable-window wording.
- [x] Domain outlooks filter range events to planets relevant to that domain.
- [ ] Replace daily stepping with exact ingress/root-finding for production-grade boundaries.
- [ ] Add timezone-aware display and local-date boundary tests.

### US-GOC-013 - User validation

Acceptance criteria:

- [x] Existing period text includes a validation prompt.
- [ ] Let users rate a Gocharam period as accurate, partly accurate, missed, or not applicable.
- [ ] Save domain-specific feedback and notes in Supabase.
- [ ] Show accuracy by rule, planet, domain, and engine/content version.

## Epic 5: Product Surfaces

### US-GOC-014 - Dedicated Gocharam explorer

Acceptance criteria:

- [x] Dedicated page shows comprehensive domain tabs.
- [x] Domain view shows rationale separately from plain-language reading.
- [x] Strengths, cautions, practical focus, timing, leading factors, and Dasha alignment are visible.
- [x] Existing period and validation timeline remain available.
- [ ] Add planet explorer subtab.
- [ ] Add chart and timeline synchronization.
- [ ] Add print/PDF report layout.
- [x] Web explorer separates nine current placements from named special overlays.
- [x] Web explorer exposes modifier, source, convention, and claim provenance.

### US-GOC-015 - Shared consumers

Acceptance criteria:

- [x] Transits receives canonical Gocharam and AV data.
- [x] Calendar receives canonical Gocharam with Dasha context.
- [x] Dasha transit context uses canonical planet snapshots and Sade Sati.
- [x] CE and Daily guidance consume canonical rules.
- [x] Native Gochara and Full Transits screens consume the live versioned Gocharam profile.
- [x] Native copy adapts to Guided, Balanced, and Practitioner presentation modes.
- [ ] Dashboard consumes a compact canonical domain projection.
- [ ] Ask AI cites canonical evidence IDs and content sources.

## Epic 6: Validation and Operations

### US-GOC-016 - Automated verification

Acceptance criteria:

- [x] Vedha, exemptions, nodes, AV thresholds, and Kakshya boundaries have tests.
- [x] Existing Gocharam, Transit, Calendar, CE, and Daily tests remain green.
- [x] Domain interpretation contract and minimum explanatory depth have tests.
- [x] Compatibility entry point is tested against the canonical engine.
- [x] Exhaustive test proves exactly one baseline record for every planet-house pair.
- [x] Live API verification asserts nine placement matches and evidence-bearing modifiers.
- [ ] Add golden charts approved by an astrologer.
- [ ] Add exact station/ingress fixtures and timezone boundary cases.
- [ ] Add performance budgets and persisted daily cache.

## External Review Inputs Needed

- [ ] Preferred authority order for Gocharam and Vedha.
- [ ] Exact editions and page/chapter/verse references.
- [ ] Approved treatment of Rahu and Ketu in classical favourable-house/Vedha tables.
- [ ] Approved BAV/SAV thresholds and Kakshya interpretive use.
- [ ] Approved role of Lagna versus Moon in final weighting.
- [ ] Ten reference profiles with expected Saturn/Jupiter periods and outcomes.
- [ ] Review and approval of English domain interpretation clauses.
- [ ] Translation glossary before Telugu or other regional-language generation.
