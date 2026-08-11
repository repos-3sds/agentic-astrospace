# KB extraction — design

**Status:** canonical design for turning the eight scanned classical texts into
KB entries. Living document; update as books are completed.

The goal is a student's notebook with footnotes: rules extracted from many
books, written in our own words, each traceable to book, chapter and page so
any claim can be re-checked. Not a copy of anyone's translation — the facts and
rules of the tradition are nobody's property, and `references.json`'s own
convention already says so ("statement is a paraphrased rule, never copied
translation text").

## What we are working with

| Book | Pages | OCR usable? | Median accuracy |
| --- | --- | --- | --- |
| Uttara Kalamritam | 258 | **yes (English)** | no pages flagged |
| BPHS Vol 1 (Sharma) | 659 | no | 46% |
| BPHS Vol 2 (Sharma) | 820 | no | 46% |
| Saravali | 353 | no | 42% |
| Phala Deepika | 548 | no | 38% |
| Jataka Parijata | 684 | no | 32% |
| Jatak Parijata v2 | 684 | no | 44% |
| `7136b975-c819-…` | 659 | — | **byte-identical duplicate of BPHS Vol 1 — delete** |

Seven of eight books have a failed OCR text layer. The EPUBs say so themselves,
per page. **The scans are excellent** — 300 DPI, high contrast, both scripts
legible — so the material is fine; only the text layer is junk.

This is not a footnote. It is the root cause of every fabricated KB document
produced for this project so far: a model handed `111६ 51111 8॥16 {116 001`
pattern-completes into plausible astrology. Reading four page images of BPHS
ch.19 corrected an LLM summary of that same chapter on eight points, including
four of nine planet-to-limb assignments and the rule's entire governing frame.

## Principle: the table of contents is the completeness oracle

You cannot prove nothing was missed by counting pages — you never know what you
did not look at. But every book here has a detailed TOC, and Uttara Kalamritam's
is *shloka-level*. That is a checklist the book supplies about itself.

So step one for every book is: **read the TOC and turn it into a manifest**
(`docs/kb_manifests/<book>.json`). Chapter, title, page range, and where
available the per-shloka topic list. The manifest is then the unit of work, the
unit of review, and the coverage report.

### The manifest must be gated, not trusted

The pilot proves why. A naive parse of Uttara Kalamritam's TOC returned:

```
Ch I     8 entries      Ch V     0 entries   <-- silent loss
Ch II   10 entries      Ch VI    2 entries
Ch IV    0 entries      Ch VII   4 entries
(Ch III missing entirely)
```

Chapter III vanished and IV/V came back empty, because the TOC spans more pages
than the parser sampled and its regex is fragile. Nothing errored. That is
exactly the failure mode this whole design exists to prevent, and it appeared on
the first and easiest book.

**Gate:** chapter numbers must be contiguous from the first to the last, no
chapter may have zero entries, and the page ranges must tile the book without
gaps. A manifest failing any of these is rejected, not used.

## Principle: tier extraction by consequence, not by page

4,000 pages read one image at a time is not affordable. It is also unnecessary,
because the accuracy a passage needs depends on what it becomes.

- **Tier 1 — prose** (~85% of pages). "The 6th house signifies enemies, debt,
  disease." Clean text layer, or re-OCR, is adequate; residual errors are
  visible and it gets rewritten in our words anyway.
- **Tier 2 — rules that become logic.** Planet→limb mappings, conjunction
  conditions, yoga definitions. **Vision read.** A 5% error rate over a
  nine-row table means one wrong row, and we now have a concrete example of
  what that costs.
- **Tier 3 — numeric tables that become code constants.** Vimshopaka weights,
  the 60 D-60 deities, dasha year counts. **Vision plus an arithmetic
  self-check** — weights sum to 20, list lengths are right, sequences do not
  repeat. The Vimshopaka table was wrong three times running and every round
  was caught by arithmetic, never by reading.

## Principle: provenance is per claim, and it is about trust

Every extracted rule carries: book, chapter, page, verse, `extraction_method`
(`text_layer` / `vision` / `vision+arithmetic`), and `verified_by`.

This is not bookkeeping. An LLM summary of BPHS ch.19 delivered a *perfect*
dhatu table and a *wrong* limb table in the same response, under the same
heading, with the same confident tone. Nothing distinguished them. Provenance is
what lets a reading know how much weight a rule can bear — and lets us find
every claim that rested on a method we later stop trusting.

**Translator's Notes are tagged separately.** Sharma's *Bhavat Bhavam* reasoning
on p.235 is his 20th-century analysis, not Parasara's verse. Both are usable;
conflating them would misrepresent whose authority a reading is invoking.

## Order of work, and why

1. **Uttara Kalamritam** (258pp) — *the pilot*. The only book whose English text
   layer works, small, and already load-bearing (`INDU_KALA` in
   `special_lagnas.py` cites it), so the pipeline can be proven end to end and
   validated against a constant already in the engine.
2. **BPHS Vol 1** — the primary authority. Its TOC is already read; chapter 7
   (p.97), 14 (p.194), 19 (p.233), 21 (p.251), 47 (p.618) are known landmarks.
3. **BPHS Vol 2.**
4. **Saravali, Phala Deepika, Jataka Parijata** — commentaries. Deliberately
   last: with BPHS extracted first these become *cross-checks* rather than
   independent sources that must be trusted cold.

## Definition of done, per chapter

1. Every manifest entry has an extract or an explicit `skipped` with a reason.
2. Verse numbers are contiguous — a gap means a missed page.
3. Anything becoming a code constant passed its arithmetic self-check.
4. Anything **contradicting an existing engine constant halts and escalates**
   rather than overwriting. Had this gate existed, the three Vimshopaka rounds
   would have stopped at round one.
5. Third-party and diagnostic content is tagged **at extraction time**, not at
   render time.

## Safety, stated once

Some of this material is diagnostic (kushtha, consumption) and much of it
concerns third parties — father, mother, elder brother. BPHS ch.19's rules
literally produce "your mother will have an ulcer".

**No third-party health or death rule is ingested until the third-party output
net merges** (PR #21). Tagging at extraction is what makes that enforceable
later rather than a thing someone has to remember.

## Open

- Re-OCR for the seven broken books. `knowledge/ingestion/mistral.py` suggests
  this was started. OCR is wanted for *navigation* — finding candidate pages
  fast — with vision doing the extraction. Not a source of truth.
- Delete the duplicate `7136b975-c819-…epub` before it is ingested twice and
  inflates confidence in double-counted passages.
