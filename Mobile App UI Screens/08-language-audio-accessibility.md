# Epic I — Language, Audio & Accessibility

**Goal:** Reach the actual core audience. Telugu and audio are **functional requirements**,
not polish — the Guided core (Lakshmi, Padma) is Telugu-first and often wants to listen.
Plus standard a11y and low-connectivity resilience for elder/rural users.

**Screens:** Language picker · Audio player (global) · Large-text mode · A11y settings.

---

### I1 · Telugu content & mixed-script
**Story:** As a **Telugu-first user (L, P) or diaspora parent (M)**, I want the app and its readings in Telugu, so that I actually understand my guidance.
**Personas:** L, P, M · **Mode:** G, B · **Priority:** P0 · **Feasibility:** 🔨 (English-only today)

**Acceptance criteria**
- GIVEN language settings, WHEN Telugu is selected, THEN UI chrome and generated readings (Today, Ask answers, remedies, festivals) render in Telugu.
- GIVEN mixed-script content (Telugu + Sanskrit/English terms), WHEN rendered, THEN fonts and layout handle it without clipping or tofu.
- GIVEN a term with no natural Telugu equivalent, WHEN shown, THEN it appears with a plain gloss rather than untranslated jargon.
- GIVEN language is set at onboarding or later, WHEN changed, THEN it applies app-wide immediately and persists.
- GIVEN device language is Telugu on first launch, WHEN the app opens, THEN Telugu is the default.

---

### I2 · Audio rendering everywhere
**Story:** As a **user who prefers to listen (L, P, M, commuters)**, I want key content read aloud, so that I don't have to read.
**Personas:** L, P, M · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN Today, Ask answers, and remedy guidance, WHEN a **▶ Listen** control is present, THEN the content is rendered as audio in the selected language.
- GIVEN audio, WHEN the tone is Gentle vs Direct (A7), THEN the register matches (warm vs plain).
- GIVEN playback, WHEN the screen locks or app backgrounds, THEN audio continues with lock-screen/Control-Center controls.
- GIVEN offline with cached audio (C9), WHEN played, THEN cached audio works without network.

---

### I3 · Large-tap, low-connectivity mode
**Story:** As an **elder/rural user on a budget Android with a weak network (P)**, I want big text, taps over swipes, and reliability, so that the app is usable for me.
**Personas:** P, L · **Mode:** G · **Priority:** P1 · **Feasibility:** 🔨 (partly in mobile plan)

**Acceptance criteria**
- GIVEN large-tap mode (auto-suggested for Guided/elder or manually enabled), WHEN active, THEN font sizes increase, primary actions are large tap targets, and swipe-only interactions have tap equivalents.
- GIVEN a weak/absent network, WHEN using core surfaces, THEN Today (C9) and cached content remain available; slow calls show reassuring states, not raw errors.
- GIVEN a budget device, WHEN the app runs, THEN animations are lightweight and can be reduced automatically.

---

### I4 · Standard accessibility (WCAG AA)
**Story:** As a **user relying on assistive tech or accommodations**, I want the app to meet accessibility standards, so that I can use it fully.
**Personas:** all (esp. P) · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨 (partly covered in mobile plan)

**Acceptance criteria**
- GIVEN any screen, WHEN evaluated, THEN text/background contrast meets **WCAG AA**, and interactive targets are ≥ 44px.
- GIVEN a screen reader (VoiceOver/TalkBack), WHEN navigating, THEN all controls and chart glyphs have meaningful labels; charts expose a text-alternative summary.
- GIVEN OS-level 200% text zoom, WHEN applied, THEN layouts reflow without truncation or horizontal page scroll.
- GIVEN reduced-motion is enabled, WHEN animations would play, THEN they are replaced with static equivalents.
- GIVEN colour is used to convey meaning (e.g., day quality), WHEN rendered, THEN meaning is also conveyed by text/shape (not colour alone).
