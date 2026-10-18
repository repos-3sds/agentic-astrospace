"""Range-outlook prose shows reader dates, not ISO dates (audit U15)."""
from astrospace.core.vedic.gocharam.interpretation import _day_label, _range_outlook


def test_day_label_reads_like_a_date():
    assert _day_label("2026-11-01") == "1 Nov 2026"
    assert _day_label("not a date") == "not a date"


def test_range_outlook_prose_has_no_iso_dates():
    timeline = {
        "scan_days": 90,
        "next_365_days": [
            {"title": "Saturn enters Pisces", "date": "2026-11-01", "tone": "challenging", "planet": "Saturn"},
            {"title": "Jupiter leaves Gemini", "date": "2027-01-15", "tone": "supportive", "planet": "Jupiter"},
        ],
        "previous_365_days": [
            {"title": "Rahu moves", "date": "2026-05-02", "tone": "neutral", "planet": "Rahu"},
        ],
    }
    out = _range_outlook(timeline)
    text = out["reading"] + " " + out["previous_reading"]
    assert "1 Nov 2026" in text and "15 Jan 2027" in text and "2 May 2026" in text
    assert "2026-11-01" not in text
