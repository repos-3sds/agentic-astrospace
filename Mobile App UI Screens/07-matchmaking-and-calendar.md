# Epic G — Matchmaking (Compatibility) · Epic H — Festival & Observance Calendar

Two high-value event/habit surfaces the engine already half-supports. Matchmaking is the
classic high-spend Indian event; the observance calendar is the daily/seasonal retention hook.

---

## Epic G — Matchmaking

**Goal:** Turn Gun Milan into a guided, honest, shareable story (not a table), and make it
easy to check a prospect. Non-fear framing is the wedge vs. upsell-driven competitors.

**Screens:** Compatibility intro · Add prospect · Gun Milan story · Dosha detail · Match report / share.

### G1 · Gun Milan guided story
**Story:** As a **matchmaking parent (S) / diaspora parent (M)**, I want a compatibility result told as a clear story, so that I understand what actually matters, not just a score.
**Personas:** S, M · **Mode:** B · **Priority:** P0 · **Feasibility:** ✅ (36-point Ashta Koota + cancellations)

**Acceptance criteria**
- GIVEN two profiles, WHEN Gun Milan runs, THEN the result is presented as: overall verdict → the few koota that matter here → dosha checks → remedy (if needed) → suggested muhurtham.
- GIVEN a score, WHEN shown, THEN it is contextualized in plain language (what it means), never presented as a bare number to fear.
- GIVEN Nadi/Bhakoot situations, WHEN present, THEN cancellations are computed and shown (the engine supports them).
- GIVEN a sensitive result, WHEN low, THEN it is framed as "a flag, not a verdict" with next steps, honoring tone (A7) and safety (Epic M).

### G2 · Add a prospect (lightweight)
**Story:** As a **parent (S)**, I want to add a prospective match's birth details without full profile setup, so that I can check compatibility quickly.
**Personas:** S, M · **Mode:** B · **Priority:** P1 · **Feasibility:** ✅ (chart creation exists)

**Acceptance criteria**
- GIVEN the compatibility flow, WHEN "add prospect" is chosen, THEN a minimal birth-details entry (name/date/time/place) creates a lightweight profile for matching.
- GIVEN unknown prospect time, WHEN entered, THEN the A4 graceful path and confidence flags apply.
- GIVEN a lightweight prospect, WHEN created, THEN the user can later promote it to a full profile or delete it.

### G3 · Shareable match report
**Story:** As a **parent (S)**, I want to share the match result on WhatsApp, so that I can discuss it with family the way we actually communicate.
**Personas:** S, M · **Mode:** B · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a completed Gun Milan, WHEN "share" is tapped, THEN a clean report (image/PDF) is generated with the verdict, key factors, and honest framing — no fear language.
- GIVEN the report, WHEN shared via the OS share sheet (Epic K), THEN no private data beyond what the user chose is included.
- GIVEN monetization, WHEN a detailed report is a paid event, THEN the free version still communicates the honest headline (no fear-gating).

### G4 · Dosha pairing (safety)
**Story:** As a **user seeing a dosha (e.g., Manglik)**, I want it paired with cancellation and remedy, so that I'm informed, not alarmed.
**Personas:** S, M, L · **Mode:** all · **Priority:** P0 (safety) · **Feasibility:** ✅ + 🔨 remedy

**Acceptance criteria**
- GIVEN a Manglik/Gandanta/Grahan flag in compatibility, WHEN shown, THEN it is always paired with its cancellation status and a remedy path, framed as "a flag, not a verdict" (Epic M).
- GIVEN tone = Gentle, WHEN a dosha appears, THEN language is supportive; GIVEN Direct, THEN it is honest — neither is fear-driven.

---

## Epic H — Festival & Observance Calendar

**Goal:** Give the devout core (Padma, Lakshmi) and diaspora (Meera) a personalized "what
to observe and when," turning panchanga into a calm rhythm and a retention loop.

**Screens:** Calendar (month) · Day detail · Festival detail · Observance reminders · Family view.

### H1 · Personalized observance calendar
**Story:** As a **devout user (P, L, M)**, I want to know which festivals and vrats apply to me and when, so that I never miss an important observance.
**Personas:** P, L, M · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨 (panchanga ✅; personalization new)

**Acceptance criteria**
- GIVEN the calendar, WHEN opened, THEN upcoming festivals/vrats are listed with dates, computed from panchanga (tithi/masa/nakshatra) for the user's location.
- GIVEN a festival, WHEN tapped, THEN its detail shows what it is, when to observe, and simple prep guidance.
- GIVEN a diaspora user (M), WHEN dates are computed, THEN they are timezone/location-correct for the user's current place (Epic L), not birth place.

### H2 · Festival countdown & reminders
**Story:** As a **busy or abroad user (L, M)**, I want reminders ahead of a festival, so that I have time to prepare.
**Personas:** L, M, P · **Mode:** G, B · **Priority:** P1 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN an upcoming festival, WHEN reminders are enabled (opt-in), THEN the user is notified ahead of time (Epic K) with prep guidance.
- GIVEN a countdown, WHEN a widget is added (Epic K), THEN days-to-festival is glanceable on the home screen.
- GIVEN notifications, WHEN sent, THEN they are warm and informational, never fear-based.

### H3 · Panchanga as a calm monthly rhythm
**Story:** As a **user**, I want the daily almanac shown as a readable rhythm, so that I can see the month at a glance without a data dump.
**Personas:** P, A, R · **Mode:** all · **Priority:** P2 · **Feasibility:** ✅ (full panchanga)

**Acceptance criteria**
- GIVEN the month view, WHEN rendered, THEN each day surfaces its key panchanga (tithi/nakshatra) compactly, expandable to full detail (yoga/karana/windows).
- GIVEN a day, WHEN tapped, THEN it deep-links to "Ask about this date" (Epic D5) and its muhurta windows.
- GIVEN a Practitioner, WHEN viewing a day, THEN full panchanga + day-windows (Rahu Kalam, Choghadiya, Hora, etc.) are available.

### H4 · Family / timezone-correct observance
**Story:** As a **diaspora anchor (M)**, I want festivals correct for where I am while staying connected to family back home, so that we can observe together across timezones.
**Personas:** M · **Mode:** B · **Priority:** P2 · **Feasibility:** 🔨

**Acceptance criteria**
- GIVEN a diaspora user with family profiles, WHEN a festival is shown, THEN it can display both the user's local timing and the home-location timing.
- GIVEN location settings, WHEN the user travels, THEN observance timing follows the current location by preference (Epic L).
