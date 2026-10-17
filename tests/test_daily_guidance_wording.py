"""Do/Avoid card titles read as what they are (regression 2026-10-17, M1)."""
from astrospace.context.daily import TARA_ACTION, _FAVOURABLE_TARAS, _DOMAIN_ACTIONS, _distinct

AVOID_OPENERS = ("avoid", "don't", "hold off")


def test_every_avoid_title_says_what_to_avoid():
    titles = [t for (_, stance), rows in _DOMAIN_ACTIONS.items() if stance == "avoid" for t in rows]
    titles += [TARA_ACTION[t] for t in TARA_ACTION if t not in _FAVOURABLE_TARAS]
    assert all(t.lower().startswith(AVOID_OPENERS) for t in titles), titles


def test_a_title_cut_short_from_another_is_dropped():
    rows = [{"headline": "Keep the day light and simple"}, {"headline": "Keep the day light"},
            {"headline": "Avoid late nights"}]
    assert [r["headline"] for r in _distinct(rows)] == ["Keep the day light and simple", "Avoid late nights"]
