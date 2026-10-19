Status: canonical. Sources, method and exclusions for Today's Subhashita (astrospace/core/subhashita/subhashitas.json); verses selected 2026-10-17, Sanskrit re-keyed from public-domain prints 2026-10-19.


# Quote-of-the-day corpus: sources and method

`subhashitas.json` holds 122 entries. Each one has `id`, `source`, `ref`, `sanskrit`,
`english`, `meaning` and `provenance`. `meaning` is one plain line on what the
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

## Where the Sanskrit comes from

The verses were first chosen from modern e-texts (2026-10-17). Those keyings are
someone else's work, so on 2026-10-19 (decision D12) every verse was **re-keyed
by hand from a scan of a print edition published before 1931**, read off the
page image rather than the scan's OCR. The e-texts are no longer used.

- `scripts/subhashita/rekey/transcriptions.tsv` has one row per verse: the
  verse `id`, the edition, the 0-based scan leaf, the printed page where the
  scan shows one, the text **in the print's own spelling**, and a note.
- `astrospace/core/subhashita/editions.json` is the edition registry: title,
  editor, publisher, place, year and archive.org identifier.
- Each corpus entry's `provenance` carries the edition id, a link that opens
  the scan at that page (`https://archive.org/details/<id>/page/n<leaf>/mode/1up`),
  the printed page and the note. Notes record where the print numbers a verse
  differently (for example Garuda 1.113.34 is printed as 113.33, Chanakya 8.11
  as 8.12) and where a second print was consulted.

| Edition | Verses |
| --- | --- |
| Bhagavad Gita, ed. J. Cockburn Thomson, Hertford: Stephen Austin, 1855 | 53 |
| Bhagavad Gita with Shankara's bhashya, Anandashrama Sanskrit Series 34, Poona, 1909 | 2 (16.2, 18.66) |
| Chanakya Niti Darpana, ed. Mihirachandra, Bombay: Venkateshvara Press, 1899 | 45 |
| Garuda Purana, ed. Jivananda Vidyasagara, Calcutta, 1890 | 9 |
| Vishnu Purana with Sridhara's commentary, ed. Jivananda Vidyasagara, Calcutta, 1882 | 2 |
| Markandeya Purana, ed. Jivananda Vidyasagara, Calcutta, 1879 | 3 |
| Bhagavata Purana, ed. E. Burnouf, tome 1, Paris: Imprimerie Royale, 1840 | 2 (1.2.6, 1.8.25) |
| Bhagavata Purana vol. II, ed. T. R. Krishnacharya, Bombay: Nirnaya Sagar, 1916 | 4 (skandhas 9-12) |
| Bhagavata Purana with Hindi tika, Bombay: Khemraj, 1924 | 2 (4.31.14, 7.5.23) |

`ref` and `id` keep the numbering the app shipped with, so a verse shared before
the re-key still resolves; where a print numbers a verse differently, the note says so.

### Which reading wins

The print's. Where the print reads differently from the e-text the verse was
chosen from, the corpus now follows the print, and the English was revised where
the meaning moved (Chanakya 1.16, 3.13, 4.18, 10.16). 36 verses changed text;
many of those are only spacing or a single letter (Garuda 1.111.24 नोदेति fixes
an e-text typo, नोदति). Two exceptions, both consulted against a second print:

- Gita 16.2 and 18.66: Thomson 1855 prints a minority reading; the 1909 Poona
  print has the common one, so those two verses cite the 1909 print.
- Markandeya 91.9: both scans of the 1879 print read सर्वमङ्गलमङ्गल्ये where the
  usual recitation is सर्वमङ्गलमाङ्गल्ये. The corpus follows the print for now;
  the Brihat Stotra Ratnakara (Bombay 1912) is to be checked with the mantra re-key.

### Spelling rules (`scripts/subhashita/rekey/normalise.py`)

The build turns the print's spelling into one house spelling. These rules never
change a word:

1. Split sandhi is joined: a final consonant written apart from the next word
   (Thomson's `मात्रास्पर्शास् तु`) is fused, and a space before avagraha removed.
2. A final anusvara before a danda is written म्.
3. An anusvara before a stop inside a word is written as that stop's nasal
   (संतुष्ट → सन्तुष्ट, कांचन → काञ्चन).
4. A consonant doubled after repha is written single (र्त्त → र्त, र्द्ध → र्ध).
5. An elided a after a long a, which some prints mark with avagraha (ाऽऽ, ाऽ), is dropped.
6. An avagraha the print leaves out is restored, only in the three listed words
   (प्रलयेपि, एकोपि, कोप्रियः in Chanakya 3.6, 4.6, 3.13).

Line breaks follow the corpus layout: two lines per anushtubh, four for the
longer metres.

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
Sanskrit against the cited print (each entry links its page), especially the
36 verses where the print and the e-text differed; (b) the Chanakya chapter.verse numbers against whichever
printed edition the app will cite; and (c) that each English rendering is faithful.
The renderings are deliberately short and loose. They are not translations to
quote in scholarship.

Until that review is done, the daily verse push starts **off** for everyone
(`DEFAULT_NOTIFICATION_PREFS` in `astrospace/db/crud_mobile.py`, and the
Settings > Notifications default). Readers can turn it on; the verse on Today,
the share image and the widget are unchanged. Flip both defaults, and
`test_off_by_default_until_the_scholar_review`, once the review is in.

## Regenerating

`python scripts/subhashita/build_corpus.py astrospace/core/subhashita/subhashitas.json`
rebuilds the file from `rekey/transcriptions.tsv`, with no network. The English
renderings live in the script. Adding a verse: key it from a pre-1931 print into
the TSV (adding the edition to `editions.json` if it is new), keep the source
alternation, and keep each English line at 180 characters or fewer.
`tests/test_subhashita.py` checks that every entry has provenance in a registered
pre-1931 edition.
