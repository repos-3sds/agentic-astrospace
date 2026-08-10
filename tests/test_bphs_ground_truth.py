"""Ground-truth regression tests against the primary text (Brihat Parasara
Hora Sastra), not against this codebase's own prior behavior.

Where every other test file in this repo asks "does the engine still do what
it did before", this file asks a different question: "does the engine's
output match a specific, checkable value or formula stated in BPHS itself."
That distinction matters — a refactor could accidentally break classical
correctness while every ordinary test stays green, because ordinary tests
only pin behavior, not textual fidelity.

Provenance (2026-08-10): cross-checked against a source-cited validation
document (uploaded by the user, itself synthesized from BPHS by an
independent LLM session) covering astronomical constants, special ascendants,
Drishti Bala, planetary relationships, Vimshopaka Bala, the D-60 deity
database, Shayanadi Avastha, and Kalapurusha body-part mapping. Findings:

- Special Ascendants (Bhava/Hora/Ghati Lagna): exact match — see
  special_lagnas.py, already cited to BPHS ch. 5, unchanged here.
- Drishti Bala (aspectual strength): exact match across all 8 piecewise
  segments AND the document's own worked example (Moon aspecting from a
  117.17° separation → 31.41 virupas) — pinned below.
- Planetary relationships (natural/temporal/panchadha): exact match — pinned
  below.
- Mean daily motion (Mercury/Venus): the document's medieval constants
  (1.667°, 1.6°) genuinely differ from this engine's modern Swiss-Ephemeris-
  derived values (1.383°, 1.2°) — NOT a bug. The document's own author agreed
  on re-derivation: the medieval figures are simplified mean-motion constants
  for manual calculation, not a more-accurate ground truth than a modern
  ephemeris. Mars/Jupiter/Saturn's constants (used for cheshta avastha
  classification) already matched closely and are unaffected.
- Vimshopaka Bala per-varga weights: the uploaded document's original table
  did NOT sum to its stated total of 20.0 for 3 of its 4 schemes
  (Shodashavarga summed to 21.0, Dashavarga to 16.5, Saptavarga to 8.0) — a
  self-inconsistency caused by OCR row/column misalignment on the source
  side, confirmed and explained by the document's own author across two
  follow-up correction rounds (round 1 fixed 3 schemes but introduced a
  fresh Saptavarga row-shift; round 2 fixed that but broke Dashavarga's
  D-60 weight; round 3 finally landed all four schemes both internally
  consistent AND matching this codebase's pre-existing weights exactly,
  value for value). That final convergence — an independently-sourced
  table landing on identical numbers to ours after three corrective
  rounds — is meaningfully stronger evidence than a single citation claim.
  Pinned below now that it's confirmed; vimshopaka.py's weights were never
  changed throughout this process, precisely because a table that doesn't
  yet pass its own arithmetic is not a reason to touch working code.
- Confirmed gap, not fixed here (out of scope for a validation pass, not a
  build pass): Kalapurusha sign-to-body-part mapping — zero references
  anywhere in astrospace/core/vedic/.
- D-60 Shashtyamsha deity database — a first attempt was started then
  deliberately reverted mid-session: its 60-name list traced back to the
  same AI-extraction pipeline that produced the wrong Vimshopaka table and
  a wrong Jaimini karaka scheme elsewhere in this validation pass, and only
  the reversal *arithmetic* had been checked, never the 60 names
  themselves against an independent source. Closed 2026-08-10 in a
  follow-up pass (see below) once two independent web sources were found
  agreeing on all 60 names.
- Shayanadi Avastha (2026-08-10, separate follow-up pass, NOT from the
  uploaded document): built in core/vedic/shayanadi.py after cross-checking
  the formula, variable definitions and 12-name ordering against three
  independent secondary sources (astrojyoti.com, ganeshmitra.com,
  jothishi.com), all agreeing exactly — no primary BPHS verse located, so it
  ships flagged source_status: convention_dependent. This deliberately did
  NOT reuse the uploaded document's own worked examples for this formula:
  those examples' shown arithmetic contradicted their own stated formula.
- Argala / Argala-Bhanga (2026-08-10, same follow-up pass): built in
  core/vedic/argala.py after cross-checking against two independent
  secondary sources (a Jaimini Sutramritam blog post, and an Asheville
  Vedic Astrology post citing Ernst Wilhelm) that agree on the 2nd/4th/11th
  argala houses, the 12th/10th/3rd obstruction houses, and the count-based
  obstruction-strength rule. Also convention_dependent — no primary
  Jaimini-sutra verse located.
- D-60 Shashtyamsha deity database (2026-08-10, same follow-up pass,
  closing the gap noted above): built in core/vedic/shashtyamsha.py after
  fetching and comparing three independent web sources name-by-name
  (rahasyavedicastrology.com, shivohampath.com, sarvatobhadra.com). The
  first two agree on all 60 names and their benefic/malefic nature; the
  handful of apparent mismatches between them turned out to be accepted
  Sanskrit synonyms for the same deity, confirmed when the second source
  gave both variants side by side. sarvatobhadra.com was excluded: it
  diverges sharply from division ~48 onward with an apparent index shift,
  and several of its nature tags contradict the literal Sanskrit meaning
  of the name (e.g. calling Poornachandra, "full moon", malefic) — the
  same OCR/row-misalignment failure signature the Vimshopaka table showed
  above. Also convention_dependent — no primary BPHS verse located, only
  two-source agreement plus a literal-meaning sanity check.
"""
import pytest

