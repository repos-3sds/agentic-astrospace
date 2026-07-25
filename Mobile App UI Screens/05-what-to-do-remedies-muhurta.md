# Epic E — What to Do (Remedies & Muhurta)

**Goal:** Close the biggest product gap — turn description into prescription. 6 of 7
personas want remedies and/or timing; 5 of 7 already perform remedies. This is table
stakes, currently absent. Remedies are offered as *traditional practice*, never fear leverage.

**Screens:** Remedy card · Remedy detail · Remedy tracker/streak · Muhurta finder (goal
picker) · Muhurta results · Muhurta detail.

> **Feasibility note:** the remedy engine and goal-based muhurta finder are **new builds**
> (🔨) — raw windows and dosha/dasha data exist (✅), but the affliction→remedy mapping and
> goal→window ranking do not yet.

---

### E1 · Remedy recommendation tied to affliction
**Story:** As a **believer (L, P, S, M)**, I want a specific remedy for what's actually afflicting my chart, so that I know what to do about it.
**Personas:** L, P, S, M · **Mode:** G, B · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN an affliction/dosha/dasha context, WHEN a remedy is requested, THEN the app recommends remedies (gem / mantra / vrat / donation / colour / deity) mapped to that specific cause — not generic.
- GIVEN a remedy, WHEN shown, THEN it states the affliction it addresses in plain language and links to the evidence (Epic J).
- GIVEN multiple remedies, WHEN presented, THEN they are ordered by relevance and the user can pick what fits their practice.
- GIVEN a Guided user, WHEN remedies show, THEN language is simple and actionable; GIVEN a Practitioner, THEN the classical rationale is available.
- **Constraint:** remedies are never gated behind payment framed as "remove your dosha" (Epic M).

---

### E2 · Remedy provenance & honest framing
**Story:** As a **skeptic-adjacent or careful user (R, M)**, I want remedies labelled as tradition rather than guaranteed fixes, so that I trust the app's honesty.
**Personas:** R, M, A · **Mode:** B, Pr · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN any remedy, WHEN shown, THEN it is labelled as traditional practice, not deterministic fact, with a source/tradition note where available.
- GIVEN a convention-dependent remedy (e.g., numerology-based), WHEN shown, THEN it is explicitly marked as convention-dependent.
- GIVEN a remedy involving purchase (e.g., a gemstone), WHEN shown, THEN it is informational and never a store CTA or fear-driven upsell.

---

### E3 · Remedy tracker / streak
**Story:** As a **practicing believer (L, P, S)**, I want to track a remedy I'm doing (e.g., a mantra count or a weekly vrat), so that I stay consistent and feel progress.
**Personas:** L, P, S, M · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a remedy with a repeatable action (e.g., 108 chants), WHEN the user starts it, THEN a counter/tracker is created with progress state.
- GIVEN a mantra counter, WHEN the user taps to count, THEN each tap increments with a soft haptic (Epic K) and the running total persists.
- GIVEN a recurring remedy (weekly vrat/donation), WHEN scheduled, THEN reminders can be set (opt-in, Epic K) and a streak is maintained.
- GIVEN a missed day, WHEN it occurs, THEN the app is encouraging, never shaming or fear-inducing.

---

### E4 · Goal-based muhurta finder
**Story:** As a **planner (S, M, A, R)**, I want the best time to do a specific thing, so that I can act with confidence.
**Personas:** S, M, A, R, L · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨 (raw windows ✅)

**Acceptance criteria**
- GIVEN the muhurta finder, WHEN opened, THEN the user picks a goal (e.g., sign a deal, travel, buy gold, start a venture, marriage-related) from a curated list plus free text.
- GIVEN a goal and a date range, WHEN computed, THEN the app returns ranked favorable windows using panchanga + day-windows + the profile's chart relevance.
- GIVEN a diaspora user (M), WHEN windows are computed, THEN the user's current location/timezone is used by preference (Epic L).
- GIVEN a goal touching health/legal/finance, WHEN chosen, THEN the app pairs timing with a refer-out where appropriate (Epic M) and avoids guaranteeing outcomes.
- **Constraint:** no goal implying self-harm, death timing, or illegal activity is supported.

---

### E5 · Muhurta results & detail
**Story:** As a **user**, I want ranked time windows I can understand and act on, so that I can pick one and schedule it.
**Personas:** S, M, A, R · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN muhurta results, WHEN shown, THEN each window has a start/end time, a plain quality label, and a **[Why]** to the computed factors (tithi, nakshatra, windows, chart fit).
- GIVEN a chosen window, WHEN selected, THEN the user can add it to their device calendar (with permission) and/or set a reminder (Epic K).
- GIVEN no strong window in range, WHEN results are empty, THEN the app says so honestly and suggests the nearest acceptable option rather than inventing one.
- GIVEN a Practitioner, WHEN viewing a window, THEN full technical factors are expandable.

---

### E6 · No-manipulation guardrail (cross-cutting)
**Story:** As a **user**, I want remedies and timing offered helpfully, never as fear leverage, so that I trust the app isn't exploiting me.
**Personas:** all · **Mode:** all · **Priority:** P0 (safety) · **Feasibility:** 🔨 (see Epic M)

**Acceptance criteria**
- GIVEN any remedy or timing feature, WHEN presented, THEN it never uses fear ("disaster unless you pay/act now") to drive action or purchase.
- GIVEN a paid tier includes remedies/muhurta, WHEN monetized, THEN the value is depth/convenience, not "unlock to avoid doom."
- GIVEN a sensitive dosha (e.g., Manglik), WHEN a remedy is offered, THEN it is paired with a cancellation and a "flag, not a verdict" framing (Epic M).
