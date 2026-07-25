# Epic L — Profiles, Modes & Settings

**Goal:** Let users manage multiple people's charts, move the depth/tone dials anytime, and
control location/conventions — so the experience stays adaptive, not locked.

**Screens:** Profile switcher · Add/Edit profile · Comfort dial (mode) · Tone setting ·
Open-to preference · Location settings · Conventions · Settings home.

---

### L1 · Multi-profile management
**Story:** As a **family/practitioner user (S, M, A)**, I want to add, switch, and edit multiple charts, so that I can manage everyone I care about.
**Personas:** S, M, A, L · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅ (profiles/kundlis exist)

**Acceptance criteria**
- GIVEN profiles, WHEN the switcher is opened, THEN all profiles show with name/relation and the active one is indicated; switching takes one tap.
- GIVEN "add profile," WHEN chosen, THEN the birth-details flow (Epic A3–A5) creates a new profile, including the unknown-time path.
- GIVEN a profile, WHEN edited, THEN birth details, relation, and name can be changed, and dependent computations refresh.
- GIVEN relation (self vs. named), WHEN set, THEN downstream copy adapts (self vs. name).
- GIVEN a Guided single-profile user, WHEN they have one profile, THEN the switcher stays minimal/unobtrusive.

---

### L2 · Comfort dial (change mode anytime)
**Story:** As a **user whose needs change (R growing into A; L wanting just simplicity)**, I want to adjust how much detail I see, so that the app grows with me.
**Personas:** all · **Mode:** sets G/B/Pr · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN settings, WHEN the comfort dial is opened, THEN the user can move between Guided / Balanced / Practitioner with a plain description of each.
- GIVEN a mode change, WHEN applied, THEN labels, nav priority, default disclosure, and copy register update app-wide immediately — over the same stable routes.
- GIVEN a mode change, WHEN made, THEN no data is lost and the user stays on the current surface (which re-renders at the new depth).
- GIVEN Practitioner is enabled, WHEN first selected post-onboarding, THEN the Conventions options (L5) become available.

---

### L3 · Tone setting (gentle / direct)
**Story:** As a **user**, I want to change whether tough readings are gentle or direct, so that the app matches my emotional needs over time.
**Personas:** all · **Mode:** all · **Priority:** P0 (safety) · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN settings, WHEN tone is opened, THEN **Gentle**/**Direct** is selectable with a plain explanation of the difference.
- GIVEN a change, WHEN applied, THEN all hard-content framing (Today, Ask, doshas) reflects it immediately.
- GIVEN either setting, WHEN death/longevity/medical/legal/financial content is implicated, THEN refer-out (Epic M) overrides tone.
- GIVEN default, WHEN unset, THEN **Gentle** applies.

---

### L4 · "Open-to" preference
**Story:** As a **practitioner (A)**, I want to choose where the app opens, so that I land on my workbench instead of Today if I prefer.
**Personas:** A (and any power user) · **Mode:** Pr, B · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN settings, WHEN "open to" is set, THEN options include **Today** (default) or **Last viewed chart/tool**.
- GIVEN a returning session (B3), WHEN restored, THEN the app honors this preference and the last active profile.
- GIVEN a Common user, WHEN they never change it, THEN Today remains the default.

---

### L5 · Location settings (birth vs. current)
**Story:** As a **diaspora user (M)**, I want daily panchang/muhurta computed for where I am, so that timings are actually correct abroad.
**Personas:** M, and any traveler · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨 (defaults to birth place today)

**Acceptance criteria**
- GIVEN location settings, WHEN opened, THEN the user can choose whether daily/panchang/muhurta uses **birth place** or **current location**.
- GIVEN current location, WHEN selected (with permission), THEN panchanga, day-windows, festivals, and muhurta recompute for that timezone/geo.
- GIVEN the birth chart itself, WHEN location preference changes, THEN the natal chart remains birth-based (only time-of-day/daily computations follow current location).
- GIVEN no location permission, WHEN current-location is chosen, THEN the user can enter a city manually (Epic A5 autocomplete).

---

### L6 · Conventions (Practitioner)
**Story:** As a **practitioner (A)**, I want to change my calculation conventions anytime, so that I can match different schools or cross-check.
**Personas:** A · **Mode:** Pr · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN conventions settings, WHEN opened, THEN ayanamsha (Lahiri/Raman/KP), node type (mean/true), and chart style (S/N/E) are editable.
- GIVEN a change, WHEN saved, THEN all computations and provenance displays update, and the change is reflected in the Computed badge (Epic J2).
- GIVEN a Common user, WHEN they never enter Practitioner, THEN these controls stay hidden (smart defaults apply).

---

### L7 · Settings home
**Story:** As a **user**, I want one place for preferences, language, notifications, account, and privacy, so that I can find controls easily.
**Personas:** all · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅ (settings exist)

**Acceptance criteria**
- GIVEN settings home, WHEN opened, THEN it groups: Experience (mode, tone, open-to), Language & Audio (Epic I), Notifications (Epic K5), Location (L5), Conventions (L6, Practitioner only), Account & Privacy (Epic B).
- GIVEN any setting, WHEN changed, THEN the change persists and syncs for signed-in users.
- GIVEN a Guided user, WHEN in settings, THEN advanced/Practitioner sections are hidden or clearly secondary.
