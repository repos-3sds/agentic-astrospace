# Gocharam Engine — Review Request for an Astrologer

**Status:** point-in-time review request, prepared 2026-07-29. This is not a
tracker — see `docs/gocharam_engine_checklist.md` for the living build log.
This document exists to be handed to a practicing astrologer for review; it
explains what the software calculates and asks for a verdict on the items
listed in Section 8.

---

## 1. Purpose

This app (AstroSpace) computes Vedic transits ("Gocharam") for users
automatically, on every visit, for any birth chart. Nothing in it is written
by hand per-user — it is a fixed set of classical rules and a fixed table,
applied by calculation. This document explains exactly what that rule set
is, what it is based on, what is a direct classical source versus a common
applied convention, and what still needs a qualified astrologer's judgment.

We are not asking you to review code. We are asking you to review the
**astrological content**: is the rule table correct, is the terminology
right, and are the conventions we chose (where the classical texts are
silent or disputed) the ones you would choose.

---

## 2. System design in plain terms

- **Style:** South Indian Gocharam. Every transit is judged primarily from
  the natal **Moon sign** ("Chandra Lagna"), with the natal **Ascendant
  (Lagna)** used as a secondary, practical cross-check for a small number of
  rules (noted below).
- **Sidereal, Lahiri ayanamsha by default** (user-configurable), whole-sign
  houses, Swiss Ephemeris positions, mean node for Rahu/Ketu by default.
- **One calculation, many screens.** The web app and the native mobile app
  both read the same computed result — there is no separate "mobile logic"
  that could disagree with "web logic."
- **Every result carries its evidence.** A user never just sees "favourable"
  — they see the house it's computed from, whether Vedha (obstruction)
  applies, the Ashtakavarga support level, the planet's dignity, and the
  active Dasha, all as separate, inspectable facts.

---

## 3. Primary classical source

**Phaladeepika, chapter 26** — the standard favourable-house and Vedha
(obstruction) table for the seven visible grahas (Sun through Saturn). This
is the backbone of the whole engine: every planet's baseline "is this a good
house to be in" verdict comes from this table, reproduced below in full.

Everything **not** in this table (Rahu/Ketu's borrowed convention, the named
long-cycle labels like Sade Sati, the plain-language commentary) is
explicitly labeled in the software as a **configured convention** or
**editorial synthesis**, never presented as a direct quotation from
Phaladeepika or any other single text. Section 7 explains this labeling.

---

## 4. The favourable-house / Vedha table

For each planet, "favourable house" is counted **from the natal Moon**.
"Vedha house" is the house that, if a **different** planet is transiting it
**at the same time**, cancels/obstructs the favourable result.

| Planet | Favourable houses (from Moon) | Vedha house for each |
|---|---|---|
| Sun | 3, 6, 10, 11 | 9, 12, 4, 5 |
| Moon | 1, 3, 6, 7, 10, 11 | 5, 9, 12, 2, 4, 8 |
| Mars | 3, 6, 11 | 12, 9, 5 |
| Mercury | 2, 4, 6, 8, 10, 11 | 5, 3, 9, 1, 8, 12 |
| Jupiter | 2, 5, 7, 9, 11 | 12, 4, 3, 10, 8 |
| Venus | 1, 2, 3, 4, 5, 8, 9, 11, 12 | 8, 7, 1, 10, 9, 5, 11, 6, 3 |
| Saturn | 3, 6, 11 | 12, 9, 5 |

**Exemption:** no Vedha operates between **Sun and Saturn** (father–son) or
between **Moon and Mercury**, even if one is in the other's Vedha house.

**Rahu and Ketu** are not part of the Phaladeepika table. By configured
South-Indian convention, the software treats them like Saturn (favourable in
3, 6, 11 with the same Vedha houses) — this is explicitly flagged in the
software as `convention_dependent`, not attributed to Phaladeepika.

**→ Please confirm:** is this table, as reproduced, the version/edition you
would use? Do you agree with the Rahu/Ketu-as-Saturn convention, or do you
use a different treatment?

---

## 5. Named long-cycle rules (Saturn and Jupiter)

