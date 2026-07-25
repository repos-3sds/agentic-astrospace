# Epic F — Chart & Practitioner Depth

**Goal:** Serve the expert (Anand) a genuine workbench and give the believer→learner
growth path — all over the same route tree. Depth is opt-in via mode; nothing here forces
a Guided user to navigate an astrologer's tools.

**Screens:** Chart (S/N/E) · Planet detail · Divisional charts · Dashas · Ashtakavarga ·
Shadbala · Jaimini · Provenance panel · Learning sheet · Notes.

---

### F1 · Chart render (3 styles) + interaction
**Story:** As a **practitioner (A)**, I want my chart in my preferred style with native zoom and tap-to-inspect, so that I can read it comfortably on a phone.
**Personas:** A, R · **Mode:** Pr, B · **Priority:** P0 · **Feasibility:** ✅ (S/N/E rendered)

**Acceptance criteria**
- GIVEN a profile, WHEN the chart opens, THEN it renders in the chosen style (South/North/East) and can be switched in one tap.
- GIVEN the chart, WHEN pinch-zoomed, THEN it scales crisply (vector) without horizontal-scroll of the page.
- GIVEN a planet/house is tapped, WHEN selected, THEN a detail sheet shows sign, nakshatra + pada, dignity, retrograde/combustion, and lordships.
- GIVEN a small screen, WHEN the chart renders, THEN it is never a shrunk desktop table (anti-pattern) — it is a native, legible chart.

---

### F2 · Collapse the plain layer (practitioner depth)
**Story:** As a **practitioner (A)**, I want to skip the plain summaries and go straight to tools, so that I'm not slowed down by beginner content.
**Personas:** A · **Mode:** Pr · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN Practitioner mode, WHEN a surface has both a plain layer and technical depth, THEN the plain layer can be collapsed by default per the mode's disclosure setting.
- GIVEN a collapsed plain layer, WHEN the practitioner wants it, THEN it can be re-expanded (nothing is removed, only prioritized).
- GIVEN a Guided user, WHEN the same surface loads, THEN the plain layer is primary and technical depth is collapsed.

---

### F3 · Provenance panel
**Story:** As a **practitioner (A) or skeptic (R)**, I want to see exactly how a chart was computed, so that I can trust and reproduce it.
**Personas:** A, R · **Mode:** Pr, B · **Priority:** P1 · **Feasibility:** ✅ (engine emits all of it)

**Acceptance criteria**
- GIVEN any chart/reading, WHEN the provenance panel is opened, THEN it shows ayanamsha, node type, house system, calculation place, and confidence flags.
- GIVEN a convention-dependent output, WHEN shown, THEN it is flagged (`convention_dependent`/`VERIFY`).
- GIVEN an approximate birth time (A4), WHEN provenance is shown, THEN reduced confidence is stated explicitly.

---

### F4 · Divisional (varga) charts
**Story:** As a **practitioner (A)**, I want D1–D60 divisional charts, so that I can analyze specific life areas.
**Personas:** A · **Mode:** Pr · **Priority:** P1 · **Feasibility:** ✅ (20 vargas, vargottama)

**Acceptance criteria**
- GIVEN a profile, WHEN varga charts open, THEN D1–D60 (the supported set) are selectable, each rendered in the chosen style with placements.
- GIVEN a varga, WHEN shown, THEN vargottama and relevant dignities are indicated.
- GIVEN navigation, WHEN switching vargas, THEN it is fast and remembers the selected style.

---

### F5 · Dashas (5-level)
**Story:** As a **practitioner (A)**, I want the full Vimshottari tree, so that I can trace timing precisely; and as a **Guided user**, I want it labelled "Life Periods" so it's not opaque.
**Personas:** A (depth), L/R (labels) · **Mode:** Pr / adaptive label · **Priority:** P1 · **Feasibility:** ✅ (5 levels + Yogini)

**Acceptance criteria**
- GIVEN a profile, WHEN dashas open, THEN maha→antar→pratyantar→sukshma→prana are navigable, plus Yogini dasha.
- GIVEN Guided/Balanced mode, WHEN the nav label renders, THEN it reads "Life Periods" (adaptive label), while the route stays stable.
- GIVEN a period, WHEN selected, THEN the active/current period is highlighted and can feed Ask/Today context.

---

### F6 · Strength & advanced (Ashtakavarga, Shadbala, Jaimini)
**Story:** As a **practitioner (A)**, I want Ashtakavarga, Shadbala, and Jaimini tools, so that I can do rigorous analysis.
**Personas:** A · **Mode:** Pr · **Priority:** P2 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN Practitioner mode, WHEN advanced tools open, THEN Ashtakavarga (BAV/SAV, shodhana, pinda, kakshya), Shadbala (v1 + BPHS virupa), and Jaimini (chara karakas, arudha padas, special lagnas) are available.
- GIVEN these surfaces on mobile, WHEN rendered, THEN dense tables reflow to native layouts (no horizontal page scroll).
- GIVEN a Common user, WHEN they never opt into Practitioner, THEN these surfaces are de-prioritized in nav (not the front door).

---

### F7 · Learning layer
**Story:** As a **learner/skeptic (A, R) or a believer becoming curious**, I want to tap a yoga or term and see the classical rule, verse, and a worked example, so that I understand *why*.
**Personas:** A, R, and believer→learner growth · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a yoga/dosha/term anywhere in the app, WHEN tapped, THEN a learning sheet shows a plain definition, the classical rule/source, and a worked example from the user's own chart where possible.
- GIVEN the learning sheet, WHEN opened from a "Why this?" (Epic J), THEN it deep-links to the exact concept behind that reading.
- GIVEN Guided mode, WHEN a term appears in plain copy, THEN tapping it is optional and non-intrusive (the growth loop, not a requirement).

---

### F8 · Notes
**Story:** As a **practitioner (A)**, I want to keep notes on a profile, so that I can record observations across sessions.
**Personas:** A, S · **Mode:** Pr · **Priority:** P2 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN a profile, WHEN notes are opened, THEN free-text notes can be added, edited, and are saved to the profile.
- GIVEN notes exist, WHEN the profile is exported/shared (Epic B/K), THEN the user controls whether notes are included.
- GIVEN sync, WHEN signed in, THEN notes are available across the user's devices.
