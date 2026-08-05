# Jaimini Validation — 2026-08-06

**Status:** point-in-time audit + living test-vector log for
`astrospace/core/vedic/jaimini.py`. Fold new chart examples into this file
rather than starting a second Jaimini validation doc.

Scope: US-PR-011 (Jaimini calculation test vectors) from
[practitioner_epics_user_stories_2026-08-06.md](practitioner_epics_user_stories_2026-08-06.md).
This exists so that US-PR-012 (Jaimini UI convention disclosure) and any
future Jaimini-facing UI claim have something concrete to cite instead of
trusting the implementation on faith.

## What is implemented

`chara_karakas()` and the arudha-pada family (`arudha_pada_detail`,
`arudha_lagna`, `upapada`, `arudha_padas`) in
[astrospace/core/vedic/jaimini.py](../astrospace/core/vedic/jaimini.py).
Everything below is backed by a test in
[tests/test_jaimini_dashas.py](../tests/test_jaimini_dashas.py).

## Seven vs eight karaka scheme

- **Eight-karaka** (default): Sun..Saturn + Rahu, eight slots including
  Pitrikaraka. This is the scheme BPHS and modern software (Jagannatha Hora,
  Parashara's Light) default to.
- **Seven-karaka**: Sun..Saturn only — no Rahu, no Pitrikaraka. Selected via
  `chara_karakas(positions, scheme="seven")`.
- Both are exposed; the caller (API/UI) picks. AstroSpace does not hide the
  choice — `source_status` on the result should read as convention-dependent
  until a per-user default is settled (currently: eight, matching majority
  software convention).

Tests: `TestCharaKarakas.test_eight_scheme_assignments`,
`test_seven_scheme_excludes_rahu_and_pik`.

## Rahu reverse degree

Rahu moves retrograde through the zodiac, so its degree-in-sign is counted
backward for ranking purposes: `effective_degree = 30 - degree_in_sign`. Ketu
is excluded from the eight-karaka scheme entirely (also standard — Ketu is
not ranked as a karaka in the mainstream eight-karaka convention).

Verified two ways:
1. **Internal**: `TestCharaKarakas.test_rahu_degree_reversal` — a synthetic
   chart with Rahu at 5° in-sign asserts `effective_degree == 25.0`.
2. **External cross-check**: `TestJaiminiValidationChartExamples
   .test_external_source_worked_example_eight_scheme` reproduces a worked
   example published by jagannathhora.com ("Chara Karakas in Jaimini
   Astrology: Complete 8-Karaka Guide", fetched 2026-08-06) — within-sign
   degrees Saturn 28 / Mercury 25 / Mars 22 / Venus 19 / Moon 16 / Jupiter 11
   / Sun 6, Rahu 7 (raw, reversed to 23) — and gets the same ranking order the
   source states (Saturn=AK, Mercury=AmK, Rahu=BK, Mars=MK, Venus=PK, ...).
   This is the closest thing to an external validation this pass could do
   without a second full ephemeris toolchain to cross-run a real birth chart
   against; it confirms the *ranking rule*, not a specific person's chart.

## Arc-second tie behavior

Ranking sorts by the full float `effective_degree`, so ties are resolved
deterministically by the exact degree (down to whatever float precision the
ephemeris gives) rather than by any implicit planet-priority list. When two
planets land within one arc-second of each other, the result's `notes`
array records it explicitly (`"Tie to the arc-second between X and Y..."`)
so the caller can flag it as a close call rather than silently picking a
winner.

Test: `TestCharaKarakas.test_arcsecond_tie_is_noted`.

Caveat: below arc-second precision, ranking is still a strict total order
(Python float comparison never truly ties two independently-computed floats
except by construction). The tie *note* is a courtesy flag for the
practitioner, not a claim that the underlying computation is ambiguous.

## A1 (Arudha Lagna) / UL (Upapada) exception

The arudha of a house is as far from the house's lord as the lord is from
the house (same direction of count). BPHS's stated exception: if that raw
result lands in the house itself or the 7th from it, take the 10th from the
raw result instead. Implemented identically for every house (A1..A12), so
A1/AL and A12/UL inherit the same exception without special-casing.

Tests: `TestArudhaPada.test_worked_example_lord_in_tenth` (7th-house
collision), `test_exception_lord_in_own_house` (lands in the house itself),
`test_exception_lord_in_seventh` (lands exactly in the 7th), plus the
Scorpio/Aquarius-specific exception vector below
(`test_aquarius_dual_lordship_uses_primary_lord_saturn`).

## Scorpio / Aquarius dual-lordship convention

Scorpio and Aquarius have two classical lords in nodal-inclusive schemes
(Scorpio: Mars primary / Ketu co-lord; Aquarius: Saturn primary / Rahu
co-lord). AstroSpace's `SIGN_LORDS` table
([constants.py](../astrospace/core/vedic/jaimini.py)) uses only the
**primary lord** (Mars, Saturn) for arudha-pada house-lord lookups.

- This is a defensible, common convention (many software packages default
  to primary rulership for arudha calculations), but it is **not** the only
  one — some traditions use the "stronger of the two lords" rule instead.
- **Pending**: the stronger-lord variant is not implemented. Until it is,
  any arudha pada whose house sign is Scorpio or Aquarius should carry a
  `convention_dependent: true` flag when exposed to a Practitioner UI, per
  US-PR-012.

Tests: `TestJaiminiValidationChartExamples
.test_scorpio_dual_lordship_uses_primary_lord_mars` (no-exception case) and
`.test_aquarius_dual_lordship_uses_primary_lord_saturn` (exception-firing
case) — chosen specifically so both the lordship convention and the BPHS
exception rule are exercised together.

## Chart examples on file

Three, as required by US-PR-011's acceptance criteria:

1. **External-source worked example** (algorithm cross-check, not a birth
   chart) — see "Rahu reverse degree" above.
2. **Reference ephemeris chart** — 14 Aug 1991, 06:12 IST, Vijayawada
   (16.51N, 80.63E). This is the same synthetic test profile used throughout
   `tests/test_remedies_muhurta.py` and elsewhere in this suite; it is not
   tied to a real named individual. Full eight/seven-karaka assignments and
   A1/UL results are pinned in
   `TestJaiminiValidationChartExamples.test_reference_chart_eight_scheme_pinned`
   so a regression anywhere in the sidereal-positions → karaka pipeline (not
   just the ranking function in isolation) is caught.
3. **Scorpio/Aquarius dual-lordship pair** — synthetic charts isolating the
   convention above.

If a fourth agent or a future pass wants to cross-check against a second
independent ephemeris/Jaimini toolchain (e.g. running the same birth data
through Jagannatha Hora or a published astrologer's worked chart), append it
here as chart example 4 rather than opening a new doc.

## What mobile can rely on

- `chara_karakas(positions, scheme=...)["karakas"]` and `["notes"]` are
  stable; `notes` already carries the tie-flag text — surface it verbatim
  rather than re-deriving "closeness" client-side.
- `arudha_padas(...)["notes"]` documents the exception rule and the
  Scorpio/Aquarius convention in plain language already; the API layer
  (`vedic_routes.jaimini`) should pass these through, not summarize them
  away, so US-PR-012's "show selected scheme, Rahu handling, arudha
  exception rule, and dual-lordship caveat" acceptance criterion is met by
  rendering existing fields rather than adding new backend surface.
- Nothing here is marked `verified_common` in the KB sense (see
  [knowledge/vedic_rules](../astrospace/knowledge/vedic_rules)) — Jaimini
  rules are not yet in that KB. That is a reasonable next step once UI
  prominence increases, but out of scope for this pass.

## Explicitly not done in this pass

- No cross-run against a second Jaimini software package on a real
  ephemeris chart (would need that toolchain's output as ground truth;
  none was available in this session).
- No stronger-lord variant for Scorpio/Aquarius.
- No sub-lord (Sub-Sub, Karakamsha) extensions — out of scope for US-PR-011.