Because Saturn and Jupiter move slowly enough (roughly 2.5 years and 1 year
per sign respectively) to warrant dedicated attention, the software names
these specific configurations, all measured from the natal Moon:

| Name | Trigger | Notes |
|---|---|---|
| **Sade Sati** | Saturn in the 12th, 1st, or 2nd house from Moon | Three "legs": 12th = rising/first, 1st = peak/core, 2nd = setting/final. |
| **Ashtama Shani** | Saturn in the 8th house from Moon | |
| **Ardhashtama Shani** (also called **Kantaka Shani**) | Saturn in the 4th house from Moon | Both names are used in practice; the software now shows one combined label. |
| **Ashtama Guru** | Jupiter in the 8th house from Moon | Generally read as a cautionary Jupiter transit. |
| **Jupiter's Bhagya transit** | Jupiter in the 9th house from Moon | Read as one of the most auspicious Gochara positions. |

**Retrograde handling:** Saturn regularly moves forward across one of these
house boundaries, then retrogrades back across it, then finally crosses
forward for good. The software now detects **every** such pass within a
~4-year window around today and labels each one — first entry, retrograde
return, or final exit — with its own start/end date, rather than reporting
one (sometimes wrong) continuous window. This was checked against a real,
verifiable event: Saturn's 2022 entry into Aquarius, retrograde return to
Capricorn, and final Aquarius re-entry in early 2023.

**→ Please confirm:** do you agree with the house definitions above? Is
"Ardhashtama Shani (Kantaka Shani)" the right combined name, or do you
distinguish these as two different things in your practice?

---

## 6. Other named overlay rules

Beyond the two above, the software flags a small number of additional
named triggers (all measured from natal Moon unless noted):

| Name | Planet | Houses | Reading |
|---|---|---|---|
| Guru Bala (from Moon) | Jupiter | 2, 5, 7, 9, 11 | Supportive |
| Guru Bala (from Lagna) | Jupiter | 2, 5, 7, 9, 11 | Supportive, secondary cross-check |
| Rahu caution | Rahu | 1, 5, 7, 8, 9, 12 | Challenging |
| Ketu caution | Ketu | 1, 5, 7, 8, 9, 12 | Challenging |
| Mars trigger | Mars | 1, 4, 7, 8, 12 | Challenging |
| Upachaya strength | Sun, Mars, or Saturn | 3, 6, 11 | A general classical principle that these three malefics are considered strong (not weak) in the 3rd/6th/11th houses regardless of the favourable-house table above — currently only narrated in the commentary, not a separate activation rule. |
| Chandrashtama | Moon | 8 | The same configuration daily muhurta timing already flags separately in this app; noted here only in the narrative text, not recalculated twice. |

**→ Please confirm:** are the Rahu/Ketu caution houses (1, 5, 7, 8, 9, 12)
and the Mars trigger houses (1, 4, 7, 8, 12) consistent with your practice?
These are labeled `south_indian_common_practice`, not tied to a specific
text, and are the least classically anchored part of the rule set.

---

## 7. Modifiers — what adjusts a verdict without overriding it

The software never lets a modifier silently change the base classical
verdict; it always keeps the base verdict and the modifier as separate,
visible facts. Four modifiers currently apply:

1. **Vedha** (Section 4) — obstructs a favourable placement.
2. **Ashtakavarga (BAV/SAV/Kakshya).** Standard Bhinnashtakavarga/
   Sarvashtakavarga bindu counts for the transited sign, plus which of the
   eight 3°45′ Kakshya segments the planet occupies and whether that
   segment's own lord actually contributed a bindu. Thresholds currently
   configured: **BAV 5+ = strong, 4 = average, ≤3 = weak**; **SAV 30+ =
   strong, 25–29 = average, <25 = weak**.
3. **Dignity.** Whether the transiting planet is Exalted, in Moolatrikona,
   in its Own sign, or Debilitated in the sign it's currently transiting
   (independent of the house-from-Moon reading). Rahu/Ketu are treated as
   dignity-neutral, since classical dignity conventions for the nodes vary.
