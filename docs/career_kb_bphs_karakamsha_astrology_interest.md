# Career KB — BPHS Karakamsha and Matsya Yoga: reading astrology/occult inclination

**Status: source extract, cross-verified.** Prompted by a direct question —
whether the app could predict a reader's inclination toward astrology or
occult subjects without being asked — audited against the KB (zero coverage
found) and then against the source books. Two BPHS rules turned up, both
cross-checked in two independent translations (R. Santhanam and Girish Chand
Sharma) with near word-for-word agreement. Citations are `S <chapter>.<verse>,
p.<page>` / `G <chapter>.<verse>` (Sharma's pages weren't pinned down for
these chapters — chapter+verse only, matching the convention already used for
Sharma citations elsewhere in this KB).

This is additive to
[docs/career_kb_bphs_10th_house.md](career_kb_bphs_10th_house.md) — a
different technique (Jaimini's Karakamsha, and a general yoga), not 10th
house/lord content.

---

## The finding

**BPHS's "Effects of Karakamsha" chapter (S ch.33 / G ch.35 — same shlokas
41-45 in both, chapters numbered differently between recensions) reads
planets in the Atmakaraka's navamsa sign — the Karakamsha — or in the 5th
sign from it, as naming a learned pursuit.** The full list, because the
Ketu/Rahu clause only makes sense in context — this is one continuous rule
naming a different pursuit per planet, not an isolated astrology-specific
verse:

> **S/G 41-45** — Jupiter and the Moon together there → an author. Venus
> alone → a lesser writer. Mercury alone → a still lesser writer. Jupiter
> alone → all-knowing, a writer, versed in Veda and Vedanta, but not an
> orator or grammarian. Mars → a logician. Mercury → a Mimamsaka (follower of
> Mimamsa philosophy). Saturn → dull-witted in the assembly. The Sun → a
> musician. The Moon → a follower of Sankhya philosophy, versed in rhetoric
> and singing. **Ketu or Rahu → an astrologer.**

Both translators note the same qualifier: "should Jupiter be related to the
said positions, the stated effect will more surely come to pass" — Jupiter's
involvement strengthens whichever specific-planet reading applies, it doesn't
override it.

**Separately, Matsya Yoga (S ch.36 / G ch.37, verses 21-22 in both) reaches
the same profession through a completely different combination** — house
placements, not Karakamsha:

> **S/G 21-22, MATSYA YOGA** — benefics in the 9th house and the ascendant,
> mixed planets in the 5th house, malefics in the 4th and 8th houses. "The
> native born in this yoga will be an astrologer, a kindness incarnate, be
> endowed with virtues, intelligence, strength and beauty, will be famous,
> learned and pious."

Two independent techniques, two independent translations, converging on the
same profession — about as well-grounded as a single claim gets in this KB.

---

## What was handled carefully rather than extracted verbatim

**Matsya Yoga has a real, translator-acknowledged manuscript disagreement.**
Santhanam's note: some editions (Sri Venkateswara Press, Thakur Prasad
Pustaka Bhandar, C.G. Rajan, and Jataka Parijata) require *malefics* — not
benefics — in the ascendant and 9th house, with the 5th/4th/8th unchanged.
Sharma's note cites the same alternate reading independently (Khem Raj, Shri
Krishna Dasa Prakashana Bombay edition). Both translators judge the
benefics-in-lagna-and-9th reading correct — Santhanam reasons that Parashara's
own three-group structure (benefics / malefics / mixed) only makes sense that
way — but the disagreement is real and both sides cite named published
editions. Extracted as `convention_dependent` with an `observance_note`
recording both readings, not silently resolved to one.

**The Karakamsha list's other entries (author, logician, musician, etc.) were
not extracted as separate references.** They're real and could ground other
career questions (a reader asking about writing or philosophy as a
livelihood, for instance), but that's a separate KB pass — this one was
scoped to the astrology-interest question that prompted it. Recorded here so
the rest of the list isn't lost if someone returns to it.

**A pre-existing extraction gap, found and fixed in passing:** Phaladeepika
Adhyaya V's Mercury-navamsa sloka (already extracted as
`phal5_navamsa_tenth_lord_livelihood`) reads in full: "...through composing
poems, the study of sacred scriptures, by being a scribe or through some
clerical work, or some trick, **through a knowledge of astrology**, through
the study of the Vedas on other's behalf..." — the existing reference's
summary ("writing, scholarship or clerical work") dropped the
astrology-specific phrase entirely. Corrected in place, not left as a
separate near-duplicate reference. Note this is a *different* technique from
BPHS's Karakamsha rule — Phaladeepika ties astrology to **Mercury's** navamsa
(the analytical/scholarly angle), BPHS's Karakamsha rule ties it to
**Ketu/Rahu** (the occult/intuitive angle). Complementary, not contradictory;
both worth citing depending on which factor a reading actually turns up.

**Checked and explicitly not found:** Brihat Jataka's own navamsa-of-10th-lord
Mercury entry (already fully extracted this session as
`bj10_2_3_navamsa_tenth_lord_full_table`) does not mention astrology — its
list is writer, mechanic, painter, sculptor, engraver, poet, mathematician,
architect. Recorded as a checked negative, not a silent gap.

---

## Engine change this required

Karakamsha itself — the Atmakaraka's navamsa sign, read as its own reference
point — was not computed anywhere in the engine before this. Added as
`jaimini.karakamsha()`: cheap, since the Atmakaraka (`chara_karakas`) and D9
sign lookup (`vargas.varga_sign`) already existed separately — this is a
lookup, not a new calculation. Wired into `VedicChart.jaimini()` and exposed
domain-independently in the CE bundle as `bundle["karakamsha"]` (same
reasoning as `jaimini_karaka_array`: a chart-level Jaimini fact, not scoped to
one domain). Registered as a citable `technical_basis[].source` section name
in `verifier.py` — along with `jaimini_karaka_array`, which turned out to
have the same gap already.

This backlog item already existed
([docs/backend_astro_depth_checklist_2026-08-06.md](backend_astro_depth_checklist_2026-08-06.md),
Deferred backlog §B) from an earlier KB audit that surfaced the same gap
without building it. Closed here.

---

## Update — `spirituality` domain registered

The `spirituality` deferral below described the state as of the first pass.
Since then: `spirituality` is now registered in `AGENT_REGISTRY` (its own
addendum in `astrospace/agents/registry.py`, matching every other domain's
non-directive/dosha-as-flag framing, with extra care for the domain's real
stakes — renunciation, real gurus, past-life claims). The Karakamsha
reference (`bphs33_karakamsha_ketu_rahu_astrologer`) now carries both
`career` and `spirituality` in `domains`, plus `spiritual_inclination` in
`subdomains` — the Ketu/Rahu-in-Karakamsha finding is read as a soul-level
pull toward occult/intuitive knowledge as much as a livelihood indicator.
Matsya Yoga stays career-only: it names a specific profession outcome, not
a general spiritual inclination, so extending its domain would overstate
what the yoga actually claims.

## Not extracted / deferred

- The rest of the Karakamsha 41-45 list (author, logician, musician,
  Sankhya-follower, Mimamsaka) — see above.
- The Karakamsha chapter continues well past shloka 45 (2nd through 12th
  houses from Karakamsha, aspects on Ketu in Karakamsha, Gulika in
  Karakamsha) — not surveyed this pass.
