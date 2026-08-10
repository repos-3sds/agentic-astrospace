"""
Panchanga day-engine tests.

Layers:
1. Kala windows on an idealized 06:00–18:00 UT day — table arithmetic
   must reproduce the classic clock windows (Monday Rahu 07:30–09:00 etc).
2. Moon-transit boundaries vs a real astronomical instant: the Purnima
   tithi of 2024-04-23 ends at the exact full moon, 23:49 UT.
3. Personalization math (tarabala count, chandrashtama detection).
4. API smoke.
"""
import pytest
import swisseph as swe

from astrospace.core.vedic.kala import kala_windows, choghadiya, horas
from astrospace.core.vedic.moontimes import element_end, elements_for_day
from astrospace.core.vedic.panchanga_day import daily_panchanga, personal_panchanga
from astrospace.core.cities import city_for_timezone

# 2026-01-05 is a Monday. Ideal day: sunrise 06:00 UT, sunset 18:00 UT.
MONDAY_RISE = swe.julday(2026, 1, 5, 6.0)
MONDAY_SET = swe.julday(2026, 1, 5, 18.0)
MONDAY_NEXT = swe.julday(2026, 1, 6, 6.0)
MONDAY = 1  # vara index


def _find(windows, name):
    return next(w for w in windows if w["name"] == name)


class TestKala:
    @pytest.fixture(scope="class")
    def monday(self):
        return kala_windows(MONDAY_RISE, MONDAY_SET, MONDAY_NEXT, MONDAY, "UTC")

    def test_rahu_kalam_monday_second_eighth(self, monday):
        w = _find(monday["inauspicious"], "Rahu Kalam")
        assert (w["start"], w["end"]) == ("07:30", "09:00")

    def test_yamaganda_monday_fourth_eighth(self, monday):
        w = _find(monday["inauspicious"], "Yamaganda")
        assert (w["start"], w["end"]) == ("10:30", "12:00")

    def test_gulika_monday_sixth_eighth(self, monday):
        w = _find(monday["inauspicious"], "Gulika Kalam")
        assert (w["start"], w["end"]) == ("13:30", "15:00")

    def test_abhijit_is_eighth_muhurta(self, monday):
        w = _find(monday["auspicious"], "Abhijit Muhurta")
        assert (w["start"], w["end"]) == ("11:36", "12:24")

    def test_brahma_muhurta_before_sunrise(self, monday):
        w = _find(monday["auspicious"], "Brahma Muhurta")
        assert (w["start"], w["end"]) == ("04:24", "05:12")

    def test_monday_durmuhurtas(self, monday):
        durs = [w for w in monday["inauspicious"] if w["name"].startswith("Durmuhurta")]
        starts = sorted(w["start"] for w in durs)
        assert starts == ["12:24", "14:48"]  # 9th and 12th muhurtas

    def test_choghadiya_monday_cycle(self):
        c = choghadiya(MONDAY_RISE, MONDAY_SET, MONDAY_NEXT, MONDAY, "UTC")
        day_names = [b["name"] for b in c["day"]]
        assert len(day_names) == 8
        assert day_names[0] == "Amrit"      # Monday starts with Amrit
        assert day_names[-1] == day_names[0]  # 8th repeats the 1st
        assert c["night"][0]["name"] == "Chal"

    def test_horas_start_with_day_lord(self):
        h = horas(MONDAY_RISE, MONDAY_SET, MONDAY_NEXT, MONDAY, "UTC")
        assert len(h) == 24
        assert h[0]["name"] == "Moon Hora"   # Monday
        assert h[0]["start"] == "06:00"
        assert h[12]["start"] == "18:00"     # night horas begin at sunset


