# UX Current State — AstroSpace

> The app as it exists today, so redesign starts from reality. Grounded in the
> Angular app under `ui/src/app/`. Screenshots not embedded (per import
> constraints); this is the structural inventory.

## Platform

- Responsive **Angular 20** web app (PrimeNG, signals), served by FastAPI.
- **Desktop:** persistent left sidebar + top bar (profile switcher).
- **Mobile:** a mobile shell was recently added — compact top bar + **bottom nav**
  (Home, Vedic, Calendar, Ask AI, **More**), with a grouped "More" sheet. Still
  maturing; several tabs remain desktop-dense.
- Light + dark themes. Auth via Supabase (Google / magic link / password).

## Top-level structure

```
/auth            Sign in / up
/app (Home)      Workspace dashboard: profile switcher, "Today across profiles",
                 recent kundlis, stats (kundlis, relations, alerts)
/settings        Preferences (ayanamsha, node type, chart style, theme)
/kundli/:id/...  The per-profile workspace (tabs below)
```

Profiles ("kundlis") are created via an **Add** dialog (name, relation, birth
date/time, **city autocomplete**, notes). Relation drives some copy (self vs. name).

## The per-profile workspace — current tab IA (≈15 tabs)

| Tab | Route | What it does today | Persona fit |
|---|---|---|---|
| **Overview** | `/overview` | Hero, big-three (Sun/Moon/Asc), **"What matters today"** (computed **daily guidance** panel — verdict, colour, number, do/avoid, CE context) + live transit intel, birth details, Masa card, planetary positions | Everyone (the closest thing to a Guided surface) |
| **Vedic** | `/vedic` | Avkahada, Ghatak, **Favourable points** (lucky number/colour/gem/…), dignities, graha table, strength, varga summary | Practitioner-leaning |
| **Varga Charts** | `/varga-charts` | D1–D60 divisional charts (S/N/E styles) + placements | Practitioner |
| **Dashas** | `/dashas` | Vimshottari 5-level tree (maha/antar/pratyantar side-by-side) + charts | Practitioner |
| **Jaimini** | `/jaimini` | Chara karakas, arudha padas, special lagnas, Yogini dasha | Practitioner |
| **Gocharam** | `/gocharam` | South-Indian gochara profile + plain readings | Balanced |
| **Transits** | `/transits` | Full transit analysis, aspects, timeline, AV support | Practitioner |
| **Calendar** | `/calendar` | Panchanga + dasha + transit "intelligence feed", personal day checks | Balanced |
| **Ashtakavarga** | `/ashtakavarga` | BAV/SAV, shodhana, pinda tables | Practitioner |
| **Yogas & Doshas** | `/yogas-doshas` | Yoga/dosha cards (Manglik, Gandanta, Grahan, Mahapurusha, …) | Balanced |
| **Chart** | `/chart` | Recently reworked into a **mobile hub** linking to the chart-related tabs | Navigation |
| **Readings** | `/readings` | AI reading generation (today / week / year) | Everyone |
| **Compatibility** | `/compat` | Gun Milan match against another profile | Believer (matchmaking) |
| **Notes** | `/notes` | Free notes on the profile | Practitioner |
| **Ask AI** | `/ask` | Q&A surface (not yet fully CE-driven as the question-first front door) | Everyone (underused) |

## Honest assessment of the current UX

**Strengths**
- The computed depth is real and mostly well-rendered (charts in 3 styles, dense
  tables, provenance).
- The **daily guidance panel** (Overview) is the one genuinely believer-oriented
  surface — plain verdict + almanac + do/avoid, with evidence underneath.
- Recent polish: city autocomplete, eastern-chart fix, dashas layout, mobile shell.

**Gaps / tensions (the design brief)**
1. **It's an astrologer's workbench that believers must navigate.** ~15 data tabs; the
   believer's needs (today, ask, what-to-do) are panels inside it, not the front door.
2. **No experience mode.** One UI at one depth — jargon for believers, dumbed-down for
   practitioners depending on where you look.
3. **No question-first entry.** "Ask AI" exists but isn't the CE-driven surface the
   believer's mental model wants.
4. **Descriptive, not prescriptive.** No remedies, no goal-based muhurta — the actions
   users most want.
5. **English-text-only.** No Telugu, no audio — a reach blocker for the core.
6. **Nav labels are technical** (Dashas, Gocharam, Ashtakavarga) — opaque to believers.
7. **Mobile still maturing** — some tabs are desktop-dense; see `mobile_app_plan.md`.

## Where a redesign should start

- Treat **Overview → "What matters today"** as the seed of the Guided/Today surface.
- Turn **Ask AI** into the CE-driven, question-first front door.
- Re-label + re-prioritize nav per experience mode over the **existing stable routes**
  (don't fork).
- Add the **"what to do"** surfaces (remedies, muhurta) the personas demand.
