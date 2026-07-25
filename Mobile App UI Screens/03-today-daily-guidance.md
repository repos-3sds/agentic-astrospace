# Epic C — Today / Daily Guidance

**Goal:** Make "Today" the entire home for the common user — one calm card that says what
today is and what to do, with everything else a swipe away. This is the retention engine.

**Screens:** Today card (home) · Day-quality detail · Today-vs-Always · Next-window strip
· Audio player · Offline Today.

---

### C1 · Today is the home
**Story:** As a **returning common user (L, R, P, M)**, I want to open the app straight onto my day, so that I get value in one glance with no navigation.
**Personas:** L, R, P, M · **Mode:** G, B · **Priority:** P0 · **Feasibility:** ✅ (daily guidance CE-wired)

**Acceptance criteria**
- GIVEN a signed-in common user, WHEN the app cold-opens, THEN the first screen is **Today** for the active profile — not a dashboard or tab grid.
- GIVEN Today, WHEN rendered, THEN it shows, in one viewport: a plain one-line verdict, one thing to do, one to avoid, and a day-quality indicator.
- GIVEN more detail is wanted, WHEN the user swipes down, THEN secondary sections (almanac, windows, why) progressively reveal — never shown all at once for Guided.
- GIVEN a Practitioner, WHEN they open Today, THEN it still appears but with quick access to the workbench (Epic F) and per their "open-to" preference (Epic L).

---

### C2 · Day-quality indicator
**Story:** As a **user**, I want a glanceable sense of how today is, so that I can gauge my day in a second.
**Personas:** all · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅ (tarabala + chandrabala + gochara severity)

**Acceptance criteria**
- GIVEN today's computation, WHEN the indicator renders, THEN it is derived from tarabala + chandrabala + effective gochara severity, and its bluntness respects the tone setting (A7).
- GIVEN a Guided user with **Gentle** tone, WHEN the day is difficult, THEN the indicator communicates "take it easy" without alarming language.
- GIVEN a Direct user (R/A), WHEN the day is difficult, THEN the indicator may state it plainly.
- GIVEN the indicator, WHEN tapped, THEN it expands to the plain reasons and a **[Why this?]** to the computed evidence (Epic J).
- **Constraint:** the indicator never encodes death/longevity or medical verdicts (Epic M).

---

### C3 · One-to-do / one-to-avoid
**Story:** As a **believer**, I want one clear action and one thing to avoid, so that I know what to *do*, not just what today "is."
**Personas:** L, R, P, S, M · **Mode:** G, B · **Priority:** P0 · **Feasibility:** ✅ (do/avoid + muhurta windows)

**Acceptance criteria**
- GIVEN daily guidance, WHEN shown, THEN exactly one recommended action and one caution are surfaced, each phrased plainly and actionably.
- GIVEN an action has a favorable window, WHEN present, THEN the time window (from computed muhurta) is attached ("good between 10:12–11:40").
- GIVEN a caution touches health/legal/money, WHEN surfaced, THEN it refers out rather than adjudicating (Epic M).
- GIVEN the user wants alternatives, WHEN they tap "more", THEN additional do/avoid items are revealed without cluttering the default view.

---

### C4 · Today vs. Always separation
**Story:** As a **user**, I want daily things kept separate from my permanent traits, so that I don't confuse "today's number" with "my lucky number."
**Personas:** all · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN Today, WHEN it displays colour/number/tarabala, THEN these are visually grouped as **"Today"** and labelled as changing daily.
- GIVEN the birth-constant lucky signature, WHEN shown, THEN it lives in a separate **"Always"** group labelled as personal and permanent.
- GIVEN a universal value (e.g., "number of the day"), WHEN shown, THEN it is distinguished from a personal value ("your lucky number") in wording (Epic J).

---

