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

## Where each text was read (D12)

Every verse the corpus ships is keyed from a print published before 1931 and
links the scanned page it was read from. The transcriptions are in
`scripts/mantra_corpus/rekey/transcriptions.tsv` in the print's own spelling;
`rekey/editions.json` lists the editions and is copied into `meta.editions`;
each mantra carries a `provenance` object.

| `provenance.kind` | Count | What it means |
| --- | --- | --- |
| `print` | 29 | Keyed from the page at `scan_page_url` (all Navagraha Stotra and Vedic verses, Mahamrityunjaya, Gayatri, Sarpa sukta, Manojavam, Rama nama, Guru vandana, Sarvamangala). |
| `formula` | 29 | Nama, bija and other short name-plus-salutation formulas. There is no edition text to key. |
| `reference_only` | 6 | Long recitations named as practices; no text shipped. |
| `no_print_located` | 4 | Sri Sukta v.1, Vakratunda, Saraswati vidyarambha, Santana Gopala. No pre-1931 print found yet; the text is unchanged. |

| Edition | Used for |
| --- | --- |
| Brihat Stotra Ratnakara, 7th ed., Nirnaya Sagar, Bombay 1912 | Navagraha Stotra (p.357), Rama Raksha vv.33, 38 (p.250) |
| Weber, Vajasaneyi Samhita, London/Berlin 1852 | the nine BPHS Vedic verses, Mahamrityunjaya, Sarpa sukta, Gayatri |
| Max Müller, Hymns of the Rig-Veda, London 1873 | RV 1.91.16 and 7.4.1 (Moon and Venus, Taittiriya forms) |
| Weber, Die Taittirîya-Saṃhitâ, Leipzig 1871 (roman script) | TS 3.4.11 and 4.7.13 (Sun and Mercury, Taittiriya forms) |
| Guru Gita, Samvad Gyan Ratnakar Press, Calcutta 1886 | Guru vandana |
| Jivananda, Markandeya Purana, Calcutta 1879 | Sarvamangala (Devi Mahatmya 11.10) |

The print's reading wins where it differs from the popular one; each such case
is stated in `disagreements`. Rama nama opens "राम रामेति रामेति", Guru vandana
reads "गुरुरेव परं ब्रह्म", Sarvamangala reads "मङ्गल्ये", and Mahamrityunjaya
reads "मामृतात्". "ॐ" before Gayatri and Mahamrityunjaya is the reciter's
prefix and is not in the print.

Spelling is normalised by `rekey/normalise.py`: the Subhashita rules (see
[subhashita_corpus.md](subhashita_corpus.md)), plus two for Weber's Madhyandina
print. Its ꣳ before a sibilant is written ं, and its avagraha before an
independent vowel (येऽअन्तरिक्षे) is written as a space. Vedic accent marks are
not reproduced.

## Regenerate

To correct a text, edit its row in `rekey/transcriptions.tsv`, not
`corpus_data.py`; the transcription overrides it at build time.

```
python3 -m pip install indic-transliteration
python3 scripts/mantra_corpus/build_corpus.py /tmp/mantras
cp /tmp/mantras/mantras.json astrospace/core/vedic/mantra_corpus/mantras.json
cp /tmp/mantras/bphs_antardasha_remedies.json astrospace/core/vedic/mantra_corpus/bphs_antardasha.json
```

Unbuilt follow-ups (audio, long texts, long-vow counts) are in the Deferred
backlog of [backend_astro_depth_checklist_2026-08-06.md](backend_astro_depth_checklist_2026-08-06.md).
