"""Day timings against DrikPanchang, city by city (audit 2026-10-28).

Each expected value was read off drikpanchang.com's day panchang for that
geoname and date. Drik prints whole minutes; the engine's own minute can sit
either side of Drik's by its seconds, so the check allows one minute. The
cases cover the time zones and DST days the audit asked for: India, Singapore,
Toronto and New York (the November fall-back and March spring-forward days),
Sydney (October spring-forward), Los Angeles, Auckland, and high latitudes
(Oslo at midsummer, Reykjavik at midwinter).
"""
from datetime import datetime

import pytest

from astrospace.context.timing_place import SOURCE_BIRTH_CITY, choose_place
from astrospace.core.vedic.panchanga_day import daily_panchanga

TOLERANCE_MIN = 1

# city, nation, date, {window or "sunrise"/"sunset": "HH:MM" start}
DRIK = [
    ("Hyderabad", "IN", (2026, 8, 26), {"sunrise": "06:01", "Rahu Kalam": "12:18",
                                        "Yamaganda": "07:35", "Gulika Kalam": "10:44",
                                        "Amrit Kalam": "13:33", "Brahma Muhurta": "04:30"}),
    ("New Delhi", "IN", (2026, 10, 28), {"sunrise": "06:30", "sunset": "17:39",
                                         "Rahu Kalam": "12:05", "Yamaganda": "07:54",
                                         "Brahma Muhurta": "04:47", "Durmuhurta": "11:42"}),
    ("Kolkata", "IN", (2026, 10, 30), {"sunrise": "05:40", "Rahu Kalam": "09:55",
                                       "Abhijit Muhurta": "10:57", "Varjya": "16:49",
                                       "Amrit Kalam": "21:58"}),
    ("Singapore", "SG", (2026, 10, 29), {"sunrise": "06:46", "Rahu Kalam": "14:19",
                                         "Abhijit Muhurta": "12:24", "Brahma Muhurta": "05:11"}),
    ("Toronto", "CA", (2026, 10, 28), {"sunrise": "07:48", "sunset": "18:14",
                                       "Rahu Kalam": "13:01", "Brahma Muhurta": "06:00"}),
    ("New York", "US", (2026, 11, 1), {"sunrise": "06:26", "sunset": "16:52",
                                       "Rahu Kalam": "15:34", "Abhijit Muhurta": "11:18",
                                       "Amrit Kalam": "11:55"}),
    ("New York", "US", (2027, 3, 14), {"sunrise": "07:10", "Rahu Kalam": "17:33",
                                       "Abhijit Muhurta": "12:42", "Amrit Kalam": "20:51"}),
    ("Sydney", "AU", (2026, 10, 4), {"sunrise": "06:29", "sunset": "19:00",
                                     "Rahu Kalam": "17:26", "Abhijit Muhurta": "12:19"}),
    ("Los Angeles", "US", (2026, 10, 31), {"sunrise": "07:12", "Rahu Kalam": "09:54",
                                           "Abhijit Muhurta": "12:15"}),
    ("Auckland", "NZ", (2026, 10, 28), {"sunrise": "06:21", "Rahu Kalam": "13:05",
                                        "Varjya": "10:02", "Amrit Kalam": "18:45"}),
    ("Oslo", "NO", (2026, 6, 21), {"sunrise": "03:54", "sunset": "22:44",
                                   "Rahu Kalam": "20:23", "Abhijit Muhurta": "12:41"}),
    ("Reykjavik", "IS", (2026, 12, 21), {"sunrise": "11:22", "Rahu Kalam": "11:53",
                                         "Abhijit Muhurta": "13:17"}),
]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _starts(day: dict, name: str) -> list[str]:
    if name in ("sunrise", "sunset"):
        return [day[name]]
    rows = day["windows"]["auspicious"] + day["windows"]["inauspicious"]
    return [w["start"] for w in rows if w["name"] == name or w["name"].startswith(f"{name} (")]


@pytest.mark.parametrize("city,nation,ymd,expected", DRIK,
                         ids=[f"{c}-{y}-{m:02d}-{d:02d}" for c, _, (y, m, d), _ in DRIK])
def test_matches_drikpanchang_within_a_minute(city, nation, ymd, expected):
    day = daily_panchanga(*ymd, city=city, nation=nation)
    for name, drik in expected.items():
        starts = _starts(day, name)
        assert starts, f"{name} missing"
        delta = min(abs(_minutes(s) - _minutes(drik)) for s in starts)
        assert delta <= TOLERANCE_MIN, f"{name}: engine {starts} vs Drik {drik}"


