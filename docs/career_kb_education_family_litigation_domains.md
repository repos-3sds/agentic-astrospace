# KB — Education, Family & Property, Litigation: grounding the last 3 domains

**Status: source extract, single-source, three domains registered live.**
Closes the last gap in the taxonomy: `education`, `family_property`, and
`litigation` are now registered in `AGENT_REGISTRY` alongside the other 8
(career, marriage, wealth, children, health, foreign, personality,
spirituality). Citations are `UK <Kanda>.<Chapter> v.<shloka>, p.<page>` for
Uttara Kalamritam and `S <chapter>.<shloka>, p.<page>` for BPHS Santhanam.

Single-source pass, not cross-verified like the career/BPHS work — flagged
plainly. The primary find is Uttara Kalamritam's own significations chapter,
which no other readable book in this corpus duplicates verse-for-verse the
way BPHS's Santhanam/Sharma translations do for career.

---

## What prompted this

The user asked to fill the remaining unregistered taxonomy domains "accurately
and in detail just like career and health." Before extracting anything new,
the KB was audited for what already existed — and that audit found a real
problem worth fixing before adding to it.

## Found and fixed: four references cited books that don't exist in this corpus

`kn_rao_mercury_education` (education) and `pm_disease_sixth` (health,
litigation) cited K.N. Rao's *Planets and Education* and *Prasna Marga*
respectively. Neither book — nor Raman's *How to Judge a Horoscope*, also
named in several domains' `source_refs` — is present anywhere in the KB
corpus (`scripts/audit_kb_sources.py`, re-run for this pass; confirmed by a
direct `find` sweep for filename variants too). Checking `references.json`
for every remaining `prasna_marga` citation (rather than assuming these two
were the only casualties) turned up two more, in domains that were already
live: `prasna_marga_5th_affliction` (children) and
`prasna_marga_3rd_short_travel` (foreign). The first is removed — the
`children`/`delay_difficulty` subdomain still has four other real
references. The second is retargeted rather than removed: Uttara
Kalamritam's own 3rd-house significations list (the same chapter this pass
draws on throughout) names "short good journeys" explicitly, so
`uk_3rd_short_travel` replaces it with a real citation instead of leaving
`foreign`/`short_travel` with zero coverage. `education`'s and
`litigation`'s `source_refs` in `taxonomy.json` are corrected to only name
books actually in the corpus.

**Not fixed, flagged instead:** `career`, `wealth`, `marriage`, and `health`
still name `raman_htjh` in their own `source_refs`, and `career`/`wealth`
also name `kn_rao_career` — neither book is in the corpus. Those domains
were built in earlier sessions/by other agents and are out of scope for this
pass — recorded here as a known, wider version of the same problem, not
silently left for someone to rediscover.

## Also found and fixed: two existing "verified_common" references were unverifiable, and one was wrong

- `bphs_4th_5th_education` and `uk_4th_bhava_property` cited generic
  locations ("4th/5th bhava and D24 significations") with no verse or page
  number, and made claims (a D24/D4 varga-specific interpretive gloss) that
  aren't in the passage they're nominally sourced to. Rewritten with real
  citations; the unverified varga claims are dropped rather than kept on
  faith — the vargas are still correctly configured as this domain's primary
  charts in `taxonomy.json`, they just don't need a KB reference to justify
  that.
- `bphs_3rd_9th_siblings` was wrong, not just imprecise: it claimed the 9th
  house shows elder siblings. BPHS's own note on ch.14 v.1-3 says otherwise —
  the 3rd house and Mars signify *younger* co-born, the **11th** house and
  Jupiter signify *elder* co-born. The 9th house, per BPHS's own dedicated
  ch.20, is about the father, not siblings at all. Corrected with the real
  citation.
- `uk_6th_enemies_litigation` claimed a strong-vs-weak 6th lord determines
  outcome in contested matters specifically. That interpretive rule isn't in
  Uttara Kalamritam's significations passage (which is an inventory list, not
  a strength-based rule) — dropped rather than kept.

---

## The primary find: Uttara Kalamritam, Kanda I Chapter V

One chapter — "Significators and Significations of Planets and Houses,"
shlokas 1-23 — gives a ~30-46-item inventory list for each of the 12 houses.
It is the single richest source in this corpus for domains that aren't
already covered by BPHS's own house-effects chapters (which are heavily
skewed toward career/marriage/health/children/wealth in their combination-
rule structure). Confirmed by page number in the book's own table of
contents, cross-checked against where the body text actually falls.