### C5 · Live next-window strip
**Story:** As a **user planning my day**, I want to know the next auspicious/inauspicious window as it approaches, so that I can time things well.
**Personas:** L, S, M, A · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅ (Rahu Kalam, Abhijit, Choghadiya, etc.)

**Acceptance criteria**
- GIVEN the current time, WHEN Today renders, THEN the next relevant window (e.g., Rahu Kalam start, Abhijit muhurta) is shown with a live countdown.
- GIVEN a window is imminent (configurable, e.g., <45 min), WHEN it approaches, THEN a gentle, non-fear nudge is available (and can drive a notification / Live Activity — Epic K).
- GIVEN a diaspora user (M), WHEN windows are computed, THEN they use the user's **current** location/timezone by preference, not birth place (Epic L).
- **Constraint:** window nudges are informational, never framed as doom or upsell.

---

### C6 · Gentle framing for hard days
**Story:** As a **protect-me user (L, P, S, M)**, I want difficult transits delivered kindly and with a remedy, so that guidance supports me instead of scaring me.
**Personas:** L, P, S, M · **Mode:** G, B · **Priority:** P0 (safety) · **Feasibility:** 🔨 (remedy engine) + ✅ (transit data)

**Acceptance criteria**
- GIVEN tone = **Gentle** and a hard transit today, WHEN surfaced, THEN it is framed supportively, paired with a remedy/next step, and labelled "a flag, not a verdict."
- GIVEN tone = **Direct**, WHEN a hard transit occurs, THEN honest framing is used, still within safety limits.
- GIVEN any hard content, WHEN it implicates health/legal/money/death, THEN refer-out (Epic M) supersedes both tones.
- GIVEN a remedy is offered, WHEN shown, THEN it is presented as traditional practice, never as "pay to remove" (Epic E/M).

---

### C7 · Audio brief (Listen)
**Story:** As a **Guided/elder/commuting user (L, P, M)**, I want to listen to my day, so that I don't have to read.
**Personas:** L, P, M · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨 (TTS render)

**Acceptance criteria**
- GIVEN Today, WHEN rendered, THEN a **▶ Listen** control plays the daily guidance as ~30s audio in the user's language (Epic I).
- GIVEN audio plays, WHEN the app is backgrounded or the screen locks, THEN playback continues with lock-screen controls.
- GIVEN Telugu is selected, WHEN Listen is tapped, THEN Telugu audio is used.
- GIVEN reduced data mode, WHEN audio is requested, THEN it is generated/streamed efficiently or served from cache.

---

### C8 · Profile-aware Today
**Story:** As a **user with family profiles (S, M, A)**, I want Today to clearly reflect whose day I'm viewing, so that I don't mix up people.
**Personas:** S, M, A · **Mode:** all · **Priority:** P1 · **Feasibility:** ✅

**Acceptance criteria**
- GIVEN multiple profiles, WHEN Today is shown, THEN the active profile's name/avatar is visible and switchable in one tap (Epic L).
- GIVEN a profile switch, WHEN made, THEN Today recomputes for that profile without a full reload/flash.
- GIVEN a Guided user with one profile, WHEN Today is shown, THEN the switcher is minimized to avoid clutter.

---

### C9 · Offline / cached Today
**Story:** As a **low-connectivity user (P) or commuter (R)**, I want my day even without signal, so that the app is reliable everywhere.
**Personas:** P, R, M · **Mode:** all · **Priority:** P1 · **Feasibility:** 🔨 (engine is data-file-free → on-device/cached feasible)

**Acceptance criteria**
- GIVEN the last successful compute, WHEN the device is offline, THEN Today renders from cache with a clear "offline — last updated at HH:MM" note.
- GIVEN on-device computation is available, WHEN offline, THEN the day's core card (verdict/do/avoid/windows) is computed locally without a server round-trip.
- GIVEN connectivity returns, WHEN restored, THEN Today silently refreshes to the authoritative computed result.
- GIVEN audio (C7), WHEN offline and previously cached, THEN cached audio still plays.
