# AstroSpace — Vision & Roadmap

This document is written for AI agents and developers who will continue building AstroSpace. It captures the product philosophy, the decisions already made and why, the current state of the system, and what to build next — in priority order.

Read this before touching any code.

---

## The Core Idea

AstroSpace is not a horoscope website. It is a **personal astrology intelligence layer** — a system that knows the complete astrological profile of everyone you care about and generates deeply personalised, astronomically accurate, AI-interpreted guidance across time.

The end-user experience goal:
> "I open AstroSpace and it already knows it's Priya's Saturn return year, that her Venus is transiting my 7th house this month, and that today the Moon is triggering my natal Chiron. It tells me what that means in plain language and what to do about it."

This is fundamentally different from generic sun-sign content. Every interpretation is derived from:
1. The exact natal chart (calculated from birth date, time, and city)
2. Current planetary positions (Swiss Ephemeris, real-time)
3. The active aspects between (1) and (2)
4. A curated knowledge base of astrological meanings
5. A Claude AI agent that synthesises all of the above into personalised prose

---

## Design Principles

**1. Precision over generalisation**
Every reading must reference actual chart placements. "Your Sun in Scorpio square your natal Pluto" is more useful than "transformation is in the air." The AI agents are constrained by tools that force them to look up real chart data before writing.

**2. Offline-first calculations**
The chart engine never calls external APIs during normal operation. Swiss Ephemeris runs locally via kerykeion. The city database (80+ cities) covers most users without GeoNames. This means the core works anywhere, anytime, for free.

**3. The database is the memory**
The system remembers every kundli, every reading, every note. This is what separates AstroSpace from a stateless chatbot. Over time, the system can track how transits played out, flag upcoming cycles, and build a longitudinal picture of a person's life.

**4. Agents as specialists, not generalists**
Each AI capability is a separate agent class with a focused system prompt and specific tools. The `PeriodAgent` does time-based readings. The `CompatibilityAgent` does synastry. They do not overlap. New capabilities should be new agents.

**5. The frontend serves the kundli, not the astrology**
The UI is organised around people (kundlis in the sidebar), not around astrological concepts. A user thinks "I want to know about Priya" — not "I want to read about Venus transits." Everything flows from selecting a person.

---

## What Has Been Built (Current State)

### Core Engine — `astrospace/core/`

- `chart.py` — `BirthChart` class. Calculates all 10 planets, 12 houses, major aspects. Handles kerykeion v5 API (uses `p.position` not `p.pos`, 3-letter sign abbreviations mapped via `SIGN_ABBR`). Returns planets as a dict keyed by planet name.
- `transits.py` — `TransitCalculator`. Gets current sky positions and synastry aspects to any natal chart.
- `cities.py` — Offline city lookup. 80+ major world cities with lat/lng/timezone. Eliminates GeoNames dependency.
- `planets.py` — Static meaning dictionaries for planets, signs, houses, aspects (used by legacy agents).

### AI Agents — `astrospace/agents/`

All agents inherit `BaseAstroAgent` in `base.py`. The base class runs a tool-use loop: send message → handle tool calls → repeat until `end_turn`.

- `base.py` — Tool-use loop. Handles both `sk-ant-api-` keys and `sk-ant-si-` session tokens (the latter uses `auth_token=` for Bearer auth).
- `period_agent.py` — **Primary reading agent.** Chains 4 tools: `get_natal_chart` → `get_current_transits` → `get_transits_to_natal` → `lookup_knowledge`. Generates daily/weekly/monthly/quarterly/yearly readings.
- `reading_agent.py` — Deep natal chart reading (one-time, no transits).
- `horoscope_agent.py` — Generic sun-sign horoscopes.
- `compatibility_agent.py` — Synastry report for two people.
- `transit_agent.py` — Transit interpretation for a natal chart.

### Knowledge Base — `astrospace/knowledge/astro_kb.py`

200+ interpretations across:
- Planet in sign (Sun through Mars across all 12 signs)
- Planet in house (key placements for Sun, Moon, Venus, Mars, Jupiter, Saturn)
- Aspect meanings (conjunction, opposition, trine, square, sextile, quincunx)
- Transit windows (named transits like "Jupiter conjunct Sun", "Saturn return")
- Period archetypes (what matters in a daily vs yearly reading)

This is the most important file to expand. Richer knowledge = richer readings.

### Database — `astrospace/db/`

SQLAlchemy 2.0 ORM. SQLite by default, PostgreSQL via `DATABASE_URL` env var.

Two tables: `kundlis` (birth profiles + chart data) and `readings` (cached AI output). Readings have a smart cache: daily readings don't regenerate for 20 hours; yearly readings for 350 days.

### API — `astrospace/api/`

- `kundli_routes.py` — CRUD at `/api/v1/kundlis`. Chart is auto-calculated on create.
- `reading_routes.py` — Generate/retrieve at `/api/v1/readings`. Handles cache logic.
- `routes.py` — Original stateless endpoints (`/chart`, `/reading`, `/compatibility`, `/transits`, `/transits/current`, `/horoscope`).