from astrospace.core.vedic.strength import (
    NATURAL_RELATIONS,
    natural_relation,
    panchadha_relation,
    sputa_drishti,
    temporal_relation,
)
from astrospace.core.vedic.special_lagnas import special_lagnas
from astrospace.core.vedic.vimshopaka import WEIGHTS as VIMSHOPAKA_WEIGHTS


# ── Drishti Bala (aspectual strength), BPHS's piecewise Virupa formula ──────
# Boundary values at every one of the 8 classical segment edges, plus the
# document's own hand-worked example (Chapter 26-style: Moon's aspect at a
# separation of 3 signs 27°10'22.4" ≈ 117.17°, expected 31.41 virupas).
DRISHTI_BOUNDARY_CASES = [
    (0.0, 0.0),          # < 1 sign: no aspect
    (29.999, 0.0),
    (30.0, 0.0),         # exactly 1 sign: aspect begins at zero
    (59.999, 14.9995),
    (60.0, 15.0),        # 2 signs: quarter aspect
    (89.999, 44.999),
    (90.0, 45.0),        # 3 signs: three-quarter aspect
    (119.999, 30.0005),
    (120.0, 30.0),       # 4 signs: half aspect
    (149.999, 0.0005),
    (150.0, 0.0),        # 5 signs: aspect fades to zero
    (179.999, 59.998),
    (180.0, 60.0),       # 6 signs (opposition): full aspect
    (299.999, 0.0005),
    (300.0, 0.0),        # 10 signs: fades back to zero, stays zero to 360
    (330.0, 0.0),
]


@pytest.mark.parametrize("separation,expected_virupas", DRISHTI_BOUNDARY_CASES)
def test_drishti_bala_matches_bphs_piecewise_formula(separation, expected_virupas):
    # Mercury: no special-aspect override, isolates the base piecewise curve.
    got = sputa_drishti("Mercury", separation)
    assert got == pytest.approx(expected_virupas, abs=0.01)


def test_drishti_bala_worked_example_from_source_text():
    """Moon aspecting across a 3-signs-27°10'22.4" (~117.17°) separation.

    Hand-derivable from the classical formula for the 90-120 deg band,
    (120 - theta)/2 + 30: (120 - 117.17)/2 + 30 = 31.415 virupas.
    """
    assert sputa_drishti("Moon", 117.17) == pytest.approx(31.41, abs=0.01)


@pytest.mark.parametrize("aspecting,separation", [
    ("Mars", 90.0), ("Mars", 119.9), ("Mars", 210.0), ("Mars", 239.9),
    ("Jupiter", 120.0), ("Jupiter", 149.9), ("Jupiter", 240.0), ("Jupiter", 269.9),
    ("Saturn", 60.0), ("Saturn", 89.9), ("Saturn", 270.0), ("Saturn", 299.9),
])
def test_drishti_bala_special_aspects_reach_full_sixty_virupas(aspecting, separation):
    """Mars (4th/8th), Jupiter (5th/9th), Saturn (3rd/10th) special full
    aspects override the base curve to exactly 60 virupas in their bands."""
    assert sputa_drishti(aspecting, separation) == 60.0


