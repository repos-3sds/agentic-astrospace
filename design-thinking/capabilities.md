# Engine Capabilities — "Design Material"

> What the calculation engine can actually produce today (design *with* this) versus
> what it cannot yet (design *toward* this, but flag as new build). Grounded in the
> Python engine under `astrospace/core/vedic/` and `astrospace/context/`.

## ✅ Available today — safe to design around

### Chart & positions
- Sidereal planetary positions (Swiss Ephemeris, Moshier — no data files). Ayanamsha:
  **Lahiri / Raman / KP**; node type **mean / true**. Whole-sign houses, sidereal lagna.
- **20 divisional charts** D1–D60 (Rashi, Navamsha, Dashamsha, etc.), with vargottama.
- Nakshatra + pada, sign lords, dignities, retrograde, combustion.
- Three chart styles rendered: **South / North / Eastern** Indian.

### Panchanga & timing
- Full panchanga: tithi, nakshatra, yoga, karana, vara (sunrise-bounded).
- **Masa** (amanta + purnimanta), adhika-masa detection, samvatsara, ritu, ayana.
- Sunrise/sunset, moonrise/moonset.
- Day windows: **Rahu Kalam, Yamaganda, Gulika, Abhijit, Brahma Muhurta, Durmuhurta,
  Choghadiya, Hora, Varjya, Amrit Kalam**, plus Gulika/Mandi longitude. Disha shool,
  panchaka, Bhadra (Vishti).

### Strength, yogas, doshas
- **Shadbala** — v1 (0–100) + classical BPHS **virupa** (six balas, required minima).
- **Ashtakavarga** — BAV/SAV, shodhana, pinda, kakshya.
- **Yogas** — Pancha Mahapurusha, Raja/Dhana (with parivartana + graha-drishti
  sambandha), Chandra/Surya yogas, Gajakesari, Neecha Bhanga, Vipareeta, Kalasarpa,
  and more — each with strength + provenance.
- **Doshas** — Manglik (with exceptions + net severity), Gandanta, Grahan, Kalasarpa flag.

### Periods & Jaimini
- **Vimshottari dasha** — 5 levels (maha → prana) + Yogini dasha.
- **Jaimini** — chara karakas (8/7 scheme), arudha padas A1–A12, Upapada, special
  lagnas (Bhava/Hora/Ghati).

### Transits & daily
- **Gochara** with classical **vedha** (obstruction) + **Ashtakavarga transit
  weighting** (BAV/SAV/kakshya, effective severity).
- **Daily Guidance** (CE-wired): a verdict (100+ word, plain), a structured `reading`
  (summary / focus / best-for / avoid / energy / relationship / money / work tone /
  timing note / **plain_why** + **technical_why**), colour of the day, number of the
  day, tarabala, chandrabala, do/avoid with muhurta windows, lucky signature, and the
  CE context (dasha chain, active gochara, references).
- **Lucky/favourable** — numerology moolank **and** chart-based (lagna-lord) number;
  lucky colour, gem, metal, direction, days, time.

### Compatibility
- **Gun Milan** (Ashta Koota, 36-point) with Nadi/Bhakoot cancellations, plus
  Manglik/Gandanta/Grahan dosha checks.

### Context Engine (partial)
- **16-domain** taxonomy, split by topic rather than by house (career, wealth, personality,
  siblings/self-effort, family/parents, property/assets, education, children, health,
  marriage, business partnerships, rivals/disputes, litigation, foreign, spirituality/
  dharma/fortune, gains/income/social circle, expenses/losses) — see
  `context_engine_taxonomy.md` v2 for the full mapping and why the split happened.
- Domain **assembler** (houses/karakas/vargas/yogas/dasha-relevance/gochara/KB refs),
  keyword/LLM **router**, pluggable **knowledge base**, daily-guidance wiring, optional
  LangGraph graph with checkpointing.

### Data & validation
- City database: **complete Andhra Pradesh + Telangana** (villages) + world cities.
- External golden validation anchors (panchanga vs. published sources, eclipse, a
  natal fixture) — partial; full golden-chart suite still pending.

## ❌ Not built yet — design "toward," mark as new build

- **Remedies / upaya engine** — no gem/mantra/vrat/donation/deity recommendations tied
  to affliction/dasha/dosha. *(Highest-leverage gap.)*
- **Goal-based muhurta finder** — no "best time this month to sign / travel / buy /
  marry." (Raw windows exist; no goal-oriented finder.)
- **Festival / vrat / observance calendar** — panchanga exists; personalized
  what-to-observe-and-when does not.
- **Multi-language content (Telugu)** and **audio** rendering.
- **Timezone/geo-correct daily panchang** — defaults to birth place; wrong for diaspora.
- **Experience modes** (guided/balanced/practitioner) — not implemented.
- **Conversational "Ask" surface** — CE exists but isn't wired to a question-first UI;
  the "Ask AI" tab is not yet the CE-driven front door.
- **Notifications / daily-habit loop** (morning "your day").
- **Astrologer marketplace / human handoff.**
- **Full KP system** (sub-lords, Placidus cusps) — only KP *ayanamsha* is offered.
- **Learning layer** — no "tap a yoga → classical rule + verse + worked example."

## How to read this for design

- If a design idea uses something in the ✅ list, it's **feasible now** — the data is
  in `chart.to_dict()`, `daily_guidance()`, `transit_analysis()`, `gun_milan()`, etc.
- If it needs something in the ❌ list, it's a **new engine build** — scope it as such,
  and note that four of the six ❌ items (remedies, muhurta, language/audio, timezone)
  are exactly what the personas most demand.
