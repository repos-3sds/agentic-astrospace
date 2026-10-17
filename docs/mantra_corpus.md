# Mantra corpus and the personal remedy plan

**Status: canonical.** Source of truth for remedy mantra texts and for how the
Remedies page picks a profile's two or three remedies.

## What it is

| Path | What it holds |
| --- | --- |
| `astrospace/core/vedic/mantra_corpus/mantras.json` | 68 mantras. Each has Telugu script, English letters, Devanagari and IAST (`text.te/en/sa/iast`), meanings in English, Telugu and Hindi, source, KB page, counts, preferred day, disagreements, app-care note and `maps_to`. |
| `astrospace/core/vedic/mantra_corpus/bphs_antardasha.json` | All 81 Vimshottari dasha/bhukti pairs with the remedy BPHS (Santhanam tr., ch.52-60) names, each with its page. 61 name a mantra. |
| `astrospace/core/vedic/remedy_plan.py` | Picks at most three remedies for a chart. |
| `scripts/mantra_corpus/` | The build scripts. Devanagari is the master text; IAST and Telugu are generated from it with `indic-transliteration`, so the scripts cannot drift. |

The full research write-up, catalogue and CSVs are in the project's shared
files at `research/mantras/`.

## How the plan picks remedies

`GET /api/v1/remedies/{kundli_id}/plan` returns at most three groups, one mantra each:

1. **This period.** The mantra BPHS names for the running mahadasha/antardasha
   pair. Long recitations are swapped for a short verse from the same tradition
   (`_SHORT_FORM`), and the long text is named as the fuller practice. Where BPHS
   names only charity or a priest-led rite, the antardasha lord's nama mantra is
   used and the group says so.
2. **Main life area.** Houses scored by the dasha lords: antardasha lord occupies
   3, rules 2; mahadasha lord occupies 2, rules 1 (whole-sign from lagna). The top
   house maps to a deity (`_LIFE_AREAS`); that pairing is household convention and
   is labelled convention-dependent. No area is called "health".
3. **One flag**, only if present: gandanta, grahan, or the running dasha lord
   debilitated or combust. A flag, not a verdict.

The old `GET /api/v1/remedies/{kundli_id}` catalogue is unchanged.

## Care rules (non-negotiables)

- BPHS frames many dasha remedies against disease or early death. Only the
  practice and the page citation are shown, never that reason.
- Mahamrityunjaya is presented as a prayer to Shiva for steadiness.
- Bija and Vedic mantras are never chosen by default (many traditions expect a
  teacher). Santana Gopala is never auto-surfaced.
- Lakshmi mantras carry no money-outcome copy.

## Findings worth knowing

- BPHS 84.19 gives Mars 10,000 japa (*diśaḥ* = 10); Santhanam's printed table says 11,000.
- Telugu temples recite the Taittiriya Navagraha Sukta, which differs from BPHS
  for the Sun, Moon, Mercury and Venus. Both are in the corpus (`*-vedic-taittiriya`).
- The nine nama mantras and 20 short deity texts were not compared with an online
  edition; a Sanskrit reader should proofread before wide release.

## Regenerate

```
python3 -m pip install indic-transliteration
python3 scripts/mantra_corpus/build_corpus.py /tmp/mantras
cp /tmp/mantras/mantras.json astrospace/core/vedic/mantra_corpus/mantras.json
cp /tmp/mantras/bphs_antardasha_remedies.json astrospace/core/vedic/mantra_corpus/bphs_antardasha.json
```

Unbuilt follow-ups (audio, long texts, long-vow counts) are in the Deferred
backlog of [backend_astro_depth_checklist_2026-08-06.md](backend_astro_depth_checklist_2026-08-06.md).
