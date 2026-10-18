"""Do lines on a caution day don't push for fresh starts (audit U21)."""
from astrospace.context.daily import _GENTLE_DO, _gentle_do


def test_caution_day_softens_pushy_do_lines():
    rows = [
        {"headline": "Take the first step at work", "text": "Career: …", "source": "domain"},
        {"headline": "Good day to start important things", "plain_headline": "Good day to start important things",
         "text": "Today's tara is Parama Mitra", "source": "tarabala"},
        {"headline": "Read or study quietly", "text": "Growth: …", "source": "domain"},
    ]
    out = _gentle_do(rows)
    titles = [row["headline"] for row in out]
    assert "Take one small step at work" in titles
    assert "Keep any new start small" in titles
    assert out[1]["plain_headline"] == out[1]["headline"]
    assert not any(title in _GENTLE_DO for title in titles)
    assert rows[0]["headline"] == "Take the first step at work"  # input untouched