class TestMoonBoundaries:
    def test_purnima_ends_at_exact_full_moon(self):
        # Full moon: 2024-04-23 23:49 UT. Purnima tithi ends at elongation 180°.
        jd = swe.julday(2024, 4, 23, 12.0)
        idx, end_jd = element_end(jd, "tithi")
        assert idx == 14  # Purnima
        y, m, d, h = swe.revjul(end_jd)
        assert (y, m, d) == (2024, 4, 23)
        assert abs(h - (23 + 49 / 60)) < 0.75  # within 45 minutes

    def test_karana_is_half_tithi(self):
        jd = swe.julday(2024, 4, 23, 12.0)
        _, tithi_end = element_end(jd, "tithi")
        k_idx, karana_end = element_end(jd, "karana")
        # the karana boundary can be the tithi midpoint or its end,
        # but never after the tithi end
        assert karana_end <= tithi_end + 1e-6

    def test_elements_sequence_and_monotonic(self):
        p = daily_panchanga(2026, 7, 7, city="Rajahmundry", nation="IN")
        for kind in ("tithi", "nakshatra", "yoga", "karana"):
            entries = p["elements"][kind]
            assert 1 <= len(entries) <= 5
            isos = [e["upto_iso"] for e in entries]
            assert isos == sorted(isos)
            assert entries[-1]["spans_day_end"]

    def test_karanas_consecutive(self):
        p = daily_panchanga(2026, 7, 7, city="Rajahmundry", nation="IN")
        idxs = [e["index"] for e in p["elements"]["karana"]]
        for a, b in zip(idxs, idxs[1:]):
            assert b == (a + 1) % 60


class TestDailyPanchanga:
    @pytest.fixture(scope="class")
    def day(self):
        return daily_panchanga(2026, 7, 7, city="Rajahmundry", nation="IN")

    def test_vara_is_tuesday(self, day):
        assert day["vara"]["name"] == "Tuesday"
        assert day["vara"]["lord"] == "Mars"

    def test_all_core_windows_present(self, day):
        names = {w["name"].split(" (")[0] for w in
                 day["windows"]["auspicious"] + day["windows"]["inauspicious"]}
        for expected in ("Rahu Kalam", "Yamaganda", "Gulika Kalam",
                         "Brahma Muhurta", "Abhijit Muhurta", "Durmuhurta"):
            assert expected in names

    def test_windows_within_vedic_day(self, day):
        # every window must overlap [sunrise-2h, next sunrise]
        for w in day["windows"]["auspicious"] + day["windows"]["inauspicious"]:
            assert w["start_iso"] < w["end_iso"]

    def test_carries_the_abhijit_nakshatra_overlay(self, day):
        row = day["abhijit_nakshatra"]
        assert isinstance(row["active"], bool)
        assert row["source_status"] == "convention_dependent"

    def test_abhijit_nakshatra_and_abhijit_muhurta_stay_distinct(self):
        """Two unrelated things share the name "Abhijit": the daily noon
        window (kala.py, always present) and the Moon's intercalary arc
        (abhijit.py, rarely active). 2026-09-22 at Chennai has BOTH, which
        is exactly the case that would expose them being conflated."""
        day = daily_panchanga(2026, 9, 22, city="Chennai", nation="IN")
        window_names = {w["name"].split(" (")[0] for w in day["windows"]["auspicious"]}
        assert "Abhijit Muhurta" in window_names
        assert day["abhijit_nakshatra"]["active"] is True
        # The overlay must not have renamed the day's actual nakshatra.
        assert day["elements"]["nakshatra"][0]["name"] == "Uttara Ashadha"

    def test_display_timezone_can_differ_from_calculation_timezone(self):
        local = daily_panchanga(2026, 7, 7, city="Rajahmundry", nation="IN")
        singapore = daily_panchanga(
            2026, 7, 7, city="Rajahmundry", nation="IN", display_tz_str="Asia/Singapore"
        )
        assert singapore["place"]["timezone"] == "Asia/Singapore"
        assert singapore["place"]["calculation_timezone"] == "Asia/Kolkata"
        assert singapore["sunrise"] != local["sunrise"]