class TestAuditFixes:
    def test_no_abhijit_on_wednesday(self):
        # Drik lists Abhijit as "None" on Wednesdays; its slot is Durmuhurta.
        day = daily_panchanga(2026, 10, 28, city="New Delhi", nation="IN")
        assert day["vara"]["name"] == "Wednesday"
        names = [w["name"] for w in day["windows"]["auspicious"]]
        assert "Abhijit Muhurta" not in names

    def test_mrigashira_amrit_kalam_at_its_38th_ghati(self):
        # Singapore 2026-10-29: Drik 03:33 to 05:00 on the 30th (was 23:10).
        day = daily_panchanga(2026, 10, 29, city="Singapore", nation="SG")
        row = next(w for w in day["windows"]["auspicious"]
                   if w["name"] == "Amrit Kalam (Mrigashira)")
        assert row["start_iso"].startswith("2026-10-30T03:3")

    def test_moola_second_varjya(self):
        # Hyderabad 2026-11-13: Drik shows 15:29 to 17:17 besides the 56th-ghati rule.
        day = daily_panchanga(2026, 11, 13, city="Hyderabad", nation="IN")
        starts = [w["start"] for w in day["windows"]["inauspicious"]
                  if w["name"] == "Varjya (Moola)"]
        assert any(abs(_minutes(s) - _minutes("15:29")) <= 1 for s in starts)

    def test_dst_fall_back_day_is_on_standard_time_at_sunrise(self):
        day = daily_panchanga(2026, 11, 1, city="New York", nation="US")
        assert datetime.fromisoformat(day["sunrise_iso"]).utcoffset().total_seconds() == -5 * 3600


class TestFestivalPlaceFollowsDayTimings:
    def test_same_zone_keeps_the_birth_city(self):
        # Festivals took Mumbai for every Indian reader; Today took the birth city.
        assert choose_place("Hyderabad", "IN", "Asia/Kolkata") == (
            "Hyderabad", "IN", SOURCE_BIRTH_CITY)

    def test_other_zone_takes_its_listed_city(self):
        assert choose_place("Hyderabad", "IN", "America/Toronto")[:2] == ("Toronto", "CA")


class TestClockChangeWeekend:
    """US and Canada fall back at 2 am on Sunday 1 Nov 2026."""

    @pytest.mark.parametrize("city,nation", [("Toronto", "CA"), ("New York", "US")])
    def test_each_day_carries_its_own_offset(self, city, nation):
        offsets = {}
        for d in (31, 1, 2):
            month = 10 if d == 31 else 11
            day = daily_panchanga(2026, month, d, city=city, nation=nation)
            offsets[d] = day["sunrise_iso"][-6:]
            rahu = next(w for w in day["windows"]["inauspicious"] if w["name"] == "Rahu Kalam")
            assert rahu["start_iso"][-6:] == offsets[d]
        assert offsets == {31: "-04:00", 1: "-05:00", 2: "-05:00"}

    def test_sunrise_moves_back_an_hour_on_the_clock(self):
        sat = daily_panchanga(2026, 10, 31, city="Toronto", nation="CA")["sunrise"]
        sun = daily_panchanga(2026, 11, 1, city="Toronto", nation="CA")["sunrise"]
        assert _minutes(sat) - _minutes(sun) in range(57, 60)  # an hour back, ~2 min later in UT

    def test_muhurta_night_blocks_show_the_new_clock(self):
        from astrospace.core.vedic import muhurta

        day = daily_panchanga(2026, 10, 31, city="Toronto", nation="CA")
        last = muhurta._blocks(day, {}, None)[-1]
        # The night ends at Sunday's sunrise, 06:26 EST, not 07:26 on the old clock.
        assert last["end"].isoformat().endswith("-05:00")
        assert last["end"].strftime("%H:%M") == datetime.fromisoformat(
            daily_panchanga(2026, 11, 1, city="Toronto", nation="CA")["sunrise_iso"]).strftime("%H:%M")


class TestBirthClock:
    def test_india_war_time(self):
        from astrospace.core.vedic.chart import VedicChart

        clock = VedicChart("x", 1943, 6, 1, 12, 0, "Kolkata", "IN").meta()["birth_clock"]
        assert clock["utc_offset"] == "+06:30"

    def test_repeated_and_skipped_hours_are_named(self):
        from astrospace.core.vedic.chart import VedicChart

        repeated = VedicChart("x", 2026, 11, 1, 1, 30, "New York", "US").meta()["birth_clock"]
        skipped = VedicChart("x", 2026, 3, 8, 2, 30, "New York", "US").meta()["birth_clock"]
        assert repeated["status"] == "repeated" and "twice" in repeated["note"]
        assert skipped["status"] == "skipped" and "03:30" in skipped["note"]
