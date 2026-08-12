# Health KB extension — cautions, constitutional susceptibility, and injury

**Status: source extract, grounded.** Extends
[health_kb_bphs_6th_house.md](health_kb_bphs_6th_house.md), which classified
most of ch.17's disease material as `gated_medical` in one broad bucket. This
pass re-examines that bucket shloka by shloka, applies the same **flag, not
verdict** treatment CLAUDE.md already gives a dosha to health-susceptibility
content, and fixes a real bug that would have made the result invisible to
users regardless.

Sources: `S 17.6–19½, p.114–118` and `S 24.85, 90, pp.167–168`.

---

## The governing principle, stated once so it doesn't need restating per row

CLAUDE.md's non-negotiable is *"no medical verdicts."* A caution is not a
verdict — that is the exact distinction the file already draws for a dosha:
*"a flag, not a verdict... never suppress one, never escalate it."* This
extension applies that same standard to health susceptibility: **name the
body system or the life-stage worth attending to; never name the specific
disease; never state a specific age.** That is the line every row below
holds to, and it is a real, meaningful line — not every excluded shloka
crosses back over it, and this document says exactly which do and don't.

It also means the earlier framing of this domain — that named-disease
content is inherently a "Western import" the classical text doesn't really
support — was wrong. Medical astrology (Jyotirvaidyam) is a real classical
discipline; the objection was never to the *existence* of health-prediction
content, only to serving a specific diagnosis as a certainty. The Cornell
tables specifically (pp.115–117, named modern diseases quoted from a 20th-c.
Western reference work inside Santhanam's commentary) stay excluded — not
because predicting health is illegitimate, but because achieving the actual
goal here (a caution that prompts a checkup) doesn't need named-disease
specificity at all, and using them would still mean citing a different,
copyrighted author's compiled work as if it were Parasara's. Nothing below
depends on that material.

---

## Reworked shloka by shloka

**S17.9–12½ is nine separate clauses, one per planet, not one claim.**
Previously gated as a whole; read individually, they split three ways:

- **Jupiter** — "destroys any disease." Protective, positive, always safe.
- **Mercury / Saturn / Moon (phlegmatic clause)** — bilious / windy /
  phlegmatic. These are the three Ayurvedic dosha categories (Pitta, Vata,
  Kapha), Parasara's own constitutional vocabulary — not diagnoses.
- **Mars** — "wounds and hits by weapons." A materially different claim from
  disease: injury/accident-proneness, the direct classical answer to "will I
  have an accident."
- **Sun, Ketu** — reframed as cautions below, dropping the verse's specific
  terms in favour of the body system they concern.
- **Venus** ("disease through females") — still excluded: too ambiguous to
  state responsibly under any framing, caution or verdict.
- **Rahu** ("danger through low-caste men") — still excluded, on a completely
  separate ground from every other exclusion in this pass: caste-based
  framing from the source period, unrelated to the medical question at all.

**S17.6 (facial disease)** and **S17.7–8½ (a specific historical skin/immune
condition, named across three planetary variants)** reframe as body-system
cautions — facial area, skin/immune area — dropping the specific historical
disease term, which is both stigmatizing and more specific than the
underlying signal warrants.

**S17.13–19½ (timing of illness) reframes as life-stage vigilance, not onset
of a named illness at an exact age.** The verse ties seven combinations to
ages 6, 12, 19, 22, 26, 29, 30, 45, 59, each with a named illness. Neither
the illness name nor the literal age is carried over — only which life stage
(childhood / youth / midlife-and-later) the combination flags as worth extra
attention, the same softening already applied to marriage and children
timing (early-vs-delayed rather than a literal year), extended here to
illness timing.

**ch.24.85–96 (8th lord) is almost entirely about longevity, not day-to-day
health** — same finding as ch.19. Two placements carry real, non-longevity
content: **85** (8th lord in lagna — general wound/injury vulnerability) and
**90** (8th lord in the 6th — general, unnamed illness susceptibility), each
stripped of the longevity/childhood-danger clauses riding in the same verse.

---

## The rules now servable

| Rule | Frame | Subdomain |
| --- | --- | --- |
| Jupiter clause (17.9–12½) — tends to protect against illness | positive flag | `vitality` |
| Mercury clause — Pitta/bilious-type constitutional sensitivity | caution | `chronic_disease` |
| Saturn clause — Vata/windy-type constitutional sensitivity | caution | `chronic_disease` |
| Moon clause (phlegmatic only) — Kapha/phlegmatic-type sensitivity | caution | `chronic_disease` |
| Mars clause — injury/accident-proneness | caution | `accidents_surgery` |
| S17.6 — facial-area caution | caution | `chronic_disease` |
| S17.7–8½ — skin/immune-system caution | caution | `chronic_disease` |
| S17.9–12½ Sun clause — feverish/inflammatory-susceptibility caution | caution | `acute_disease` |
| S17.9–12½ Ketu clause — abdominal/digestive-area caution | caution | `chronic_disease` |
| S17.13–19½ (childhood clauses) — childhood as a vigilance period | caution | `acute_disease` |
| S17.13–19½ (youth clauses) — youth/young adulthood as a vigilance period | caution | `acute_disease` |
| S17.13–19½ (midlife/later clauses) — midlife and later as a vigilance period | caution | `chronic_disease` |
| S24.85 — 8th lord in lagna: general injury/wound vulnerability | caution | `accidents_surgery` |
| S24.90 — 8th lord in 6th: general illness susceptibility | caution | `acute_disease` |

Fourteen rows, four subdomains (`accidents_surgery` and `acute_disease` had
**zero** references before this pass). Every row names an area or a
life-stage, never a diagnosis, never a year.

## Still excluded, and why each one specifically

- **S17.7–8½'s specific historical disease name** (kept only as a
  body-system caution above, not by name) — stigmatizing, and the name adds
  nothing the system-level caution doesn't already say.
