# Epic A — Onboarding & Activation

**Goal:** Get any new user — believer or practitioner — to a *real, personal, computed*
answer before we ask for an account. Value first, account later; depth on demand.

**Success metric:** % of new installs that reach "The Aha" (A10/A11) < 90 seconds, and
% that then choose to save (A12).

**Screens:** Welcome · Hook Question · Birth Details (name / date / time / place) ·
How-You-Like-Answers · Tone · Conventions (expert) · Casting · The Aha (common / expert)
· Soft Save.

---

### A1 · Welcome screen
**Story:** As a **new visitor**, I want to instantly grasp what AstroSpace is and start without a signup wall, so that I feel invited, not gated.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a first launch, WHEN the app opens, THEN a one-line value prop ("Vedic astrology, computed. Ask anything.") and a primary **[Get started]** are visible in one viewport with no scroll.
- GIVEN the welcome screen, WHEN rendered, THEN a low-emphasis secondary **[I already have a space]** is present for returning users.
- GIVEN **[Get started]** is tapped, WHEN pressed, THEN onboarding begins with **no** account or sign-in requirement.
- GIVEN the device language is Telugu, WHEN the screen loads, THEN the value prop and CTAs render in Telugu (see Epic I).
- GIVEN reduced-motion is enabled at OS level, WHEN any welcome animation would play, THEN it is replaced by a static state.

---

### A2 · Hook question ("What's on your mind?")
**Story:** As a **believer (L, R, S, M)**, I want to start by naming what I care about, so that the app feels like it answers *my* question, not a generic chart.
**Personas:** L, R, S, M · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨 (CE domain routing exists ✅)

**Acceptance criteria**
- GIVEN onboarding starts, WHEN the hook screen shows, THEN domain chips are offered (Work, Marriage, Money, Health, My child, Just today) plus a free-text field.
- GIVEN a chip or free text is chosen, WHEN submitted, THEN the intent is stored and mapped to a CE life-domain, and is used to personalize The Aha (A10).
- GIVEN the user taps **[Skip]**, WHEN skipped, THEN onboarding proceeds with no penalty and The Aha falls back to a general signature.
- GIVEN a health/legal/money/death-related free-text intent, WHEN detected, THEN the eventual answer routes through the refer-out pattern (Epic M), never a prediction.
- GIVEN an expert selects Practitioner later, WHEN the hook was skipped, THEN no re-prompt occurs.

---

### A3 · Birth details — one field per screen
**Story:** As a **new user**, I want to enter my birth details calmly, one thing at a time, so that it never feels like a bureaucratic form.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨 (city DB ✅)

**Acceptance criteria**
- GIVEN birth-detail capture, WHEN it begins, THEN each of {who is this for, date of birth, time of birth, place of birth} appears on its own screen with a single primary input and a progress indicator.
- GIVEN a date field, WHEN focused, THEN a native date control is used (no free-typed date parsing).
- GIVEN any step, WHEN the user taps back, THEN prior entries are preserved.
- GIVEN "Who is this for?", WHEN answered, THEN the choice (self vs. a named person) drives downstream copy (self vs. name).
- GIVEN all four fields complete, WHEN the user advances, THEN the app proceeds to mode capture (A6) — auth is **not** requested here.

---

### A4 · Unknown birth time — graceful path
**Story:** As a **user who doesn't know my exact birth time (common in the audience)**, I want to proceed anyway, so that I'm not blocked at the door.
**Personas:** L, P, An, M · **Mode:** G, B · **Priority:** P0 · **Feasibility:** 🔨 (confidence flags ✅)

