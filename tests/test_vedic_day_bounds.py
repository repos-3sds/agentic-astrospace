"""vedic_day_bounds() — the sunrise-to-next-sunrise interval a moment falls
inside, used to give daily-guidance an authoritative cache-validity window
(docs/reliable_native_core_architecture_2026-08-14.md)."""
import swisseph as swe

from astrospace.core.vedic.positions import vedic_day_bounds


def test_returns_the_bracketing_sunrise_pair_for_a_normal_latitude():
    jd = swe.julday(2026, 7, 21, 4.5)  # ~10am IST in UT
    bounds = vedic_day_bounds(jd, 28.6, 77.2)  # New Delhi
    assert bounds is not None
    rise, next_rise = bounds
    assert rise < jd < next_rise
    assert next_rise - rise < 1.1  # roughly one day apart, not several

def test_none_when_sunrise_is_undefined_at_the_pole_in_polar_night():
    jd = swe.julday(2026, 12, 21, 12.0)
    assert vedic_day_bounds(jd, 69.6, 18.9) is None  # Tromso, polar night
