# AstroSpace — AI-Powered Astrology Engine

AstroSpace is a full-stack astrology application that combines Swiss Ephemeris precision (via kerykeion) with Claude AI autonomous agents to generate natal charts, personalised readings, compatibility analyses, and live transit interpretations. It is built for personal use: save kundlis for your family and friends, and generate AI readings across any time period.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Database](#database)
- [Upgrading to Supabase (PostgreSQL)](#upgrading-to-supabase)
- [Python Version](#python-version)
- [Contributing / Agents](#contributing--agents)

---

## Features

| Feature | Description |
|---|---|
| Natal Chart | Full planetary positions, houses, aspects via Swiss Ephemeris |
| Big Three | Sun, Moon, Ascendant with zodiac emoji badges |
| AI Readings | Daily / Weekly / Monthly / Quarterly / Yearly via Claude agents |
| Kundli Manager | Save, edit, delete birth profiles for family and friends |
| Chart Wheel | Canvas-rendered natal chart with coloured zodiac segments |
| Compatibility | AI synastry analysis between any two saved kundlis |
| Live Transits | Current sky positions + transit-to-natal aspect calculation |
| Notes | Personal notes per kundli, persisted in the database |
| Knowledge Base | 200+ curated astrological interpretations used by AI agents |
| Offline Mode | Built-in 80+ city database — no GeoNames API key needed |
| Caching | Readings cached per period (daily 20h, weekly 6d, monthly 25d…) |

---

## Architecture

```
Browser (SPA)
     │
     │  HTTP / REST
     ▼
FastAPI (main.py)
     │
     ├── /api/v1/kundlis        ← CRUD: create, list, get, update, delete
     ├── /api/v1/readings       ← generate + retrieve AI readings
     ├── /api/v1/chart          ← one-shot chart calculation (no DB)
     ├── /api/v1/compatibility  ← AI synastry report
     ├── /api/v1/transits       ← transit reading for a natal chart
     └── /api/v1/transits/current ← live sky snapshot
          │
          ├── astrospace/core/         ← Swiss Ephemeris via kerykeion
          │     chart.py              BirthChart — planets, houses, aspects
          │     transits.py           TransitCalculator — current sky + aspects
          │     cities.py             Offline city → lat/lng/tz lookup
          │     planets.py            Meaning dictionaries
          │
          ├── astrospace/agents/       ← Claude AI tool-use agents
          │     base.py               BaseAstroAgent — tool-use loop
          │     period_agent.py       Daily/Weekly/Monthly/Quarterly/Yearly
          │     reading_agent.py      Natal chart deep reading
          │     horoscope_agent.py    Sun-sign horoscopes
          │     compatibility_agent.py Synastry reports
          │     transit_agent.py      Transit interpretations
          │
          ├── astrospace/knowledge/    ← Astrological knowledge base
          │     astro_kb.py           Planet-in-sign, house, transit windows
          │
          ├── astrospace/db/           ← SQLAlchemy ORM
          │     models.py             Kundli + Reading tables
          │     crud.py               Database operations
          │     database.py           Engine + session factory
          │
          └── astrospace/ai/
                client.py             Anthropic SDK wrapper
                prompts.py            Agent system prompts
```

---

## Directory Structure

```
agentic-astrospace/
├── main.py                    FastAPI app entry point
├── requirements.txt           Python dependencies
├── .env                       API keys (not committed)
├── astrospace.db              SQLite database (auto-created)
│
├── frontend/                  Static SPA served by FastAPI
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── astrospace/
│   ├── core/                  Chart engine (no AI)
│   ├── agents/                Claude AI agents
│   ├── api/                   FastAPI routers
│   ├── db/                    Database models + CRUD
│   ├── knowledge/             Astrological knowledge base
│   └── ai/                    Anthropic client + prompts
│
├── docs/                      GitHub Pages marketing site
└── tests/
```

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- An Anthropic API key — get one at https://console.anthropic.com

### 1. Clone

```bash
cd ~/Documents
git clone https://github.com/repos-3sds/agentic-astrospace.git
cd agentic-astrospace
```

### 2. Install Dependencies

```bash
pip3 install fastapi uvicorn sqlalchemy kerykeion anthropic python-dotenv
```

If `kerykeion` fails on Mac:
```bash
brew install python3   # ensure system Python is up to date
pip3 install kerykeion
```

If `kerykeion` fails on Ubuntu/Debian:
```bash
sudo apt-get install -y python3-scour
pip3 install kerykeion
```

### 3. Set Your API Key

Create a `.env` file in the project root:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." > .env
```

### 4. Run

```bash
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. Open

Navigate to **http://localhost:8000** in your browser.

The Swagger API docs are at **http://localhost:8000/docs**.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for AI readings |
| `DATABASE_URL` | No | PostgreSQL URL for Supabase. Defaults to local SQLite |
| `ANTHROPIC_BASE_URL` | No | Override Anthropic API base URL (used in Claude Code sessions) |

---

## API Reference

### Kundlis (Birth Profiles)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/kundlis` | List all kundlis |
| `POST` | `/api/v1/kundlis` | Create kundli (auto-calculates chart) |
| `GET` | `/api/v1/kundlis/{id}` | Get single kundli with full chart data |
| `PATCH` | `/api/v1/kundlis/{id}` | Update name, relation, notes, etc. |
| `DELETE` | `/api/v1/kundlis/{id}` | Delete kundli and all its readings |

**Create Kundli — example request:**
```json
POST /api/v1/kundlis
{
  "name": "Priya Sharma",
  "relation": "friend",
  "birth_year": 1992,
  "birth_month": 3,
  "birth_day": 22,
  "birth_hour": 9,
  "birth_minute": 15,
  "birth_city": "Mumbai",
  "birth_nation": "IN"
}
```

### Readings (AI-Generated)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/readings/{id}/generate` | Generate or retrieve cached reading |
| `GET` | `/api/v1/readings/{id}` | List all readings for a kundli |
| `GET` | `/api/v1/readings/{id}/latest/{period}` | Get the most recent reading for a period |

**Generate Reading — example request:**
```json
POST /api/v1/readings/{kundli_id}/generate
{
  "period": "daily",
  "force_refresh": false
}
```

Valid `period` values: `daily`, `weekly`, `monthly`, `quarterly`, `yearly`.

### Core Astrology (Stateless)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/chart` | Calculate natal chart without saving |
| `POST` | `/api/v1/reading` | Deep natal chart AI reading |
| `POST` | `/api/v1/horoscope` | Sun-sign horoscope |
| `POST` | `/api/v1/compatibility` | Synastry report for two people |
| `POST` | `/api/v1/transits` | Transit reading for a natal chart |
| `GET` | `/api/v1/transits/current` | Current positions of all planets |

---

## Database

AstroSpace uses SQLite by default. The database file `astrospace.db` is created automatically in the project root when the server starts.

### Schema

**`kundlis` table**

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `name` | TEXT | Person's name |
| `relation` | TEXT | self / friend / spouse / parent / sibling / child |
| `birth_year/month/day` | INT | Birth date |
| `birth_hour/minute` | INT | Birth time (24h) |
| `birth_city` | TEXT | City name used for chart calculation |
| `birth_nation` | TEXT | ISO country code (US, IN, GB…) |
| `sun_sign` | TEXT | Calculated and stored at creation |
| `moon_sign` | TEXT | Calculated and stored at creation |
| `ascendant` | TEXT | Calculated and stored at creation |
| `chart_data` | JSON | Full chart dict (planets, houses, aspects) |
| `notes` | TEXT | Personal notes |
| `created_at` | DATETIME | |
| `updated_at` | DATETIME | Auto-updated on PATCH |

**`readings` table**

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `kundli_id` | TEXT (FK) | References `kundlis.id` — cascades on delete |
| `reading_type` | TEXT | daily / weekly / monthly / quarterly / yearly |
| `period_label` | TEXT | Human label e.g. "June 2026", "Q2 2026" |
| `content` | TEXT | Full AI-generated markdown reading |
| `generated_at` | DATETIME | When the reading was generated |

---

## Upgrading to Supabase

To persist data in the cloud using Supabase PostgreSQL:

1. Create a project at https://supabase.com
2. In the Supabase SQL Editor, run:

```sql
CREATE TABLE kundlis (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relation TEXT DEFAULT 'friend',
    birth_year INT,
    birth_month INT,
    birth_day INT,
    birth_hour INT DEFAULT 12,
    birth_minute INT DEFAULT 0,
    birth_city TEXT NOT NULL,
    birth_nation TEXT DEFAULT 'US',
    sun_sign TEXT,
    moon_sign TEXT,
    ascendant TEXT,
    chart_data JSONB,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE readings (
    id TEXT PRIMARY KEY,
    kundli_id TEXT REFERENCES kundlis(id) ON DELETE CASCADE,
    reading_type TEXT NOT NULL,
    period_label TEXT,
    content TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT NOW()
);
```

3. Copy the connection string from **Settings → Database → Connection string (URI)** and add to `.env`:

```bash
DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
```

4. Install the PostgreSQL driver:
```bash
pip3 install psycopg2-binary
```

5. Restart the server. SQLAlchemy automatically uses PostgreSQL when `DATABASE_URL` starts with `postgresql://`.

---

## Python Version

**Minimum: Python 3.9**

The codebase avoids `X | Y` union type syntax (Python 3.10+) and uses `Optional[X]` from `typing` throughout. All type annotations are compatible with Python 3.9+.

---

## Contributing / Agents

If you are a developer or AI agent continuing this project, read `VISION.md` first. It describes the long-term product direction, the architectural decisions made and why, and a prioritised backlog of what to build next.

Key conventions:
- All chart calculations go through `astrospace/core/chart.py` — never call kerykeion directly from agents or routes
- All AI calls go through `astrospace/agents/base.py` — the tool-use loop is centralised there
- New features that need AI reasoning should be new agent classes in `astrospace/agents/`
- Knowledge base additions go in `astrospace/knowledge/astro_kb.py`
- New API endpoints need a new router file in `astrospace/api/` and must be registered in `main.py`