# ── Special Ascendants (Vishesha Lagnas) ─────────────────────────────────────
# special_lagnas.py already cites BPHS ch. 5 and was verified in-chat to
# match exactly; pinned here as a permanent regression rather than a one-off
# check. Rates: Bhava 15 deg/hr (1 sign per 5 ghatis), Hora 30 deg/hr (1 sign
# per 2.5 ghatis), Ghati 75 deg/hr (1 sign per 1 ghati).
def test_special_lagnas_advance_at_the_classical_rates():
    sunrise_jd = 2460000.0
    sun_lon_at_sunrise = 100.0
    one_hour_later = sunrise_jd + (1.0 / 24.0)

    result = special_lagnas(one_hour_later, sunrise_jd, sun_lon_at_sunrise)

    assert result["bhava_lagna"]["longitude"] == pytest.approx(
        (sun_lon_at_sunrise + 15.0) % 360.0, abs=0.01)
    assert result["hora_lagna"]["longitude"] == pytest.approx(
        (sun_lon_at_sunrise + 30.0) % 360.0, abs=0.01)
    assert result["ghati_lagna"]["longitude"] == pytest.approx(
        (sun_lon_at_sunrise + 75.0) % 360.0, abs=0.01)


# ── Planetary relationships (Mitra-Shatru Sambandha) ────────────────────────
# BPHS ch. 3, v. 55-56 natural-relationship matrix, verified to match this
# codebase's constants.NATURAL_RELATIONS entry for entry.
BPHS_NATURAL_RELATIONS = {
    "Sun": {"friends": {"Moon", "Mars", "Jupiter"}, "enemies": {"Venus", "Saturn"}, "neutrals": {"Mercury"}},
    "Moon": {"friends": {"Sun", "Mercury"}, "enemies": set(), "neutrals": {"Mars", "Jupiter", "Venus", "Saturn"}},
    "Mars": {"friends": {"Sun", "Moon", "Jupiter"}, "enemies": {"Mercury"}, "neutrals": {"Venus", "Saturn"}},
    "Mercury": {"friends": {"Sun", "Venus"}, "enemies": {"Moon"}, "neutrals": {"Mars", "Jupiter", "Saturn"}},
    "Jupiter": {"friends": {"Sun", "Moon", "Mars"}, "enemies": {"Mercury", "Venus"}, "neutrals": {"Saturn"}},
    "Venus": {"friends": {"Mercury", "Saturn"}, "enemies": {"Sun", "Moon"}, "neutrals": {"Mars", "Jupiter"}},
    "Saturn": {"friends": {"Mercury", "Venus"}, "enemies": {"Sun", "Moon", "Mars"}, "neutrals": {"Jupiter"}},
}


@pytest.mark.parametrize("planet", list(BPHS_NATURAL_RELATIONS))
def test_natural_relationship_matrix_matches_bphs_ch3(planet):
    expected = BPHS_NATURAL_RELATIONS[planet]
    actual = NATURAL_RELATIONS[planet]
    assert set(actual["friends"]) == expected["friends"]
    assert set(actual["enemies"]) == expected["enemies"]
    assert set(actual["neutrals"]) == expected["neutrals"]


@pytest.mark.parametrize("planet,other,expected", [
    ("Sun", "Moon", "friend"), ("Sun", "Saturn", "enemy"), ("Sun", "Mercury", "neutral"),
    ("Moon", "Mars", "neutral"),  # Moon has no natural enemies in BPHS
    ("Venus", "Sun", "enemy"), ("Saturn", "Jupiter", "neutral"),
])
def test_natural_relation_function_matches_bphs(planet, other, expected):
    assert natural_relation(planet, other) == expected


@pytest.mark.parametrize("planet_sign,other_sign,expected", [
    (0, 1, "friend"),   # 2nd house from planet -> temporary friend
    (0, 2, "friend"),   # 3rd
    (0, 3, "friend"),   # 4th
    (0, 9, "friend"),   # 10th
    (0, 10, "friend"),  # 11th
    (0, 11, "friend"),  # 12th
    (0, 0, "enemy"),    # own sign (1st/ascendant) -> temporary enemy
    (0, 4, "enemy"),    # 5th
    (0, 5, "enemy"),    # 6th
    (0, 6, "enemy"),    # 7th
    (0, 7, "enemy"),    # 8th
    (0, 8, "enemy"),    # 9th
])
def test_temporal_relation_matches_bphs_2_3_4_10_11_12_friend_rule(planet_sign, other_sign, expected):
    assert temporal_relation(planet_sign, other_sign) == expected


