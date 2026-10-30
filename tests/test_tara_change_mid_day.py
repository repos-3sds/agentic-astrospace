"""A day whose star (or Moon sign) changes after sunrise is two answers, not one.

Hawk, 2026-10-30, Singapore: his Tara was kind until the late morning and
then turned. The star changed from Mrigashira to Ardra at 11:34 that day.
For a Rohini birth star that is Sampat (kind) until 11:34, then Vipat.
Today's ring shows the part in force now and its sheet shows both parts.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from astrospace.agents import daily_brief_agent as dba
from astrospace.context import daily_guidance
from astrospace.context.daily import TARA_ACTION, waking_day_parts
from astrospace.core.vedic import VedicChart
from astrospace.core.vedic.constants import NAKSHATRAS
from astrospace.core.vedic.nakshatra import nakshatra_of
from astrospace.core.vedic.panchanga_day import daily_panchanga, personal_panchanga

SGT = ZoneInfo("Asia/Singapore")
SINGAPORE = {"lat": 1.29, "lng": 103.85, "tz_str": "Asia/Singapore"}
ROHINI = NAKSHATRAS.index("Rohini")


@pytest.fixture(scope="module")
def day():
    return daily_panchanga(2026, 10, 30, **SINGAPORE)


@pytest.fixture(scope="module")
def chart():
    chart = VedicChart("Reader", 1990, 6, 21, 10, 0, city="Singapore", nation="SG")
    assert nakshatra_of(chart.positions["Moon"]["lon"])["index"] == ROHINI
    return chart


def _guidance(chart, hour, minute=0):
    return daily_guidance(chart, relation="self",
                          as_of=datetime(2026, 10, 30, hour, minute, tzinfo=SGT), **SINGAPORE)


def test_the_tara_comes_as_periods_split_at_the_star_change(day):
    personal = personal_panchanga(day, janma_nakshatra_index=ROHINI, janma_rashi_index=1)
    first, second = personal["tarabala_periods"]
    assert (first["tara"], first["favourable"]) == ("Sampat", True)
    assert (second["tara"], second["favourable"]) == ("Vipat", False)
    assert first["from_iso"] == day["sunrise_iso"]
    assert first["until"] == second["from"] == "11:34"
    assert second["until_iso"] == day["next_sunrise_iso"]
    # The sunrise answer is unchanged for everything that reads it.
    assert personal["tarabala"]["tara"] == "Sampat"


def test_the_moon_sign_comes_as_periods_too(day):
    assert [s["name"] for s in day["moon_signs"]] == ["Gemini"]
    personal = personal_panchanga(day, janma_nakshatra_index=ROHINI, janma_rashi_index=1)
    (moon,) = personal["chandrabala_periods"]
    assert moon["house_from_rashi"] == 2 and moon["from_iso"] == day["sunrise_iso"]


def test_a_moon_sign_change_splits_chandrabala():
    # 2026-10-31 in Singapore: the Moon enters Cancer at 02:30 on 1 November,
    # before that day's sunrise, so the Vedic day of the 31st has two signs.
    day = daily_panchanga(2026, 10, 31, **SINGAPORE)
    assert [s["name"] for s in day["moon_signs"]] == ["Gemini", "Cancer"]
    personal = personal_panchanga(day, janma_nakshatra_index=ROHINI, janma_rashi_index=5)
    houses = [p["house_from_rashi"] for p in personal["chandrabala_periods"]]
    assert houses == [10, 11]


def test_the_score_has_a_part_for_each_star(chart):
    v = _guidance(chart, 10, 50)["verdict"]
    morning, afternoon = v["day_score_periods"]
    assert (morning["tara"], afternoon["tara"]) == ("Sampat", "Vipat")
    assert morning["day_score"] - afternoon["day_score"] == 23  # +15 star, then -8
    assert morning["day_score_parts"]["transits"] == afternoon["day_score_parts"]["transits"]
    for part in (morning, afternoon):
        assert sum(part["day_score_parts"].values()) == part["day_score"]


@pytest.mark.parametrize("hour,tara,period", [(10, "Sampat", 0), (15, "Vipat", 1)])
def test_the_reading_follows_the_part_in_force_at_as_of(chart, hour, tara, period):
    g = _guidance(chart, hour)
    v = g["verdict"]
    assert g["tarabala"]["tara"] == tara
    assert v["day_score"] == v["day_score_periods"][period]["day_score"]
    assert v["tone"] == v["day_score_periods"][period]["tone"]
    assert len(g["tarabala_periods"]) == 2


def test_do_and_avoid_name_the_switch_time(chart):
    g = _guidance(chart, 9)
    rows = {r["headline"] for r in g["do_today"] + g["avoid_today"] if r["source"] == "tarabala"}
    assert rows == {"Good day for money and plans until 11:34 am", "Avoid risks and new starts from 11:34 am"}
    assert "At 11:34 am the day's star turns to Vipat" in g["verdict"]["text"]


def test_a_part_that_is_over_drops_off(chart):
    g = _guidance(chart, 15)
    rows = [r["headline"] for r in g["do_today"] + g["avoid_today"] if r["source"] == "tarabala"]
    assert rows == ["Avoid risks and new starts"]
    assert "turns to" not in g["verdict"]["text"]


def test_the_brief_gets_the_parts_and_must_name_the_time(chart):
    payload = _guidance(chart, 12)
    signals = dba.brief_input(payload, "Reader", "Friday, 30 October")
    parts = signals["day_parts"]
    assert [(p["from"], p["tara"]) for p in parts] == [("sunrise", "Sampat"), ("11:34 am", "Vipat")]
    brief = dba.DailyBrief.model_construct(
        summary="A calm day.", focus="Keep it simple.", why=["Your star is kind."],
        do=[dba.BriefItem(headline="Plan your money", detail="A kind star.")],
        avoid=[dba.BriefItem(headline="Avoid new starts", detail="Go slowly.")],
        headline="x", card_title="y", timing_note="", narrative="", spoken=[],
    )
    assert any("11:34 am" in gap for gap in dba.coverage_gaps(brief, payload))
    brief.summary = "A strong morning; after 11:34 am, slow down."
    assert not any("11:34 am" in gap for gap in dba.coverage_gaps(brief, payload))


def test_a_day_of_one_part_has_no_parts_for_the_brief():
    one = {"from_iso": "2026-10-30T06:45:56+08:00", "until_iso": None, "day_score": 55, "tone": "positive"}
    assert waking_day_parts({"day_score_periods": [one]}) == []


def test_a_change_late_at_night_does_not_split_the_day():
    early = {"from_iso": "2026-10-30T06:45:56+08:00", "day_score": 66, "tone": "positive", "tara": "Sampat"}
    late = {"from_iso": "2026-10-30T22:10:00+08:00", "day_score": 43, "tone": "mixed", "tara": "Vipat"}
    assert waking_day_parts({"day_score_periods": [early, late]}) == []


# Hawk, 2026-10-31, 3:43 am in India: Today said "Complete important tasks
# before 5:39 am" and "Your star turns less kind at 5:39 am, in 25h 57m".
# The Vedic day of the 31st runs to sunrise on 1 November, and the star
# changes three times inside it: at sunrise, at 7:12 am on the 31st, and at
# 5:39 am on the 1st. The 5:39 am change is tomorrow's small hours, not this
# morning, and the sunrise sliver until 7:12 is gone before most readers are up.
IST = ZoneInfo("Asia/Kolkata")
HYDERABAD = {"lat": 17.385, "lng": 78.4867, "tz_str": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def reader_in_india():
    return VedicChart("Reader", 1985, 3, 10, 8, 0, city="Hyderabad", nation="IN")


def _india(chart, hour, minute=0):
    return daily_guidance(chart, relation="self",
                          as_of=datetime(2026, 10, 31, hour, minute, tzinfo=IST), **HYDERABAD)


def test_a_change_in_the_small_hours_after_midnight_does_not_split_the_day(reader_in_india):
    g = _india(reader_in_india, 3, 43)
    starts = [p["from_iso"][:16] for p in g["tarabala_periods"]]
    assert starts == ["2026-10-31T06:13", "2026-10-31T07:12", "2026-11-01T05:39"]
    assert waking_day_parts(g["verdict"]) == []
    assert "5:39" not in g["verdict"]["text"]
    lines = " ".join(r["headline"] for r in g["do_today"] + g["avoid_today"])
    assert "5:39" not in lines


@pytest.mark.parametrize("hour,minute", [(3, 43), (6, 30), (9, 0)])
def test_before_the_waking_day_the_ring_reads_its_first_part(reader_in_india, hour, minute):
    # Before sunrise and in the sliver until 7:12 the ring shows the star of
    # 7:12 onward, the same star the Do/Avoid row names.
    g = _india(reader_in_india, hour, minute)
    v = g["verdict"]
    second = v["day_score_periods"][1]
    assert second["from_iso"].startswith("2026-10-31T07:12")
    assert v["day_score"] == second["day_score"]
    assert g["tarabala"]["tara"] == second["tara"]
    rows = [r["headline"] for r in g["do_today"] + g["avoid_today"] if r["source"] == "tarabala"]
    assert rows == [TARA_ACTION[second["tara"]]]


def test_a_change_just_after_midnight_does_not_split_the_day():
    day = {"from_iso": "2026-10-30T06:45:56+08:00", "day_score": 66, "tone": "positive", "tara": "Sampat"}
    night = {"from_iso": "2026-10-31T00:20:00+08:00", "day_score": 43, "tone": "mixed", "tara": "Vipat"}
    assert waking_day_parts({"day_score_periods": [day, night]}) == []
