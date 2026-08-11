"""BPHS 47.3-4 — where inside a dasha the weight falls.

Cases are written from the rule as stated in the source, not from the
implementation: drekkana decides the third, retrogradation reverses the order,
and the middle is its own mirror.
"""
import pytest

from astrospace.core.vedic.dasha_phase import (
    annotate_emphasis,
    dasha_emphasis,
    emphasis_window,
)

# Aries 0-30°: drekkana boundaries at 10° and 20°.
FIRST_DREKKANA = 5.0
SECOND_DREKKANA = 15.0
THIRD_DREKKANA = 25.0


@pytest.mark.parametrize("lon,expected", [
    (FIRST_DREKKANA, "early"),
    (SECOND_DREKKANA, "middle"),
    (THIRD_DREKKANA, "late"),
])
def test_direct_motion_follows_the_drekkana(lon, expected):
    assert dasha_emphasis(lon, retrograde=False)["phase"] == expected


@pytest.mark.parametrize("lon,expected", [
    (FIRST_DREKKANA, "late"),    # reversed
    (SECOND_DREKKANA, "middle"),  # its own mirror
    (THIRD_DREKKANA, "early"),   # reversed
])
def test_retrograde_reverses_the_order(lon, expected):
    assert dasha_emphasis(lon, retrograde=True)["phase"] == expected


def test_retrogradation_is_the_only_difference():
    """Same longitude, opposite motion — first and third drekkana swap, the
    middle does not move. Stated as one assertion so a change that reverses
    only one direction cannot pass."""
    for lon, direct, retro in [(FIRST_DREKKANA, "early", "late"),
                               (SECOND_DREKKANA, "middle", "middle"),
                               (THIRD_DREKKANA, "late", "early")]:
        assert dasha_emphasis(lon, False)["phase"] == direct
        assert dasha_emphasis(lon, True)["phase"] == retro


@pytest.mark.parametrize("lon,drekkana", [
    (0.0, 1), (9.999, 1), (10.0, 2), (19.999, 2), (20.0, 3), (29.999, 3),
])
def test_drekkana_boundaries(lon, drekkana):
    """10° and 20° belong to the drekkana they open, not the one they close."""
    assert dasha_emphasis(lon, False)["drekkana"] == drekkana


def test_the_rule_holds_in_every_sign():
    """The drekkana is a position within its own sign, so the answer must not
    depend on which sign that is."""
    for sign in range(12):
        base = sign * 30.0
        assert dasha_emphasis(base + 5.0, False)["phase"] == "early"
        assert dasha_emphasis(base + 15.0, False)["phase"] == "middle"
        assert dasha_emphasis(base + 25.0, False)["phase"] == "late"


def test_emphasis_window_splits_the_span_in_thirds():
    w_early = emphasis_window("2019-01-01T00:00:00", "2022-01-01T00:00:00", "early")
    w_mid = emphasis_window("2019-01-01T00:00:00", "2022-01-01T00:00:00", "middle")
    w_late = emphasis_window("2019-01-01T00:00:00", "2022-01-01T00:00:00", "late")
    assert w_early["from"].startswith("2019-01-01")
    assert w_early["to"] == w_mid["from"]
    assert w_mid["to"] == w_late["from"]
    assert w_late["to"].startswith("2022-01-01")


def test_window_accepts_iso_strings_because_that_is_what_dashas_emit():
    """`dashas._period` stores ISO strings. A datetime-only contract would look
    right and never fire against the real timeline."""
    w = emphasis_window("2019-01-01T00:00:00", "2035-01-01T00:00:00", "late")
    assert w["from"] < w["to"]


def test_window_rejects_a_backwards_span():
    with pytest.raises(ValueError):
        emphasis_window("2022-01-01T00:00:00", "2019-01-01T00:00:00", "early")


def test_window_rejects_an_unknown_phase():
    with pytest.raises(ValueError):
        emphasis_window("2019-01-01T00:00:00", "2022-01-01T00:00:00", "whenever")


def test_annotate_attaches_phase_and_window():
    mahadashas = [{"lord": "Jupiter", "start": "2019-01-01T00:00:00",
                   "end": "2035-01-01T00:00:00"}]
    positions = {"Jupiter": {"lon": THIRD_DREKKANA, "retrograde": False}}
    out = annotate_emphasis(mahadashas, positions)
    assert out[0]["emphasis"]["phase"] == "late"
    assert out[0]["emphasis"]["window"]["to"].startswith("2035-01-01")
    assert "BPHS 47.3-4" in out[0]["emphasis"]["source"]


def test_annotate_does_not_mutate_its_input():
    """The dasha timeline is shared with callers that pin it in tests."""
    mahadashas = [{"lord": "Jupiter", "start": "2019-01-01T00:00:00",
                   "end": "2035-01-01T00:00:00"}]
    annotate_emphasis(mahadashas, {"Jupiter": {"lon": 5.0, "retrograde": False}})
    assert "emphasis" not in mahadashas[0]


def test_a_lord_with_no_natal_position_is_skipped_not_guessed():
    """Absent must be distinguishable from 'falls early', or a caller cannot
    tell a missing computation from a real answer."""
    out = annotate_emphasis([{"lord": "Jupiter", "start": "2019-01-01T00:00:00",
                              "end": "2035-01-01T00:00:00"}], {})
    assert "emphasis" not in out[0]


def test_nodes_are_reversed_by_the_general_rule_not_a_special_case():
    """Rahu and Ketu are always retrograde, and `positions.py` already reports
    that, so no node-specific branch should exist for this to come out right."""
    out = annotate_emphasis(
        [{"lord": "Rahu", "start": "2019-01-01T00:00:00", "end": "2037-01-01T00:00:00"}],
        {"Rahu": {"lon": FIRST_DREKKANA, "retrograde": True}},
    )
    assert out[0]["emphasis"]["phase"] == "late"


def test_period_without_dates_still_gets_a_phase():
    """The phase depends only on the natal chart; the window needs the span.
    Losing the dates should not lose the rule."""
    out = annotate_emphasis([{"lord": "Jupiter"}],
                            {"Jupiter": {"lon": 5.0, "retrograde": False}})
    assert out[0]["emphasis"]["phase"] == "early"
    assert "window" not in out[0]["emphasis"]
