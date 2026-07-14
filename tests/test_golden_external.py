"""
External golden anchors — panchanga days and astronomical instants validated
against publicly published sources.

Every web-fetched value is embedded below as a constant, so these tests never
touch the network. Each constant records the source URL and the date it was
fetched (2026-07-14). See SOURCES.

Conventions / tolerances
------------------------
* Engine: Swiss Ephemeris, Lahiri ayanamsha, mean nodes, sunrise-to-sunrise day.
* mypanchang.com computes with NASA JPL ephemeris and the standard drik
  (Chitrapaksha/Lahiri-family) ayanamsha; element END TIMES agreed with our
  engine to well under a minute on all three days, asserted at +/-5 minutes.
* Sunrise: +/-3 minutes (disc-edge vs centre and refraction conventions).
* Moonrise: +/-10 minutes, asserted only where the source's moonrise falls
  inside our sunrise-to-next-sunrise day window (mypanchang lists
  midnight-to-midnight events, so a moonrise BEFORE local sunrise appears on
  the source's row but is `None` in our payload — see SOURCES notes).
* Eclipse geometry: at eclipse maximum Sun-Moon elongation < 1 deg and the
  luminaries must sit within 5 deg of the Rahu/Ketu axis (mean node).
* Sankranti: our Capricorn ingress must fall within +/-6 hours of the
  published moment (published Indian sources themselves differ by ~20 min).
* Purnima: Sun-Moon elongation within 1 deg of 180 at the published instant.
"""
import datetime as dt

import pytest
import swisseph as swe

from astrospace.core.vedic.panchanga_day import daily_panchanga
from astrospace.core.vedic.positions import sidereal_positions


# ── Sources (all fetched 2026-07-14) ─────────────────────────────────────────

SOURCES = {
    "mypanchang_aug_2023": {
        "url": "http://www.mypanchang.com/caltable.php?cityname=NewDelhi-India&yr=2023&mn=8&monthtype=0",
        "accessed": "2026-07-14",
        "fetched": {
            "1_aug_2023": {
                "masa": "Adhika Shravana", "paksha": "Shukla",
                "tithi": "Purnima 24:01:26+", "nakshatra": "U.shada 16:03:03",
                "yoga": "Priti 18:52:19", "karana": "Bava 24:01:26+",
                "sunrise": "05:43:30", "sunset": "19:11:20",
                "moonrise": "19:16:58",
            },
        },
    },
    "mypanchang_nov_2024": {
        "url": "http://www.mypanchang.com/caltable.php?cityname=NewDelhi-India&yr=2024&mn=11&monthtype=0",
        "accessed": "2026-07-14",
        "fetched": {
            "1_nov_2024": {
                "weekday": "Friday",
                "masa": "Aashvayuja",  # = amanta Ashwina
                "paksha": "Krishna",
                "tithi": "Amavasya 18:16:53", "nakshatra": "Svaati 27:30:53+",
                "yoga": "Priti 10:40:39", "karana": "Nagava 18:16:53",
                "sunrise": "06:34:21", "sunset": "17:34:49",
                # 06:13:45 precedes local sunrise: outside our
                # sunrise-to-next-sunrise day, so not asserted.
                "moonrise": "06:13:45",
            },
        },
    },
    "mypanchang_jul_2026": {
        "url": "http://www.mypanchang.com/caltable.php?cityname=NewDelhi-India&yr=2026&mn=7&monthtype=0",
        "accessed": "2026-07-14",
        "fetched": {
            "14_jul_2026": {
                "weekday": "Tuesday",
                "masa": "Nija Jyeshtha",  # month header: "July 2026[Nija Jyeshtha- Ashaadha]";
                                          # July 15 starts Ashaadha (2026 had Adhika Jyeshtha)
                "paksha": "Krishna",
                "tithi": "Amavasya 15:13:22", "nakshatra": "Punarvasu 24:09:26+",
                "yoga": "Vyaghata", "karana": "Nagava",
                "sunrise": "05:33:50", "sunset": "19:20:05",
                # 05:01:54 precedes local sunrise: not asserted (see above).
                "moonrise": "05:01:54",
            },
        },
    },
    "nasa_eclipse_2024_04_08": {
        "url": "https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl=+20240408",
        "accessed": "2026-07-14",
        "fetched": {"greatest_eclipse_ut": "2024-04-08 18:17:15 UT",
                    "greatest_eclipse_td": "18:18:29 TDT", "delta_t": "74.0 s"},
    },
    "astrosage_makar_sankranti_2025": {
        "url": "https://horoscope.astrosage.com/makar-sankranti-2025-date-time-remedies-significance/",
        "accessed": "2026-07-14",
        "fetched": {"moment": "January 14, 2025, 8:41 AM IST "
                              "(page: 'at 8:41 AM, the Sun will transit into the "
                              "Capricorn zodiac sign'; Moment of Sankranti: 8:40 AM)"},
        "note": "Other Indian sources publish 09:03 AM IST for the same event; "
                "the ~20 min spread is why the tolerance is a generous +/-6 h.",
    },
    "astropixels_full_moon_jul_2024": {
        "url": "https://astropixels.com/ephemeris/phasescat/phases2001.html",
        "accessed": "2026-07-14",
        "fetched": {"full_moon": "Jul 21 10:17 UT (2024) — Guru Purnima 2024"},
    },
}