### Frontend — `frontend/`

Single-page app served as static files by FastAPI. No build step, no framework — vanilla JS.

- Sidebar with kundli list + search
- 5 tabs per kundli: Overview, Chart (canvas wheel), Readings, Compatibility, Notes
- Period selector (Daily/Weekly/Monthly/Quarterly/Yearly) with reading display
- Add/Edit modal for kundli creation
- Markdown renderer for AI reading output

---

## Architectural Decisions — Why Things Are the Way They Are

### Why kerykeion and not a raw ephemeris?
kerykeion wraps the Swiss Ephemeris (the industry gold standard for planetary calculations) in Python. It calculates everything locally with millisecond precision. The alternative was calling an external API for every chart — that adds latency, cost, and failure modes.

### Why did we use `Optional[X]` instead of `X | None`?
The `X | None` union syntax requires Python 3.10+. The target user base may be on Python 3.9 (macOS ships 3.9 via Xcode). Using `Optional[X]` from `typing` keeps the code compatible with Python 3.9+.

### Why SQLite and not Postgres from the start?
Zero-config local development. The `DATABASE_URL` env var lets any deployment swap to PostgreSQL/Supabase without code changes. SQLAlchemy abstracts the difference completely.

### Why does `to_dict()` return planets as a dict (not a list)?
The frontend and API routes need to look up "the Sun" and "the Moon" by name constantly. A dict keyed by planet name (`{"Sun": {...}, "Moon": {...}}`) makes that O(1). JSON serialises either way.

### Why is the knowledge base a Python file and not a database table?
It's version-controlled, reviewable, and the AI agents can reference it via tool call without a DB round-trip. It will move to a database table when the content needs to be user-editable (future feature).

---

## Roadmap — What to Build Next

Items are ordered by user impact. Each item includes the exact files to create or modify.

### Priority 1 — Transit Calendar

**What:** A calendar view showing when significant transits are exact (orb < 1°) for a kundli — "Saturn conjunct your natal Sun peaks on March 15, 2027."

**Why:** The most-requested astrology feature. Currently we show what's happening *now* but not what's coming.

**How:**
- New core function `calculate_upcoming_transits(natal_chart, months_ahead=12)` in `core/transits.py`
  - Iterate forward day by day, compute synastry, detect exact-aspect crossings
  - Return list of `{date, transit_planet, natal_planet, aspect, exact_date}`
- New API endpoint `GET /api/v1/kundlis/{id}/calendar?months=12`
- New frontend tab "Calendar" with month-view grid using CSS Grid

### Priority 2 — Expand the Knowledge Base

**What:** Add planet-in-sign entries for Jupiter, Saturn, Uranus, Neptune, Pluto. Add more planet-in-house combos (currently only key placements exist). Add composite aspect patterns (Grand Trine, T-Square, Yod).

**Why:** Every AI reading is only as good as the knowledge base behind it. The current KB covers Sun/Moon/Venus/Mars/Mercury well, but outer planets are sparse.

**File:** `astrospace/knowledge/astro_kb.py` — add entries to `PLANET_IN_SIGN` and `PLANET_IN_HOUSE` dicts. No schema changes needed.

### Priority 3 — Vedic / Jyotish Mode

**What:** Toggle between Western (Tropical) and Vedic (Sidereal) chart calculation. Vedic astrology uses the sidereal zodiac (shifted ~23° from tropical), adds concepts like nakshatras (27 lunar mansions) and dashas (planetary period cycles).

**Why:** The user base is heavily Indian. Vedic is the primary system for most South Asian families.

**How:**
- kerykeion supports sidereal via `sidereal_mode="FAGAN_BRADLEY"` parameter
- New `VedicChart` class in `core/chart.py` or a `sidereal=True` flag on `BirthChart`
- New `NAKSHATRA_MEANINGS` dict in the knowledge base
- New `VedicAgent` in `agents/` with Jyotish-aware system prompt
- UI toggle (Western/Vedic) stored per kundli or as a global setting

### Priority 4 — Family Dashboard

**What:** A home screen showing all kundlis at once with their current most significant transit highlighted. "Priya: Jupiter conjunct Sun (expansion!)" "Dad: Saturn return (major restructuring)."

**Why:** Power users manage 10+ kundlis. They need a glanceable family overview, not just one person at a time.

**How:**
- New endpoint `GET /api/v1/dashboard` — returns all kundlis with their top 3 active transits
- Computed server-side by calling `TransitCalculator.get_transits_to_natal()` for each kundli
- New frontend home panel (replaces the "Your Cosmic Family Awaits" empty state)

### Priority 5 — Push Notifications / Reminders

**What:** Alert the user when a significant transit is exact for any saved kundli. "Saturn is now exactly square Priya's natal Moon. Read her weekly reading."

