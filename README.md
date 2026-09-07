# AstroSpace — Vedic Astrology, Computed

AstroSpace is a Vedic astrology platform: a FastAPI + Swiss Ephemeris backend
that computes real sidereal charts (Lahiri ayanamsha) — planets, houses,
divisional charts (D1–D60), dashas, yogas, doshas, strength, and transits —
grounded by a classical-text knowledge base, interpreted by a configured AI
provider's agents that are gated by a deterministic safety and verification
layer, and served
to readers through two front ends: a responsive **web app** and a
Figma-designed **native app** (`/m/*`, packaged with Capacitor for iOS and
Android) sharing one backend and one Supabase Postgres database.

AI explains and personalizes; the astrology itself is calculated, testable,
and auditable — see [CLAUDE.md](CLAUDE.md) for the product's non-negotiable
constraints (no death/medical/legal/financial verdicts, dosha as a flag never
a verdict, convention-dependent content always labelled).

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Database](#database)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Contributing / Agents](#contributing--agents)

---

## Features

| Feature | Description |
|---|---|
| Vedic Chart Engine | Sidereal (Lahiri) planets, houses, D1–D60 vargas, Avkahada Chakra — via Swiss Ephemeris |
| Dashas | Vimshottari (all 5 levels) + Yogini + Chara dasha systems |
| Yogas & Doshas | Rule-based detection with classical-text citations and provenance labels, never a bare verdict |
| Strength | Classical (virupa-based) Shadbala, Ashtakavarga (BAV/SAV/Shodhana), avasthas, combustion, planetary war |
| Gocharam | Canonical Moon-first transit engine with Vedha/Ashtakavarga-weighted severity |
| Compatibility | Ashta Koota / Gun Milan scoring with per-koota breakdown and Manglik/Kuja dosha |
| Calendar Intelligence | Panchanga, active dasha, and transit feed per day, with muhurta and festival detection |
| Ask AI | Deterministic domain-routed reading pipeline (see below) — never a free-form chat |
| Profile Context Ledger | Reader-authored durable life facts (retired, married, has children, …) that constrain — never overwrite — AI interpretation |
| Knowledge Base | Machine-checked citations from classical texts (BPHS and others), ingested with provenance and confidence gating |
| Two Front Ends | A responsive web app and a native app (`/m/*`, Capacitor for iOS/Android) sharing one backend |

### The Ask AI pipeline

Every question to `AskOrchestrator` (`astrospace/agents/orchestrator.py`)
runs through one sequential gate before any content reaches a reader:
input safety check → domain routing → registry check (unconfigured domains
never reach a model) → deterministic context assembly (chart data + KB
citations + Profile Context Ledger facts) → structured-reading model
generation → deterministic verification (`astrospace/agents/verifier.py` —
regex/set-membership only, no second model call) → one repair attempt on
failure → persist only after a pass. A death/medical/legal/financial verdict
never ships; a dosha is always framed as a flag.

---

## Architecture

Detailed operational documentation:

- [CLAUDE.md](CLAUDE.md) — product non-negotiables and where things live.
- [Admin Console](docs/admin_console.md) — roles, APIs, workflows, audit,
  Supabase objects, operations, and limitations.
- [Knowledge Base Engine](docs/knowledge_ingestion.md) — source provenance,
  OCR/EPUB ingestion, LLM boundaries, quality gates, retrieval scope, hybrid
  search, and Context Engine integration.
- [Context Engine Taxonomy](docs/context_engine_taxonomy.md) — domain
  routing and context-assembly contract.
- [Native Builds](docs/native_builds.md) — Capacitor packaging for iOS/Android.
- [Mobile Screen Build Plan](docs/mobile_screen_build_plan.md) — the native
  app's Figma-to-screen implementation tracker.
- [Profile Context Ledger Architecture](docs/profile_context_ledger_architecture_2026-08-14.md) —
  the reader-authored life-facts system and its deterministic Ask integration.

```
Web SPA (/)  ·  Native app (/m/*, Capacitor)
                     │
                     │  HTTP / REST + SSE
                     ▼
FastAPI (main.py) — serves the built Angular SPA same-origin in production
     │
     ├── /api/v1/kundlis          ← CRUD: birth profiles
     ├── /api/v1/vedic/{id}       ← chart, vargas, dashas, yogas, strength, gocharam
     ├── /api/v1/context/{id}     ← Context Engine bundle + daily guidance
     ├── /api/v1/ask/{id}         ← Ask AI (non-streaming + SSE stream)
     ├── /api/v1/profiles/{id}/context ← Profile Context Ledger
     ├── /api/v1/compatibility    ← synastry / Gun Milan
     ├── /api/v1/remedies, /muhurta, /festivals
     ├── /api/v1/admin            ← ops console (role-gated, audited)
     └── /api/v1/auth, /settings, /me
          │
          ├── astrospace/core/vedic/   ← Swiss Ephemeris engine (sidereal, Lahiri)
          │     chart.py, positions.py, dashas.py, doshas.py, gocharam/, ...
          │
          ├── astrospace/agents/       ← AI agents (provider-configurable)
          │     orchestrator.py        AskOrchestrator — the one Ask pipeline
          │     domain_agent.py        config-driven structured-reading agent
          │     verifier.py            deterministic safety/quality gate
          │     safety.py              refer-out + prohibited-verdict/dosha-overclaim regex
          │
          ├── astrospace/context/      ← Context Engine (assembler, KB retrieval, routing)
          │     assembler.py, kb.py, router.py, taxonomy.py, profile_context.py
          │
          ├── astrospace/db/           ← SQLAlchemy ORM (SQLite dev / Supabase Postgres prod)
          │     models.py, crud.py, crud_mobile.py, crud_profile_context.py, seed.py
          │
          ├── astrospace/api/          ← FastAPI routers (thin — computation lives above)
          │
          └── astrospace/knowledge/    ← classical-text KB ingestion + rules
```

---

## Directory Structure

```
agentic-astrospace/
├── main.py                    FastAPI app entry point
├── requirements.txt           Python dependencies
├── setup.py                   Python package metadata (python_requires>=3.11)
├── .env                       API keys and DB URL (not committed)
├── astrospace.db              SQLite database (local dev, auto-created)
│
├── ui/                        Angular 20 SPA — web app + native app (/m/*)
│   ├── src/app/features/      landing, dashboard, kundli, settings, mobile/
│   ├── android/, ios/         Capacitor native shells
│   └── capacitor.config.ts
│
├── astrospace/
│   ├── core/vedic/            Swiss Ephemeris Vedic chart engine (no AI)
│   ├── agents/                AI agents (provider-configurable) — Ask orchestrator, verifier, safety
│   ├── context/                Context Engine — assembly, KB retrieval, routing, taxonomy
│   ├── api/                   FastAPI routers (thin wrappers over the above)
│   ├── db/                    SQLAlchemy models + CRUD
│   ├── knowledge/             Astrological knowledge base + ingestion
│   └── admin/                 Admin console security + audit middleware
│
├── supabase/migrations/       Postgres schema migrations (production DB)
├── docs/                      Operational docs, KB manifests, screen-build trackers
├── design-thinking/           Product/design principles
└── tests/                     Backend test suite (pytest)
```

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Node.js (for the Angular SPA) — see `ui/package.json` for the Angular version
- An Anthropic or Gemini API key for AI readings

### 1. Clone

```bash
cd ~/Documents
git clone https://github.com/repos-3sds/agentic-astrospace.git
cd agentic-astrospace
```

### 2. Backend — install and configure

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# edit .env: set AI_PROVIDER + the matching API key at minimum
```

If `kerykeion`/`pyswisseph` fail to build, install a C toolchain first
(`brew install python3` on macOS, `sudo apt-get install -y python3-scour
build-essential` on Debian/Ubuntu) and retry.

### 3. Run the backend

```bash
.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The Swagger API docs are at **http://localhost:8000/docs**.

### 4. Frontend — the Angular SPA (web app)

```bash
cd ui
npm install
npm run start   # ng serve, proxies API calls to :8000 — see proxy.conf.json
```

Open **http://localhost:4200**. In production, FastAPI serves the built SPA
same-origin from `/` (and the native app from `/m/*`) — there is no separate
frontend deployment.

### 5. Native app (optional)

See [docs/native_builds.md](docs/native_builds.md) for the full Capacitor
iOS/Android build and device-verification workflow.

---

## Environment Variables

See [.env.example](.env.example) for the authoritative, commented list.
Summary:

| Variable | Required | Description |
|---|---|---|
| `AI_PROVIDER` | No | `gemini` or `anthropic`; the mobile Ask experience defaults to Gemini |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Yes for Gemini | Gemini API key + model id |
| `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` | Yes for Anthropic | Anthropic API key + model id (fallback/provider switch) |
| `DATABASE_URL` | No | Defaults to local SQLite; set to a Supabase Postgres URL for cloud persistence |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` | No | When both are set, API routes require Supabase bearer tokens |
| `ASTROSPACE_DEV_AUTH_BYPASS` | No | Local visual QA only — never set in a deployed environment |
| `GEONAMES_USERNAME` | No | Defaults to `anonymous`; only needed for city lookups outside the offline city database |
| `ALLOWED_ORIGINS` | No | Extra CORS origins, comma-separated; native app origins are always allowed regardless of this setting |

`.env` holds real credentials — it is never committed and should be edited
directly, not read into an agent transcript.

---

## Database

SQLite is the local-dev default (`astrospace.db`, auto-created on first run).
Production uses **Supabase Postgres** — schema and RLS policies live in
[supabase/migrations/](supabase/migrations/), applied via the Supabase CLI or
dashboard, not by SQLAlchemy `create_all()`. Catalog tables (remedies,
festivals, muhurta goals) are seeded from the engine code, never
hand-authored:

```bash
.venv/bin/python -m astrospace.db.seed
```

Set `DATABASE_URL` to a `postgresql+psycopg://...` URL to point the backend
at Supabase; SQLAlchemy switches driver automatically based on the scheme.

---

## API Reference

The full, current route list is generated live at **`/docs`** (Swagger UI)
and **`/redoc`** — this README does not hand-maintain an endpoint table that
would drift from `main.py`'s router registration. Start here instead:

- [Context Engine Taxonomy](docs/context_engine_taxonomy.md) for the domain
  routing/context-assembly contract behind `/api/v1/context` and
  `/api/v1/ask`.
- [Admin Console](docs/admin_console.md) for `/api/v1/admin/*`.
- `astrospace/api/` — one thin router file per resource; each one imports the
  computation it wraps from `astrospace/core/vedic/`, `astrospace/context/`,
  or `astrospace/agents/` rather than implementing it inline.

---

## Testing

```bash
# Backend — 1900+ tests
.venv/bin/python -m pytest tests/ -q

# Frontend
cd ui && npx ng test --watch=false --browsers=ChromeHeadless
```

For UI changes, also verify visually in a browser (or the iOS/Android
simulator for `/m/*`) — a green build is not evidence a screen renders
correctly; see [CLAUDE.md](CLAUDE.md)'s "Verify visually, not just by build".

---

## Contributing / Agents

Read [CLAUDE.md](CLAUDE.md) first — it states the product's non-negotiable
constraints and where things live. Then:

- [VISION.md](VISION.md) — product philosophy and long-term direction.
- [AGENTS.md](AGENTS.md) — cross-agent operating protocol for this repo
  (multiple AI agents work here concurrently on shared `main`).
- [docs/agent_work_ledger.md](docs/agent_work_ledger.md) — who is doing what
  today.

Key conventions:

- All chart calculations go through `astrospace/core/vedic/` — never call
  `kerykeion`/`pyswisseph` directly from agents or routes.
- All AI generation goes through `astrospace/agents/orchestrator.py`'s
  `AskOrchestrator` — there is no second, unverified answer path.
- `astrospace/api/` routers stay thin; computation lives in `core/vedic`,
  `context/`, or `agents/`.
- New Ask domains are configured in `astrospace/agents/registry.py`, not
  hand-rolled per domain.
- Knowledge base additions go through the ingestion pipeline
  (`docs/knowledge_ingestion.md`) with real provenance — never a hand-typed
  citation with no source check.
- `/` is the web app; `/m/*` is the separate, Figma-designed native app
  (`ui/src/app/features/mobile/`) — they are not the same screens under two
  routes.
- Markdown docs declare their own status in the first three lines
  (`canonical`, `source of truth`, `point-in-time audit`, or `superseded`) —
  see CLAUDE.md's "Docs state their own status".