# ── Task 1: Panchanga golden days (New Delhi) ────────────────────────────────

PANCHANGA_DAYS = [
    {
        "id": "2023-08-01_adhika_shravana_purnima",
        "source": "mypanchang_aug_2023",
        "date": (2023, 8, 1),
        "vara": "Tuesday",
        "tithi_at_sunrise": "Purnima",
        "tithi_ends": "2023-08-02T00:01:26+05:30",
        "nakshatra_at_sunrise": "Uttara Ashadha",   # source spelling "U.shada"
        "nakshatra_ends": "2023-08-01T16:03:03+05:30",
        "paksha": "Shukla",
        "amanta_masa": "Adhika Shravana",
        "adhika": True,
        "sunrise": "05:43:30",
        "moonrise": "19:16:58",
    },
    {
        "id": "2024-11-01_ashwina_amavasya",
        "source": "mypanchang_nov_2024",
        "date": (2024, 11, 1),
        "vara": "Friday",
        "tithi_at_sunrise": "Amavasya",
        "tithi_ends": "2024-11-01T18:16:53+05:30",
        "nakshatra_at_sunrise": "Swati",            # source spelling "Svaati"
        "nakshatra_ends": "2024-11-02T03:30:53+05:30",
        "paksha": "Krishna",
        "amanta_masa": "Ashwina",                   # source spelling "Aashvayuja"
        "adhika": False,
        "sunrise": "06:34:21",
        "moonrise": None,   # source 06:13:45 is before sunrise (day-window mismatch)
    },
    {
        "id": "2026-07-14_jyeshtha_amavasya",
        "source": "mypanchang_jul_2026",
        "date": (2026, 7, 14),
        "vara": "Tuesday",
        "tithi_at_sunrise": "Amavasya",
        "tithi_ends": "2026-07-14T15:13:22+05:30",
        "nakshatra_at_sunrise": "Punarvasu",
        "nakshatra_ends": "2026-07-15T00:09:26+05:30",
        "paksha": "Krishna",
        "amanta_masa": "Jyeshtha",                  # source spelling "Nija Jyeshtha"
        "adhika": False,
        "sunrise": "05:33:50",
        "moonrise": None,   # source 05:01:54 is before sunrise (day-window mismatch)
    },
]

SUNRISE_TOLERANCE_MIN = 3.0
MOONRISE_TOLERANCE_MIN = 10.0
ELEMENT_END_TOLERANCE_MIN = 5.0


