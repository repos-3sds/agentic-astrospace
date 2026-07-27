# Mobile Data Contract

What each native screen needs, which endpoint provides it, and the **shape the
layout assumes**. Companion to [mobile_screen_build_plan.md](mobile_screen_build_plan.md),
which tracks whether a screen is *drawn*. This tracks whether it is *true*.

## Why this exists

Three defects shipped past a green build and a type checker on 2026-07-27, all
the same shape — engine output that the layout was never sized for:

| defect | types said | reality | result |
| --- | --- | --- | --- |
| day gauge | `score: number` | signed tally, `-4` | clamped to 0, empty ring on every real reading |
| verdict card | `text: string` | 469 chars | Do/Avoid pushed off-screen |
| SAV header | `total: number` | asserted 337, cells summed 356 | header contradicted its own grid |

A type says `string`. It does not say *110 characters or the card breaks*. That
missing sentence is what this file is.

The placeholder values in every unwired screen were chosen to fit the design,
so **each one carries the same latent break**. Assume a screen is wrong until
its budgets are checked against a live payload.

## How to read a budget

A budget is a constraint the **layout** depends on. Violating it is a bug in
whichever side moved — usually the engine, since the design is fixed.

```
field                 type        budget                    breaks if violated
verdict.text          string      unbounded → SHEET ONLY    card overflow
reading.summary       string      ≤ 110 chars               card overflow
verdict.score         int         signed, NOT a percentage  gauge reads empty
sav[]                 int[12]     must sum to 337           header ≠ grid
```

Three budget kinds:

- **Length** — how much text a component was drawn to hold.
- **Range/scale** — what a number means. `score` is the cautionary case: it is
  a tally, not a percentage, and rendering it as one emptied the gauge.
- **Invariant** — a relationship that must hold across fields. SAV summing to
  337 is classical, not incidental; twelve values summing to anything else are
  not a chart.

## Rules

1. **Derive, never assert.** No total stated beside the data it summarises.
   Compute it from the same array the user is looking at. (The 337 bug.)
2. **No invented precision.** If the engine returns a band, do not render a
   percentage. See `gaugePositionFromScore` — it maps through the band so the
   ring and the label cannot disagree.
3. **One mapping, one place.** An engine field gets exactly one interpretation
   in the app. Two screens interpreting `score` separately is how they drift.
4. **Conventions travel with values.** Anything convention-dependent carries
   its `observance_note` / provenance to the surface that shows it.
5. **Placeholder must look placeholder.** A screen on literals must not be
   indistinguishable from a wired one, or it ships.

## Endpoint → screens → owner

Wire **by endpoint, not by screen**. `/vedic/{id}/all` feeds four screens; four
separate wirings produce four interpretations of the same payload.

| endpoint | feeds | status | owner |
| --- | --- | --- | --- |
| `/kundlis` | profile switcher, settings, onboarding | ✅ wired | — |
| `/context/{id}/daily` | Today, day-quality sheet, why-reading | ✅ wired | — |
| `/panchanga/{id}/today` | Today panchang grid | ⚠️ partial | A |
| `/vedic/{id}/all` | chart hub, full render, planet sheet, provenance | ✅ wired | — |
| `/vedic/{id}/dashas` + `/yogini-dashas` | Life Periods (21, 21b–d) | ⬜ placeholder | A |
| `/vedic/{id}/yogas-doshas` | Yogas & Doshas (22), Manglik sheet | ⬜ placeholder | A |
| `/vedic/{id}/ashtakavarga` | Strength — Ashtakavarga (23b) | ⬜ placeholder | A |
| `/vedic/{id}/jaimini` | Strength — Jaimini (23c) | ⬜ placeholder | A |
| `/vedic/{id}/transits` | Gochara (27), Full Transits (27b) | ⬜ placeholder | B |
| `/panchanga/cities` | location settings, birth details | ⬜ placeholder | B |
| `/readings/{id}` + `/claims` | Readings (31), Accuracy (31b) | ⬜ **no data** | B |
| `/ask/{id}` | Ask thread | ✅ wired | — |
| *(none — festivals)* | Calendar (28), festival sheet | ⬜ **endpoint unverified** | B |
| *(none)* | Compatibility (30, 30b, 30c) | ⬜ **no endpoint identified** | B |
| *(none)* | Muhurta (14, 15) | ⬜ **no endpoint identified** | A |
| *(none)* | Remedies (12, 13) | ⬜ **no endpoint identified** | A |
| *(none)* | Notes (32) | ⬜ **no endpoint identified** | B |