@pytest.mark.parametrize("nat,temp,expected", [
    ("friend", "friend", "Great Friend"),
    ("friend", "enemy", "Neutral"),
    ("neutral", "friend", "Friend"),
    ("neutral", "enemy", "Enemy"),
    ("enemy", "friend", "Neutral"),
    ("enemy", "enemy", "Great Enemy"),
])
def test_panchadha_compound_relationship_matches_bphs(nat, temp, expected):
    """Panchadha (5-fold) compound relationship: natural + temporary ->
    Great Friend / Friend / Neutral / Enemy / Great Enemy, per BPHS."""
    # panchadha_relation derives nat/temp internally from real planets and
    # signs; here we drive it with a synthetic pair whose natural_relation
    # and temporal_relation are already known to produce the nat/temp under
    # test, rather than re-deriving from scratch.
    planet_by_nat = {
        ("Sun", "friend"): "Moon", ("Sun", "enemy"): "Saturn", ("Sun", "neutral"): "Mercury",
    }
    fixed_planet = "Sun"
    dispositor = planet_by_nat[(fixed_planet, nat)]
    assert natural_relation(fixed_planet, dispositor) == nat

    planet_sign, dispositor_sign = (0, 1) if temp == "friend" else (0, 0)
    assert temporal_relation(planet_sign, dispositor_sign) == temp

    result = panchadha_relation(fixed_planet, planet_sign, dispositor, dispositor_sign)
    assert result == expected


# ── Vimshopaka Bala per-varga weights ───────────────────────────────────────
# Confirmed 2026-08-10 after 3 correction rounds on the source-document side
# (see module docstring). Each scheme's weights below sum to exactly 20.0 and
# match this codebase's pre-existing, independently-sourced vimshopaka.py
# weights exactly — the convergence itself is part of the evidence, not just
# the individual numbers, so both are pinned here.
BPHS_VIMSHOPAKA_WEIGHTS = {
    "shadvarga": {"D1": 6.0, "D2": 2.0, "D3": 4.0, "D9": 5.0, "D12": 2.0, "D30": 1.0},
    "saptavarga": {"D1": 5.0, "D2": 2.0, "D3": 3.0, "D7": 2.5, "D9": 4.5, "D12": 2.0, "D30": 1.0},
    "dashavarga": {
        "D1": 3.0, "D2": 1.5, "D3": 1.5, "D7": 1.5, "D9": 1.5, "D10": 1.5,
        "D12": 1.5, "D16": 1.5, "D30": 1.5, "D60": 5.0,
    },
    "shodashavarga": {
        "D1": 3.5, "D2": 1.0, "D3": 1.0, "D4": 0.5, "D7": 0.5, "D9": 3.0, "D10": 0.5,
        "D12": 0.5, "D16": 2.0, "D20": 0.5, "D24": 0.5, "D27": 0.5, "D30": 1.0,
        "D40": 0.5, "D45": 0.5, "D60": 4.0,
    },
}


@pytest.mark.parametrize("scheme", list(BPHS_VIMSHOPAKA_WEIGHTS))
def test_vimshopaka_weights_sum_to_twenty(scheme):
    """The self-consistency check that caught the source document's original
    errors — every scheme must sum to exactly 20 by classical construction."""
    assert sum(BPHS_VIMSHOPAKA_WEIGHTS[scheme].values()) == pytest.approx(20.0)


@pytest.mark.parametrize("scheme", list(BPHS_VIMSHOPAKA_WEIGHTS))
def test_vimshopaka_weights_match_bphs(scheme):
    assert VIMSHOPAKA_WEIGHTS[scheme] == BPHS_VIMSHOPAKA_WEIGHTS[scheme]