def _clock_minutes(text: str) -> float:
    """'HH:MM' or 'HH:MM:SS' → minutes past midnight."""
    parts = [int(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.append(0)
    h, m, s = parts
    return h * 60 + m + s / 60


@pytest.mark.parametrize("case", PANCHANGA_DAYS, ids=lambda c: c["id"])
class TestPanchangaGoldenDays:
    @pytest.fixture()
    def day(self, case):
        y, m, d = case["date"]
        return daily_panchanga(y, m, d, city="New Delhi", nation="IN")

    def test_vara(self, case, day):
        assert day["vara"]["name"] == case["vara"]

    def test_tithi_at_sunrise(self, case, day):
        assert day["elements"]["tithi"][0]["name"] == case["tithi_at_sunrise"]

    def test_tithi_end_time(self, case, day):
        ours = dt.datetime.fromisoformat(day["elements"]["tithi"][0]["upto_iso"])
        published = dt.datetime.fromisoformat(case["tithi_ends"])
        assert abs((ours - published).total_seconds()) / 60 <= ELEMENT_END_TOLERANCE_MIN

    def test_nakshatra_at_sunrise(self, case, day):
        assert day["elements"]["nakshatra"][0]["name"] == case["nakshatra_at_sunrise"]

    def test_nakshatra_end_time(self, case, day):
        ours = dt.datetime.fromisoformat(day["elements"]["nakshatra"][0]["upto_iso"])
        published = dt.datetime.fromisoformat(case["nakshatra_ends"])
        assert abs((ours - published).total_seconds()) / 60 <= ELEMENT_END_TOLERANCE_MIN

    def test_paksha(self, case, day):
        assert day["masa"]["paksha"] == case["paksha"]

    def test_amanta_masa_and_adhika_flag(self, case, day):
        assert day["masa"]["amanta"] == case["amanta_masa"]
        assert day["masa"]["adhika"] is case["adhika"]

    def test_sunrise(self, case, day):
        diff = abs(_clock_minutes(day["sunrise"]) - _clock_minutes(case["sunrise"]))
        assert diff <= SUNRISE_TOLERANCE_MIN

    def test_moonrise(self, case, day):
        if case["moonrise"] is None:
            pytest.skip("source moonrise precedes sunrise; outside our day window")
        assert day["moonrise"] is not None
        diff = abs(_clock_minutes(day["moonrise"]) - _clock_minutes(case["moonrise"]))
        assert diff <= MOONRISE_TOLERANCE_MIN


# ── Task 2: Astronomical anchors ─────────────────────────────────────────────

def _elongation(positions: dict) -> float:
    return (positions["Moon"]["lon"] - positions["Sun"]["lon"]) % 360.0


def _axis_distance(lon_a: float, lon_b: float) -> float:
    return abs((lon_a - lon_b + 180.0) % 360.0 - 180.0)


class TestAstronomicalAnchors:
    def test_solar_eclipse_2024_04_08_geometry(self):
        # NASA GSFC greatest eclipse: 2024-04-08 18:17:15 UT
        # (SOURCES["nasa_eclipse_2024_04_08"]).
        jd = swe.julday(2024, 4, 8, 18 + 17 / 60 + 15 / 3600)
        pos = sidereal_positions(jd)
        elong = _elongation(pos)
        elong = min(elong, 360.0 - elong)
        assert elong < 1.0  # new moon at eclipse maximum

        node_dist = min(_axis_distance(pos["Sun"]["lon"], pos["Rahu"]["lon"]),
                        _axis_distance(pos["Sun"]["lon"], pos["Ketu"]["lon"]))
        assert node_dist < 5.0  # luminaries on the nodal axis

    def test_makar_sankranti_2025_ingress(self):
        # AstroSage: Sun enters Capricorn 2025-01-14 08:41 IST = 03:11 UT
        # (SOURCES["astrosage_makar_sankranti_2025"]).
        published_jd = swe.julday(2025, 1, 14, 3 + 11 / 60)

        lo = swe.julday(2025, 1, 13, 12.0)
        hi = swe.julday(2025, 1, 15, 12.0)
        assert sidereal_positions(lo)["Sun"]["lon"] < 270.0 <= sidereal_positions(hi)["Sun"]["lon"]
        for _ in range(48):  # bisection to sub-second precision
            mid = (lo + hi) / 2
            if sidereal_positions(mid)["Sun"]["lon"] >= 270.0:
                hi = mid
            else:
                lo = mid
        ingress_jd = (lo + hi) / 2

        assert abs(ingress_jd - published_jd) * 24.0 <= 6.0  # hours

    def test_guru_purnima_2024_full_moon_instant(self):
        # Astropixels (Fred Espenak): Full Moon 2024 Jul 21 10:17 UT
        # (SOURCES["astropixels_full_moon_jul_2024"]).
        jd = swe.julday(2024, 7, 21, 10 + 17 / 60)
        elong = _elongation(sidereal_positions(jd))
        assert abs(elong - 180.0) < 1.0
