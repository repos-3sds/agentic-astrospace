# Health KB — BPHS, Effects of the Sixth House, in two translations

**Status: source extract, cross-verified.** Every rule below appears in *two
independent English translations* of the same chapter, read separately and by
different methods. Where they disagree, the disagreement is recorded rather than
resolved.

**Sources**

| | Translation | Chapter | Read how |
| --- | --- | --- | --- |
| **S** | R. Santhanam, `BPHS-Santhanam-Vol-1.pdf` | **17**, printed pp.113–120 (PDF 124–130) | text layer, 97.0% measured |
| **G** | Girish Chand Sharma, Vol 1 | **19**, printed pp.233–236 | rendered page images ([PR #26](../../../pull/26)) |

The chapter numbering differs between editions — Sharma's 19 and Santhanam's 17
are the same chapter, *Effects of the Sixth House*. Cite the translation
alongside the number or the reference is ambiguous.

---

## Why this document is a cross-check, not a second extract

[PR #26](../../../pull/26) extracted this chapter from Sharma by reading page
images, because that volume has no text layer at all. It corrected several
errors in an earlier LLM summary. Santhanam's volume, added later, is
machine-readable at 93.6% — so the same chapter can now be read a second time,
independently, and the two compared.

That is the two-agreeing-sources bar this project holds itself to, actually
executed rather than asserted. It produced one substantive result: **the two
translations agree on every rule, and differ on exactly one word.**

### Santhanam independently confirms both of PR #26's corrections

PR #26 said an LLM summary had merged planets and flipped a conjunction. Reading
Santhanam blind of that:

| Rule | LLM summary (wrong) | G (PR #26) | S (this read) |
| --- | --- | --- | --- |
| Leprosy | "Ascendant Lord, Mars, **and** Mercury" (three planets) | Mars **or** Mercury *as* ascendant lord | "Mars **or** Mercury having ownership of the ascending sign" ✓ |
| Fevers/tumours | "the 6th **or** 8th lord" | "the 6th **and** the 8th lords" | "the lords of the 6th **and** 8th" ✓ |

Both corrections hold in the second translation. The vision-read method that
produced PR #26 is validated.

### The one disagreement: मुख, Moon

Shlokas 3–5 assign a body part to each planet. Seven of eight match exactly:

| Planet | G (Sharma) | S (Santhanam) |
| --- | --- | --- |
| Sun | head | head |
| **Moon** | **mouth** | **face** |
| Mars | neck | neck |
| Mercury | navel | navel |
| Jupiter | — | nose |
| Venus | eyes | eyes |
| Saturn | foot | feet |
| Rahu/Ketu | stomach | abdomen |

**Neither is an error.** The Sanskrit *mukha* (मुख) covers both mouth and face,
and the two translators split it differently. This is convention-dependent in
exactly the sense CLAUDE.md means: state the rule and the ambiguity, do not pick
one and imply precision that the source does not have.

It also partly rehabilitates the LLM summary PR #26 marked wrong. That summary
said "face or throat"; "face" is defensible under Santhanam. The summary was
still unreliable — it was wrong about the chapter number, the governing frame,
and two conjunction rules — but this particular cell was a translation
difference, not a fabrication. Worth recording, because "the model was wrong"
and "the sources differ" are different problems with different fixes.

---

## The rules (Santhanam ch.17, shlokas 1–28)

Citations are `S 17.<shloka>, p.<printed page>`. Retrieval class in brackets —
see "Retrieval gating" below.

### Scope of the house
**S 17.1, p.113** — the 6th house governs diseases, ulcers and bruises. `[safe]`

### Affliction and the affected limb
**S 17.2, p.113** — 6th lord in the 6th, the ascendant, or the 8th → ulcers or
bruises on the body; the sign occupying the 6th indicates which limb. `[safe]`

**S 17.3–5, p.113–114** — a karaka or bhava lord joining the 6th lord, or placed
in the 6th/8th, carries the affliction **to the relative that karaka signifies**,
not to the native. Body-part assignment per planet as tabled above. Rahu and
Ketu own no house, so only their placement in the 6th/8th counts. `[safe]`

> The governing frame here is **relatives**, and PR #26 flagged an LLM summary
> for reading it as a body-map for the native. Santhanam is explicit: the
> example given is the mother incurring the affliction via the 4th lord.

### Named-condition rules
**S 17.6, p.114** — ascendant lord in a sign of Mars or Mercury, aspected by
Mercury → diseases of the face. `[gated_medical]`

**S 17.7–8½, p.114** — Mars or Mercury owning the ascendant and joining Moon,
Rahu and Saturn → leprosy; Moon in a non-Cancer ascendant with Rahu → white
leprosy; Saturn in place of Rahu → black; Mars → blood-leprosy.
`[gated_medical]`

**S 17.9–12½, p.115** — lords of the 6th and 8th in the ascendant, with: Sun →
fever and tumours; Mars → swellings, hardened vessels, weapon wounds; Mercury →
bilious disease; **Jupiter → destroys any disease**; Venus → disease through
women; Saturn → windy disease; Rahu → danger through low-caste men; Ketu →
navel disease; Moon → danger through water and phlegmatic disorder.
`[gated_medical]`

### Timing
**S 17.13–19½, p.117** — timing of illness. `[gated_medical]`

**S 17.20–22, p.118** — Moon conjunct 6th lord, 8th lord in the 6th, 12th lord
in the ascendant → trouble from animals in the 8th year. Rahu in the 6th with
Saturn in the 8th from Rahu → danger from fire in years 1–2, from birds in
year 3. `[gated_death]` (early-childhood danger)

**S 17.23–25, p.118** — Sun in the 6th or 8th with Moon in the 12th from that
Sun → danger through water in years 5 and 9. Saturn in the 8th with Mars in the
7th → smallpox in years 10 and 30. `[gated_death]`

**S 17.26, p.118** — 11th and 6th lords exchanging signs → loss of wealth in the
31st year. `[safe]`

**S 17.27, p.118** — 5th lord in the 6th, 6th lord with Jupiter, 12th lord in
the ascendant → one's sons become enemies. `[safe]`

**S 17.28, p.119** — ascendant lord and 6th lord in exchange → fear from dogs in
years 10 and 19. `[safe]`

---

## Deliberately NOT extracted: the Cornell disease tables

Printed pp.115–117 carry long planet-by-planet lists of named modern diseases —
cancer, diabetes, syphilis, epilepsy, tuberculosis and dozens more. **These are
not Parasara and not Santhanam.** The text says so plainly: Santhanam introduces
them with

> "Dr. H. L. Cornell, M. D., in his 'Encyclopaedia of Medical Astrology' enlists
> some important diseases under different planetary captions... I quote some as
> below"

They are excluded for three separate reasons, any one sufficient:

1. **Provenance.** Ingesting them would attribute a 20th-century Western medical
   astrology reference to a classical Sanskrit text. Our KB's value is that a
   citation means something.
2. **Copyright.** The project's position — that we are a student writing our own
   notes from the classics — covers learning a rule from Parasara. It does not
   cover copying a distinct modern reference work's tables wholesale out of a
   translation that is itself quoting them.
3. **Safety.** A planet→named-disease lookup is a diagnosis generator, and
   CLAUDE.md's non-negotiable is explicit that medical verdicts refer out.

Their location is recorded here so nobody re-derives this decision or assumes
the pages were missed. Santhanam also points to his own Saravali ch.47 notes for
the same material; Saravali is in the corpus and readable, so **that pointer is
a trap** — the same exclusion applies there.

---

## Retrieval gating

The KB stays raw, per standing instruction; the guardrails live at the domain
agent. These classes tell the agent layer what it is holding:

| Class | Meaning |
| --- | --- |
| `safe` | May be cited in a reading with normal framing. |
| `gated_medical` | Names a disease. Never surfaced as a prediction or diagnosis; usable only as a *susceptibility* framing, and the medical refer-out takes precedence. |
| `gated_death` | Concerns danger to life, childhood mortality, or longevity. **Must not be retrievable until the third-party death guard lands** — [PR #21](../../../pull/21) into [PR #20](../../../pull/20), currently open with a known regression where "will not live long" is missed for both parties. |

**The `gated_death` rules above are not safe to serve today.** `safety.py`'s
death cluster is anchored to "you", so third-party phrasing passes through, and
these shlokas are phrased about children and relatives. Extracting them now is
deliberate — the work is done and recorded — but retrieval must stay closed
until that net merges.

---

## The 6th lord through the twelve houses (S ch.24.61–72, pp.147–150)

This is the servable core of the health domain: where the 6th lord sits, stated
as disposition rather than diagnosis. All `[safe]` — none of these name a
disease or a lifespan.

| 6th lord in | Effect (S ch.24) |
| --- | --- |
| 1st | sickly; well known; hostile to his own people |
| 2nd | adventurous, famous among his group |
| 3rd | given to anger; bereft of (fraternal) support |
| 4th | devoid of maternal happiness |
| 5th | fluctuating finances |
| 6th | enmity with his own circle |
| 7th | deprived of happiness through the spouse |
| 8th | sickly, inimical |
| 9th | trades in wood and stone |
| 10th | well known among his men |
| 11th | gains wealth through his enemies |
| 12th | spends on vices; hostile |

Only the 1st and 8th placements are health claims at all; the rest are
temperament, relationships and money. **That is a finding, not an omission** —
BPHS treats the 6th lord as a significator of conflict and expenditure at least
as much as of illness, and a health reading built from this chapter should say
so rather than forcing every placement into a sickness frame.

> **Textual note.** The section heading reads "EFFECTS OF THE 6TH LORD IN
> VARIOUS HOUSES (up to shloka 71)" but the series runs to **72**, which carries
> the 12th house. Trusting the heading drops a placement. The book's own
> cross-references are not reliable bounds — the same lesson the Uttara
> Kalamritam contents taught.

---

## Chapter 19 (Eighth House) — extracted, and not servable

**S ch.19, pp.139–141 (PDF 139–141). Class: `gated_death` in full.**

This chapter is *not* the chronic-illness chapter its title suggests. It is a
longevity chapter end to end — shloka 1 "LONG LIFE", 2 "SHORT LIFE", 4–7 long
life yogas, 8–13 short life, including explicit infant mortality:

- 8th lord in an angle → long life; 8th lord with the ascendant lord or a
  malefic in the 8th → short-lived (1–2)
- weak ascendant lord with the 8th lord in an angle → a span of 20–32 years (8)
- 8th house, 8th lord and 12th house all conjunct malefic → "death instant at
  birth"; 8th lord in the 8th with an afflicted Moon → death within a month of
  birth (8–13)
- Santhanam's note is the useful structural point: a well-placed 8th lord is
  **not sufficient** on its own — the ascendant lord's strength is a
  simultaneous requirement for long life

**Product conclusion: this chapter is never served.** CLAUDE.md refers longevity
out to a professional, so no reading cites it, whatever the output guard does.
It is extracted for completeness and audit — so nobody re-reads it wondering
whether it was missed — and marked closed. The same applies to ch.43
(Longevity), ch.44 (Maraka), ch.71, and ch.9–10 (arishta/balarishta).

The distinction worth holding: the death guard in `safety.py` is a **net for
model output**, not a licence to retrieve this material. Fixing the net (see
below) does not open this chapter.

## What is not here

- **ch.9 Evils at Birth** (pp.87–94) and **ch.10 Antidotes** — not extracted; `gated_death`
- **ch.43 Longevity**, **ch.44 Maraka**, **ch.71 via Ashtaka Varga** — not extracted; `gated_death`
- **ch.24** lords other than the 6th — the 8th lord series belongs to the same
  gated class; the rest are other domains
- **ch.81** features of the parts of the body (pp.789–801) — physical
  description rather than health; unread
