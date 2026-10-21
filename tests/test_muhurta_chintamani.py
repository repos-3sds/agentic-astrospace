"""Goal lists checked against the 1907 Muhurta Chintamani print.

Each assertion names the verse it comes from, so a later change to a list has
to argue with the book rather than with a test.
"""
from datetime import date

from astrospace.core.vedic import muhurta
from astrospace.core.vedic.constants import NAKSHATRAS

G = muhurta.GOALS


def test_every_listed_star_is_a_real_nakshatra():
    for slug, goal in G.items():
        assert set(goal["prefer_nakshatra"]) <= set(NAKSHATRAS), slug


def test_sources_cite_the_print_or_are_left_empty():
    cited = {slug for slug, g in G.items() if g.get("source")}
    assert {"buy_vehicle", "buy_gold", "start_venture", "join_job", "griha_pravesha",
            "move_rented_home", "bhoomi_puja", "seemantham", "namakarana",
            "annaprashana", "mundan", "karnavedha", "upanayana", "vidyarambha",
            "start_journey"} <= cited
    for slug in cited:
        assert G[slug]["source"].startswith("Muhurta Chintamani "), slug
    # No verse read for these yet: common practice, and no false citation.
    for slug in ("start_sadhana", "general", "property_registration"):
        assert not G[slug].get("source"), slug


def test_vehicle_2_16_and_2_18():
    stars = set(G["buy_vehicle"]["prefer_nakshatra"])
    assert {"Ashwini", "Pushya", "Hasta", "Revati", "Mrigashira", "Swati",
            "Shatabhisha", "Punarvasu"} <= stars
    assert not stars & {"Rohini", "Anuradha", "Dhanishta"}
    assert G["buy_vehicle"]["shun_vara"] == ["Tuesday"]


def test_shop_opening_2_17():
    g = G["start_venture"]
    assert set(g["prefer_nakshatra"]) == {"Anuradha", "Rohini", "Uttara Phalguni",
                                          "Uttara Ashadha", "Uttara Bhadrapada",
                                          "Ashwini", "Pushya", "Hasta"}
    assert "Tuesday" in g["shun_vara"]
    assert 10 in g["avoid_lagna"]  # Aquarius


def test_joining_service_2_26():
    g = G["join_job"]
    assert set(g["prefer_nakshatra"]) == {"Ashwini", "Pushya", "Hasta", "Anuradha"}
    assert set(g["prefer_vara"]) == {"Sunday", "Wednesday", "Thursday", "Friday"}


def test_house_entry_13_1_and_old_house_13_2():
    assert "Dhanishta" not in G["griha_pravesha"]["prefer_nakshatra"]
    assert {"Shatabhisha", "Pushya", "Swati", "Dhanishta"} <= set(
        G["move_rented_home"]["prefer_nakshatra"])
    for slug in ("griha_pravesha", "move_rented_home", "bhoomi_puja"):
        assert {"Sunday", "Tuesday"} <= set(G[slug]["shun_vara"]), slug


def test_bhoomi_puja_tithis_12_18():
    assert {1, 4, 8, 9, 14, 15} <= G["bhoomi_puja"]["avoid_tithi"]


def test_samskaras_chapter_5():
    assert set(G["seemantham"]["prefer_vara"]) == {"Sunday", "Tuesday", "Thursday"}
    assert {6, 8, 12} <= G["seemantham"]["avoid_tithi"]
    assert len(G["namakarana"]["prefer_nakshatra"]) == 16
    assert {1, 6, 8, 11, 12} <= G["annaprashana"]["avoid_tithi"]
    assert {1, 6} <= G["mundan"]["avoid_tithi"]
    assert "Anuradha" not in G["mundan"]["prefer_nakshatra"]
    assert "Jyeshtha" in G["mundan"]["prefer_nakshatra"]
    assert {"chaturmas", "kharmas"} <= G["karnavedha"]["season"]
    assert {"Ashlesha", "Moola", "Ardra", "Purva Phalguni"} <= set(
        G["upanayana"]["prefer_nakshatra"])
    assert {"Ardra", "Anuradha"} <= set(G["vidyarambha"]["prefer_nakshatra"])
    assert "Monday" in G["vidyarambha"]["prefer_vara"]


