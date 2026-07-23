"""CE-wired daily guidance: computed, rule-based, non-generic."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from astrospace.context import daily_guidance
from astrospace.context.daily import _score_day, _subject_words
from astrospace.core.vedic.chart import VedicChart

DELHI = {"city": "New Delhi", "nation": "IN"}


@pytest.fixture(scope="module")
def guidance():
    chart = VedicChart("Daily", 1990, 1, 1, 12, 0, **DELHI)
    as_of = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    return daily_guidance(chart, relation="self", as_of=as_of)


class TestVerdict:
    def test_verdict_is_plain_and_toned(self, guidance):
        v = guidance["verdict"]
        assert 40 <= v["word_count"] <= 130
        assert v["tone"] in ("supportive", "positive", "mixed", "caution")
        assert v["text"].count(".") >= 3  # multi-sentence

    def test_reading_is_practical_before_technical(self, guidance):
        reading = guidance["reading"]
        assert reading["summary"]
        assert reading["focus"]
        assert reading["energy"] in ("low", "moderate", "steady", "high")
        assert reading["best_for"]
        assert reading["avoid"]
        assert reading["work_tone"]
        assert reading["money_tone"]
        assert reading["relationship_tone"]
        assert reading["plain_why"]
        assert reading["technical_why"]

    def test_technical_why_names_real_signals(self, guidance):
        text = guidance["verdict"]["text"]
        technical = " ".join(guidance["reading"]["technical_why"])
        # Technical proof stays available, but no longer pollutes the common-user
        # reading by forcing Sanskrit labels into the main verdict.
        assert guidance["star_of_day"]["nakshatra"] in technical
        assert guidance["tarabala"]["tara"] in technical
        assert guidance["star_of_day"]["nakshatra"] not in text

    def test_pronoun_grammar_for_self_and_other(self):
        assert _subject_words("self")["you"] == "you"
        assert _subject_words("parent")["you"] == "them"


class TestColorAndNumber:
    def test_color_from_weekday_lord(self, guidance):
        c = guidance["color"]
        assert c["hex"].startswith("#")
        assert c["planet"] in (
            "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"
        )
        assert "vara" in c["source"]

    def test_number_computed_and_personalized(self, guidance):
        n = guidance["number"]
        assert 1 <= n["value"] <= 9
        assert n["fit"] in ("favourable", "challenging", "neutral")
        assert 1 <= n["ruling_number"] <= 9

    def test_color_and_number_change_by_day(self):
        chart = VedicChart("Drift", 1990, 1, 1, 12, 0, **DELHI)
        d1 = daily_guidance(chart, relation="self",
                            as_of=datetime(2026, 7, 20, 10, tzinfo=ZoneInfo("Asia/Kolkata")))
        d2 = daily_guidance(chart, relation="self",
                            as_of=datetime(2026, 7, 21, 10, tzinfo=ZoneInfo("Asia/Kolkata")))
        # Different weekdays => different day colour (Mon vs Tue lords differ).
        assert d1["color"]["planet"] != d2["color"]["planet"]


class TestDoAvoidAndContext:
    def test_do_avoid_carry_sources(self, guidance):
        for row in guidance["do_today"] + guidance["avoid_today"]:
            assert row["source"] in ("tarabala", "chandrabala", "gochara", "muhurta", "ghatak")

    def test_rahu_kalam_window_present_in_avoid(self, guidance):
        assert any(row["source"] == "muhurta" and row.get("window") for row in guidance["avoid_today"])
        assert any("Rahu Kalam" in row for row in guidance["reading"]["technical_why"])

    def test_ce_context_is_wired(self, guidance):
        ctx = guidance["context"]
        assert ctx["route_domain"] in ("health", "wealth", "career")
        assert isinstance(ctx["dasha_chain"], list) and ctx["dasha_chain"]
        assert isinstance(ctx["references"], list)
        assert "active_gochara" in ctx

    def test_lucky_signature_is_birth_constant(self, guidance):
        sig = guidance["lucky_signature"]
        assert sig["gem"] and sig["metal"] and sig["direction"]

    def test_numerology_lucky_number(self, guidance):
        num = guidance["lucky_numbers"]["numerology"]
        assert 1 <= num["number"] <= 9
        assert num["ruling_planet"]
        assert "moolank" in num["source"]

    def test_astrological_lucky_number_from_lagna_lord(self, guidance):
        astro = guidance["lucky_numbers"]["astrological"]
        assert 1 <= astro["number"] <= 9
        assert astro["planet"]
        assert "Lagna lord" in astro["source"]
        assert len(astro["witnesses"]) == 4
        assert astro["witnesses"][0]["label"] == "Lagna lord"
        # confirmation_count only counts the OTHER three witnesses, never itself
        assert astro["confirmation_count"] == len(astro["confirmed_by"])
        assert astro["confirmation_count"] <= 3

    def test_astrological_number_independent_of_calendar_date(self):
        chart = VedicChart("StableAstro", 1990, 1, 1, 12, 0, **DELHI)
        d1 = daily_guidance(chart, relation="self",
                            as_of=datetime(2026, 7, 20, 10, tzinfo=ZoneInfo("Asia/Kolkata")))
        d2 = daily_guidance(chart, relation="self",
                            as_of=datetime(2026, 7, 21, 10, tzinfo=ZoneInfo("Asia/Kolkata")))
        assert d1["lucky_numbers"]["astrological"] == d2["lucky_numbers"]["astrological"]
        assert d1["lucky_numbers"]["numerology"] == d2["lucky_numbers"]["numerology"]


class TestScoring:
    def test_chandrashtama_drags_score_down(self):
        base_personal = {
            "tarabala": {"tara": "Sampat"},
            "chandrabala": {"favourable": True, "chandrashtama": False},
            "ghatak_alerts": [],
        }
        ctx = {"supportive_rules": [], "challenging_rules": []}
        good = _score_day(base_personal, ctx)[0]
        base_personal["chandrabala"] = {"favourable": False, "chandrashtama": True}
        bad = _score_day(base_personal, ctx)[0]
        assert bad < good
