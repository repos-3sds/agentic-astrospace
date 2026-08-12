# Cross-check pass — Phaladeepika against the BPHS extracts

**Status: source extract and cross-verification, grounded.** Read from the
Mistral OCR export of `2015.92117.Mantreswaras-Phaladeepika.pdf`
(`ocr-playground-download-20260726T003631Z/…/markdown.md`), measured at 91.1%
median accuracy (see [kb_corpus_sources.md](kb_corpus_sources.md)). Translator:
**V. Subrahmanya Sastri** — a third translator in the corpus, distinct from
Santhanam (BPHS, Saravali). Citations are `Adhyaya <N> sloka <M> (Sastri
trans.)`.

This is the two-agreeing-sources pass the project has owed since the marriage
KB shipped. It does two things: adds new servable material Phaladeepika alone
supplies, and upgrades specific existing claims from single-source to
independently corroborated.

---

## Why Phaladeepika, not Saravali

Saravali was the standing candidate, named in four prior PRs. It doesn't work:
the only volume in our corpus (Vol I, OCR export) runs chapters 1–26 —
fundamentals, planetary theory, yogas — and never reaches a house-effect
chapter. Checked directly rather than assumed: chapters 5–7 (Miscellaneous
Matters, Yoga Karakas, Planetary Indications) contain no house-lord-in-house
material comparable to what was grounded from BPHS. Saravali remains untouched
for this purpose; it would need its later volume, which we do not hold.

**Phaladeepika is structurally the right candidate.** Its table of contents
(Adhyayas V, X, XII, XIV, XX) maps almost one-to-one onto the domains already
grounded: profession, the 7th house, children, disease/death, and — directly
useful — a dedicated chapter on the dasha effects of each bhava lord, the same
question BPHS ch.47–48 answers.

---

## Career (Adhyaya V) — a different technique, not a repeat

BPHS's career material is Rashi-placement of the 10th lord (`21`, `24.109-120`
— where the lord *sits*). Phaladeepika's Adhyaya V uses an entirely different
technique: the **navamsa occupied by the 10th lord** determines the *type* of
livelihood — its own sloka for each of the nine navamsa-lords (Sun's navamsa →
government service; Mercury's → writing, scholarship, clerical work; Mars's →
metals, adventure, conflict; and so on).

This isn't agreement or disagreement with BPHS — it's a second, independent
classical method addressing the same question, which is itself informative:
two authors centuries apart both treat the 10th lord as the key significator
of livelihood, just through different vargas. **Extracted as new material**,
not a repeat.

## Marriage (Adhyaya X) — real convergence, plus a real new problem

### Convergent
- **X.1, X.4, X.15** — the 7th house or its lord afflicted by, aspected by, or
  positioned between malefics: harm to the marriage. This is the same claim as
  **S 18.16**, stated independently. Two authors, same underlying rule.
- **X.9–10** — a strong, well-placed 7th lord (even sign, unafflicted,
  aspected by Jupiter) brings a marriage with happiness and children. Same
  claim as **S 18.4–5**.
- **X.13** — marriage may occur during the dasha of the planet occupying,
  aspecting, or owning the 7th house, or when the lagna lord transits into the
  7th sign. **New, safe, and useful**: a dasha-based marriage-timing technique
  BPHS's chapter 18 doesn't offer directly. Added.

### A worse version of a problem already known
- **X.3** gives *unconditional* single-placement spouse-death predictions —
  "Venus in Scorpio identical with the 7th, the wife will die" — with no
  strength check, no secondary condition. This is less hedged than anything
  kept from BPHS. `gated_death`, and a harder case for the same reason: there
  is no multi-factor combination here to soften, just a placement and a
  verdict. Excluded outright, same as BPHS's spouse-death timing.
- **X.2, 5–8** predict the exact **number of wives**, with the count of those
  who die attributed to the count of malefics among the significators. Same
  exclusion class as BPHS's number-of-children block (ch.16.24–32): a
  chart-derived exact count is the kind of deterministic claim this project
  avoids everywhere, and here it is explicitly bound to a death count on top.
  Excluded as a block.
- **X.11–12** — a technique for deriving the **spouse's own birth sign and
  home direction** from the native's chart. New exclusion ground, not covered
  by prior reasoning: astrology that purports to describe a *specific future
  partner's* characteristics is a direct enabler of match
  acceptance/rejection on astrological grounds — exactly the compatibility-
  gatekeeping harm Vedic astrology is sometimes reasonably criticised for.
  Excluded.

## Children (Adhyaya XII) — the most severe content problem found so far

### Convergent
- **XII.1, XII.10** — Jupiter and a well-placed, strongly-aspected 5th lord
  assure children; the character of the children follows the 5th lord's
  strength. Same claim as **S 16.12, 16.16**.
- **XII.8** — the 5th house in a Saturn/Mercury sign aspected by Mandi or
  Saturn, or a weak 5th lord disconnected from the 1st and 7th lords,
  indicates a child by adoption. Same claim as **S 16.11**, and it maps onto
  the taxonomy's `adoption` subdomain the same way.
- **XII.25–27, 29–30** — the birth of a child may occur during the dasha of
  the lagna lord, 7th lord, 5th lord, Jupiter, or a planet aspecting/occupying
  the 5th, or when Jupiter transits the 5th lord's sign. **New, safe,
  children-timing technique**, structurally parallel to the marriage-timing
  rule above. Added.