def test_journey_tithis_11_9():
    assert {6, 8, 12, 15} <= G["start_journey"]["avoid_tithi"]


def test_sarvartha_siddhi_1_28():
    assert muhurta._special_days("Saturday", {"nakshatra": "Swati", "tithi_number": 3}) \
        == ["Sarvartha Siddhi"]
    assert muhurta._special_days("Saturday", {"nakshatra": "Hasta", "tithi_number": 3}) == []
    # A stronger yoga on the same day is named alone.
    assert muhurta._special_days("Thursday", {"nakshatra": "Pushya", "tithi_number": 3}) \
        == ["Guru Pushya"]


def test_amrit_siddhi_monday_takes_either_star():
    for nak in ("Mrigashira", "Shravana"):
        assert muhurta._special_days("Monday", {"nakshatra": nak, "tithi_number": 3}) \
            == ["Amrit Siddhi"]


def test_shunned_weekday_is_marked_down_not_dropped(monkeypatch):
    day = date(2026, 11, 7)  # a Saturday with a slot that clears the bar
    args = dict(janma_nakshatra_index=3, janma_rashi_index=1, city="Hyderabad",
                nation="IN", limit=30)
    monkeypatch.setattr(muhurta, "_MIN_SCORE", 0)  # keep the marked-down slots in view
    plain = muhurta.find("general", day, day, **args)["results"]
    monkeypatch.setitem(G, "general", dict(G["general"], shun_vara=["Saturday"]))
    shunned = muhurta.find("general", day, day, **args)["results"]
    assert plain, "the Saturday needs at least one slot for this check"
    by_start = {r["start"]: r for r in shunned}
    assert set(by_start) == {r["start"] for r in plain}  # nothing dropped
    for r in plain:
        if r["start"] in by_start:
            s = by_start[r["start"]]
            assert s["score"] < r["score"]
            assert "Saturday is a day the old rules avoid for this" in s["why"]["against"]


def test_rules_source_reaches_the_payload():
    out = muhurta.find("join_job", date(2026, 11, 2), date(2026, 11, 3),
                       janma_nakshatra_index=3, janma_rashi_index=1,
                       city="Hyderabad", nation="IN")
    assert out["rules_source"] == "Muhurta Chintamani 2.26 (1907 Venkateshwar Press print)"


def test_locked_next_gives_the_date_and_never_the_time():
    args = dict(janma_nakshatra_index=3, janma_rashi_index=1, city="Hyderabad", nation="IN")
    out = muhurta.find("general", date(2026, 11, 2), date(2026, 11, 15),
                       locked_from=date(2026, 11, 16), locked_days=60, **args)
    locked = out["locked_next"]
    assert set(locked) == {"date", "quality"}
    assert locked["date"] >= "2026-11-16"
    assert muhurta.find("general", date(2026, 11, 2), date(2026, 11, 3), **args)["locked_next"] is None


def test_wedding_6_53_and_engagement_6_10():
    wed = G["marriage_related"]
    assert set(wed["prefer_nakshatra"]) == {
        "Mrigashira", "Hasta", "Moola", "Anuradha", "Magha", "Rohini", "Revati",
        "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada", "Swati"}
    assert wed["avoid_tithi"] == muhurta.RIKTA_TITHIS  # full moon allowed
    eng = set(G["engagement"]["prefer_nakshatra"])
    assert set(wed["prefer_nakshatra"]) | {"Krittika", "Shravana", "Dhanishta",
                                           "Purva Ashadha"} <= eng
    assert "Sunday" not in G["engagement"]["prefer_vara"]


def test_contract_2_42():
    assert set(G["sign_contract"]["prefer_nakshatra"]) == {"Pushya", "Anuradha", "Purva Phalguni"}