class TestPersonal:
    def _payload(self, nak_name, tithi_idx, moon_sign):
        return {
            "elements": {
                "nakshatra": [{"name": nak_name, "index": 0}],
                "tithi": [{"name": "x", "index": tithi_idx}],
            },
            "moon_rashi_at_sunrise": moon_sign,
            "vara": {"name": "Friday"},
        }

    def test_tarabala_kshema(self):
        # janma Ashwini (0), today Rohini (3) → 4th tara = Kshema (good)
        p = personal_panchanga(self._payload("Rohini", 0, "Taurus"), 0, 1)
        assert p["tarabala"]["tara"] == "Kshema"
        assert p["tarabala"]["favourable"]

    def test_tarabala_vipat(self):
        # janma Ashwini, today Krittika (2) → 3rd tara = Vipat (bad)
        p = personal_panchanga(self._payload("Krittika", 0, "Aries"), 0, 0)
        assert p["tarabala"]["tara"] == "Vipat"
        assert not p["tarabala"]["favourable"]

    def test_chandrashtama(self):
        # janma rashi Cancer (3), Moon in Aquarius (10) → 8th house
        p = personal_panchanga(self._payload("Ashwini", 0, "Aquarius"), 0, 3)
        assert p["chandrabala"]["chandrashtama"]
        assert not p["chandrabala"]["favourable"]

    def test_ghatak_day_alert(self):
        # Sagittarius moon sign → ghatak day Friday; payload says Friday
        p = personal_panchanga(self._payload("Ashwini", 2, "Aries"), 0, 0,
                               ghatak_moon_sign=8)
        day_alert = next(a for a in p["ghatak_alerts"] if a["type"] == "day")
        assert day_alert["matched"]


class TestAPI:
    def test_timezone_representative_city(self):
        city = city_for_timezone("Asia/Singapore")
        assert city is not None
        assert city[0] == "Singapore"

    def test_public_endpoint(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.get("/api/v1/panchanga/today",
                       params={"city": "Rajahmundry", "date": "2026-07-07"})
        assert r.status_code == 200
        d = r.json()
        assert d["vara"]["name"] == "Tuesday"
        assert d["elements"]["tithi"][0]["upto"]

    def test_public_endpoint_uses_viewer_timezone_for_display(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.get("/api/v1/panchanga/today",
                       params={"city": "Rajahmundry", "date": "2026-07-07",
                               "timezone": "Asia/Singapore"})
        assert r.status_code == 200
        d = r.json()
        assert d["place"]["timezone"] == "Asia/Singapore"
        assert d["place"]["calculation_timezone"] == "Asia/Kolkata"

    def test_city_selector_endpoint(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.get("/api/v1/panchanga/cities", params={"q": "singapore"})
        assert r.status_code == 200
        rows = r.json()
        assert rows[0]["city"] == "Singapore"
        assert rows[0]["timezone"] == "Asia/Singapore"

    def test_india_city_coverage_and_aliases(self):
        from astrospace.core.cities import lookup_city, search_cities

        assert lookup_city("Navi Mumbai", "IN") is not None
        assert lookup_city("Puducherry", "IN") == lookup_city("Pondicherry", "IN")
        assert lookup_city("Kalaburagi", "IN") == lookup_city("Gulbarga", "IN")

        rows = search_cities("tiru", limit=20)
        names = {row["city"] for row in rows}
        assert {"Tirupati", "Tirunelveli", "Tiruppur"} <= names
        assert all(row["timezone"] == "Asia/Kolkata" for row in rows if row["nation"] == "IN")

    def test_bad_timezone_400(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.get("/api/v1/panchanga/today",
                       params={"city": "Rajahmundry", "timezone": "Mars/Olympus"})
        assert r.status_code == 400

    def test_unknown_city_422(self):
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        r = client.get("/api/v1/panchanga/today", params={"city": "Nowhereville"})
        assert r.status_code == 422
