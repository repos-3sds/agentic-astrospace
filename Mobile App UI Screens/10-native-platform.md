# Epic K — Native Platform Superpowers

**Goal:** Make this a *real native app*, not a web wrapper — widgets, Live Activities,
watch, assistant, notifications, share, offline, haptics. These are the daily-habit and
organic-growth surfaces.

**Screens/surfaces:** Home & lock widgets · Live Activity / Dynamic Island · Watch
complication · Siri/Assistant · Notification settings · Share sheet story cards · Haptics.

---

### K1 · Home & lock-screen widgets
**Story:** As a **daily user (L, R, M)**, I want my day on my home/lock screen, so that I get value without opening the app.
**Personas:** L, R, M, S · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨 (data ✅)

**Acceptance criteria**
- GIVEN widgets, WHEN added, THEN options include: day-quality, next auspicious/inauspicious window, today's tithi/nakshatra, and remedy-of-the-day.
- GIVEN a widget, WHEN the day changes or a window passes, THEN it refreshes on the platform's schedule.
- GIVEN a widget is tapped, WHEN activated, THEN it deep-links to the relevant in-app surface (Today, window detail, remedy).
- GIVEN multiple profiles, WHEN a widget is configured, THEN the user chooses which profile it reflects.

---

### K2 · Live Activities / Dynamic Island
**Story:** As a **user timing something (S, A, M)**, I want a live countdown to/through an important window, so that I don't miss it.
**Personas:** S, A, M, L · **Mode:** all · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN an active/upcoming window (Rahu Kalam, a chosen muhurta, a vrat), WHEN a Live Activity is started, THEN it shows a live countdown on the lock screen / Dynamic Island.
- GIVEN the window ends, WHEN it passes, THEN the activity resolves and clears cleanly.
- GIVEN a remedy timer (E3), WHEN running, THEN it can surface as a Live Activity.
- **Constraint:** live surfaces are informational and calm, never fear-driven countdowns to "doom."

---

### K3 · Watch complication
**Story:** As a **user with a smartwatch (R, A, M)**, I want day-quality and next window on my wrist, so that I can glance without my phone.
**Personas:** R, A, M · **Mode:** all · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN watchOS/Wear, WHEN a complication is added, THEN it shows day-quality and the next window, tapping through to a minimal watch view.
- GIVEN limited connectivity, WHEN the phone is away, THEN the complication shows the last synced value with a staleness indicator.

---

### K4 · Siri / Google Assistant
**Story:** As a **hands-busy user (L, M)**, I want to ask by voice from the OS, so that I get quick answers without opening the app.
**Personas:** L, M, R · **Mode:** all · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN assistant intents, WHEN the user asks "is now a good time?" or "when's Rahu Kalam today?", THEN the app answers from computed data for the active profile.
- GIVEN a spoken answer, WHEN safety-sensitive (health/legal/money/death), THEN it refers out (Epic M) rather than predicting.
- GIVEN the assistant answer, WHEN more depth is wanted, THEN it offers to open the app at the relevant surface.

---

### K5 · Smart notifications (opt-in, non-fear)
**Story:** As a **daily user (L, M)**, I want a gentle morning nudge and timely window alerts, so that the app becomes a helpful habit — without spamming or scaring me.
**Personas:** L, M, S, P · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN notifications, WHEN first offered, THEN they are opt-in with clear categories (morning brief, window alerts, festival reminders, remedy reminders) the user can toggle individually.
- GIVEN a morning brief, WHEN sent, THEN it links straight to Today and is warm/plain (respecting tone A7).
- GIVEN a window alert, WHEN sent, THEN it is informational and time-relevant, never fear-based or upsell-driven.
- GIVEN frequency, WHEN the user engages little, THEN cadence backs off automatically.

---

### K6 · Share sheet → story cards
**Story:** As a **user who shares things (An, S, M)**, I want to share a beautiful card of my reading/match/why, so that I can send it to family or post it.
**Personas:** An, S, M, L · **Mode:** all · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a reading, match report, or "why this reading," WHEN "share" is tapped, THEN a clean, branded story card (image) is generated for the OS share sheet.
- GIVEN a share card, WHEN created, THEN it excludes sensitive data the user didn't opt to include, and never encodes personal data in a URL (privacy).
- GIVEN a match report (G3), WHEN shared, THEN framing stays honest and non-fear.

---

### K7 · Offline-first core
**Story:** As a **commuter/rural user (R, P, M)**, I want core features to work without signal, so that the app is dependable.
**Personas:** R, P, M · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨 (engine is data-file-free)

**Acceptance criteria**
- GIVEN offline, WHEN the app is used, THEN Today (C9), cached charts, and cached audio remain available.
- GIVEN on-device computation, WHEN offline, THEN the day's core card can be computed locally.
- GIVEN reconnection, WHEN restored, THEN local results reconcile to authoritative server results.

---

### K8 · Haptics as ritual
**Story:** As a **practicing user (L, P, S)**, I want tactile feedback during remedies and at window boundaries, so that the experience feels grounded and ritual-like.
**Personas:** L, P, S · **Mode:** G, B · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a mantra counter (E3), WHEN the user taps to count, THEN a soft haptic confirms each count.
- GIVEN entering/leaving a key window, WHEN it occurs (with the app active or via notification), THEN a distinct, subtle haptic can signal it.
- GIVEN reduced-motion / system haptics off, WHEN set, THEN haptics respect the OS preference.