- **S17.9–12½ Venus and Rahu clauses** — Venus is too ambiguous to state
  under any framing; Rahu is caste-based framing, an exclusion unrelated to
  the medical question this whole document is about.
- **S17.13–19½'s literal ages and named illnesses** — kept as life-stage
  vigilance flags above; the specific year and specific disease are the two
  things this framing exists to not restate.
- **ch.19, ch.24's ten longevity-flavoured 8th-lord placements** —
  unchanged, `gated_death`, regardless of the caution reframe: longevity
  refers out under CLAUDE.md categorically, and a caution framing doesn't
  change what longevity content is.
- **The Cornell disease tables** — unchanged. See "the governing principle"
  above: this isn't about the legitimacy of medical astrology as a field, it's
  that the actual goal here doesn't need this specific, copyrighted,
  misattributed material, and everything it would add is already covered by
  the reframed constitutional/system-level content above.

**Two exclusions in this pass are judgment calls, not mechanically
enforced** — same category as the childlessness/sin content excluded from
the children KB. The store-level `_MORTAL` guard is built to catch
longevity/death vocabulary and correctly does; it does not catch a named
disease with no death-adjacent word ("leprosy" alone), or death described by
euphemism ("the child will be deprived of its mother," ch.24.88, confirmed
by direct mutation test to slip past every existing pattern). A disease-name
blocklist would be its own large, easily-bypassed system that creates false
confidence, and "deprived of" cannot be added to the guard without breaking
already-shipped, correct references (`bphs24_80_seventh_lord_in_eighth`
legitimately reads "deprives the native of marital happiness"). Two new,
narrower guards were added instead, specific to this content class: no
`bphs17_*` caution reference may name a diagnosis-grade disease
(`test_health_caution_references_do_not_name_a_disease`), and no
vigilance-period reference may state a literal age
(`test_vigilance_period_references_do_not_state_a_literal_age`). Both
mutation-tested against the exact drift they exist to catch.

---

## The bug this pass also found: silent truncation, unrelated to content

Adding fourteen references made health's total 27 — and exposed that
`assemble_domain`'s `kb_limit` defaulted to **12**. Verified directly, not
assumed: with the old default, **11 of the 14 new references never reached
the bundle at all**, including both accident/injury rules and all three
vigilance-timing rules — the exact content this pass was built to add. They
existed, passed every content check, and were still invisible to a reading.

Fixed by raising the default to 30 (comfortably covers health's current 27;
verified all 14 previously-cut references now reach the bundle). A
regression test (`test_no_domains_bundle_reference_count_exceeds_kb_limit`)
guards the general case — whichever domain has the most references must not
exceed the assembler's default capacity — so this can't recur silently for
any domain as the KB keeps growing. Mutation-tested against the actual bug:
reverting the default to 12 makes the new test fail, confirming it would
have caught this before it shipped.

**Not fixed here, logged as a deliberate follow-up:** retrieval currently
queries with a domain's *entire* subdomain list regardless of what the
specific question is about — `assemble_domain` receives the real question
text but never uses it to narrow the KB query, only a text-similarity
retriever for `source_passages` uses it. A question-aware subdomain filter
would make the ranking itself smarter rather than relying on raising the cap
every time the KB grows; that's real new infrastructure (a subdomain
classifier, or reuse of existing intent detection), and deserves its own
deliberate scoping rather than being built as a side effect of a KB
extraction pass.
