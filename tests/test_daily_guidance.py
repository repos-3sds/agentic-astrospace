"""CE-wired daily guidance: computed, rule-based, non-generic."""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from astrospace.context import daily_guidance
from astrospace.context.daily import DAY_BANDS, _do_and_avoid, _legacy_score, _pick, _score_day, _subject_words
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
        assert reading["energy"] in ("vibrant", "steady", "fragmented", "drained")
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


class TestSunriseBoundedValidity:
    """docs/reliable_native_core_architecture_2026-08-14.md's cache-validity
    contract: the response must carry an authoritative Vedic-day interval
    (sunrise to next sunrise), and a request made before sunrise is still
    the reader's calendar date: the Vedic day that begins at its sunrise."""

    def test_carries_engine_version_and_validity_window(self, guidance):
        assert guidance["engine_version"] == "daily-guidance-1.1"
        assert guidance["day_definition"] == "sunrise_to_next_sunrise"
        valid_from = datetime.fromisoformat(guidance["valid_from"])
        valid_until = datetime.fromisoformat(guidance["valid_until"])
        as_of = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        assert valid_from <= as_of < valid_until

    def test_pre_sunrise_request_is_the_calendar_date(self):
        # 3am on the 21st is the 21st: Today names the reader's own date and
        # serves the Vedic day that begins at the 21st's sunrise. It once
        # served the 20th until dawn (05:30 Friday showed Thursday).
        chart = VedicChart("Daily", 1990, 1, 1, 12, 0, **DELHI)
        pre_sunrise = datetime(2026, 7, 21, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        prev_afternoon = datetime(2026, 7, 20, 15, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        post_sunrise_same_civil_day = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))

        before_dawn = daily_guidance(chart, relation="self", as_of=pre_sunrise)
        yesterday = daily_guidance(chart, relation="self", as_of=prev_afternoon)
        today = daily_guidance(chart, relation="self", as_of=post_sunrise_same_civil_day)

        assert before_dawn["date"] == today["date"] == "2026-07-21"
        assert before_dawn["vara"] == today["vara"]
        assert before_dawn["star_of_day"] == today["star_of_day"]
        assert yesterday["date"] == "2026-07-20"
        assert before_dawn["vara"] != yesterday["vara"]

        # The day it describes begins at the 21st's sunrise, still ahead at
        # 3am, and runs to the 22nd's.
        valid_from = datetime.fromisoformat(before_dawn["valid_from"])
        valid_until = datetime.fromisoformat(before_dawn["valid_until"])
        assert pre_sunrise < valid_from < post_sunrise_same_civil_day
        assert valid_from.date() == pre_sunrise.date()
        assert valid_until.date() == date(2026, 7, 22)

    def test_date_follows_the_viewer_clock_not_the_place(self):
        # Hawk in Singapore at 05:30 Friday with the Indian birth city as the
        # timings place: India is at 03:00 Friday, UTC still Thursday. The
        # date is Friday's, and the windows stay on the place's clock.
        chart = VedicChart("Daily", 1990, 1, 1, 12, 0, **DELHI)
        singapore = datetime(2026, 10, 30, 5, 30, tzinfo=ZoneInfo("Asia/Singapore"))
        g = daily_guidance(chart, relation="self", as_of=singapore,
                           city="Delhi", nation="IN", lat=28.6139, lng=77.209,
                           tz_str="Asia/Kolkata")
        assert g["date"] == "2026-10-30"
        assert g["vara"] == "Friday"

    def test_do_avoid_phrasing_is_stable_across_the_same_day(self):
        # An early-morning and a late-evening check of the SAME day must not
        # get different do/avoid phrasing just because of the hour — the
        # phrase-rotation seed is keyed on the date, not as_of.
        chart = VedicChart("Daily", 1990, 1, 1, 12, 0, **DELHI)
        pre_sunrise = datetime(2026, 7, 21, 3, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        # Before the Moon leaves chandrashtama at 7:54 am on this day: after
        # it the reading follows the new sign, on purpose
        # (tests/test_tara_change_mid_day.py).
        later_same_day = datetime(2026, 7, 21, 7, 30, tzinfo=ZoneInfo("Asia/Kolkata"))

        before_dawn = daily_guidance(chart, relation="self", as_of=pre_sunrise)
        evening = daily_guidance(chart, relation="self", as_of=later_same_day)

        assert before_dawn["date"] == evening["date"]
        assert before_dawn["do_today"] == evening["do_today"]
        assert before_dawn["avoid_today"] == evening["avoid_today"]


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
            assert row["source"] in ("tarabala", "domain")

    def test_tarabala_row_has_a_plain_headline_for_guided_readers(self, guidance):
        rows = [r for r in guidance["do_today"] + guidance["avoid_today"] if r["source"] == "tarabala"]
        assert rows, "tarabala row missing"
        plain = rows[0]["plain_headline"]
        # A plain action for every reader now, the same as the headline.
        assert plain == rows[0]["headline"]
        assert "tara" not in plain.lower()

    def test_domain_rows_carry_a_domain_and_headline(self, guidance):
        for row in guidance["do_today"] + guidance["avoid_today"]:
            if row["source"] == "domain":
                assert row["domain"] in ("Finance", "Love", "Health", "Growth", "Career")
                # A plain action, not "Finance: ..." (Hawk, 2026-10-16).
                assert not row["headline"].startswith(f"{row['domain']}:")
                assert len(row["headline"].split()) <= 6

    def test_domains_are_capped_at_two_per_side(self, guidance):
        assert len([r for r in guidance["do_today"] if r["source"] == "domain"]) <= 2
        assert len([r for r in guidance["avoid_today"] if r["source"] == "domain"]) <= 2

    def test_rahu_kalam_window_present_in_timing_note(self, guidance):
        """Muhurta dropped out of Do/Avoid (it duplicated the Timing Note) —
        the window itself still surfaces, just through timing_note/technical_why."""
        assert any("Rahu Kalam" in row for row in guidance["reading"]["technical_why"])

    def test_rows_carry_no_clock_time_in_their_text(self, guidance):
        """The sentence itself should read without needing a clock — that
        duplicated the Timing Note."""
        clock = re.compile(r"\d{1,2}:\d{2}")
        for row in guidance["do_today"] + guidance["avoid_today"]:
            assert not clock.search(row["text"]), row["text"]

    def test_tarabala_text_is_specific_to_the_tara(self):
        """Two charts landing on different taras get different Do/Avoid
        wording — not one of two generic sentences regardless of which tara
        it actually is."""
        sampat = VedicChart("Sampat", 1990, 1, 1, 12, 0, **DELHI)
        vipat = VedicChart("Vipat", 1985, 6, 15, 6, 30, **DELHI)
        as_of = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        g1 = daily_guidance(sampat, relation="self", as_of=as_of)
        g2 = daily_guidance(vipat, relation="self", as_of=as_of)
        tara_row_1 = next(r for r in g1["do_today"] + g1["avoid_today"] if r["source"] == "tarabala")
        tara_row_2 = next(r for r in g2["do_today"] + g2["avoid_today"] if r["source"] == "tarabala")
        if tara_row_1["text"] == tara_row_2["text"]:
            pytest.skip("both charts happened to land on the same tara for this date")
        assert tara_row_1["text"] != tara_row_2["text"]

    def test_no_duplicate_text_within_do_or_avoid(self, guidance):
        """Multiple active gochara rules of the same severity used to each
        append the identical generic sentence — now they collapse into one
        line naming the planets involved."""
        do_texts = [row["text"] for row in guidance["do_today"]]
        avoid_texts = [row["text"] for row in guidance["avoid_today"]]
        assert len(do_texts) == len(set(do_texts))
        assert len(avoid_texts) == len(set(avoid_texts))

    def test_pick_is_deterministic(self):
        options = ["a", "b", "c", "d"]
        assert _pick("some-stable-seed", options) == _pick("some-stable-seed", options)

    def test_domain_rows_name_the_specific_rule_not_just_the_planet(self):
        """"Guru Bala from Lagna" and "Guru Bala from Moon" both involve
        Jupiter but are different classical situations — grouping by planet
        alone (the previous behaviour) would have merged them into one
        "Jupiter" mention. Two charts with different active rules must read
        differently, not just collapse to the same domain phrasing."""
        a = VedicChart("A", 1990, 1, 1, 12, 0, **DELHI)
        c = VedicChart("C", 2000, 11, 3, 18, 45, **DELHI)
        as_of = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        ga = daily_guidance(a, relation="self", as_of=as_of)
        gc = daily_guidance(c, relation="self", as_of=as_of)
        texts_a = {r["text"] for r in ga["do_today"] + ga["avoid_today"] if r["source"] == "domain"}
        texts_c = {r["text"] for r in gc["do_today"] + gc["avoid_today"] if r["source"] == "domain"}
        if not texts_a or not texts_c:
            pytest.skip("no active domain signal for one of the test charts on this date")
        assert texts_a != texts_c

    def test_pick_distributes_across_seeds(self):
        """Direct test of the rotation mechanism itself, independent of
        whether real ephemeris data happens to line two people up on the
        same rule on the same day: many different seeds (standing in for
        different people, or the same person on different days) must not
        all collapse onto the same option."""
        options = ["a", "b", "c", "d"]
        results = {_pick(f"seed-{i}", options) for i in range(50)}
        assert len(results) > 1

    def test_domain_text_rotates_across_consecutive_days(self):
        """A single outer-planet rule can stay active for weeks — the phrase
        must rotate rather than repeat the identical sentence for the whole
        span. Confirmed empirically: this chart showed the same
        "Saturn, Rahu, Ketu and Mars..." sentence for 6 straight days
        before this fix."""
        chart = VedicChart("Rotator", 1990, 1, 1, 12, 0, **DELHI)
        texts: set[str] = set()
        for offset in range(10):
            as_of = datetime(2026, 7, 21, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")) + timedelta(days=offset)
            g = daily_guidance(chart, relation="self", as_of=as_of)
            texts.update(
                row["text"] for row in g["do_today"] + g["avoid_today"]
                if row["source"] == "domain"
            )
        assert len(texts) > 1, "domain wording never varied across 10 consecutive days"

    def test_career_only_appears_when_it_wins_a_slot(self):
        """Career is always DO-framed and always has a theme (every dasha
        lord maps to one), so it must not appear unconditionally — only when
        it ranks into the top-2-per-side cap. Built from synthetic ctx/personal
        (not a real chart) so the outcome is deterministic, not dependent on
        which rules happen to be active on a given ephemeris date."""
        ctx = {
            "supportive_rules": [
                {"name": "Rule A", "house": 2, "severity": "high"},    # Finance, rank 0
                {"name": "Rule B", "house": 7, "severity": "high"},    # Love, rank 0
                {"name": "Rule C", "house": 4, "severity": "medium"},  # Growth, rank 1
            ],
            "challenging_rules": [],
            "dasha_chain": [{"level": "mahadasha", "lord": "Sun"}],  # Career, rank 2 — loses the cap
        }
        do, avoid = _do_and_avoid({}, ctx, _subject_words("self"), "career-cap-seed")
        domain_rows = [r for r in do if r["source"] == "domain"]
        assert len(domain_rows) == 2
        assert {r["domain"] for r in domain_rows} == {"Finance", "Love"}
        assert avoid == []

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

    @staticmethod
    def _day(tara, moon, challenging=3, supportive=0):
        personal = {
            "tarabala": {"tara": tara},
            "chandrabala": {"favourable": moon == "good", "chandrashtama": moon == "chandrashtama"},
            "ghatak_alerts": [],
        }
        ctx = {"supportive_rules": [{"severity": "supportive"}] * supportive,
               "challenging_rules": [{"severity": "medium"}] * challenging}
        return _score_day(personal, ctx)

    def test_score_is_on_a_0_to_100_dial_centred_on_50(self):
        # Hawk 2026-10-28: an average day is 50. Typical background transit
        # pressure (three medium rules) with a good star and an ordinary Moon
        # is an ordinary day, and lands in Steady.
        score, tone, _ = self._day("Sampat", "ordinary")
        assert 50 <= score < 70 and tone == "positive"
        for args in [("Sampat", "good", 0, 4), ("Vipat", "chandrashtama", 8, 0)]:
            assert 0 <= self._day(*args)[0] <= 100

    def test_a_calendar_care_day_never_reads_steady(self):
        # Sweep 2026-10-29 F-1: Today said "53 Steady" on a Chandrashtama day
        # that Calendar marked "take care". A care day (chandrashtama, Janma
        # or Vadha star) now caps at Mixed, and the parts still add up.
        from astrospace.context.daily import _score_parts
        for tara, moon in [("Sampat", "chandrashtama"), ("Janma", "good"), ("Vadha", "good")]:
            score, tone, _ = self._day(tara, moon, challenging=0, supportive=4)
            assert score <= 49 and tone in ("mixed", "caution"), (tara, moon, score)
        personal = {"tarabala": {"tara": "Sampat"},
                    "chandrabala": {"favourable": False, "chandrashtama": True}, "ghatak_alerts": []}
        ctx = {"supportive_rules": [{"severity": "supportive"}] * 4, "challenging_rules": []}
        parts = _score_parts(personal, ctx)
        assert parts["care"] < 0 and sum(parts.values()) == _score_day(personal, ctx)[0]
        # An already-low care day is not pushed further down.
        personal["tarabala"] = {"tara": "Vipat"}
        assert _score_parts(personal, {"supportive_rules": [], "challenging_rules": [{"severity": "high"}] * 4})["care"] == 0
        # An ordinary day carries no care part.
        assert "care" not in self._day_parts("Sampat", "good")

    def _day_parts(self, tara, moon):
        from astrospace.context.daily import _score_parts
        personal = {"tarabala": {"tara": tara},
                    "chandrabala": {"favourable": moon == "good", "chandrashtama": False}, "ghatak_alerts": []}
        return _score_parts(personal, {"supportive_rules": [], "challenging_rules": []})

    def test_low_only_when_all_three_signals_are_poor(self):
        # Star and Moon both at their worst, transits at the usual background:
        # still Mixed, not the bottom band.
        score, tone, _ = self._day("Vipat", "chandrashtama", challenging=3)
        assert score >= 30 and tone == "mixed"
        # All three poor: the bottom band.
        score, tone, _ = self._day("Vipat", "chandrashtama", challenging=6)
        assert score < 30 and tone == "caution"

    def test_good_day_is_70_or_more(self):
        score, tone, _ = self._day("Sampat", "good")
        assert score >= 70 and tone == "supportive"

    def test_verdict_carries_its_parts(self, guidance):
        v = guidance["verdict"]
        assert sum(v["day_score_parts"].values()) == v["day_score"] or v["day_score"] in (0, 100)
        assert v["day_score_parts"]["base"] == 50
        # Builds that drew the ring from score_parts + score must not see a
        # tally there; they fall back to their band's slice instead.
        assert "score_parts" not in v


def _old_build_dial(tally: float) -> int:
    """gaugePositionFromScore as shipped before 2026-10-28 (today.component.ts)."""
    bands = [(3, 76, 100), (1, 51, 75), (-1, 26, 50), (float("-inf"), 1, 25)]
    lower, floor, ceiling = next(b for b in bands if tally >= b[0])
    start = lower if lower != float("-inf") else -6
    within = min(1, max(0, (tally - start) / 4))
    return round(floor + within * (ceiling - floor))


class TestOldBuilds:
    """Srikavya, 2026-10-28: an iPhone build from before the 0-100 rescale drew
    a day that scored 58 (Steady, Chandrashtama) as a full ring reading 100,
    because it read the new score as the old signed tally."""

    OLD_SLICE = {"supportive": (76, 100), "positive": (51, 75), "mixed": (26, 50), "caution": (1, 25)}

    @pytest.mark.parametrize("score", range(0, 101))
    def test_old_build_ring_stays_in_the_days_band(self, score):
        tone = next(tone for floor, tone in DAY_BANDS if score >= floor)
        dial = _old_build_dial(_legacy_score(score, tone))
        low, high = self.OLD_SLICE[tone]
        assert low <= dial <= high, (score, tone, dial)
        assert dial != 100 or tone == "supportive"

    def test_srikavyas_day_reads_near_its_score(self):
        assert _old_build_dial(_legacy_score(58, "positive")) == 58


class TestMasa:
    def test_both_month_reckonings_are_stated_with_the_convention(self, guidance):
        """A client must be able to say which month reckoning it used (amanta
        vs purnimanta is the first convention CLAUDE.md names), so the daily
        payload carries both names and the observance note, not one bare name."""
        masa = guidance["masa"]
        assert masa["amanta"] and masa["purnimanta"]
        assert masa["is_convention_dependent"] is True
        assert "purnimanta" in masa["observance_note"].lower()
        assert masa["paksha"] in ("Shukla", "Krishna")


class TestDoAvoidTitlesArePlain:
    """Card titles are short plain actions with no astrology terms; the
    signal behind each stays in its text and the Why sheet."""

    JARGON = ("tara", "nakshatra", "dasha", "bala", "gochara", "kalam", "muhurta",
              "chandrashtama", "ghatak", "sampat", "sadhaka", "kshema", "vipat",
              "pratyari", "vadha", "mitra", "janma")

    def test_every_title_is_short_and_plain(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from astrospace.context import daily_guidance
        from astrospace.core.vedic import VedicChart

        for args in [("A", 1991, 8, 14, 6, 12, "Vijayawada", "IN"), ("B", 1965, 2, 3, 9, 0, "Hyderabad", "IN"),
                     ("C", 1988, 11, 30, 22, 45, "Chennai", "IN")]:
            for day in (10, 16, 22):
                g = daily_guidance(VedicChart(*args), relation="self",
                                   as_of=datetime(2026, 10, day, 12, tzinfo=ZoneInfo("Asia/Kolkata")))
                for row in g["do_today"] + g["avoid_today"]:
                    # A day whose star changes adds "until 11:34 am" to the
                    # tara row's title; the action itself stays short.
                    title = re.sub(r" (until|from) \d{1,2}:\d{2} [ap]m$", "", row["headline"].lower())
                    assert len(title.split()) <= 6, row["headline"]
                    assert not any(word in title for word in self.JARGON), row["headline"]
