# Epic B — Authentication & Account

**Goal:** Make sign-in a *reward for wanting to keep value*, not a toll booth. Preserve
guest work; keep account management honest and privacy-respecting.

**Screens:** Sign-in sheet · Magic-link / OTP · Account · Delete account.

---

### B1 · Soft save prompt (post-value)
**Story:** As a **new user who just saw my reading**, I want a clear reason to save, so that signing up feels worth it.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN value has been delivered (Aha), WHEN the save prompt shows, THEN it names the concrete benefit ("keep your space + daily guidance"), not a generic "sign up."
- GIVEN the prompt, WHEN dismissed, THEN the guest session continues uninterrupted.
- GIVEN the prompt is dismissed 2+ times, WHEN shown again, THEN frequency backs off (no nagging on every screen).

---

### B2 · Sign-in methods
**Story:** As a **user**, I want to sign in the easy way I already use, so that I don't fight with passwords.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅ (Supabase: Google / magic link / password)

**Acceptance criteria**
- GIVEN the sign-in sheet, WHEN shown, THEN Google one-tap, magic-link/OTP email, and password are all available, with the platform-preferred method emphasized.
- GIVEN a chosen method, WHEN authentication succeeds, THEN the user returns to exactly where they were (no context loss).
- GIVEN authentication fails, WHEN it errors, THEN a plain, non-technical message and a retry are shown; birth details and guest state are never lost.
- GIVEN a low-connectivity user (P), WHEN using magic link, THEN clear guidance ("check your email, tap the link") is shown and the pending state survives backgrounding.
- **Constraint:** the app never asks the user to enter financial credentials or third-party passwords into a non-native field.

---

### B3 · Returning-user recognition
**Story:** As a **returning user**, I want the app to remember me, so that I land on my day, not a login screen.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN a previously signed-in user, WHEN they re-open the app, THEN they are silently restored to their session and routed per their "open-to" preference (Epic L), not to sign-in.
- GIVEN a session token is expired, WHEN re-opening, THEN re-auth is requested with the least friction available (biometric/refresh) and prior view is restored.
- GIVEN multiple profiles, WHEN restored, THEN the last active profile is selected.

---

### B4 · Guest → account merge
**Story:** As a **guest who created a profile before signing up**, I want that profile to carry over, so that I never re-enter birth details.
**Personas:** all · **Mode:** all · **Priority:** P0 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a guest profile exists locally, WHEN the user completes sign-up, THEN the guest profile(s), mode, tone, and conventions are migrated to the account.
- GIVEN a merge conflict (the account already has profiles), WHEN merging, THEN no data is overwritten silently; duplicates are detected and the user is asked how to resolve.
- GIVEN merge succeeds, WHEN complete, THEN the local guest copy is reconciled to the synced account copy (single source of truth).

---

### B5 · Account & data controls (privacy)
**Story:** As a **user**, I want to manage or delete my account and data, so that I stay in control of deeply personal information.
**Personas:** all · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN account settings, WHEN opened, THEN sign-out, change-email, and **delete account** are available with plain descriptions.
- GIVEN **delete account**, WHEN chosen, THEN a clear confirmation explains what is removed (charts, notes, history) and that it is irreversible; deletion only proceeds on explicit confirm.
- GIVEN deletion completes, WHEN done, THEN all personal chart/birth data is removed from sync per policy, and the app returns to the welcome state.
- GIVEN an export request, WHEN made, THEN the user can export their own charts/readings (supports "share with my family astrologer", Epic J/K).
- **Constraint:** personal birth data is never placed in URLs/query strings or shared with any endpoint the user didn't choose.