### The worst content problem found in either book
**XII.12 and 14–24** — a block that calculates a fertility-favourable tithi
from planetary positions, and then, if the calculation is unfavourable,
**names a specific past-life sin for each possible planet involved and
prescribes a ritual to atone for it** — a fault against Shiva for the Sun, the
anger of a wronged mother-figure for the Moon, a fault against a village
deity for Mars, and so on through all seven grahas, each with its own
prescribed worship. Childlessness is framed throughout as **karmic punishment
for the mother's or father's actions in a previous life**.

This is excluded outright, and it is a harder call than anything before it.
It is not primarily a "gendered language" or "exact count" problem — it is a
text that tells someone struggling to conceive that their condition is a
consequence of sin. There is no rephrasing that keeps a servable rule and
removes that framing; the framing *is* the content. Whether or not a reading
mentions "remedy" language elsewhere (CLAUDE.md permits traditional remedies,
never framed as "pay to remove"), attributing infertility to moral failing is
outside what this product does under any framing.

Related and excluded on a related but distinct ground:
- **XII.11** repeats the sex-of-children prediction problem already found at
  **S 16.13** — independently, in a second source. Not a new finding so much
  as confirmation that this is a real recurring pattern in the classical
  literature, not a one-off. Both stay excluded.
- **XII.6–7**, "yogas leading to family extinction," are excluded on
  severity grounds: the framing is anxiety-inducing in a way adjacent to
  `gated_death` even though it is not literally about the reader's own
  mortality.

---

## Dasha (Adhyaya XX) — the strongest single result of this pass

**Phaladeepika's dasha chapter opens with the same organising principle BPHS
47.5–6 and 48.1 state**, independently: the dasha of a bhava lord is read
differently depending on the lord's own strength and placement — not fixed by
which house it rules. Sloka 14 states this explicitly as the chapter's
governing premise before splitting into the strong-lord case (slokas 2–13)
and the weak-lord case (slokas 15–20). Slokas 22, 27, 30 and 34–38 restate the
same principle at the level of transits and sub-periods.

This is not a paraphrase of BPHS — it is a second author independently
choosing to lead with the identical interpretive rule. **`bphs48_1_dignity_over_nature`
is cross-verified** as of this pass; noted here rather than restated as a new
reference, since the existing entry already carries `status: verified_common`
and the corroboration is a fact about the claim's standing, not new content.

**The maraka-lords caveat is independently corroborated too.** BPHS's own
commentary (not the base verse) argues that a well-placed 2nd or 7th lord's
dasha gives gain, not just distress — already shipped as
`bphs48_maraka_lords_also_signify_their_house`, `convention_dependent`,
because it rests on one translator's gloss against a flatter reading. Phaladeepika's
strong-2nd-lord dasha (family success, good meals, eloquence — sloka 3) and
strong-7th-lord dasha (new possessions, marriage celebrations, virility —
sloka 8) state the *same* positive reading directly, as the base verse, not as
commentary on a different reading. **Added as a new reference below**, itself
`verified_common` since it is Phaladeepika's own direct statement.

The one place the two texts appear to differ is presentational, not
substantive: BPHS's ch.48.2-8 table (already grounded) reads as a flat
per-house list; Phaladeepika's chapter states from the outset that every
entry in such a list is conditional on the lord's strength. Read together, the
correct interpretation is Phaladeepika's explicit framing applied to BPHS's
table — which is exactly what `bphs48_1_dignity_over_nature` already told an
agent to do. The two texts do not conflict; the second one makes explicit
what the first required inference to reach.

**Excluded**: slokas 31–32 give an explicit calculation procedure for timing
a native's own death (weakest of several significators, refined by a Jupiter
transit trigger). `gated_death`, consistent with every other death-timing
material in this corpus — never extracted for retrieval regardless of the
output guard.

---

## What this pass changes, concretely

| | Before | After |
| --- | --- | --- |
| Career | single-source (BPHS) | + new technique (navamsa-of-10th-lord), Phaladeepika |
| Marriage | single-source | 3 claims cross-verified, 1 new timing rule |
| Children | single-source | 3 claims cross-verified, 1 new timing rule |
| Dasha dignity principle | single-source, already `verified_common` | independently corroborated by a second author |
| Maraka-lords-give-gain caveat | single-source, `convention_dependent` | corroborated by a direct (non-commentary) statement in a second text |

## Not extracted

- **Adhyaya VIII** (planet-in-house effects, all twelve houses) and **Adhyaya
  XVI** (general bhava effects) — a different organizing technique again
  (planet-in-house rather than lord-in-house); large, and the natural next
  cross-check pass once this one is reviewed.
- **Adhyaya XIV** (Diseases, Death) — not opened. Health already has a
  cross-verified extract (career/health/marriage/children pattern established
  by the 6th-house Sharma/Santhanam comparison); this chapter is the next
  candidate for extending that specifically, not attempted here to keep this
  pass to a size that can be reviewed.
- **Adhyaya XIX, XXI–XXII** (dasha systems and sub-periods generally) — belong
  with the engine backlog (only Vimshottari is built), not the KB.
