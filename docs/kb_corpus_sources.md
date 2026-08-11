# KB corpus — what each source is, and whether it can be read

**Status: source of truth** for which books in `Astro Space Knowledge Base/` are
machine-readable. Regenerate with `python scripts/audit_kb_sources.py` — the
table below is that command's output, not a hand-written list.

This file exists because the corpus has been described from memory twice and
been wrong both times. The most recent error, corrected below, was asserting
that one volume "tested clean" when it has no extractable text at all. Numbers
in prose go stale and get misquoted; a command does not. **Re-run the audit
rather than trusting this page**, and if the two disagree, the command wins.

## The inventory

| Source | Words | Accuracy | Verdict |
| --- | ---: | ---: | --- |
| `PDFs/BPHS-Santhanam-Vol-1.pdf` | 194,442 | **93.6%** | **Readable** — extract as text |
| `ocr/…Sharma Volume 1.pdf/markdown.md` | 156,242 | **93.8%** | **Readable** — OCR export |
| `ocr/saravaliofkalyan01kalyuoft.pdf/markdown.md` | 81,051 | **94.9%** | **Readable** — OCR export |
| `ocr/2015.406251.Brihat-Jataka_text.pdf/markdown.md` | 109,168 | **91.2%** | **Readable** — OCR export |
| `ocr/2015.92117.Mantreswaras-Phaladeepika.pdf/markdown.md` | 89,666 | **91.1%** | **Readable** — OCR export |
| `ocr/Uttara kalamritam..pdf/markdown.md` | 53,816 | **89.2%** | **Readable** — OCR export |
| `PDFs/dokumen.pub_nakshatra-…ebook.epub` | 39,084 | **90.6%** | **Readable** — extract as text |
| `EPUBS/Uttara kalamritam..epub` | 59,859 | 84.8% | Marginal — spot-check first |
| `PDFs/Uttara kalamritam..pdf` | 42,393 | 80.5% | Marginal — spot-check first |
| `PDFs/BPHS-Santhanam-Vol-2.pdf` | 105,878 | 56.1% | OCR mush — vision only |
| `PDFs/…Sharma Volume 1.pdf` | **0** | — | **No text layer** — vision only |
| `PDFs/…Sharma Volume 2.pdf` | **0** | — | **No text layer** — vision only |
| `PDFs/2015.406251.Brihat-Jataka_text.pdf` | 0 | — | No text layer — vision only |
| `PDFs/2015.92117.Mantreswaras-Phaladeepika.pdf` | 0 | — | No text layer — vision only |
| `PDFs/saravaliofkalyan01kalyuoft.pdf` | 0 | — | No text layer — vision only |
| `PDFs/Phala Deepika …Sastri.pdf` (92 MB) | 4,368 | — | Near-empty — vision only |
| all seven `EPUBS/*.epub` scans | 4k–8k | — | Near-empty — vision only |

`ocr/` above is `ocr-playground-download-20260726T003631Z/`.

## What the columns mean

**Zero words is not bad OCR — it is a different failure.** A file with no text
layer is a clean image scan; nothing ran on it. A file at 40% had OCR run and
produce mush. The first is recoverable by reading pages as images or by OCRing
once; the second is recoverable only by redoing the OCR.

**"Vision only" is not "useless".** Uttara Kalamritam's whole manifest was built
by reading rendered pages, and the scans are good. It means budget image reads,
not that the book is out of reach.

**The `EPUBS/*.epub` scans are page images wrapped in HTML** — roughly ten words
per page, which is the running header. Their ~90% "accuracy" is measured on that
handful of words and means nothing. Judge them by the word count, not the
percentage.

## Findings that cost real time to learn

**The OCR exports were nearly invisible and are the most valuable files here.**
`ocr-playground-download-…/` contains *directories named `<book>.pdf`*, each
holding a `markdown.md`. A suffix-based scan matches the directory, finds no
text, and reports a perfectly good book as empty — which is exactly what the
first version of the audit script did. Five books are already OCR'd there at
89–95%, including the Sharma BPHS whose own PDF has no text layer at all. There
is also a `pages/page-N/markdown.md` per page, which gives page-level anchors
for citation. `scripts/ingest_mistral_exports.py` already exists to read these.

**`BPHS-Santhanam-Vol-1.pdf` is not volume 1.** It holds the complete text,
chapters 1–97, with chapter 97 present in the body. It carries two contents
blocks — chapters 1–45 at PDF page 2 and 46–97 at PDF page 400 — which is what
makes it look like a part volume. No second volume is needed from this
translation. See `docs/kb_manifests/bphs_santhanam.json`.

**Prose and tables fail independently in the same file.** Santhanam Vol 1 scores
93.6% overall, and its 36 weak pages are charts, speculums and dasha tables
whose columns the extractor flattens. Uttara Kalamritam's prose extracted fine
while its three-column contents flattened into an unusable run of numbers. Never
conclude "this file is readable" from a prose sample and then read a table with
it.

**One true duplicate exists.** `EPUBS/7136b975-c819-43ae-8c04-b510504137e2.epub`
is byte-identical (md5 `5a520265039f…`) to
`EPUBS/…Sharma Volume 1.epub`. It was missed by a checksum sweep that filtered
on filename first — the lesson being to hash everything and group, rather than
hash the files you already suspect. Deleting it loses nothing; it is left in
place pending a decision.

## Corrections to earlier claims

- **"Sharma Vol 2 tested clean" — wrong.** It has zero extractable text, exactly
  like Sharma Vol 1. Both are image scans. Stated here because work was planned
  around pairing it with Santhanam Vol 1.
- **"7 of 8 books at 32–46% median" — misleading.** That measured the *PDF text
  layers*, several of which are simply absent. With the OCR exports counted, six
  sources are readable above 89%.
- **"There are no duplicate copies" — wrong**, see the UUID-named EPUB above.

## What this changes

The corpus is in far better shape than the earlier assessment implied. Readable
right now, without any new OCR: **BPHS** (two independent translations — a real
cross-check, which the two-agreeing-sources bar needs), **Saravali**, **Brihat
Jataka**, **Phaladeepika**, **Uttara Kalamritam**, and a **nakshatra** text.

Per-book structure and extraction bounds live in `docs/kb_manifests/`, gated by
`scripts/check_kb_manifest.py`. A manifest may not claim a book is readable
without a measured number, and may not measure below 60%.