4. **Retrograde motion** — noted as "review, repeat, or internalize the
   transit theme," not treated as good or bad on its own.

A challenging rule is stepped one level milder when BAV support is strong,
dignity is strong, or the Kakshya lord gave a bindu — and one level more
serious under the opposite conditions (this direction was previously
missing from the software and was added this session). A supportive rule is
marked "diluted" under the same weakening conditions.

**→ Please confirm:** are the BAV/SAV thresholds above (5/4/3 and 30/25)
the ones you'd use, or do you use different cutoffs? Do you agree dignity
and Kakshya-bindu status should modify severity the way described?

---

## 8. How the plain-language commentary is written — and its review status

For all 108 planet/house combinations (9 planets × 12 houses from Moon), the
commentary shown to users is assembled from:

- The favourable/unfavourable verdict (Section 4 — classical, verified).
- The houses that planet classically **aspects** from that position (Mars:
  4th & 8th in addition to the ordinary 7th; Jupiter: 5th & 9th; Saturn: 3rd
  & 10th; every other planet: 7th only) — this is geometry, not opinion,
  and is stated as a computed fact, not a citation.
- One authored paragraph per planet (nine total, reused across that
  planet's twelve houses) describing its classical transit temperament.
- The named effect from Sections 5–6, **only for the 17 of 108
  combinations where one genuinely exists** (mostly Saturn and Jupiter). The
  other 91 combinations are not given an invented name.

**Every one of these 108 entries is currently labeled internally as
`ai_authored_pending_astrologer_review`.** None of it claims to be a
verbatim quotation from any text. This is precisely the review this
document is requesting: **your sign-off (or corrections) would clear that
flag.**

A sample entry, so you can see the actual tone and content being reviewed
(Mars in the 3rd house from Moon):

> *Gochara of Mars in the 3rd house from Janma Chandra (Sahaja Bhava). Base
> verdict is favourable per the classical favourable-house table
> (Phaladeepika ch.26 for the seven visible grahas; Rahu/Ketu by explicit
> South-Indian convention). Mars is a fiery, assertive malefic of courage,
> initiative and decisive action, carrying a special aspect on the 4th and
> 8th houses in addition to the ordinary 7th. From here it aspects the 6th,
> the 9th and the 10th houses from itself. This placement is classically
> named: an Upachaya house, traditionally strong ground for a malefic
> transit. Resolve BAV/SAV, kakshya, station/retrograde state, natal
> contacts and dasha concordance separately before judging intensity — this
> record is the base verdict, not the final effective read.*

---

## 9. What this document is **not** asking you to review

- The ephemeris/position calculations (Swiss Ephemeris — an established,
  independently verifiable astronomical library, not an editorial choice).
- The software architecture or how the data reaches the screen.
- Anything already labeled `classical_table` and reproduced verbatim from
  Section 4 above, unless you believe the table itself is wrong.

---

## 10. Open questions we'd specifically like your judgment on

1. Preferred authority/edition order if Phaladeepika conflicts with another
   text you'd weight higher for Gochara specifically.
2. Exact chapter/verse references we could cite alongside "Phaladeepika
   ch.26" for the table in Section 4, if you have a preferred edition.
3. Whether the Rahu/Ketu-as-Saturn convention (Section 4) is the one you'd
   endorse, or whether you use an independent nodal table.
4. Whether the BAV/SAV thresholds (Section 7) match your practice.
5. Whether Lagna should carry more weight than "practical cross-check only"
   in your view.
6. Approval (or correction) of the English commentary clauses — Section 8
   and the nine per-planet "voice" paragraphs behind it.
7. Any additional named cycles you know of, for planets other than Saturn
   and Jupiter, that we should add (with source if possible) rather than
   leave as the general favourable-house table alone.
8. A reference chart with known Saturn/Jupiter transit outcomes you'd be
   willing to let us validate the engine against (this is still an open
   item from our own internal build log).

---

*Prepared from `astrospace/core/vedic/gocharam/` as of 2026-07-29. Happy to
answer any question about how a specific number was computed — the intent
here is full transparency, not a black box.*