**Why:** Turns AstroSpace from a reactive tool (you remember to check it) to a proactive one (it tells you when something important is happening).

**How:**
- Scheduled job (APScheduler or cron) that runs `calculate_upcoming_transits` nightly
- Stores upcoming alerts in a new `alerts` table
- Delivery: email (SMTP), push (Web Push API), or in-app notification badge
- New `POST /api/v1/kundlis/{id}/alerts` to configure which transit types to alert on

### Priority 6 — Reading History & Journaling

**What:** Show all past readings in a timeline. Let the user add a journal entry ("this week's reading was accurate — the Venus transit brought a new relationship") and rate the reading.

**Why:** Creates a feedback loop that improves AI prompt quality over time. Also gives users a record of their astrological journey.

**How:**
- `readings` table already stores all generated readings with `generated_at` timestamp
- Add `user_note TEXT` and `accuracy_rating INT` columns to the `readings` table
- New `PATCH /api/v1/readings/{reading_id}` endpoint
- New "History" tab in the frontend showing a reverse-chronological list of readings with inline note editing

### Priority 7 — Multi-User / Auth

**What:** Let multiple people each have their own kundlis, private to their account. Currently the app is single-user (no login).

**Why:** Sharing the app with a partner or family member currently means everyone sees everyone's kundlis.

**How:**
- Add `users` table with email + hashed password (or OAuth via Google)
- Add `user_id` foreign key to `kundlis` table
- FastAPI dependency injection for authentication (JWT or session cookie)
- Login/logout UI in the sidebar footer
- Use Supabase Auth for the simplest path — it handles OAuth + JWT automatically

### Priority 8 — iOS / Android App

**What:** Native mobile app that wraps the existing API.

**Why:** Astrology is a mobile-first experience. Users check their reading in the morning on their phone.

**How:**
- The REST API is already complete — no backend changes needed
- React Native or Flutter frontend consuming `/api/v1/*`
- Backend deployed on Railway, Render, or Supabase Edge Functions
- Push notifications via APNs/FCM connected to the alerts system (Priority 5)

---

## Known Issues & Technical Debt

| Issue | File | Notes |
|---|---|---|
| `Test User` kundli has no chart data | `astrospace.db` | Created before chart auto-calc was implemented. Delete and recreate. |
| `requirements.txt` version pins are loose | `requirements.txt` | Add `sqlalchemy>=2.0` and `pydantic>=2.0` pins |
| No error handling in frontend `runCompat()` | `frontend/app.js` | If either kundli lacks chart data, the compatibility call may 500 |
| kerykeion cache dir | `astrospace/core/chart.py` | kerykeion writes to a `cache/` dir in the project root. Add to `.gitignore` |
| Reading `period_label` for quarterly uses a format string that needs manual construction | `api/reading_routes.py` | The `datetime.strftime` call has a `{q}` placeholder that won't be filled by strftime — there's a fix below it but the code is duplicated |

---

## File Map for Quick Navigation

```
To add a new AI capability:        astrospace/agents/          (new agent class)
                                   astrospace/api/             (new route file)
                                   main.py                     (register router)

To improve AI reading quality:     astrospace/knowledge/astro_kb.py
                                   astrospace/ai/prompts.py

To change chart calculations:      astrospace/core/chart.py

To add a new city:                 astrospace/core/cities.py   (CITIES dict)

To change the database schema:     astrospace/db/models.py     (add column)
                                   astrospace/db/crud.py       (add function)

To change the UI:                  frontend/index.html         (structure)
                                   frontend/style.css          (styling)
                                   frontend/app.js             (logic)

To change API contracts:           astrospace/api/models.py    (Pydantic models)
```

---

## Model & API Choices

**AI Model:** `claude-opus-4-8` (Anthropic). Selected for its reasoning depth — astrological synthesis requires holding many chart placements in context simultaneously and drawing non-obvious connections between them. Do not downgrade to Haiku for readings; the quality drop is significant. Haiku is appropriate for simple lookups or classification tasks.

**Astrology Engine:** kerykeion v5 (Python wrapper for Swiss Ephemeris). Breaking changes from v4: `p.pos` → `p.position`, sign abbreviations are 3-letter (`"Can"` not `"Cancer"`). These are already handled in `chart.py` via `SIGN_ABBR` dict and `p.position`.

**Database ORM:** SQLAlchemy 2.0 with `Mapped[]` type annotations. The `Optional[X]` pattern (not `X | None`) is required for Python 3.9 compatibility.

---

## Session Token Note (Claude Code Environments)

When running inside a Claude Code remote session, `ANTHROPIC_API_KEY` may contain a session ingress token (`sk-ant-si-*`) rather than a standard API key (`sk-ant-api03-*`). These require `auth_token=key` (Bearer auth) instead of `api_key=key` when constructing the `anthropic.Anthropic()` client. This is already handled in `agents/base.py` and `ai/client.py` via a prefix check.

When deploying independently, always use a standard API key from https://console.anthropic.com.
