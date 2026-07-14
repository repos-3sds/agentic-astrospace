"""
Lunar-month (masa) engine tests.

Layers:
1. New-moon bisection: returned instants have ~zero Moon-Sun elongation
   and correctly bracket the query jd.
2. Amanta month naming, adhika detection (real Adhika Jyeshtha of 2026 and
   Adhika Shravana of 2023), paksha and purnimanta names.
3. Samvatsara / ritu / ayana / disha shool table lookups.
4. daily_panchanga payload extensions: masa, samvatsara, ritu, ayana,
   moonrise/moonset, disha_shool, panchaka, gulika, Bhadra windows.
5. Ghatak month check in personal_panchanga.
"""
import re

import pytest
import swisseph as swe

from astrospace.core.vedic.constants import LUNAR_MONTHS, NAKSHATRAS, SIGNS
from astrospace.core.vedic.masa import (
    RITUS, SAMVATSARA_NAMES, _elongation, amanta_masa, ayana,
    gulika_positions, moon_events_for_day, new_moon_after, new_moon_before,
    ritu, samvatsara,
)
from astrospace.core.vedic.panchanga_day import (
    DISHA_SHOOL, PANCHAKA_NAKSHATRA_IDX, daily_panchanga, personal_panchanga,
)

JD_TODAY = swe.julday(2026, 7, 14, 12.0)  # 2026-07-14 12:00 UT
HHMM = re.compile(r"^\d{2}:\d{2}$")


class TestNewMoons:
    def test_bracket_and_precision(self):
        before = new_moon_before(JD_TODAY)
        after = new_moon_after(JD_TODAY)
        assert before <= JD_TODAY <= after
        for jd in (before, after):
            elong = _elongation(jd)
            assert elong < 0.01 or elong > 359.99

    def test_lunation_spacing(self):
        before = new_moon_before(JD_TODAY)
        after = new_moon_after(JD_TODAY)
        assert 28.0 < after - before < 31.0


class TestAmantaMasa:
    @pytest.fixture(scope="class")
    def masa(self):
        return amanta_masa(JD_TODAY)

    def test_name_is_valid(self, masa):
        assert (masa["name"] in LUNAR_MONTHS
                or masa["name"].startswith("Adhika "))

    def test_paksha(self, masa):
        assert masa["paksha"] in {"Shukla", "Krishna"}

    def test_month_bounds(self, masa):
        assert masa["month_end_jd"] > masa["month_start_jd"]
        assert 28.0 < masa["month_end_jd"] - masa["month_start_jd"] < 31.0
        assert masa["month_start_jd"] <= JD_TODAY <= masa["month_end_jd"]

    def test_sankranti_inside_bounds_means_not_adhika(self, masa):
        from astrospace.core.vedic.masa import _sun_sign_at
        sign_at_start = _sun_sign_at(masa["month_start_jd"] + 1e-4)
        sign_at_end = _sun_sign_at(masa["month_end_jd"] - 1e-4)
        has_sankranti = sign_at_start != sign_at_end
        assert masa["adhika"] == (not has_sankranti)

    def test_known_adhika_jyeshtha_2026(self):
        # Adhika Jyeshtha ran 2026-05-16 → 2026-06-14 (no sankranti inside).
        m = amanta_masa(swe.julday(2026, 6, 1, 12.0))
        assert m["adhika"]
        assert m["name"] == "Adhika Jyeshtha"

    def test_known_adhika_shravana_2023(self):
        m = amanta_masa(swe.julday(2023, 8, 1, 12.0))
        assert m["adhika"]
        assert m["name"] == "Adhika Shravana"

    def test_regular_month_after_adhika(self):
        # The nija (regular) Jyeshtha follows: 2026-06-14 → 2026-07-14.
        m = amanta_masa(swe.julday(2026, 7, 1, 12.0))
        assert not m["adhika"]
        assert m["name"] == "Jyeshtha"

    def test_purnimanta_rules(self):
        shukla = amanta_masa(swe.julday(2026, 4, 1, 12.0))   # Chaitra Shukla
        assert shukla["paksha"] == "Shukla"
        assert shukla["purnimanta_name"] == shukla["name"]
        krishna = amanta_masa(swe.julday(2026, 7, 1, 12.0))  # Jyeshtha Krishna
        assert krishna["paksha"] == "Krishna"
        # Krishna paksha carries the NEXT amanta month's name in purnimanta.
        assert krishna["purnimanta_name"] == "Ashadha"