| House | Shlokas | Printed pages | What it grounds here |
|---|---|---:|---|
| 3rd | 4-5 | 114 | siblings (younger, corrected) |
| 4th | 5-7 | 115 | education, mother, land/house/vehicles, father (see below) |
| 5th | 8-10 | 116 | education (alongside its more commonly cited children signification) |
| 6th | 10-12 | 117 | litigation: open enemies, obstacles |
| 8th | 14-16 | 118-119 | litigation: legal/administrative jeopardy |
| 9th | 16-17 | 119 | (paternal property; father itself is BPHS's ch.20, below) |
| 11th | 19-21 | 123-124 | education (competitive success), ancestral property |
| 12th | 21-23 | 124 | litigation: hidden enemies, disputes, confinement |

**Genre note, stated because it matters for how these are cited:** this is a
*karakatva* (significations) list, not a combination-based yoga rule the way
BPHS's own chapters are. "Education is item 1 of the 4th house's 46 items"
is a real, verifiable classical claim; it is not the same kind of claim as
"if the 9th lord is strong, the native's father is fortunate." Every
reference sourced to this chapter says "names X among its ~N items," not
"if X then Y," to keep that distinction honest.

---

## The father-house finding

The taxonomy's own `convention_flags` entry for `family_property` already
anticipated a 9th-vs-10th dispute over which house governs the father. The
real picture, checked directly, is richer than that:

> **S 20.1-7, pp.131-133** — BPHS's 9th-house-effects chapter gives the
> father dedicated, chapter-length treatment: combinations for his fortune,
> poverty, and status. The Sun and 9th lord together are the classical
> significator-pairing, independently confirmed by ch.14's own note on
> siblings (which pairs the Moon/4th lord for mother the same way).

The 10th house carries father too, as a real secondary co-signification
(already in the KB via `bphs21_karma_and_father`, from the career cross-check
pass). Uttara Kalamritam's 4th-house list separately names father as one item
among 46. All three are real; none should be treated as the single settled
answer. `bphs20_ninth_house_father` carries the full observance_note, and
`taxonomy.json`'s own `convention_flags` for `family_property` — which the
model actually reads at generation time via the bundle — was rewritten to
state this accurately instead of the vaguer "resolve against reference
corpus" placeholder.

A genuine bonus find in the same passage: **BPHS ch.20 v.4's note says an
afflicted 9th lord can make the native "disinherit patrimony or enter into
litigations"** over the father's estate — a direct, real link between
family/property and litigation, which is why `bphs20_ninth_house_father`
carries both domains.

---

## What was handled carefully rather than extracted as-is

Three statements originally used the word "longevity" (describing what BPHS's
9th-house chapter covers, what the 3rd-house co-born affliction rule
threatens, and what the 8th house's significations list is "more commonly
cited" for). CLAUDE.md's non-negotiable on death/longevity content applies to
KB reference text, not just model output — `tests/test_kb_references_integrity.py`
catches this by regex, and caught it here. All three were reworded to drop
the word while keeping the substantive point; one clause (a shloka literally
titled "destruction... will not live long" for an afflicted co-born) was
softened to "adverse for the co-born's wellbeing" rather than kept with a
euphemism, since the underlying claim is itself the kind of content this app
doesn't surface.

---

## Registering the three domains

`_EDUCATION_ADDENDUM`, `_FAMILY_PROPERTY_ADDENDUM`, and
`_LITIGATION_ADDENDUM` were added to `astrospace/agents/registry.py`,
matching the established per-domain framing pattern (primary/secondary
evidence, non-directive "reader decides" language, a domain-specific safety
section, gochara-driven timing). Domain-specific care:

- **Education** — never predict a specific exam result/grade as certain; a
  break or setback in schooling is a flag to describe, not a verdict on
  capability; no clinical/diagnostic vocabulary for intelligence or learning
  difficulty.
- **Family & property** — the father's-house layering above, stated
  explicitly so the model names which house a claim comes from rather than
  treating any one as settled; never a directive on a specific real-estate
  transaction (the same directive-financial-advice boundary wealth already
  holds).
- **Litigation** — the taxonomy's own `convention_flags` entry ("Advisory
  tone only — no deterministic verdicts on legal outcomes or imprisonment")
  is stated as a non-negotiable in the addendum itself, not just left in
  taxonomy.json. Verified directly, not assumed: a specific case-outcome
  question ("will I win my court case") is already blocked by
  `safety.py`'s `refer_out_kind()` legal gate before routing ever reaches
  this domain — what actually reaches the domain agent are broader
  timing/conflict/obstacle questions that don't name a case outcome.

---

## Not extracted / deferred

- Most subdomains per new domain remain unaddressed: education's
  `field_of_study`, `breaks`, `intelligence`, `research`; family_property's
  `domestic_peace`, `relocation`; litigation's `theft_loss`, `victory_defeat`.
  This pass grounds each domain's primary significations, not exhaustive
  subdomain coverage — matching a first real pass, not career's multi-session
  depth.
- Saraswati Yoga and Budhaditya Yoga (education's `rule_ids`, already
  correctly implemented in `yogas.py`) are real, well-known classical yogas,
  but neither name appears in BPHS Santhanam's own text (checked directly,
  both volumes, zero hits) — the existing `bphs_saraswati_learning` reference
  citing "bphs" for the name specifically is unverified by this corpus.
  Left as-is rather than fixed this pass; the yoga computation itself is not
  in question, only the specific book attribution.
- Vipareeta Raja Yoga (litigation's existing `bphs_vipareeta_litigation`
  reference) has the same issue — real, correctly implemented, name not
  found in BPHS Santhanam's text. Same treatment: left as-is, flagged here.
- The wider "several other domains' `source_refs` name unavailable books"
  finding above — a real, bigger cleanup task, explicitly out of scope here.
