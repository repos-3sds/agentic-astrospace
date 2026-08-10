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
- Vimshopaka Bala per-varga weights: the uploaded document's own table does
  NOT sum to its stated total of 20.0 for 3 of its 4 schemes (Shodashavarga
  sums to 21.0, Dashavarga to 16.5, Saptavarga to 8.0 — verified by hand,
  see the commit that added this file) — a self-inconsistency that means
  that specific table in that document cannot be trusted as a faithful
  transcription, whatever its citation claims. This codebase's own
  vimshopaka.py weights (self-consistent, each scheme correctly summing to
  20, already documented as "the commonly-published Vimshopaka table") were
  NOT changed on the strength of a document that fails its own arithmetic.
  If a genuinely primary-sourced table turns up later, re-derive from that,
  not from this one.
- Confirmed gaps, not fixed here (out of scope for a validation pass, not a
  build pass): Kalapurusha sign-to-body-part mapping (zero references
  anywhere in astrospace/core/vedic/), the D-60 Shashtyamsha deity database
  (60 named deities + odd/even reversal rule — the engine computes the D-60
  *sign* correctly via vargas.d60() but has no deity layer at all), and
  Shayanadi Avastha (the 12-state modulo-12 formula — confirmed absent in an
  earlier chat-level check, not re-derived here since nothing changed).
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

    @pytest.mark.xfail(reason="D-60 Shashtyamsha deity database (60 named deities + "
                               "odd/even sign reversal): confirmed absent as of "
                               "2026-08-10. vargas.d60() computes the correct sign only.",
                        strict=False)
    def test_d60_deity_database_exists(self):
        from astrospace.core.vedic.vargas import VARGA_INFO
        assert "deities" in VARGA_INFO.get("D60", {})

    @pytest.mark.xfail(reason="Shayanadi Avastha (12-state modulo-12 formula: Nakshatra "
                               "serial x planet serial x Navamsha serial, summed with "
                               "Moon's star + Ascendant's Navamsha, mod 12): confirmed "
                               "absent as of 2026-08-10. Baladi and Cheshta avastha "
                               "systems exist and are unrelated to this one.",
                        strict=False)
    def test_shayanadi_avastha_exists(self):
        from astrospace.core.vedic import strength
        assert hasattr(strength, "shayanadi_avastha")
