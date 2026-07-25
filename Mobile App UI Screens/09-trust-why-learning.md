# Epic J — Trust & the "Why"

**Goal:** Live the brand — *"Vedic astrology, computed."* Every plain statement can show
its work; that same affordance is the believer→learner growth loop and the skeptic's
conversion path. Never fabricate; label tradition as tradition.

**Screens:** "Why this reading?" sheet · Computed badge / provenance · Universal-vs-personal
labels · Convention-dependent tags.

---

### J1 · "Why this reading?" everywhere
**Story:** As a **skeptic (R) or curious believer (L)**, I want to reveal the evidence behind any statement, so that I can trust it and learn.
**Personas:** R, L, A, S · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅ (`plain_why` + `technical_why` exist)

**Acceptance criteria**
- GIVEN any plain statement (Today, Ask answer, reading), WHEN it renders, THEN a **[Why this?]** affordance is present.
- GIVEN **[Why this?]** is tapped, WHEN expanded, THEN it reveals the computed evidence: relevant houses, karakas, yogas, active dasha chain, current gochara, and rule sources.
- GIVEN Guided mode, WHEN "Why" shows, THEN it leads with `plain_why`; GIVEN Practitioner mode, THEN `technical_why` and provenance are surfaced.
- GIVEN a term in the evidence, WHEN tapped, THEN it links to the learning layer (Epic F7).
- **Constraint:** if a statement cannot be traced to a calculation, it is not shown (never fabricate).

---

### J2 · Computed badge / calculation trail
**Story:** As a **skeptic (R) or practitioner (A)**, I want a visible sign that readings are computed, so that I distinguish this from generic horoscope apps.
**Personas:** R, A · **Mode:** B, Pr · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN a reading, WHEN shown, THEN a **Computed** badge is available that opens the calculation trail (ephemeris basis, ayanamsha, node type, house system, place, confidence).
- GIVEN a disputed convention, WHEN present, THEN the trail states which convention was used and that alternatives exist.
- GIVEN a low-confidence input (unknown time), WHEN shown, THEN the badge reflects reduced confidence.

---

### J3 · Universal vs. personal distinction
**Story:** As a **user**, I want to know when something applies to everyone vs. to me specifically, so that I'm not misled.
**Personas:** all · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN a universal value (e.g., "number of the day"), WHEN shown, THEN wording marks it as universal.
- GIVEN a personal value (e.g., "your lucky number"), WHEN shown, THEN wording marks it as personal to the profile.
- GIVEN both on one screen (Epic C4), WHEN displayed, THEN they are visually and textually separated.

---

### J4 · Honest labelling of tradition vs. fact
**Story:** As a **careful user (R, M, A)**, I want convention-dependent content labelled as tradition, so that I can weigh it honestly.
**Personas:** R, M, A · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅ (engine flags `convention_dependent`/`VERIFY`)

**Acceptance criteria**
- GIVEN convention-dependent numerology/remedies, WHEN shown, THEN they are labelled as tradition, not deterministic fact.
- GIVEN grounded reassurance, WHEN copy is written, THEN it is warm and practical — never flattery ("everything is amazing") and never doom.
- GIVEN a `VERIFY`/`convention_dependent` flag from the engine, WHEN present, THEN the UI surfaces the caveat rather than hiding it.
