Status: canonical. Sources, method and exclusions for Today's Subhashita (astrospace/core/subhashita/subhashitas.json); research done 2026-10-17.


# Quote-of-the-day corpus: sources and method

`quotes.json` holds 122 entries. Each one has `id`, `source`, `ref`, `sanskrit`,
`english`, `meaning` and `verified_from`. `meaning` is one plain line on what the
verse asks of the reader, shown under it on every surface (added 2026-10-18,
when a verse on its own read to Hawk as half a sentence); the lines live in
`scripts/subhashita/meanings.json`, which the build script merges in. The array is ordered so that no two neighbouring
entries share a `source`, and the last entry's source differs from the first, so
`index = day mod 122` never shows the same source two days running.

| Source | Count |
| --- | --- |
| Bhagavad Gita | 55 |
| Chanakya Niti (Chanakya Niti Darpana) | 45 |
| Garuda Purana (Niti-sara, Purvakhanda 108-113) | 9 |
| Bhagavata Purana | 8 |
| Markandeya Purana | 3 |
| Vishnu Purana | 2 |
| **Total** | **122** (22 Purana entries) |

## How each verse was checked

I did not type any Sanskrit from memory. A build script pulled every `sanskrit`
field programmatically out of a downloaded source file, keyed on its
chapter/verse number. Each entry's `verified_from` is the exact raw URL of the
file the text came from. The script also asserts that the chapter and verse in
the file match the `ref`.

### Sources I could reach

| Source | Reachable? | Used for |
| --- | --- | --- |
| `raw.githubusercontent.com/vedicscriptures/bhagavad-gita-data` (one JSON per verse in `slok/`) | yes | all 55 Gita verses |
| `github.com/sanskrit/raw_etexts` (cloned at commit `d0754ea9d5b68d74f5fed4783543ad1814e45e07`, raw URLs return 200) | yes | Chanakya Niti and all Puranas |
| sanskritdocuments.org `chANakyanItisort.html` | only through a summarising fetch tool, which can't return verbatim text | cross-checking Chanakya verse numbers only |
| sa.wikisource.org, GRETIL (gretil.sub.uni-goettingen.de), sacred-texts, archive.org, gitasupersite, vedabase, wisdomlib | no (blocked by the network proxy) | none |

The sandbox could not reach sa.wikisource.org or GRETIL directly. The Purana
texts were therefore read from **GRETIL's own e-texts as mirrored in Devanagari**
inside `sanskrit/raw_etexts` (`mixed/gretil_devanAgarI/...`). These files keep
GRETIL's verse labels, such as `॥ गर्प्_१,१११।२४ ॥`.

### Gita
- Text: vedicscriptures/bhagavad-gita-data, `slok/bhagavadgita_chapter_{c}_slok_{v}.json`.
- Numbering: the standard 18-chapter, 700-verse vulgate (the same as Gita Press). `ref` is `chapter.verse`.
- Normalisation: ASCII `|` / `||` became `।` / `॥`, and verse-number trailers were removed. Speaker lines (`श्रीभगवानुवाच`) were dropped.

### Chanakya Niti
- **Recension and numbering:** the 17-chapter *Chāṇakyanītidarpaṇa* (the vulgate *Vṛddha-Cāṇakya* that opens with प्रणम्य शिरसा विष्णुं). The text comes from the eBharatiSampat e-text Ebharati-4111, contributed by Rashtriya Sanskrit Vidyapeetha, Tirupati, at `sanskrit/raw_etexts/.../chANakyaH/chANakyanItidarpaNam.md`. `ref` is `chapter.verse` in that e-text's numbering.
- Numbering was cross-checked two ways. The first was the 1925 Mihirachandra Sharma edition (Ebharati-4608, in the same repo; OCR, so only partly matchable). The second was sanskritdocuments.org's text, which is based on the Sharma edition and proofread by Sunder Hattangadi. All 45 numbers agree with sanskritdocuments wherever I checked them. Of the 31 checked against the Sharma OCR, 30 agree. The exception is 8.11 (न देवो विद्यते काष्ठे), which the OCR search placed at 8.12, while sanskritdocuments has 8.11.
- Numbering differs between Chanakya Niti editions, especially in chapters 8, 13, 15 and 16. The e-text repeats some verses (8.12 = 8.13, 13.6 = 13.7, 15.18 ≈ 15.19). I dropped any candidate whose number disagreed between the sources (see below).
- Normalisation: the e-text drops the virama on a final -t before a danda (कारयेत।). I restored it (कारयेत्।) in 2.7, 13.2 and 15.10. No other edits.

### Puranas
| Text | Edition behind the GRETIL file | `ref` format |
| --- | --- | --- |
| Bhagavata Purana | GRETIL `bhagp/bhagavata-purana_N.md` (labels `भ्प्_skandha।adhyaya।verse।pada`) | skandha.adhyaya.verse |
| Vishnu Purana | Venkatesvara Steam Press, Bombay 1910 (SANSKNET input) | amsha.adhyaya.verse |
| Garuda Purana | Venkatesvara Press, Bombay (SANSKNET input) | khanda(1 = Purvakhanda).adhyaya.verse |
| Markandeya Purana | SANSKNET input, adhyayas 1-93 | adhyaya.verse, in the continuous numbering of the whole Purana |

