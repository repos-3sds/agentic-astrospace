# AstroSpace Mobile — Figma vs Web Capability and Persona Gap Analysis

**Audit date:** 27 July 2026  
**Figma source:** [AstroSpace — Mobile App (Hi-Fi)](https://www.figma.com/design/RRhuTcaKIhqILZW7JUKFzI)  
**Repository scope:** Angular web app and `/m` mobile routes, Python/FastAPI APIs, Vedic engine, product vision, persona pack, and mobile screen backlog.

---

## 1. Executive conclusion

The Figma file has strong feature breadth. It contains **100 top-level canvas nodes** (screens, states, components, and a few utility frames) covering onboarding, Today, Ask, remedies, muhurta, charts, dashas, transits, calendar, compatibility, readings, notes, settings, notifications, native surfaces, search, and subscription.

The largest gap is **not the number of screens**. It is that the file is predominantly a **Balanced-mode product with a Guided/Practitioner selector attached**.

The three modes currently exist in:

- onboarding (`5 · Persona Type`, node `8:2`);
- settings (`25b · Settings — Mode & Tone`, node `67:89`);
- one explicitly Balanced evidence sheet (`7d · Why this reading`, node `22:23`).

They do not yet change the core experience enough. Today, Ask, Chart, Calendar, Compatibility, Remedies, and the bottom navigation mostly have one hierarchy, one information density, and one set of labels.

### Product decision

Do **not** create three separate apps or calculation paths.

Use:

- one profile and calculation model;
- one route tree and shared screen components;
- the same safety rules and truth for every user;
- three presentation contracts controlling priority, terminology, density, evidence, and default navigation.

The same calculation can therefore appear as:

- **Guided:** “A steady day. Start delayed work; avoid final paperwork before noon.”
- **Balanced:** the same answer, with “Why this?” one tap away.
- **Practitioner:** the same answer with the active dasha chain, panchanga factors, gochara, vedha, Ashtakavarga support, conventions, and provenance visible.

---

## 2. What the product is trying to be

The web app and vision documents establish AstroSpace as a **personal astrology intelligence layer**, not a generic horoscope feed.

The mobile product must preserve these principles:

1. **Computed and personal:** guidance comes from the saved birth profile, current sky, active periods, classical rules, and knowledge base.
2. **People-first:** the user thinks about themselves, a child, partner, parent, or client—not about which technical engine to open.
3. **Action-oriented:** the product should answer “What matters?”, “What should I do?”, “When?”, and “Why?”
4. **Longitudinal:** profiles, readings, notes, questions, prediction claims, and timing history accumulate over time.
5. **Progressive depth:** plain guidance and practitioner-grade data are different views of the same underlying result.
6. **Auditable trust:** conventions, calculation evidence, confidence, and provenance must be available.
7. **Safe and non-fatalistic:** no death/lifespan prediction, no fear-selling, and professional referral for medical, legal, financial, or crisis concerns.
8. **India-first but diaspora-capable:** Telugu/audio, current-location timing, timezone clarity, regional conventions, and family profiles are core rather than decorative.

---

## 3. Web and engine capability baseline

The current web workspace exposes roughly fifteen profile-level feature areas plus a multi-profile home. The backend is deeper than the original static `frontend/` prototype and some older design notes.

| Capability family | Current web/backend depth | Mobile implication |
|---|---|---|
| Multi-profile home | “Today across profiles,” recent profiles, alert count, relation count | Mobile needs a family/profile overview, not only a switcher |
| Daily intelligence | Verdict, focus, best/avoid, work/money/relationship/energy tone, timing note, plain and technical why, colour, number, tarabala, chandrabala | Today must adapt by mode without changing the result |
| Panchanga | Tithi, nakshatra, yoga, karana, vara, masa, ritu, ayana, sunrise/sunset, moonrise/moonset | Guided needs only relevant actions; Practitioner needs the full almanac |
| Day windows | Rahu Kalam, Yamaganda, Gulika, Abhijit, Brahma Muhurta, Durmuhurta, Choghadiya, Hora, Varjya, Amrit Kalam, Disha Shool, Panchaka, Bhadra | Calendar day detail should expose more than the current selected windows |
| Vedic birth reference | Avkahada, Ghatak, favourable points, graha positions, dignity, retrograde, combustion, provenance | Mostly represented in Figma Practitioner Reference |
| Charts | D1 plus 20 supported vargas from D1–D60, Eastern/South/North styles, placements and annotations | Strong Figma coverage |
| Dashas | Vimshottari through five levels plus Yogini | Figma names five levels but does not design full Sookshma/Prana exploration |
| Strength and advanced | Classical Shadbala, BAV/SAV, Shodhana, Pinda, Kakshya, Jaimini karakas/arudhas/special lagnas | Broad Figma coverage; dense-table completion needs verification |
| Yogas and doshas | Yoga/dosha detection, strength, cancellations, provenance | Strong Figma coverage |
| Gochara and transits | Plain gochara, aspects, vedha, Ashtakavarga weighting, severity, timeline | Strong Figma coverage |
| Compatibility | All eight Kootas, 36-point score, Nadi/Bhakoot cancellations, Manglik/Gandanta/Grahan checks, D1/D9 comparison, AI narrative | Figma result is too summarized for Balanced/Practitioner |
| Readings and accuracy | Daily/weekly/yearly generation, saved versions, feedback, claims and outcomes | Strong Figma coverage |
| Ask | Saved threads, grounded answer generation, safety refer-out | Strong core Figma flow; mode-specific answer depth is missing |
| Remedies | Personalized remedy catalog, saved practices, completions, and streaks | Designed in Figma and supported by newer APIs |
| Muhurta | Goal list, ranked personalized windows, saved muhurtas | Designed in Figma and supported by newer APIs |
| Festivals | Catalog, yearly/upcoming festival data | Designed in Figma; personalization and regional rules need more detail |
| Notifications/native | Preferences, alerts, push tokens, widgets, live activities | Figma goes beyond the web UI and has backend foundations |
| Settings | Experience mode, tone, ayanamsha, node type, chart style, location/device preferences | Figma is missing an explicit appearance/theme and accessibility surface |
| Admin console | Knowledge sources, users, chunks, review, retrieval testing, taxonomy, audit | Internal web-only surface; no mobile parity required |

### Important source-of-truth note

`design-thinking/capabilities.md` describes remedies, muhurta, festivals, notifications, and experience modes as not built. That document is now partly stale. The current API and database contain foundations for these capabilities. Future audits should validate against code and tests first, then update the older capability note.

---

## 4. Figma coverage against the web app

Legend:

- **Covered** — the main capability and a usable mobile flow are designed.
- **Partial** — a screen exists, but meaningful web depth or persona behavior is absent.
- **Missing** — no clear mobile screen/flow was found.
- **Beyond web** — designed for native/mobile but not a primary web workspace feature.

| Area | Figma evidence | Status | Gap |
|---|---|---:|---|
| Landing, auth, password recovery | Nodes `4:2`, `5:2`, `62:88`, `206:160` | Covered | Add guest-to-account merge and auth failure/expired-link states |
| Persona and tone selection | Nodes `8:2`, `67:89` | Partial | Selection does not visibly transform the rest of the app |
| Birth details and recalculation | Nodes `11:2`, `206:493`, `206:190` | Partial | No unknown/approximate birth-time path, validation failure, or relocation explanation |
| Persona-specific first “Aha” | No dedicated Guided/Balanced/Practitioner result screens | Missing | Onboarding should prove value differently before landing on Today |
| Today | Nodes `13:2`, `20:2`, `21:22`, `22:23`, `23:25` | Partial | Excellent Balanced screen; no Guided or Practitioner hierarchy |
| Ask | Nodes `25:25`, `25:123`, `26:54`, `27:83`, `206:223`, `108:417` | Partial | Answer template is plain-first for everyone; Practitioner evidence and parameters are absent |
| Remedies and tracking | Nodes `29:55`, `29:109` | Covered | Add evidence/caution/source depth for Practitioner and feasibility alternatives for Guided |
| Goal-based muhurta | Nodes `30:56`, `31:57` | Covered | Add rule filters, exclusion reasons, timezone, save confirmation, and Practitioner raw factors |
| Chart hub and three styles | Nodes `35:57`, `36:86`, `56:88`, `57:88` | Covered | Current hub is too technical for Guided as a primary tab |
| Planet detail/provenance | Nodes `36:201`, `36:247` | Covered | Technical detail should default open in Practitioner and closed in Guided |
| Vargas | Nodes `39:87`, `61:88`, `61:195` | Covered | Confirm placement/table behavior for all 20 supported charts and small screens |
| Vimshottari/Yogini | Nodes `40:87`, `59:88`, `59:258`, `59:427` | Partial | Sookshma and Prana screens/navigation are missing despite five-level copy |
| Yogas and doshas | Nodes `41:87`, `41:210`, `62:140` | Covered | Need consistent provenance and mode-specific language for every flag |
| Shadbala/Ashtakavarga/Jaimini | Nodes `41:149`, `60:88`, `60:257`, `117:124`–`118:383` | Partial | Broad coverage, but full reductions, remaining columns, Kakshya, and deep drill-down need explicit designs |
| Gochara and full transits | Nodes `91:89`, `92:89`, `206:550` | Covered | Add filter/date controls, exactness/orb, and Practitioner traceability |
| Calendar and festival | Nodes `93:89`, `94:118`, `116:124` | Partial | Month view is festival-first; web’s full intelligence feed and complete panchanga need mode-aware coverage |
| Compatibility | Nodes `97:119`, `97:144`, `98:119`, `110:121` | Partial | Result shows only four highlighted Kootas; full eight-Koota table, cancellations, D1/D9, inputs, and provenance are missing |
| Readings and claims | Nodes `113:122`, `114:124` | Covered | Add empty/history/loading/error states and distinguish forecast from retrospective claim |
| Notes | Node `115:124` | Covered | Add edit conflict/offline state and export behavior |
| Profile switching | Node `79:89` | Partial | No complete Manage Profiles screen, profile overview, archive/delete, relationship metadata, or “Today across profiles” |
| Settings | Nodes `66:89`–`69:180`, `206:641` | Partial | Add appearance/theme, accessibility, data export progress, permissions, and per-device settings |
| Notifications | Nodes `67:173`, `206:354` | Covered | Add permission-denied and quiet-hours states; revise deterministic/fear-adjacent copy |
| Search | Node `206:591` | Beyond web | Define searchable entities, permissions, empty state, and result destination |
| Subscription | Node `206:302` | Beyond web | Define entitlement boundaries; never paywall safety, calculation provenance, or critical cancellation context |
| Native surfaces | Nodes `103:92`–`107:101` | Beyond web | Strong concept coverage; needs privacy/redaction and stale-data states |
| Dark mode examples | Nodes `108:92`, `108:186`, `108:246` | Partial | Three examples are not a complete theme specification and no appearance setting exists |
| Generic states | Nodes `108:417`, `110:121`, `110:153`, `206:190` | Partial | Offline, empty, permission, validation, expired data, partial-result, and retry states remain incomplete |

---

## 5. The three persona contracts

The mode is a **depth preference**, not a belief score and not a different truth.

| Contract | Guided | Balanced | Practitioner |
|---|---|---|---|
| Primary question | “What does this mean and what should I do?” | “What does this mean, and why?” | “Show the calculation and let me inspect it.” |
| Default density | One verdict, one action, one caution | Plain summary plus optional evidence | Tables, parameters, timelines, filters, and provenance |
| Terminology | Everyday language; translate or hide Sanskrit terms | Plain label first, term second | Classical terms first, with exact values |
| Evidence | “Why?” available but not visually dominant | One tap away | Open by default and exportable |
| Chart visibility | Secondary; story/meaning first | Preview plus drill-down | Primary workbench |
| Audio | Prominent default action | Available | Optional utility |
| Safety tone | Reassuring and clear | Calm and candid | Direct and technically qualified |
| Notifications | Few, action-based, gentle | Configurable summaries and windows | Exact transit/period alerts with filters |
| Error recovery | Plain next step | Error plus cause | Error, parameters, data freshness, and diagnostic detail |

### Recommended primary navigation

The underlying routes remain shared, but priority and labels should adapt.

| Position | Guided | Balanced | Practitioner |
|---:|---|---|---|
| 1 | Today | Today | Today |
| 2 | Ask | Ask | Chart |
| 3 | What to do | Chart | Periods |
| 4 | Calendar | Calendar | Transits |
| 5 | More | More | More |

Additional rules:

- Guided “What to do” opens remedies and muhurta.
- Balanced retains the current Figma navigation.
- Practitioner keeps Ask, Calendar, Compatibility, Readings, and Notes in More/shortcuts; they are not removed.
- A user can change mode at any time without losing data, navigation history, saved items, or calculation settings.

---

## 6. Core screens that need mode variants

### 6.1 Onboarding result / first Aha — missing

Add a result screen after chart computation and before the full app.

**Guided**

- plain personal signature;
- one reassuring strength;
- one useful “today” action;
- Listen and Continue.

**Balanced**

- signature plus Sun/Moon/Lagna;
- one “why this is personal” explanation;
- preview of Today and Chart.

**Practitioner**

- D1 chart;
- exact Lagna, Moon, nakshatra/pada;
- current five-level period stack where available;
- conventions and “Open workbench.”

### 6.2 Today (`13:2`, `20:2`)

The existing design is the Balanced baseline.

**Guided variant**

- retain day score only if explained in words;
- lead with verdict, Do, Avoid, next important window, audio;
- collapse panchanga and “lucky signature” into “See today’s details”;
- use “Good time / Avoid this time” before classical labels.

**Practitioner variant**

- show date, current location/timezone, data freshness, ayanamsha, node type;
- show active Maha/Antar/Pratyantar/Sookshma/Prana stack where available;
- show tithi/nakshatra/yoga/karana and relevant end times;
- show tarabala, chandrabala, active gochara, vedha, AV weighting;
- keep plain verdict, but put technical evidence in the first viewport.

### 6.3 Why this reading (`22:23`)

Create three component variants:

- Guided: short cause-and-effect explanation with unfamiliar terms translated.
- Balanced: current plain-first/calc-underneath design.
- Practitioner: calculation tree, exact inputs, conventions, confidence, KB references, and timestamp.

### 6.4 Ask home and answer (`25:25`, `26:54`)

**Guided**

- life-area prompts;
- voice-first;
- short verdict, action, caution, referral when needed.

**Balanced**

- current answer;
- expandable Why, Listen, Share, follow-up.

**Practitioner**

- question scope: profile, date range, location, domain, chart/varga;
- answer sections for natal promise, active dasha, gochara, supporting/contradicting factors;
- visible sources/provenance and raw calculation links;
- ability to pin result to Notes or compare dates.

### 6.5 Chart hub (`35:57`)

**Guided**

- rename to “Your story” or “Your chart”;
- lead with strengths and life areas;
- move Vargas, Shadbala, AV, and Jaimini under Advanced.

**Balanced**

- current chart preview and Explore list.

**Practitioner**

- workbench landing with D1/D9, current period, gochara, graha table, quick chart-style and ayanamsha controls;
- recent/pinned references and export.

### 6.6 Calendar (`93:89`, `116:124`)

**Guided**

- observances, next important window, reminders, simple good/avoid labels.

**Balanced**

- current month plus day timeline, personal day checks, and expandable why.

**Practitioner**

- filterable panchanga/timing/transit/dasha/festival layers;
- full window list including Hora, Durmuhurta, Gulika, Disha Shool, Panchaka, Bhadra, rise/set times;
- event provenance, regional convention, current timezone, and export.

### 6.7 Remedies (`29:55`)

**Guided**

- one feasible practice at a time;
- substitutions for cost, mobility, dietary, location, or religious preference;
- gentle reminders and streaks without guilt.

**Balanced**

- current recommendation plus why, evidence strength, and alternatives.

**Practitioner**

- triggering rule/placement/period;
- classical source or knowledge reference;
- contraindications and cancellation logic;
- ability to inspect or reject a recommendation.

### 6.8 Muhurta (`30:56`, `31:57`)

**Guided**

- top three windows with a plain reason and Add/Remind.

**Balanced**

- current cards plus relevant supporting and caution factors.

**Practitioner**

- constraints, excluded windows and why, panchanga elements, tarabala/chandrabala, location/timezone, rule set, and comparison/export.

### 6.9 Compatibility (`98:119`)

**Guided**

- overall verdict, strongest support, main caution, cancellations, and non-fatalistic framing.

**Balanced**

- all eight Kootas, score, important cancellations, dosha checks, and expandable D1/D9 comparison.

**Practitioner**

- full inputs, Koota calculation table, Nadi/Bhakoot cancellation rules, Manglik exceptions, Gandanta/Grahan checks, D1/D9 side-by-side, conventions, and report export.

---

## 7. Highest-priority gaps

### P0 — required before claiming three-mode support

1. **Mode application contract**
   - Persist `experience_mode` and tone through the settings API.
   - Apply mode to navigation, labels, disclosure, density, audio priority, and evidence defaults.
   - Keep calculations and safety invariant.

2. **Core Figma variants**
   - Design Guided/Balanced/Practitioner variants for Aha, Today, Why, Ask answer, Chart hub, Calendar day, Compatibility result, Remedies, and Muhurta.

3. **Multi-profile mobile home**
   - Add “Today across profiles,” priority alerts, recent profiles, Add/Manage Profile, and privacy-safe switching.
   - The existing switcher is necessary but not equivalent to the web dashboard.

4. **Practitioner parity**
   - Add Sookshma and Prana navigation.
   - Complete eight-Koota compatibility and D1/D9 comparison.
   - Complete panchanga/timing layers, AV reductions/Kakshya, transit parameters, and provenance.

5. **Profile and birth-data states**
   - Manage/add/edit/archive/delete profiles.
   - Unknown or approximate birth time.
   - Birth place versus current location.
   - Timezone change/travel.
   - Recalculation impact and invalid/ambiguous city handling.

6. **Safety and resilience states**
   - Offline/stale result, partial calculation, API retry, permission denied, audio unavailable, notification denied, expired auth link, subscription restore failure, and data-export progress.

### P1 — required for a complete, trustworthy product

1. Full appearance and accessibility settings.
2. Search information architecture and empty/no-permission states.
3. Reading/history empty, loading, retry, version comparison, and claim-review states.
4. Remedy alternatives and evidence.
5. Muhurta filtering, saved-window management, calendar conflict, and timezone clarity.
6. Regional festival rules and location-sensitive observance behavior.
7. Native widget/share privacy controls and stale-data indicators.

### P2 — commercialization and advanced platform work

1. Subscription entitlement map and upgrade states.
2. Watch, Live Activity, Siri/assistant, and widget production specifications.
3. Practitioner export/report templates.
4. Cross-profile comparison and practitioner/client workflow.

---

## 8. Exact Figma worklist

### Add

| Proposed screen/variant | Purpose |
|---|---|
| `6c · Aha — Guided` | Plain signature, one strength, one action, Listen |
| `6d · Aha — Balanced` | Signature plus Big Three and why |
| `6e · Aha — Practitioner` | D1, exact birth constants, current period, conventions |
| `7G / 7B / 7P · Today` | Three first-viewport hierarchies |
| `7d-G / 7d-B / 7d-P · Why` | Evidence disclosure by mode |
| `10G / 10B / 10P · Ask Answer` | Mode-specific answer composition |
| `16G / 16B / 16P · Chart Hub` | Story, explorer, and workbench entry points |
| `21e · Sookshma` and `21f · Prana` | Complete Vimshottari five-level parity |
| `28G / 28B / 28P · Calendar Day` | Action, explanation, and full almanac layers |
| `30d · Full Compatibility Detail` | Eight Kootas, cancellations, checks, D1/D9 |
| `Profiles · Overview` | Today across profiles |
| `Profiles · Manage` | Add/edit/archive/delete/relation/privacy |
| `Settings · Appearance & Accessibility` | Theme, text size, contrast, motion, screen reader, audio |
| `States · Birth time unknown/approximate` | Explain accuracy and supported fallback |
| `States · Offline/stale/partial` | Safe degraded experience |
| `States · Permissions` | Notifications, microphone, calendar, location |

### Revise

| Existing screen | Required revision |
|---|---|
| `5 · Persona Type` | Preview how the same result looks in each mode; state that truth and safety do not change |
| `7 · Today` | Add current location/timezone and freshness; create mode variants |
| `25 · Settings — Home` | Add Appearance & Accessibility and Manage Profiles |
| `25b · Mode & Tone` | Show affected surfaces and preserve separate “depth” and “delivery tone” controls |
| `26 · Profile switcher` | Add “Today across profiles” and “Manage profiles” |
| `30c · Gun Milan Results` | Add full-detail route and complete cancellation/check coverage |
| `31 · Readings` | Add no-history/loading/error/version-comparison states |
| `34 · Subscription` | Define entitlements; remove any implication that safety or basic calculation transparency is premium |
| `35 · Notification Center` | Use non-deterministic, action-based language and show profile/location context |
| `36 · Search` | Add entity filters, empty state, and result destination rules |

---

## 9. Figma-to-data validation requirement

The Figma values are design fixtures. A screen is not validated merely because its labels resemble backend output.

Every major screen should have a small annotation/table containing:

| Field | Required annotation |
|---|---|
| Data source | API endpoint and response key |
| Profile context | Whose chart is being used |
| Time context | Date, time, timezone, current versus birth location |
| Conventions | Ayanamsha, node type, house/chart style where relevant |
| Freshness | Generated/calculated timestamp and stale behavior |
| Mode behavior | Hidden, summarized, collapsed, or expanded per mode |
| Safety behavior | Disclaimer, referral, prohibited outcome, or uncertainty rule |
| Empty/error behavior | What is shown when data is absent or calculation fails |

Example for Today:

- `GET /api/v1/context/{kundli_id}/daily`
- `GET /api/v1/panchanga/{kundli_id}/today`
- profile ID and relation;
- current location and timezone;
- plain versus technical why;
- mode disclosure rules;
- loading/offline/stale fallback.

---

## 10. Current `/m` implementation reality

The Angular app already has `/m` routes for most major Figma flows, and many components reference their Figma node IDs directly. This is a good traceability foundation.

However, the existence of a route does not mean the capability is complete:

- the mobile shell currently uses one static tab set: Today, Ask, Chart, Calendar, More;
- onboarding and settings mode pickers default to local `balanced` signals;
- the mobile mode choice is not visibly applied app-wide;
- several mobile screens still contain hard-coded fixture content rather than API data;
- the backend database/settings model already has `experience_mode`, so the missing work is primarily end-to-end wiring and adaptive presentation;
- Figma and code should be reviewed together whenever a screen is promoted from mock to production.

This audit intentionally separates:

1. **Engine/API capability**
2. **Web UI capability**
3. **Figma design coverage**
4. **Mobile implementation completeness**

Conflating these four layers will overstate readiness.

---

## 11. Definition of “mobile coverage complete”

A capability is complete only when:

- it is reachable in all relevant persona modes;
- the same calculation truth is preserved across modes;
- Guided, Balanced, and Practitioner disclosure rules are specified;
- every visible field maps to a real endpoint/key;
- profile, location, timezone, and convention context are explicit;
- loading, empty, error, offline, stale, and permission states exist;
- safety language and referral behavior are defined;
- accessibility and Telugu/audio behavior are defined where relevant;
- the implementation is tested with realistic fixtures, not only Figma example text.

---

## 12. Recommended next design sequence

1. Define the mode contract and adaptive navigation.
2. Design the three onboarding Aha screens.
3. Create Today, Why, and Ask Answer variants for all three modes.
4. Create Guided/Balanced/Practitioner Chart Hub and Calendar Day variants.
5. Close concrete parity gaps: multi-profile home, five-level dashas, full compatibility, profile management, complete practitioner panchanga.
6. Add resilience, permissions, accessibility, and location/timezone states.
7. Annotate each production-bound Figma screen with endpoint/key mappings.
8. Only then finalize subscription boundaries and native extensions.

This order validates the core promise—**the right depth for the right person, backed by the same real calculation**—before expanding the number of surfaces.