class TestSamvatsaraRituAyana:
    def test_samvatsara_2026(self):
        s = samvatsara(JD_TODAY)
        assert s["name"] in SAMVATSARA_NAMES
        assert s["shaka_year"] == 1948  # after Chaitra Shukla Pratipada 2026
        assert s["name"] == "Parabhava"
        assert s["source_status"] == "convention_dependent"

    def test_samvatsara_before_new_year(self):
        # Jan 2026 is before Ugadi (Chaitra start ~2026-03-19) → Shaka 1947.
        s = samvatsara(swe.julday(2026, 1, 15, 12.0))
        assert s["shaka_year"] == 1947
        assert s["name"] == "Vishvavasu"

    def test_ritu_table(self):
        expected = {
            "Chaitra": "Vasanta", "Vaishakha": "Vasanta",
            "Jyeshtha": "Grishma", "Ashadha": "Grishma",
            "Shravana": "Varsha", "Bhadrapada": "Varsha",
            "Ashwina": "Sharad", "Kartika": "Sharad",
            "Margashirsha": "Hemanta", "Pausha": "Hemanta",
            "Magha": "Shishira", "Phalguna": "Shishira",
        }
        for i, month in enumerate(LUNAR_MONTHS):
            assert ritu(i) == expected[month]
        assert set(RITUS) == set(expected.values())

    def test_ayana(self):
        assert ayana(swe.julday(2026, 1, 15, 12.0)) == "Uttarayana"
        assert ayana(swe.julday(2026, 4, 15, 12.0)) == "Uttarayana"
        assert ayana(JD_TODAY) == "Dakshinayana"
        assert ayana(swe.julday(2026, 10, 15, 12.0)) == "Dakshinayana"

    def test_disha_shool_table(self):
        assert DISHA_SHOOL["Monday"] == "East"
        assert DISHA_SHOOL["Saturday"] == "East"
        assert DISHA_SHOOL["Thursday"] == "South"
        assert DISHA_SHOOL["Sunday"] == "West"
        assert DISHA_SHOOL["Friday"] == "West"
        assert DISHA_SHOOL["Tuesday"] == "North"
        assert DISHA_SHOOL["Wednesday"] == "North"
        assert len(DISHA_SHOOL) == 7


class TestDailyPanchangaExtensions:
    @pytest.fixture(scope="class")
    def day(self):
        return daily_panchanga(2026, 7, 14, city="New Delhi", nation="IN")

    def test_new_keys_present(self, day):
        for key in ("masa", "samvatsara", "ritu", "ayana", "moonrise",
                    "moonset", "disha_shool", "panchaka", "gulika"):
            assert key in day

    def test_masa_block(self, day):
        m = day["masa"]
        assert set(m) == {"amanta", "purnimanta", "adhika", "paksha"}
        assert (m["amanta"] in LUNAR_MONTHS
                or m["amanta"].startswith("Adhika "))
        assert m["purnimanta"] in LUNAR_MONTHS or m["purnimanta"].startswith("Adhika ")
        assert isinstance(m["adhika"], bool)
        assert m["paksha"] in {"Shukla", "Krishna"}
        # 2026-07-14 sunrise falls on the Jyeshtha amavasya day
        assert m["amanta"] == "Jyeshtha"
        assert m["purnimanta"] == "Ashadha"

    def test_ritu_ayana_samvatsara(self, day):
        assert day["ritu"] in RITUS
        assert day["ayana"] in {"Uttarayana", "Dakshinayana"}
        assert day["samvatsara"]["name"] in SAMVATSARA_NAMES

    def test_moonrise_moonset_format(self, day):
        for key in ("moonrise", "moonset"):
            value = day[key]
            assert value is None or HHMM.match(value)
        # Amavasya day in Delhi: moon sets in the evening.
        assert day["moonset"] is not None

    def test_disha_shool_matches_vara(self, day):
        assert day["vara"]["name"] == "Tuesday"
        assert day["disha_shool"] == "North"

    def test_panchaka_block(self, day):
        p = day["panchaka"]
        assert isinstance(p["active"], bool)
        assert p["nakshatra"] in NAKSHATRAS
        assert "convention" in p["note"]
        assert p["active"] == (NAKSHATRAS.index(p["nakshatra"])
                               in PANCHAKA_NAKSHATRA_IDX)

    def test_gulika_block(self, day):
        g = day["gulika"]
        for half in ("day", "night"):
            block = g[half]
            assert 0.0 <= block["longitude"] < 360.0
            assert block["sign"] in SIGNS
            assert HHMM.match(block["start_time"])
            assert "°" in block["dms"]
        assert "note" in g

    def test_bhadra_vishti_window(self):
        # 2026-07-03 (Delhi): Vishti karana prevails at sunrise.
        d = daily_panchanga(2026, 7, 3, city="New Delhi", nation="IN")
        karanas = [e["name"] for e in d["elements"]["karana"]]
        assert "Vishti" in karanas
        bhadra = [w for w in d["windows"]["inauspicious"]
                  if w["name"] == "Bhadra (Vishti Karana)"]
        assert bhadra
        for w in bhadra:
            assert w["kind"] == "inauspicious"
            assert w["start_iso"] < w["end_iso"]
        # windows list stays sorted after insertion
        isos = [w["start_iso"] for w in d["windows"]["inauspicious"]]
        assert isos == sorted(isos)

    def test_no_bhadra_when_no_vishti(self):
        d = daily_panchanga(2026, 7, 14, city="New Delhi", nation="IN")
        karanas = [e["name"] for e in d["elements"]["karana"]]
        assert "Vishti" not in karanas
        assert not [w for w in d["windows"]["inauspicious"]
                    if w["name"].startswith("Bhadra")]


