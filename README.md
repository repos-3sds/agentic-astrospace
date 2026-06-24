# AstroSpace 🌌

An AI-powered astrology engine with autonomous agents, built with Python and Claude AI.

## Features

- **Birth Chart Engine** — Natal chart calculations (planets, houses, aspects) via Swiss Ephemeris
- **AI Readings** — Deep, personalized chart interpretations powered by Claude AI
- **Daily & Weekly Horoscopes** — Generated from real-time planetary transits
- **Compatibility Analysis** — Synastry charts with AI-powered relationship readings
- **Transit Tracking** — Current planetary transits to natal chart with interpretations
- **REST API** — FastAPI-powered endpoints for all features
- **Autonomous Agents** — Claude-powered agents with astrological tool use

## Tech Stack

- **Python 3.11+**
- **kerykeion** — Swiss Ephemeris-based astrological calculations
- **Anthropic SDK** — Claude AI for interpretations and agent capabilities
- **FastAPI** — Modern REST API framework
- **Pydantic** — Data validation

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
python main.py
```

API docs at `http://localhost:8000/docs`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chart` | Calculate natal chart |
| POST | `/api/v1/reading` | Full AI natal reading |
| POST | `/api/v1/horoscope` | Daily/weekly horoscope |
| POST | `/api/v1/compatibility` | Synastry compatibility reading |
| POST | `/api/v1/transits` | Personal transit reading |
| GET  | `/api/v1/transits/current` | Current sky positions |

## Architecture

```
astrospace/
├── core/           # Astrological calculation engine
│   ├── chart.py    # Natal chart (planets, houses, aspects)
│   ├── planets.py  # Astrological meanings database
│   └── transits.py # Real-time transit calculations
├── ai/             # AI integration
│   ├── client.py   # Anthropic client wrapper
│   └── prompts.py  # Astrological system prompts
├── agents/         # Autonomous Claude agents
│   ├── base.py               # Tool-use agent loop
│   ├── reading_agent.py      # Full natal reading
│   ├── horoscope_agent.py    # Daily/weekly horoscope
│   ├── compatibility_agent.py # Synastry analysis
│   └── transit_agent.py      # Transit interpretation
└── api/            # FastAPI layer
    ├── models.py   # Pydantic request models
    └── routes.py   # REST endpoints
```

## License

MIT