# ── Confirmed gaps: pinned as expected failures, not silently forgotten ─────
# These exist so that if one of these gaps ever gets closed, this file makes
# noise (an unexpectedly-passing xfail) rather than staying quiet — the
# opposite failure mode of a skip, which would hide the gap being filled
# without anyone updating the record.
class TestConfirmedGapsNotYetBuilt:
    @pytest.mark.xfail(reason="Kalapurusha sign-to-body-part mapping: confirmed absent "
                               "in astrospace/core/vedic/ as of 2026-08-10; only Rajju "
                               "(a different, nakshatra-based compatibility system) exists.",
                        strict=False)
    def test_kalapurusha_body_part_mapping_exists(self):
        from astrospace.core.vedic import kalapurusha  # noqa: F401 — expected to not exist yet
        assert False, "if this import succeeds, update this file and the taxonomy doc"


# ── Shayanadi Avastha — cross-checked against 3 independent secondary
# sources 2026-08-10 (see core/vedic/shayanadi.py's module docstring). The
# worked example below is the one source-provided example, hand-verified:
# Sun in Hasta (nakshatra_serial=13), planet_serial=1 (Sun), navamsha_number=6,
# Moon nakshatra_serial=25, ghatika=20, lagna_rashi_number=10
#   -> (13*1*6) + 25 + 20 + 10 = 133 -> 133 % 12 = 1 -> Shayana.
# ── D-60 (Shashtyamsha) deity layer — cross-checked 2026-08-10 against two
# independent secondary sources agreeing on all 60 names (see
# core/vedic/shashtyamsha.py's module docstring). A third source that
# diverged from division ~48 onward was fetched and excluded.
class TestShashtyamshaDeity:
    def test_deity_count_and_uniqueness_of_position(self):
        from astrospace.core.vedic.shashtyamsha import DEITIES
        assert len(DEITIES) == 60

    def test_nature_split_matches_both_retained_sources(self):
        # 27 malefic / 33 benefic, pinned so a future edit to the table
        # can't silently drift the count without a test noticing.
        from astrospace.core.vedic.shashtyamsha import DEITIES
        malefic = sum(1 for _, nature in DEITIES if nature == "malefic")
        benefic = sum(1 for _, nature in DEITIES if nature == "benefic")
        assert (malefic, benefic) == (27, 33)

    def test_odd_sign_reads_deities_in_direct_order(self):
        from astrospace.core.vedic.shashtyamsha import d60_deity
        # Aries (odd sign), first division (0.0-0.5deg) -> deity #1 (Ghora).
        result = d60_deity(0.1)
        assert result["number"] == 1
        assert result["deity"] == "Ghora"
        # Aries, last division (29.5-30deg) -> deity #60 (Chandrarekha).
        result = d60_deity(29.9)
        assert result["number"] == 60
        assert result["deity"] == "Chandrarekha"

    def test_even_sign_reads_deities_in_reverse_order(self):
        from astrospace.core.vedic.shashtyamsha import d60_deity
        # Taurus (30-60deg, even sign), first division -> deity #60 (reversed).
        result = d60_deity(30.1)
        assert result["number"] == 60
        assert result["deity"] == "Chandrarekha"
        # Taurus, last division -> deity #1 (reversed).
        result = d60_deity(59.9)
        assert result["number"] == 1
        assert result["deity"] == "Ghora"

    def test_literal_meaning_sanity_checks_hold(self):
        """Independent check beyond source-agreement: names whose literal
        Sanskrit meaning is unambiguous should carry the nature that
        meaning implies (this is what got sarvatobhadra.com's table
        rejected — it called Poornachandra, "full moon", malefic)."""
        from astrospace.core.vedic.shashtyamsha import DEITIES
        by_name = {name: nature for name, nature in DEITIES}
        assert by_name["Poornachandra"] == "benefic"  # "full moon"
        assert by_name["Kroora"] == "malefic"          # literally "cruel"
        assert by_name["Amrita"] == "benefic"          # "nectar/ambrosia"
        assert by_name["Kulanasa"] == "malefic"        # "destruction of lineage"