- Markandeya 85.23 and 91.9 are from the Devi Mahatmya, which sits inside the Markandeya Purana. Its own chapter numbering differs: MarkP 85 is Devi Mahatmya ch. 5 and MarkP 91 is ch. 11. The `ref` uses the Markandeya numbering, as the source file does. 91.9 (सर्वमङ्गलमाङ्गल्ये) is usually cited as Devi Mahatmya 11.10.
- Markandeya 58.71 comes from a passage advising conduct when the planets afflict someone (ग्रहपीडा). It is relevant to the app, and it is advice about conduct, not a remedy you pay for.
- Normalisation: GRETIL separates words with spaces and hyphens. I joined them back mechanically: hyphens removed, a final consonant with virama + space + next word fused, a space before avagraha removed. For example, `एतावज् जन्म-साफल्यं` became `एतावज्जन्मसाफल्यं`, and `दैत्याःसमताम्` (VP 1.17.90) became `दैत्याः समताम्`. No letters were changed. One space in the source was kept: `सर्वपाप प्रणाशनम्` in Bhagavata 12.13.23.

## English renderings
These are my own short, plain renderings, written for this corpus and not copied
from any published translation. Each is at most 180 characters (the longest is 168).
I gave up literalness in a few places, all of them noted here:
- Chanakya 3.14 and 4.6 say *putra* (son). I rendered it "child".
- Chanakya 3.8 *kiṃśuka* is rendered "palash", the common Indian name.
- Chanakya 5.4 *nakṣatra* is rendered "birth star".
- Gita 6.40 *tāta* is rendered "dear one".
- Bhagavata 9.21.12 compresses "the eight siddhis" to "its powers".

## Candidates dropped, and why
- **Content excluded by policy:** Chanakya verses that disparage women or castes. These include 1.5, 1.15, 1.17, 2.1, 2.16, 4.13, 5.1, 5.21, 6.3, 6.4, 6.11, 8.5, 8.18, 10.4, 11.11-11.17, 14.12, 16.2, 16.3, 17.1, 17.6, 17.9-17.11 and 17.14. Also excluded: verses about death or lifespan (Chanakya 4.1, 4.4, 4.7, 5.15, 12.12, 13.1, 13.9), medical or diet claims (Chanakya 8.7, 10.19, 10.20, 17.14), and Chanakya 1.12 (it mentions the cremation ground). Gita 3.30 (युध्यस्व, "fight") and Gita 2.20 and 3.35 (death framing) were excluded too, as were Garuda Purana 1.109.36-39 and 1.109.45 (demeaning to women), all of which I read and rejected.
- **Reading disputed in the source:** Gita 2.64. The data file prints विमुक्तैस्तु with "(or वियुक्तैस्तु)". Gita Press reads वियुक्तैस्तु, so I left the verse out rather than pick a reading.
- **Number disputed between editions:** Chanakya 8.14 शान्तितुल्यं तपो नास्ति (8.13 on sanskritdocuments), 16.17 प्रियवाक्यप्रदानेन (16.13 on sanskritdocuments), and 17.15 परोपकरणं येषां (17.16 in the Sharma OCR).
- **Source text corrupt:** Chanakya 7.20 (परार्थिनाम् is ambiguous) and 10.2 (typo वाक्यः). Garuda 1.109.46 शनैर्विद्या (typo शनैर्थाः) and 1.111.33 (typo सिद्धर्यस्य). Chanakya 12.14 मातृवत्परदारेषु has a corrupt character in the e-text; the verse also appears clean as Garuda 1.111.12, but I didn't use either.
- **Doesn't stand alone:** Gita 12.13, 12.18, 13.8, 16.1 and 16.3 each continue into the next verse. Bhagavata 8.5.49 overlaps 4.31.14.
- **Possible Puranic verses not used:** I could only verify Puranas from the GRETIL mirrors listed above. I found no Padma, Shiva or Skanda candidate worth the extra risk. Twenty-two verified entries were kept rather than padding the list.

## Before launch
**Have a Sanskrit scholar read this before launch.** Ask them to check (a) the
Sanskrit against a printed critical or standard edition, especially the Garuda
and Chanakya e-texts, which are SANSKNET or eBharati keyings with known typos
elsewhere in the files; (b) the Chanakya chapter.verse numbers against whichever
printed edition the app will cite; and (c) that each English rendering is faithful.
The renderings are deliberately short and loose. They are not translations to
quote in scholarship.

Until that review is done, the daily verse push starts **off** for everyone
(`DEFAULT_NOTIFICATION_PREFS` in `astrospace/db/crud_mobile.py`, and the
Settings > Notifications default). Readers can turn it on; the verse on Today,
the share image and the widget are unchanged. Flip both defaults, and
`test_off_by_default_until_the_scholar_review`, once the review is in.

## Regenerating

`scripts/subhashita/build_corpus.py <download dir> <out.json>` rebuilds the file from the fetched sources; the English renderings live in the script. Copy its output to `astrospace/core/subhashita/subhashitas.json`. Adding verses: keep the source alternation, and keep each English line at 200 characters or fewer (tests/test_subhashita.py enforces the length).
