# Epic D — Ask (Question-first front door)

**Goal:** Match the believer's mental model — a *question* — by wiring the Context Engine
to a conversational surface. Verdict → what to do → why → follow-up. Never a wall of text.

**Screens:** Ask (text) · Ask (voice) · Suggested chips · Answer view · Ask-a-date ·
Follow-up thread.

---

### D1 · Ask by text
**Story:** As a **believer (L, R, S, M)**, I want to type a real-life question and get a computed, plain answer, so that the app feels like asking a knowledgeable friend.
**Personas:** L, R, S, M · **Mode:** G, B · **Priority:** P0 · **Feasibility:** 🔨 (CE exists ✅, UI not wired)

**Acceptance criteria**
- GIVEN the Ask surface, WHEN a question is submitted, THEN the CE routes it to a life-domain (career/wealth/marriage/health/…) and returns a computed answer for the active profile.
- GIVEN an answer, WHEN rendered, THEN it follows the template: **Verdict → What to do → [Why] → Ask a follow-up** (D4).
- GIVEN an ambiguous question, WHEN routed, THEN the app confirms the domain ("Is this about work or money?") rather than guessing silently.
- GIVEN a health/legal/money/death question, WHEN detected, THEN the refer-out pattern applies (Epic M), never a deterministic prediction.
- GIVEN copy register, WHEN Guided, THEN the answer avoids jargon; WHEN Practitioner, THEN it may include technical terms with evidence.

---

### D2 · Ask by voice (in/out)
**Story:** As a **low-literacy or hands-busy user (L, P) or commuter**, I want to ask out loud and hear the answer, so that I don't have to type or read.
**Personas:** L, P, M · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN the Ask surface, WHEN the mic is tapped, THEN speech-to-text captures the question in the selected language (incl. Telugu — Epic I).
- GIVEN an answer, WHEN voice mode is active, THEN it is also read aloud (TTS) with on-screen text.
- GIVEN a recognition error, WHEN it occurs, THEN the user can edit the transcribed text before submitting.
- GIVEN no mic permission, WHEN voice is tapped, THEN a plain explanation and a path to grant permission are shown; text input remains available.

---

### D3 · Suggested question chips
**Story:** As a **user who doesn't know what to ask**, I want smart suggestions based on my chart right now, so that I discover what's relevant.
**Personas:** L, R, S, M, An · **Mode:** G, B · **Priority:** P1 · **Feasibility:** ✅ (live dasha/gochara available)

**Acceptance criteria**
- GIVEN the Ask surface with an empty input, WHEN shown, THEN 3–5 suggested questions are generated from the profile's active dasha and current gochara (e.g., "Your Saturn period is active — ask about work & patience").
- GIVEN a chip, WHEN tapped, THEN it submits as a question and produces a full answer (D4).
- GIVEN suggestions, WHEN generated, THEN they never include death/longevity or medical prompts (Epic M).
- GIVEN a Practitioner, WHEN chips render, THEN they may reference technical triggers (dasha lord, transit aspect) plainly.

---

### D4 · Answer view (verdict → do → why → follow-up)
**Story:** As a **user**, I want answers structured so I get the point first and the detail on demand, so that I'm never overwhelmed.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨 (plain_why/technical_why ✅)

**Acceptance criteria**
- GIVEN any Ask answer, WHEN rendered, THEN a plain **Verdict** appears first, then **What to do**, then a collapsed **[Why this?]**, then a **follow-up** prompt.
- GIVEN **[Why this?]**, WHEN expanded, THEN it shows the computed evidence — relevant houses, karakas, yogas, dasha chain, active gochara, and rule sources (Epic J).
- GIVEN Guided mode, WHEN the answer shows, THEN "Why" is collapsed by default; GIVEN Practitioner mode, THEN evidence may be expanded by default.
- GIVEN a "what to do" step, WHEN a remedy or muhurta applies, THEN it links to the remedy/finder (Epic E).
- GIVEN a long answer, WHEN rendered, THEN it is chunked with headings — never a single wall of text (anti-pattern).

---

### D5 · Ask about a specific date
**Story:** As a **planner (S, M, A)**, I want to ask what a particular day is good for, so that I can time decisions and events.
**Personas:** S, M, A, R · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅ (panchanga/windows) → 🔨 goal-fit

**Acceptance criteria**
- GIVEN a calendar day (Epic H) or a date in the question, WHEN "what's this day good for?" is asked, THEN the answer summarizes the day's quality, favorable/unfavorable windows, and best-fit activities.
- GIVEN a goal is specified ("good day to travel?"), WHEN asked, THEN the answer evaluates that goal against the day and links to the muhurta finder (Epic E) for ranked windows.
- GIVEN a diaspora user (M), WHEN a date is evaluated, THEN it uses the correct timezone/location (Epic L).

---

### D6 · Evidence & provenance on answers
**Story:** As a **skeptic (R) or practitioner (A)**, I want to see the calculation behind an answer, so that I can trust it or verify it.
**Personas:** R, A · **Mode:** B, Pr · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN any answer, WHEN "Why this?" is expanded, THEN it lists the computed drivers with a **Computed** provenance reference (ayanamsha, node type, place, confidence).
- GIVEN a convention-dependent element, WHEN shown, THEN it is labelled as convention-dependent (the engine flags `convention_dependent`/`VERIFY`).
- GIVEN the evidence, WHEN a term is unfamiliar, THEN it links to the learning layer (Epic F) for a plain definition.

---

### D7 · Refer-out within Ask (cross-cutting)
**Story:** As a **user in genuine distress (health/legal/money/emergency)**, I want the app to point me to real help, so that I'm cared for, not given a fortune.
**Personas:** all · **Mode:** all · **Priority:** P0 (safety) · **Feasibility:** 🔨 (see Epic M)

**Acceptance criteria**
- GIVEN a question implicating medical, legal, financial, or emergency distress, WHEN detected, THEN the answer refers out ("please consult a doctor/lawyer/advisor") and does not adjudicate outcomes.
- GIVEN a death/longevity question, WHEN asked, THEN the app explains it does not predict death/longevity and offers a supportive reframe (Epic M).
- GIVEN a litigation/dispute question, WHEN answered, THEN tone is advisory only — never "you will win/lose."
