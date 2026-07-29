# AstroSpace — Product Plan

> **Status: superseded, with one live exception.**
>
> Most of this is history — the native app is tracked in
> [docs/mobile_screen_build_plan.md](docs/mobile_screen_build_plan.md) and the
> product intent in [VISION.md](VISION.md).
>
> **Do not delete this file.** "Phase 1 Validation" below records an open,
> unmet commitment: the Vedic engine has never been checked against a verified
> reference chart, and `tests/test_vedic.py` cites this section as the reason
> golden-chart tests do not exist. That obligation outlives the plan around it.
> Delete this file only once a reference chart has been supplied and those
> tests are written.

## Vision

A Vedic astrology platform where users create an account, manage multiple personas (self, family, friends), and get accurate divisional charts (D1–D30), Avkahada Chakra details, and AI-powered readings — all grounded in correct Vedic calculations.

---

## Known Issues to Fix (Pre-existing bugs)

| Bug | File | Fix |
|-----|------|-----|
| `auth_token` is not a valid Anthropic SDK param — crashes all agents | `astrospace/agents/base.py:17` | Replace with `api_key=` |
| Agents are synchronous, blocking FastAPI's event loop for 30–90s | All agent routes | Run in background thread / async wrapper |
| Chart wheel ignores Ascendant — Aries always at top | `frontend/app.js:258` | Rotate wheel so Ascendant sits at 9 o'clock |
| `BackgroundTasks` imported but never used in reading route | `astrospace/api/reading_routes.py` | Wire up or remove import |
| `HoroscopeAgent`, `TransitAgent`, `ReadingAgent` routes unreachable from UI | `astrospace/api/routes.py` | Expose in new frontend or deprecate |
| GitHub Pages `docs/` site calls `/api/v1/...` which 404s on static hosting | `docs/app.js` | Remove or replace with static content |
| ~~Transit tool crashed on kerykeion v5 rename (`p.pos` → `p.position`), 500ing all readings~~ | `astrospace/core/transits.py` | ✅ Fixed 2026-07-07 + agent tool errors now returned to model instead of crashing |
| ~~Reading period labels used UTC date instead of kundli-local date; daily cache used 20h timer instead of local-date rollover~~ | `astrospace/api/reading_routes.py`, `period_agent.py` | ✅ Fixed 2026-07-07 — labels follow kundli's timezone |

---

## Phase 1 — Vedic Engine (Week 1–2)