class TestGulikaGeometry:
    def test_day_gulika_saturday_starts_at_sunrise(self):
        # Saturday: part lords start from Saturn, so Gulika part is the 1st —
        # day Gulika rises exactly at sunrise.
        rise = swe.julday(2026, 7, 18, 0.0)   # a Saturday, 00:00 UT "sunrise"
        sets = rise + 0.5
        next_rise = rise + 1.0
        g = gulika_positions(rise, sets, next_rise, 6, 28.6139, 77.2090, "UTC")
        assert abs(g["day"]["start_jd"] - rise) < 1e-9
        # Night lords start from (6+4)%7=3 (Mercury); Saturn is part 4 (0-based 3)
        assert abs(g["night"]["start_jd"] - (sets + 3 * (next_rise - sets) / 8.0)) < 1e-9

    def test_day_gulika_part_matches_kala_table(self):
        # Gulika Kalam eighth-of-day table in kala.py: Sunday=7th, Monday=6th…
        from astrospace.core.vedic.kala import GULIKA_PART
        rise, sets, next_rise = 2461000.0, 2461000.5, 2461001.0
        for vara in range(7):
            g = gulika_positions(rise, sets, next_rise, vara, 28.6, 77.2, "UTC")
            part_1based = round((g["day"]["start_jd"] - rise) / ((sets - rise) / 8.0)) + 1
            assert part_1based == GULIKA_PART[vara]


class TestGhatakMonthCheck:
    def test_month_check_present_and_matching(self):
        # Aries janma rashi → ghatak month Kartika.
        payload = {
            "elements": {
                "nakshatra": [{"name": "Ashwini", "index": 0}],
                "tithi": [{"name": "x", "index": 2}],
            },
            "moon_rashi_at_sunrise": "Aries",
            "vara": {"name": "Friday"},
            "masa": {"amanta": "Kartika", "purnimanta": "Kartika",
                     "adhika": False, "paksha": "Shukla"},
        }
        p = personal_panchanga(payload, 0, 0, ghatak_moon_sign=0)
        month_alert = next(a for a in p["ghatak_alerts"] if a["type"] == "month")
        assert month_alert["matched"]
        assert month_alert["ghatak_value"] == "Kartika"

    def test_month_check_adhika_prefix_stripped(self):
        payload = {
            "elements": {
                "nakshatra": [{"name": "Ashwini", "index": 0}],
                "tithi": [{"name": "x", "index": 2}],
            },
            "moon_rashi_at_sunrise": "Aries",
            "vara": {"name": "Friday"},
            "masa": {"amanta": "Adhika Kartika", "purnimanta": "Kartika",
                     "adhika": True, "paksha": "Shukla"},
        }
        p = personal_panchanga(payload, 0, 0, ghatak_moon_sign=0)
        month_alert = next(a for a in p["ghatak_alerts"] if a["type"] == "month")
        assert month_alert["matched"]

    def test_month_check_on_real_day_payload(self):
        day = daily_panchanga(2026, 7, 14, city="New Delhi", nation="IN")
        p = personal_panchanga(day, 0, 0, ghatak_moon_sign=0)
        types = [a["type"] for a in p["ghatak_alerts"]]
        assert "month" in types
        month_alert = next(a for a in p["ghatak_alerts"] if a["type"] == "month")
        # July 2026 amanta masa is Jyeshtha, ghatak month for Aries is Kartika
        assert not month_alert["matched"]

    def test_month_check_missing_masa_is_unmatched(self):
        # Payloads without masa (older callers) must not crash.
        payload = {
            "elements": {
                "nakshatra": [{"name": "Ashwini", "index": 0}],
                "tithi": [{"name": "x", "index": 2}],
            },
            "moon_rashi_at_sunrise": "Aries",
            "vara": {"name": "Friday"},
        }
        p = personal_panchanga(payload, 0, 0, ghatak_moon_sign=0)
        month_alert = next(a for a in p["ghatak_alerts"] if a["type"] == "month")
        assert not month_alert["matched"]


class TestMoonEvents:
    def test_moon_events_bounds(self):
        from astrospace.core.vedic.positions import day_span
        span = day_span(2026, 7, 10, 28.6139, 77.2090, "Asia/Kolkata")
        rise, _sets, next_rise = span
        moonrise, moonset = moon_events_for_day(rise, next_rise, 28.6139, 77.2090)
        for event in (moonrise, moonset):
            if event is not None:
                assert rise <= event < next_rise
        # at Delhi's latitude at least one of the two occurs every day
        assert moonrise is not None or moonset is not None
