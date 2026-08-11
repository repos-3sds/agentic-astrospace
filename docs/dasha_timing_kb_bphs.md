# Dasha timing KB — BPHS chapters 47 and 48

**Status: source extract, grounded.** Read from `BPHS-Santhanam-Vol-1.pdf`
(text layer measured at 93.6%, see [kb_corpus_sources.md](kb_corpus_sources.md)).
Citations are `S <chapter>.<shloka>, p.<printed page>`.

| Chapter | Title | Printed | PDF |
| --- | --- | ---: | ---: |
| 47 | Effects of Dasha | 453–464 | 461–472 |
| 48 | Distinctive Effects of … Vimshottari Dasha lords of various houses | 465–468 | 473–476 |

This closes the gap named in [health](health_kb_bphs_6th_house.md) and
[career](career_kb_bphs_10th_house.md): both extracts say *what* a placement
means and neither says *when*. Timing is what our readings actually deliver.

---

## 1. A computable rule we are not using

**S 47.3–4, p.453.** Where the dasha lord sits **by drekkana** determines *when
inside the dasha* its effects land:

| Dasha lord's drekkana | Effects felt |
| --- | --- |
| 1st | at the commencement of the dasha |
| 2nd | in the middle |
| 3rd | at the end |

**Retrograde reverses the order** — a retrograde planet in the 3rd drekkana
delivers at the start, and in the 1st drekkana at the end. **Rahu and Ketu,
being always retrograde, are always reversed.**

This is the most immediately useful thing in either chapter, because it is
**fully computable from what the bundle already has**: D3 is in the varga set
and retrogradation is on every planet brief. It converts "during your Jupiter
dasha, 2019–2035" — a sixteen-year smear that reads as a horoscope-column
generality — into "the weight of this falls in the closing years." That is the
difference between a reading that sounds like a prediction and one that sounds
like a consultation.

Not built here; this document is the source, and the engine hook is noted in
the backlog.

## 2. Dignity and placement gate the whole dasha

**S 47.5–6, p.453** — favourable if, **at the commencement of the dasha**, the
dasha lord is in the ascendant, exalted, in own sign, or in a friend's sign.
Unfavourable if in the 6th, 8th or 12th, debilitated, or in an inimical sign.

**S 48.1, p.465** — the same principle stated as an override, and it is the
sharper formulation: an *inauspicious* planet exalted and in a good house will
**not** produce unfavourable results, and a *benefic* debilitated and in a bad
house **will** produce adverse ones. Natural benefic/malefic status does not
survive contact with dignity and placement.

**The technique note is the part worth keeping** (S 48, p.466): placement is to
be assessed **both at birth and at the commencement of the dasha**, and both
taken into account. Our bundle currently carries natal placement only. Treating
a dasha as a fixed natal property is a real simplification, and the text says
so explicitly.

## 3. Dasha of the lord of each house (S 48.2–8, pp.465–466)

| Dasha of lord of | Effect | Class |
| --- | --- | --- |
| 1st | physical well-being | `safe` |
| 2nd | distress; possibility of death | `gated_death` |
| 3rd | unfavourable effects | `safe` |
| 4th | acquisition of house and land | `safe` |
| 5th | progress in education; happiness from children | `safe` |
| 6th | danger from enemies; ill health | `gated_medical` |
| 7th | distress to wife; possibility of death of the native | `gated_death` |
| 8th | possibility of death; financial losses | `gated_death` |
| 9th | education, religious mindedness, unexpected gains of wealth | `safe` |
| 10th | recognition from and awards by Government | `safe` |
| 11th | obstacles in gains of wealth; possibility of diseases | `gated_medical` |
| 12th | distress; danger from diseases | `gated_medical` |

**For career**, the 10th-lord row is the direct hit — "recognition and awards
from Government" reads in a modern chart as institutional recognition,
promotion, public office. **For health**, the 6th, 11th and 12th rows are the
timing layer that the 6th-house extract lacked.

Three rows carry "possibility of death" and are `gated_death`: they are not
retrievable, and longevity remains a refer-out under CLAUDE.md regardless of
the output guard ([#32](../../../pull/32)).

## 4. Santhanam's own corrections, which matter more than the table

The translator disagrees with a flat reading of his own list, twice, and both
disagreements make the material *more* usable:

**The maraka lords are not only marakas.** The 2nd and 7th are maraka houses,
so the list gives them death. But the 2nd is also the house of **wealth** — if
its lord is well placed, "there will definitely be gains of wealth during the
dasha of the lord of the 2nd" — and the 7th also indicates **marriage**, so a
well-placed 7th lord brings "auspicious celebrations during his dasha". A
reading that renders a 2nd-lord dasha as distress alone is *wrong on the
source*, not merely gloomy.

**The 3rd, 6th and 11th lords.** BPHS ch.34 states these give evil effects.
Santhanam records his disagreement explicitly, from practice: they do **not**
give unfavourable effects if placed in the 3rd, 6th and 11th respectively **in
their own signs**. He also notes the 11th lord in the 2nd, or the 2nd lord in
the 11th, as a powerful Dhana yoga.

This is a genuine intra-text conflict — ch.34 versus ch.48's commentary — and
is recorded as `convention_dependent` rather than resolved, per CLAUDE.md. State
the rule used.

## 5. A cross-check we can actually run

Santhanam points to **Mantreswara's *Phaladeepika* ch.VI** for the exception
cases where 6th/8th/12th lords produce *yogas* rather than harm — Harsha yoga
(6th lord in a dusthana with the 6th afflicted) and its siblings.

**Phaladeepika is in our corpus and is readable** — the OCR export scores 91.1%
([kb_corpus_sources.md](kb_corpus_sources.md)). So this is not a dangling
reference: it is a second independent source on the most contested part of this
chapter, and the two-agreeing-sources bar can be met on it. Named here as the
next cross-check rather than left as a footnote.

---

## Not extracted

- **S 47.7 onward** — the per-planet Vimshottari dasha effects (Sun through
  Ketu), each conditioned on that planet's natal dignity and associations. Large
  and directly useful; the natural next pass.
- **ch.46** — the dasha *systems* and their calculation (Vimshottari, Astottari,
  Kalachakra, Chara and some twenty more). Our engine computes Vimshottari; the
  rest are unbuilt and belong in the backlog, not the KB.
- **ch.49–50** — Kalachakra and Chara dasha effects. Not applicable until those
  systems exist.
- **Antardasha** — ch.52–64 carry sub-period effects. The sub-period is the
  window a consultation actually names, so this is the deepest remaining gap
  after ch.47's per-planet material.