> **Status (2026-07-07): implemented, pending reference-chart validation.**
> Engine lives in `astrospace/core/vedic/` (pyswisseph/Moshier, Lahiri default, mean nodes).
> 20 vargas (D1–D60), panchanga, nakshatra, Avkahada, Ghatak, favourable points, dignity — all built.
> 44 unit tests green (BPHS formula boundaries + real-sky invariants: sankranti windows, Chaitra Purnima 2024, lagna-at-sunrise = Sun's sign, ayanamsha magnitude).
> API: `POST /api/v1/vedic/chart` + per-kundli GET routes, registered in `main.py`.
> Rules that await the user's reference chart are flagged `VERIFY` in code and `verified_rule: false` in API output: D5/D6/D8/D11 rules, Paya, Tatwa, Vashya, Vihaga, Nadi-pada, numerology table, functional benefics, Ghatak (yoga/karana/prahar columns deliberately return null until verified).

**Goal:** Accurate sidereal planetary positions and all Vedic-specific fields. Every other phase depends on this being correct. Validate against the reference chart (E.V.K. Sivanand, 4 May 1961, 13:36, Visakhapatnam) before proceeding.

### 1.1 Sidereal Position Engine

- Apply Lahiri ayanamsha correction to kerykeion tropical positions
- Output sidereal longitude for all 9 grahas (Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Rahu, Ketu)
- Support configurable ayanamsha (Lahiri default; Raman, KP as options)
- Unit tests: compare against known ephemeris values

**File:** `astrospace/core/vedic/positions.py`

### 1.2 Divisional Chart Engine (D1–D30)

Each Dn chart assigns a planet to a sign by dividing its sign into n equal parts. Implement all standard Parashari varga charts:

| Chart | Name | Division | Primary Use |
|-------|------|----------|-------------|
| D1 | Rashi | 30° | All life matters — primary chart |
| D2 | Hora | 15° | Wealth, financial prosperity |
| D3 | Drekkana | 10° | Siblings, courage, short journeys |
| D4 | Chaturthamsha | 7°30' | Property, fixed assets, fortune |
| D5 | Panchamamsha | 6° | Children, spiritual merit, past life |
| D6 | Shashthamsha | 5° | Health, enemies, obstacles |
| D7 | Saptamamsha | 4°17' | Children, progeny, grandchildren |
| D8 | Ashtamamsha | 3°45' | Longevity, hidden matters |
| D9 | Navamsha | 3°20' | Spouse, dharma, spiritual strength — most important after D1 |
| D10 | Dashamsha | 3° | Career, profession, status, fame |
| D11 | Ekadasha | 2°44' | Gains, elder siblings, fulfillment |
| D12 | Dwadashamsha | 2°30' | Parents, ancestors, past birth |
| D16 | Shodashamsha | 1°52' | Vehicles, comforts, pleasures |
| D20 | Vimshamsha | 1°30' | Spiritual progress, upasana |
| D24 | Chaturvimshamsha | 1°15' | Education, learning, knowledge |
| D27 | Bhamsha / Nakshatramsha | 1°6' | Physical strength, vitality |
| D30 | Trimshamsha | 1° | Misfortunes, evils, difficulties |

**Formula:** For a planet at sidereal longitude L in sign S (0–11):
- Degree within sign: d = L mod 30
- Division index: floor(d / (30/n))
- Map to output sign using Parashari rules per chart

**File:** `astrospace/core/vedic/vargas.py`

### 1.3 Nakshatra Engine

- 27 nakshatras, each spanning 13°20' of the zodiac
- Calculate nakshatra from Moon's sidereal longitude
- Calculate Pada (1–4): each nakshatra has 4 padas of 3°20'
- Nakshatra lord (Vimshottari sequence: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury)
- Output: nakshatra name, pada number, nakshatra lord

**File:** `astrospace/core/vedic/nakshatra.py`

### 1.4 Panchanga Engine (Five Limbs of the Day)

| Field | Description |
|-------|-------------|
| Tithi | Lunar day (1–30); based on Sun–Moon longitudinal difference |
| Vara | Day of week with ruling planet |
| Nakshatra | Moon's nakshatra (see 1.3) |
| Yoga | Sum of Sun + Moon longitudes divided into 27 parts |
| Karana | Half-tithi (11 fixed + 4 movable types) |

**File:** `astrospace/core/vedic/panchanga.py`

### 1.5 Avkahada Chakra Engine

All fields required for the Avkahada Chakra table (as shown in reference screenshot):

| Field | Source |
|-------|--------|
| Lagna | Ascendant sign (sidereal) |
| Lagna Lord | Ruling planet of Lagna sign |
| Rashi | Moon sign (sidereal) |
| Rashi Lord | Ruling planet of Moon sign |
| Nakshatra | Moon's nakshatra |
| Nakshatra Lord | Lord of Moon's nakshatra |
| Charan (Pada) | 1–4 within nakshatra |
| Tithi | From Panchanga engine |
| Paya | Metal quality (Gold/Silver/Copper/Iron) based on Rashi-Nakshatra combination |
| S.S. Yoga | From Panchanga engine |
| Karana | From Panchanga engine |
| Varna | Caste group based on Rashi (Brahmin/Kshatriya/Vaishya/Shudra) |
| Tatwa | Element (Agni/Jala/Vayu/Prithvi/Akasha) based on Nakshatra |
| Vashya | Who is under control — based on Rashi |
| Yoni | Animal symbol based on Nakshatra |
| Gana | Temperament (Deva/Manushya/Rakshasa) based on Nakshatra |
| Nadi | Pulse type (Aadi/Madhya/Antya) based on Nakshatra |
| Nadi Pada | Sub-division of Nadi |
| Vihaga | Bird symbol |
| First Letters | Suggested name starting letters from Nakshatra pada |
| Sun Sign | Western sun sign (tropical) |
| Decanate | 10° division of sun sign (1/2/3) |

**File:** `astrospace/core/vedic/avkahada.py`

### 1.6 Ghatak (Malefics) Engine

Inauspicious combinations specific to a person's chart:

| Field | Derivation |
|-------|-----------|
| Ghatak Rashi | Inauspicious moon sign for this lagna |
| Ghatak Month | Inauspicious month |
| Ghatak Tithi | Inauspicious tithis (typically 3 values) |
| Ghatak Day | Inauspicious day of week |
| Ghatak Nakshatra | Inauspicious nakshatra |
| Ghatak Prahar | Inauspicious time division |
| Ghatak Lagna | Inauspicious ascendant |
| Ghatak Yoga | Inauspicious yoga |
| Ghatak Karana | Inauspicious karana |

**File:** `astrospace/core/vedic/ghatak.py`

### 1.7 Favourable Points Engine

| Field | Derivation |
|-------|-----------|
| Lucky Number | Numerological from birth date |
| Good Numbers | Based on lagna lord and moon sign |
| Evil Numbers | Adverse numbers |
| Good Years | Age years with benefic progressions |
| Lucky Days | Days ruled by benefic planets for this chart |
| Good Planets | Natural + functional benefics |
| Evil Planets | Natural + functional malefics |
| Friendly Signs | Signs friendly to lagna |
| Good Lagna | Auspicious ascendants for the native |
| Lucky Metal | Based on lagna lord |
| Lucky Stone | Gemstone for lagna lord |
| Lucky Time | Sunrise / specific hora |
| Lucky Direction | Direction of lagna lord |

**File:** `astrospace/core/vedic/favourable.py`

### 1.8 Planet Strength (Shadbala — simplified)

- Dignity: Exalted / Own sign / Friendly / Neutral / Enemy / Debilitated
- Percentage score (0–100) for UI strength bar
- Full Shadbala (6-factor) as future enhancement

**File:** `astrospace/core/vedic/strength.py`

### Phase 1 API additions

Update `astrospace/api/routes.py` and add `astrospace/api/vedic_routes.py`:

```
GET  /api/v1/vedic/{kundli_id}/d{n}          → D-chart for given varga (1–30)
GET  /api/v1/vedic/{kundli_id}/avkahada      → Full Avkahada Chakra
GET  /api/v1/vedic/{kundli_id}/panchanga     → Panchanga for birth date
GET  /api/v1/vedic/{kundli_id}/all-charts    → All D-charts in one payload
```

### Phase 1 Validation

Before moving to Phase 2, all computed fields must match a verified reference chart provided by the user. Reference chart TBD — user will supply birth details and expected output values for validation.

---

## Phase 1.5 — Daily Panchanga (added 2026-07-07)

> **Status: core shipped 2026-07-07.** `kala.py` (Rahu Kalam, Yamaganda, Gulika,
> Durmuhurta, Brahma/Abhijit muhurta, Godhuli, Choghadiya, Horas),
> `moontimes.py` (bisection root-finding for tithi/nakshatra/yoga/karana end
> times, Varjya + Amrit Kalam from ghati tables), `panchanga_day.py`
> (orchestrator + personalization: Tarabala, Chandrabala/Chandrashtama, Ghatak
> alerts). API: `GET /api/v1/panchanga/today?city=..` and
> `GET /api/v1/panchanga/{kundli_id}/today`. UI: "Today" tab with day timeline.
> 21 tests incl. full-moon-instant golden test.
> VERIFY pending: durmuhurta table, choghadiya tables, varjya/amrit ghati
> tables, godhuli span — validate against DrikPanchang.
>
> **Remaining (Bucket 3–5):** Hindu calendar (masa Amanta/Purnimanta, Adhika
> Masa, Vikram/Shaka samvat, samvatsara, ritu/ayana), month-grid calendar API,
> festivals rules engine (~50 majors + Ekadashi/Pradosham/Sankashti autogen),
> Sade Sati tracker, AI muhurta finder, notifications.

## Phase 1.6 — Ask AI (added 2026-07-08)

> **Status: shipped.** `agents/qa_agent.py` — VedicQAAgent with kundli-bound
> tools (get_birth_chart, get_varga_chart, get_today_panchanga,
> get_current_gochara incl. sade-sati). Tools are bound server-side to one
> kundli so the model can never mis-enter birth data. System prompt enforces
> grounding: every answer ends with "Astrological basis:" citing exact
> placements; unverified-table caveats surfaced. `POST /api/v1/ask/{kundli_id}`
> with client-held history (capped 12 turns). UI: "Ask AI" chat tab with
> per-answer "grounded on" tool chips. base.py gained run_messages()
> (conversation + tools_used tracking).

## Phase 2 — Core UI (Week 3–4)

**Goal:** Complete frontend redesign. User can sign up, add personas, and view the full Kundli details page with all divisional charts.

### 2.1 Auth Screens

- Sign up (name, email, password)
- Sign in
- Forgot password (email reset flow)
- JWT session tokens stored in localStorage
- All API routes protected with auth middleware

**Files:** `frontend/auth.html`, `frontend/auth.js`, `astrospace/api/auth_routes.py`

### 2.2 Dashboard

- Left sidebar: list of personas with avatar (zodiac emoji), name, sun sign, relation
- Top bar: user name, date, persona count stats
- Empty state when no personas added
- Quick-add persona button

### 2.3 Add / Edit Persona Form

Fields:
- Full name (required)
- Relation (Self / Spouse / Father / Mother / Child / Friend / Other)
- Date of birth: day, month, year (required)
- Time of birth: hour, minute (defaults to 12:00 if unknown)
- Place of birth: city, country code (required)
- Notes (optional)

On save: call backend → calculate chart → store in DB → navigate to Kundli detail page.

### 2.4 Kundli Details Page — Basics Tab

Matching the reference screenshot layout:
- Header: name, DOB, time, place, lat/long, ayanamsha, sidereal time
- Big Three badges: Sun sign, Rashi, Lagna
- **Avkahada Chakra** table (left column)
- **Ghatak (Malefics)** table (right column top)
- **Favourable Points** grid (right column bottom)

### 2.5 Divisional Charts UI

- Horizontal scrollable tab strip: D1 · D2 · D3 · D4 · D5 · D6 · D7 · D8 · D9 · D10 · D11 · D12 · D16 · D20 · D24 · D27 · D30
- Each tab shows:
  - **Left:** North Indian kundli chart (canvas-rendered, 4×4 grid with proper ascendant placement)
  - **Right:** Planet placement table with sign, house, dignity, strength bar + AI analysis panel
- D9 (Navamsha) and D10 (Dashamsha) get visual prominence (starred tabs)
- Chart style toggle: North Indian / South Indian (future)

### 2.6 Navigation Structure

```
/ (landing)          → sign in / sign up
/dashboard           → persona list
/persona/:id         → kundli detail (tabs: Basics · Charts · Readings · Compatibility · Notes)
/persona/:id/chart/:d → specific D-chart with analysis
/settings            → account settings
```

---

## Phase 3 — AI Layer (Week 5–6)

**Goal:** Streaming, non-blocking AI readings per chart, per period, and compatibility analysis.

### 3.1 Fix Blocking Agent Architecture

- Wrap all `agent.run()` calls in `asyncio.to_thread()` or `BackgroundTasks`
- Fix `auth_token` → `api_key` bug in `base.py`
- Add streaming endpoint: `POST /api/v1/readings/{kundli_id}/stream` (SSE)
- Frontend reads SSE stream and renders markdown tokens as they arrive

### 3.2 Per-Chart AI Analysis

- Each D-chart tab has an "Generate AI reading" button
- Analysis covers: what this varga shows, key placements, strengths/weaknesses, practical guidance
- Cached per (kundli_id, varga, generation_date)
- Agent tools: `get_varga_chart`, `lookup_vedic_knowledge`, `get_planet_dignities`

### 3.3 Period Readings (Daily / Weekly / Monthly / Yearly)

- Powered by `PeriodAgent` (already partially built)
- Add Vimshottari Dasha period to prompt context
- Readings tab on persona detail page
- Period selector: Daily · Weekly · Monthly · Quarterly · Yearly

### 3.4 Kundli Milan (Compatibility)

Replace current Western synastry with proper Vedic Ashtakoot matching:

| Koota | Max Points | Checks |
|-------|-----------|--------|
| Varna | 1 | Spiritual compatibility |
| Vashya | 2 | Dominance / attraction |
| Tara | 3 | Birth star compatibility |
| Yoni | 4 | Sexual compatibility |
| Graha Maitri | 5 | Mental compatibility |
| Gana | 6 | Temperament |
| Bhakoot | 7 | Love / family |
| Nadi | 8 | Health / progeny |
| **Total** | **36** | 18+ = acceptable, 28+ = good |

- Manglik dosha check (Mars in 1/2/4/7/8/12)
- AI narrative reading of compatibility
- Score breakdown UI with colour coding

### 3.5 Dasha / Antardasha Timeline

- Vimshottari dasha calculation from Moon's nakshatra
- Timeline view: current dasha, antardasha, pratyantar dasha
- AI interpretation of current dasha period
- Visual timeline bar on persona page

---

## Phase 4 — Polish & Ship (Week 7–8)

### 4.1 Bug Fixes (from known issues list above)

All 6 pre-existing bugs fixed before release.

### 4.2 Mobile Responsive

- Sidebar collapses to bottom nav on mobile
- Chart canvas scales to screen width
- Touch-friendly tab strip on divisional charts

### 4.3 Export

- PDF export of full Kundli report (Avkahada + all charts + AI reading)
- Chart image download (PNG)
- Shareable link per persona (public read-only view)

### 4.4 Deployment

- Deploy as a split product, not a single monolith:
  - Angular UI on Cloudflare Pages.
  - FastAPI deterministic astrology engine on Render Free during beta, then Render Starter / Railway / Fly / VPS for production.
  - Supabase for Auth, Postgres, Storage, and row-level security.
  - Future Express.js context engine for memory, profile context assembly, AI prompt routing, version diffing, and orchestration.
  - Future Dify agents for fast no-code/low-code AI workflows; LangChain/LangGraph only when custom agent control is needed.
- Keep the calculation boundary strict:
  - FastAPI calculates astrology.
  - Express assembles context and routes workflows.
  - Dify / LangChain explains, summarizes, and personalizes.
  - Supabase persists users, kundlis, readings, prediction claims, gocharam periods, settings, and feedback.
- Environment:
  - Frontend: `API_BASE_URL`, Supabase public URL/key.
  - FastAPI: `DATABASE_URL`, Supabase JWT settings, AI provider keys only for legacy/internal routes.
  - Express context engine: Supabase service credentials, AI provider keys, Dify/LangGraph workflow secrets.
- Rate limiting on AI/context endpoints.
- Production database remains Supabase Postgres; local SQLite is development-only.

## Target Tech Stack And Hosting

### Current / Free Beta Stack

| Layer | Technology | Hosting |
|-------|------------|---------|
| Frontend | Angular + PrimeNG/Tailwind-style app theme | Cloudflare Pages |
| Deterministic astrology API | FastAPI + Python + Swiss Ephemeris | Render Free Web Service |
| Auth + database | Supabase Auth + Postgres + RLS | Supabase Free |
| Static public landing page | Angular route / static build | Cloudflare Pages |

Notes:
- Render Free is acceptable for beta, but it sleeps after inactivity. First request after idle can be slow.
- Cloudflare Pages is preferred over GitHub Pages because SPA routing, redirects, custom domains, preview deploys, and CDN controls are smoother.
- GitHub Pages remains acceptable for static frontend-only demos, but it cannot run FastAPI and needs SPA fallback handling.

### Future Product Stack

| Layer | Technology | Hosting Direction |
|-------|------------|-------------------|
| Frontend | Angular | Cloudflare Pages |
| Core astrology engine | FastAPI Python | Render Starter / Railway / Fly / VPS |
| Context engine | Express.js / Node.js | Render / Railway / Fly / VPS |
| Agent workflows | Dify first; LangChain/LangGraph for custom control | Dify Cloud/self-hosted or dedicated service |
| Auth/database/storage | Supabase | Supabase Pro when usage requires it |
| Background jobs | FastAPI worker or Node worker | Same backend platform or queue worker |

### Architecture Principle

AstroSpace should keep deterministic astrology separate from AI:

```
Angular UI
  -> FastAPI core astrology engine
  -> Supabase auth/database
  -> Express context engine
  -> Dify / LangGraph AI workflows
```

FastAPI is the source of truth for charts, dashas, gocharam, yogas, doshas, compatibility, panchanga, and validation-grade calculations. AI agents should never invent astrology results; they should explain and personalize the computed payload.

---

## File Structure (Target)

```
astrospace/
├── core/
│   ├── chart.py              # existing Western chart (keep for compatibility)
│   ├── transits.py           # existing
│   ├── cities.py             # existing
│   └── vedic/                # NEW — entire Vedic engine
│       ├── __init__.py
│       ├── positions.py      # sidereal positions + ayanamsha
│       ├── vargas.py         # D1–D30 divisional chart formulas
│       ├── nakshatra.py      # nakshatra + pada calculator
│       ├── panchanga.py      # tithi, yoga, karana, vara
│       ├── avkahada.py       # full Avkahada Chakra
│       ├── ghatak.py         # Ghatak malefics
│       ├── favourable.py     # lucky points
│       ├── strength.py       # planet dignity + Shadbala
│       └── milan.py          # Ashtakoot compatibility
├── agents/
│   ├── base.py               # FIX auth_token bug + async wrapper
│   ├── reading_agent.py
│   ├── period_agent.py       # add Dasha context
│   ├── varga_agent.py        # NEW — per D-chart analysis
│   └── milan_agent.py        # NEW — Vedic compatibility
├── api/
│   ├── routes.py             # existing (keep)
│   ├── kundli_routes.py      # existing (keep)
│   ├── reading_routes.py     # FIX blocking + add SSE stream
│   ├── auth_routes.py        # NEW — sign up, sign in, JWT
│   └── vedic_routes.py       # NEW — all Vedic endpoints
├── db/
│   ├── models.py             # add User model
│   ├── database.py
│   └── crud.py               # add user CRUD
frontend/
├── index.html                # complete redesign
├── style.css
├── app.js                    # split into modules
├── auth.js                   # NEW
├── chart-renderer.js         # NEW — North Indian canvas chart
└── vedic-api.js              # NEW — API calls for Vedic endpoints
tests/
├── test_chart.py             # existing
├── test_vedic_positions.py   # NEW — validate against reference chart
├── test_vargas.py            # NEW — D1–D30 formula tests
└── test_avkahada.py          # NEW — Avkahada Chakra field tests
```

---

## Starting Point

**Tomorrow's first task: Phase 1.1 + 1.2**

Build `astrospace/core/vedic/positions.py` and `astrospace/core/vedic/vargas.py`, write unit tests as stubs, and validate D1 + D9 outputs against the reference chart once the user provides it.

---

## Reference Chart for Validation

> **Pending** — user will provide a verified birth chart with known correct output values.
> Once provided, add full expected field values here and wire into `tests/test_vedic_positions.py` as fixtures.