**Acceptance criteria**
- GIVEN the time-of-birth screen, WHEN shown, THEN a prominent **[I don't know]** option is present alongside the time picker.
- GIVEN **[I don't know]** is tapped (common flow), WHEN chosen, THEN the user may pick an approximate window (morning/afternoon/evening/night) OR defer with "help me later."
- GIVEN an approximate or missing time, WHEN a chart is computed, THEN a **confidence flag** is attached and any time-sensitive output (lagna, houses, dashas) is visibly marked as lower-confidence.
- GIVEN a Practitioner (A), WHEN time is unknown, THEN the app offers a "→ rectify later" affordance instead of buckets.
- GIVEN missing time, WHEN The Aha renders, THEN it degrades to Moon-sign / nakshatra-based statements that don't require an exact ascendant, and says so plainly.

---

### A5 · Place of birth — city autocomplete
**Story:** As a **user in Andhra/Telangana or the diaspora**, I want to find even my small hometown quickly, so that my chart is calculated for the right place.
**Personas:** L, P, S, M · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅ (complete AP+TS villages + world cities)

**Acceptance criteria**
- GIVEN the place field, WHEN 2+ characters are typed, THEN matching cities/villages (incl. AP+TS villages and world cities) are suggested with region/country disambiguation.
- GIVEN a selection, WHEN made, THEN latitude/longitude and timezone are resolved and stored with the profile.
- GIVEN a diaspora user (M), WHEN a non-Indian city is selected, THEN timezone correctness is preserved for later panchang/muhurta (see Epic H / L).
- GIVEN no network, WHEN typing, THEN a cached/offline city index still returns core matches.

---

### A6 · How you like answers — the invisible mode capture
**Story:** As a **new user**, I want to say how much detail I like in plain language, so that the app adapts to me without an astrology quiz.
**Personas:** all · **Mode:** sets G/B/Pr · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN mode capture, WHEN shown, THEN exactly one human-worded question is asked with three cards: "Just tell me, simply" (→ Guided), "Tell me — and show me why" (→ Balanced, pre-selected default), "Give me the full detail" (→ Practitioner).
- GIVEN a card is chosen, WHEN confirmed, THEN `experienceMode` is set and drives labels, nav priority, default disclosure, and copy register app-wide.
- GIVEN no explicit choice, WHEN the user advances, THEN Balanced is applied as default.
- GIVEN Practitioner is chosen, WHEN confirmed, THEN the Conventions step (A8) is inserted before Casting.
- GIVEN mode is set, WHEN onboarding completes, THEN the user can change it anytime via the comfort dial (Epic L) — it is never presented as permanent.

---

### A7 · Tone / fear-handling capture
**Story:** As a **user with a personal relationship to difficult news**, I want to choose whether tough readings are gentle or direct, so that the app respects my emotional needs.
**Personas:** protect → L, P, S, M · honest → R, A · **Mode:** all · **Priority:** P0 (safety) · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN mode capture, WHEN completed, THEN a secondary one-tap question "When something's tough, should we be…" offers **[Gentle]** / **[Direct]**.
- GIVEN **[Gentle]** is set, WHEN any hard affliction (health/marriage/children/loss) would surface, THEN it is framed supportively and always paired with a cancellation/remedy and a "flag, not a verdict" note (Epic M).
- GIVEN **[Direct]** is set, WHEN a hard affliction surfaces, THEN honest framing is allowed, still within safety constraints (never death/longevity).
- GIVEN either setting, WHEN death/longevity, medical, legal, or financial-emergency content is implicated, THEN refer-out (Epic M) overrides tone entirely.
- GIVEN tone is set, WHEN onboarding ends, THEN it is editable anytime (Epic L) and defaults to **Gentle** if skipped.

---

### A8 · Conventions step (Practitioner only)
**Story:** As a **practitioner (A)**, I want to set my calculation conventions up front, so that every reading matches my school of practice.
**Personas:** A · **Mode:** Pr · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN Practitioner mode, WHEN onboarding reaches Conventions, THEN ayanamsha (Lahiri/Raman/KP), node type (mean/true), and chart style (South/North/East) are offered with sensible defaults pre-selected.
- GIVEN defaults are shown, WHEN the user does nothing, THEN Lahiri / mean / South (or platform default) apply and onboarding continues.
- GIVEN a convention is changed, WHEN saved, THEN all subsequent computations and provenance displays reflect it, and it is editable later (Epic L).
- GIVEN a Common user, WHEN onboarding runs, THEN this screen is **not** shown (smart defaults applied silently).

---

### A9 · Casting moment
**Story:** As a **new user**, I want a brief, warm sense that my chart is being computed, so that the wait feels meaningful, not like a spinner.
**Personas:** all · **Mode:** all · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN all inputs are captured, WHEN computation runs, THEN a 2–3s branded "reading your sky" state is shown (respecting reduced-motion with a static equivalent).
- GIVEN computation exceeds 5s, WHEN still pending, THEN a reassuring progress message appears; GIVEN it fails, THEN a retry with preserved inputs is offered (no data loss).
- GIVEN computation succeeds, WHEN complete, THEN the user transitions directly to The Aha (A10 or A11).

---

### A10 · The Aha — Common
**Story:** As a **believer (L, R, S, M)**, I want a plain, personal answer plus one thing to do today, so that I immediately feel the app understands me.
**Personas:** L, R, S, M, P · **Mode:** G, B · **Priority:** P0 · **Feasibility:** 🔨 (daily guidance + CE ✅)

**Acceptance criteria**
- GIVEN a computed chart, WHEN The Aha renders, THEN it shows a plain 2–3 sentence "here's you" signature in the user's copy register (no jargon on Guided).
- GIVEN today's guidance, WHEN shown, THEN exactly **one** thing to do and **one** to avoid are presented plainly.
- GIVEN the hook (A2) was answered, WHEN The Aha renders, THEN the original question is answered in plain language.
- GIVEN any plain statement, WHEN shown, THEN a single **[Why this?]** affordance reveals the computed evidence on tap (Epic J).
- GIVEN a Guided user (L/P), WHEN The Aha renders, THEN a **▶ Listen** control offers audio (Epic I).
- GIVEN a hard transit today, WHEN surfaced, THEN it honors the tone setting (A7) and pairs a caution with a remedy.

---

### A11 · The Aha — Expert
**Story:** As a **practitioner (A)**, I want to see my actual chart with provenance and flagged yogas immediately, so that I can trust and start using the tool at once.
**Personas:** A · **Mode:** Pr · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN Practitioner mode, WHEN The Aha renders, THEN the birth chart is shown in the chosen style (S/N/E), pinch-zoomable, with the big-three summarized.
- GIVEN the chart, WHEN shown, THEN a **Computed** provenance badge exposes ayanamsha, node type, house system, calculation place, and any confidence flags (Epic J).
- GIVEN computed yogas/doshas, WHEN present, THEN the strongest are auto-flagged, each with a **[Why]** to the classical rule + provenance.
- GIVEN the expert Aha, WHEN shown, THEN **[Add another chart]** and **[Explore tools]** entry points are present.
- GIVEN a Practitioner deep-links from a shared route, WHEN they arrive, THEN they land on the correct practitioner surface (stable route tree).

---

### A12 · Soft save / defer auth
**Story:** As a **new user who just saw value**, I want to save my space only when I choose to, so that I'm never forced to sign up before I'm convinced.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN The Aha is shown, WHEN the user has engaged, THEN a soft prompt "Keep your space and get daily guidance?" offers **[Save]** and **[Maybe later, keep exploring]**.
- GIVEN **[Maybe later]**, WHEN chosen, THEN the user continues as a guest with the created profile intact locally.
- GIVEN a guest leaves and returns, WHEN they re-open, THEN the save prompt reappears and the guest profile is preserved for merge on sign-up (Epic B).
- GIVEN **[Save]**, WHEN chosen, THEN the user proceeds to sign-in (Epic B) and, on success, the guest profile is migrated to the account with no re-entry of birth details.
- GIVEN save is deferred, WHEN the user navigates the app, THEN no feature is blocked except those inherently requiring an account (sync, notifications across devices).