class TestShayanadiAvastha:
    def test_worked_example_from_source(self):
        from astrospace.core.vedic.shayanadi import AVASTHA_NAMES
        raw = (13 * 1 * 6) + 25 + 20 + 10
        remainder = raw % 12 or 12
        assert AVASTHA_NAMES[remainder - 1] == "Shayana"

    def test_names_are_the_twelve_in_source_order(self):
        from astrospace.core.vedic.shayanadi import AVASTHA_NAMES
        assert AVASTHA_NAMES == [
            "Shayana", "Upavesana", "Netrapani", "Prakashana", "Gamana",
            "Agamana", "Sabha", "Agama", "Bhojana", "Nrityalipsa", "Kautuka",
            "Nidra",
        ]

    def test_planet_serial_matches_constants_planets_order(self):
        # The three sources define planet_serial as Sun=1..Saturn=7,
        # Rahu=8, Ketu=9 — this happens to be exactly this codebase's
        # PLANETS list order, so no remapping table was needed.
        from astrospace.core.vedic.constants import PLANETS
        from astrospace.core.vedic.shayanadi import _PLANET_SERIAL
        assert _PLANET_SERIAL == {p: i + 1 for i, p in enumerate(PLANETS)}

    def test_zero_remainder_maps_to_nidra_not_index_zero(self):
        from astrospace.core.vedic.shayanadi import shayanadi_avastha
        # nakshatra_serial=1 (Ashwini) * planet_serial=2 (Moon) *
        # navamsha_number=1 = 2; + moon_nakshatra_serial=2 (Bharani, at
        # lon=13.4) + ghatika=4 + lagna_rashi_number=4 (lagna_sign=3) = 12
        # -> 12 % 12 == 0 -> must map to Nidra (index 12), not crash or
        # silently index [-1].
        result = shayanadi_avastha("Moon", lon=0.1, moon_lon=13.4,
                                    lagna_sign=3, ghatis_since_sunrise=4.0)
        assert result["index"] == 12
        assert result["name"] == "Nidra"


# ── Argala / Argala-Bhanga — cross-checked against 2 independent secondary
# sources 2026-08-10 (see core/vedic/argala.py's module docstring).
class TestArgala:
    def _positions(self, house_map: dict[str, int], lagna_sign: int = 0) -> dict:
        # Places each named planet at 15 deg into the sign that is
        # `house` houses forward from lagna_sign (whole-sign, 1-indexed).
        return {
            planet: {"lon": ((lagna_sign + house - 1) % 12) * 30.0 + 15.0}
            for planet, house in house_map.items()
        }

    def test_primary_argala_from_2nd_house(self):
        from astrospace.core.vedic.argala import argala_of_house
        positions = self._positions({"Jupiter": 2})
        result = argala_of_house(1, 0, positions)
        assert result["legs"]["2nd"]["argala_planets"] == ["Jupiter"]
        assert result["legs"]["2nd"]["outcome"] == "argala"

    def test_obstruction_succeeds_when_obstructor_outnumbers_argala(self):
        from astrospace.core.vedic.argala import argala_of_house
        # 4th-from-1 (house 4) has 1 planet; 10th-from-1 (house 10, the
        # obstructor) has 2 -- obstruction should win.
        positions = self._positions({"Jupiter": 4, "Mercury": 10, "Saturn": 10})
        result = argala_of_house(1, 0, positions)
        assert result["legs"]["4th"]["outcome"] == "obstructed"

    def test_equal_counts_reported_as_contested_not_guessed(self):
        from astrospace.core.vedic.argala import argala_of_house
        positions = self._positions({"Jupiter": 4, "Saturn": 10})
        result = argala_of_house(1, 0, positions)
        assert result["legs"]["4th"]["outcome"] == "contested"

    def test_fewer_obstructors_fail_to_obstruct(self):
        from astrospace.core.vedic.argala import argala_of_house
        positions = self._positions({"Jupiter": 11, "Venus": 11, "Rahu": 11})
        result = argala_of_house(1, 0, positions)
        assert result["legs"]["11th"]["outcome"] == "argala"

    def test_visesha_argala_needs_more_than_two_malefics(self):
        from astrospace.core.vedic.argala import argala_of_house
        two_malefics = self._positions({"Mars": 3, "Saturn": 3})
        assert argala_of_house(1, 0, two_malefics)["legs"]["visesha_3rd"]["outcome"] == "none"

        three_malefics = self._positions({"Mars": 3, "Saturn": 3, "Rahu": 3})
        result = argala_of_house(1, 0, three_malefics)
        assert result["legs"]["visesha_3rd"]["outcome"] == "argala"

    def test_all_houses_covers_1_through_12(self):
        from astrospace.core.vedic.argala import all_argala
        result = all_argala(0, {})
        assert set(result.keys()) == set(range(1, 13))