Owner A / B = the two agents. One endpoint, one owner, no overlap.

## Measured budgets

Taken from a live payload on :8010, profile `d6c3ccd9…`, 2026-07-27.

### `/context/{id}/daily` — Today

| field | measured | budget | note |
| --- | --- | --- | --- |
| `verdict.score` | `-4` | **signed tally, unbounded** | map via `gaugePositionFromScore`, never clamp |
| `verdict.tone` | `caution` | `supportive\|positive\|mixed\|caution` | the real output; the band drives the label |
| `verdict.headline` | 38 | ≤ 60 | H2, two lines |
| `verdict.text` | **469** | **sheet only** | overflowed the card once already |
| `reading.summary` | 68 | ≤ 110 | this is the card's detail line |
| `reading.focus` | **121** | ≤ 110 ⚠️ | over budget, but only the *third* fallback for the DO card (`do_today[0] ?? best_for[0] ?? focus`). Live data has `do_today = 2`, so it is not currently reached. The advice card grows rather than clipping, so this degrades before it breaks — fix when convenient, not urgent. |
| `do_today[]` | 2 | ≥ 1 | Today renders `[0]` |
| `avoid_today[]` | 4 | ≥ 1 | Today renders `[0]` |

### `/vedic/{id}/ashtakavarga` — Strength

| field | measured | budget |
| --- | --- | --- |
| `sav` | 12 entries, **sum 337** | **must be 12 and sum to 337** |
| `bav.{planet}` | 12 entries, sums 48/49/39 | 12 entries; per-planet totals vary |

### `/vedic/{id}/dashas` — Life Periods

| field | measured | budget |
| --- | --- | --- |
| `mahadashas[]` | 18 | ≥ 9 — screen must scroll, not fit |
| `cycle_years` | 120 | 120 (Vimshottari) |
| `current` | 8 nested levels | maha→antar→pratyantar→sookshma→prana |

## Known violations — the work queue

21 strings exceed 110 chars in live payloads. Each is a card-overflow waiting
for that screen to be wired:

| endpoint | field | chars |
| --- | --- | --- |
| `/context/daily` | `verdict.text` | 469 |
| `/context/daily` | `reading.focus` | 121 |
| `/panchanga/today` | `panchaka.note` | 133 |
| `/panchanga/today` | `gulika.note` | 115 |
| `/vedic/all` | `yogas.conventions.association` | 175 |
| `/vedic/all` | `doshas.gandanta.rule` | 132 |
| `/vedic/all` | `special_lagnas.notes[0]` | 129 |
| `/vedic/transits` | `gochara.core_reading.rationale` | **356** |
| `/vedic/transits` | `gochara.core_reading.reading` | 236 |
| `/vedic/transits` | `gochara.ashtakavarga.note` | 224 |
| `/vedic/transits` | `gocharam_periods[0].rationale` | 176 |

**The transits payload is the worst.** Gochara (27) and Full Transits (27b) are
still placeholder, and four of their fields run 176–356 chars. Whoever wires
them should design for the long form *first* — put the narrative in a sheet and
a short line on the card, the same shape Today ended up with.

`/readings/{id}` returns `[]`. Readings (31) and Accuracy (31b) have **no data
to render**, so "wiring" them means building the empty state honestly, not
faking rows.

## Validating this

Contract tests belong in `ui/src/app/core/*.spec.ts` and must run against a
live payload, because the breakage travels engine → UI:

```ts
expect(daily.reading.summary.length).toBeLessThanOrEqual(110);
expect(sav.reduce((a, b) => a + b, 0)).toBe(337);
expect(bandOf(gaugePositionFromScore(daily.verdict.score))).toBe(daily.verdict.tone);
```

The UI currently has **one** spec file against 100 backend routes and 31 Python
test files. That asymmetry is why all three defects reached a screenshot.
