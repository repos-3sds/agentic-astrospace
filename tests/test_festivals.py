"""Tests for the Hindu festival calendar.

The valuable assertions here are the *anchors*: a handful of 2026 dates that
are independently known, chosen because each one breaks a different way if a
rule is wrong. Maha Shivaratri catches nishita-vs-sunrise, Diwali catches
pradosh, Ugadi catches kshaya tithi, Pongal catches the Sankranti sunset
rule, and Vijayadashami, Ganesh Chaturthi and Rama Navami catch the daytime
kala windows. Every one of those started out wrong; Vijayadashami 2026 was
shown a day late on the day itself.

The rest check that the engine stays self-consistent: each computed date's
panchanga actually satisfies the rule that produced it.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from astrospace.core.vedic import festivals as F
from astrospace.core.vedic.constants import LUNAR_MONTHS, NAKSHATRAS
from astrospace.core.vedic.positions import resolve_location

CHENNAI = {"city": "Chennai", "nation": "IN"}


@pytest.fixture(scope="module")
def y2026():
    """2026 resolved for Chennai — a full-year scan, so compute it once."""
    rows = F.occurrences(2026, **CHENNAI)
    return {row["slug"]: row for row in rows}, rows


@pytest.fixture(scope="module")
def facts_2026():
    lat, lng, tz = resolve_location("Chennai", "IN", None, None, None)
    return F._scan_year(2026, lat, lng, tz)


def _on(y2026, slug) -> date:
    by_slug, _ = y2026
    return by_slug[slug]["occurs_on"]


# ── Known dates ──────────────────────────────────────────────────────────────

class TestKnownDates:
    """Each anchor pins down one determination rule."""

    @pytest.mark.parametrize("slug,expected,what", [
        ("maha_shivaratri", date(2026, 2, 15), "nishita kala, not sunrise"),
        ("diwali", date(2026, 11, 8), "Amavasya at pradosh, not sunrise"),
        ("holika_dahan", date(2026, 3, 2), "Purnima at pradosh, not sunrise"),
        ("holi", date(2026, 3, 3), "the morning after Holika Dahan"),
        ("ugadi", date(2026, 3, 19), "kshaya tithi — Pratipada touches no sunrise"),
        ("tulsi_vivah", date(2026, 11, 21), "kshaya tithi — Dwadashi is skipped"),
        ("makar_sankranti", date(2026, 1, 14), "Sankranti before sunset"),
        ("tamil_puthandu", date(2026, 4, 14), "Mesha ingress before sunset"),
        ("krishna_janmashtami", date(2026, 9, 4), "amanta Shravana Krishna Ashtami"),
        ("ganesh_chaturthi", date(2026, 9, 14), "Chaturthi at madhyahna"),
        ("rama_navami", date(2026, 3, 26), "Navami at madhyahna"),
        ("vijayadashami", date(2026, 10, 20), "Dashami at aparahna"),
        ("dhanteras", date(2026, 11, 6), "Trayodashi at pradosh"),
        ("onam", date(2026, 8, 26), "Thiruvonam in Chingam"),
    ])
    def test_anchor_dates(self, y2026, slug, expected, what):
        assert _on(y2026, slug) == expected, f"{slug} is fixed by {what}"


class TestOrdering:
    """Relationships that must hold whatever the absolute dates are."""

    def test_holi_is_the_day_after_holika_dahan(self, y2026):
        assert _on(y2026, "holi") == _on(y2026, "holika_dahan") + timedelta(days=1)

    def test_pongal_runs_bhogi_pongal_mattu_kaanum(self, y2026):
        first = _on(y2026, "makar_sankranti")
        assert _on(y2026, "bhogi") == first - timedelta(days=1)
        assert _on(y2026, "lohri") == _on(y2026, "bhogi")
        assert _on(y2026, "mattu_pongal") == first + timedelta(days=1)
        assert _on(y2026, "kaanum_pongal") == first + timedelta(days=2)

    def test_diwali_cluster_is_in_order(self, y2026):
        assert (_on(y2026, "dhanteras")
                <= _on(y2026, "diwali")
                < _on(y2026, "govardhan_puja")
                < _on(y2026, "bhai_dooj"))

    def test_pitru_paksha_is_a_fortnight_ending_at_mahalaya(self, y2026):
        span = _on(y2026, "mahalaya_amavasya") - _on(y2026, "pitru_paksha_begins")
        assert timedelta(days=12) <= span <= timedelta(days=16)

    def test_ganesh_festival_spans_ten_days_to_visarjan(self, y2026):
        span = _on(y2026, "anant_chaturdashi") - _on(y2026, "ganesh_chaturthi")
        assert timedelta(days=9) <= span <= timedelta(days=11)

    def test_hartalika_teej_does_not_follow_ganesh_chaturthi(self, y2026):
        # Same day in 2026: Tritiya holds at sunrise on 14 Sep and gives way
        # to Chaturthi at 07:07, which then holds all midday.
        assert _on(y2026, "hartalika_teej") <= _on(y2026, "ganesh_chaturthi")

    def test_festivals_sharing_a_tithi_share_a_date(self, y2026):
        """Guru Nanak Jayanti and Kartika Purnima are the same tithi."""
        assert _on(y2026, "guru_nanak_jayanti") == _on(y2026, "kartika_purnima")
        assert _on(y2026, "vat_savitri") == _on(y2026, "shani_jayanti")


# Published dates for New Delhi, one rule per column, across years where the
# rule decides something. Each of these was a day off under the sunrise rule
# (or appeared on two days) before the kala windows were added.
_DELHI_KNOWN = [
    # Aparahna: Dashami began at 12:50 on 20 Oct 2026, ended 14:12 next day.
    ("vijayadashami", date(2026, 10, 20)),
    # Dashami left the afternoon on 5 Oct, but Shravana held there that day.
    ("vijayadashami", date(2022, 10, 5)),
    ("vijayadashami", date(2023, 10, 24)),
    ("vijayadashami", date(2024, 10, 12)),
    ("vijayadashami", date(2025, 10, 2)),
    # Madhyahna, whole window beating a grazed one.
    ("ganesh_chaturthi", date(2023, 9, 19)),
    ("ganesh_chaturthi", date(2024, 9, 7)),
    ("ganesh_chaturthi", date(2026, 9, 14)),
    ("rama_navami", date(2024, 4, 17)),
    ("rama_navami", date(2025, 4, 6)),
    ("rama_navami", date(2026, 3, 26)),
    # Pradosh.
    ("dhanteras", date(2024, 10, 29)),
    ("dhanteras", date(2025, 10, 18)),
    ("dhanteras", date(2026, 11, 6)),
    ("holika_dahan", date(2024, 3, 24)),
    ("holika_dahan", date(2025, 3, 13)),
    ("holi", date(2024, 3, 25)),
    ("holi", date(2025, 3, 14)),
    # Amavasya held at dusk on both days; the first is kept, once.
    ("diwali", date(2025, 10, 20)),
]


@pytest.fixture(scope="module")
def delhi_years():
    years = sorted({d.year for _, d in _DELHI_KNOWN})
    slugs = sorted({s for s, _ in _DELHI_KNOWN})
    return {y: F.occurrences(y, city="New Delhi", nation="IN", slugs=slugs)
            for y in years}


class TestKalaRules:
    @pytest.mark.parametrize("slug,expected", _DELHI_KNOWN,
                             ids=[f"{s}-{d.year}" for s, d in _DELHI_KNOWN])
    def test_published_new_delhi_dates(self, delhi_years, slug, expected):
        got = [r["occurs_on"] for r in delhi_years[expected.year]
               if r["slug"] == slug]
        assert got == [expected]

    def test_dussehra_2026_is_the_20th_in_the_south_too(self):
        for city in ("Hyderabad", "Chennai", "Bengaluru"):
            rows = F.occurrences(2026, city=city, nation="IN",
                                 slugs=["vijayadashami"])
            assert [r["occurs_on"] for r in rows] == [date(2026, 10, 20)], city

    def test_no_festival_lands_on_two_consecutive_days(self):
        for year in (2024, 2025):
            rows = F.occurrences(year, city="New Delhi", nation="IN")
            seen: dict[str, list[date]] = {}
            for r in rows:
                seen.setdefault(r["slug"], []).append(r["occurs_on"])
            for slug, days in seen.items():
                for a, b in zip(days, days[1:]):
                    assert b - a > timedelta(days=1), (slug, a, b)

    def test_kala_options_are_refused_on_instant_rules(self):
        with pytest.raises(ValueError):
            F._lunar("Ashwina", "Shukla", 10, both="first")

    def test_window_rules_state_the_rule_they_use(self):
        for slug in ("vijayadashami", "ganesh_chaturthi", "rama_navami",
                     "dhanteras", "holika_dahan"):
            festival = F.FESTIVALS_BY_SLUG[slug]
            assert "not by the tithi at sunrise" in festival["observance_note"]
            assert festival["is_convention_dependent"]


# ── Self-consistency ─────────────────────────────────────────────────────────

class TestRulesAreSatisfied:
    def test_every_lunar_date_satisfies_its_own_rule(self, y2026, facts_2026):
        """The panchanga of each computed day must match the rule that chose it.

        Kshaya days are exempt by definition — the tithi is current at no
        sunrise at all, which is precisely why they needed a fallback.
        """
        by_date = {f["date"]: f for f in facts_2026}
        _, rows = y2026

        for row in rows:
            rule = row["rule"]
            if rule["type"] != "lunar_tithi":
                continue
            if rule["at"] in F._KALA_WINDOWS:
                # A window rule: the tithi must touch the chosen day's window
                # or, failing that, the day itself (sunrise to sunrise).
                fact = by_date[row["occurs_on"]]
                target = F._abs_tithi(rule["paksha"], rule["tithi"])
                nxt = by_date[row["occurs_on"] + timedelta(days=1)]
                assert (target in fact["kala"][rule["at"]]["tithis"]
                        or target in (F._abs_at(fact), F._abs_at(nxt))), row["slug"]
                continue
            fact = by_date[row["occurs_on"]]
            tithi_field, paksha_field = F._AT_FIELDS[rule.get("at", "sunrise")]
            month = fact[F._month_field(rule)]

            if fact[tithi_field] == rule["tithi"]:
                assert fact[paksha_field] == rule["paksha"], row["slug"]
                assert month == rule["month"], row["slug"]
            else:
                nxt = by_date.get(row["occurs_on"] + timedelta(days=1))
                assert nxt is not None, row["slug"]
                target = F._abs_tithi(rule["paksha"], rule["tithi"])
                before = F._abs_tithi(fact[paksha_field], fact[tithi_field])
                after = F._abs_tithi(nxt[paksha_field], nxt[tithi_field])
                assert (before + 1) % 30 == target and (after - 1) % 30 == target, (
                    f"{row['slug']} on {row['occurs_on']} matches neither the "
                    f"rule at sunrise nor a kshaya tithi"
                )

    def test_no_festival_resolves_into_an_adhika_masa(self, y2026, facts_2026):
        """Observances belong to the nija month, never the intercalary one."""
        by_date = {f["date"]: f for f in facts_2026}
        _, rows = y2026
        for row in rows:
            if row["rule"]["type"] in ("lunar_tithi", "weekday_before_tithi"):
                assert not by_date[row["occurs_on"]]["adhika"], row["slug"]

    def test_adhika_year_does_not_duplicate_jyeshtha_festivals(self, y2026):
        """2026 has an adhika Jyeshtha; each festival must still occur once."""
        _, rows = y2026
        jyeshtha = [r for r in rows
                    if r["rule"].get("month") == "Jyeshtha"]
        assert jyeshtha, "expected Jyeshtha festivals in the catalog"
        slugs = [r["slug"] for r in jyeshtha]
        assert len(slugs) == len(set(slugs))

    def test_adhika_masa_is_disclosed_on_affected_festivals(self, y2026):
        row = dict(y2026[0])["ganga_dussehra"]
        assert "adhika" in (row["observance_note"] or "")
        assert row["is_convention_dependent"] is True

    def test_sankranti_dates_disclose_the_sunset_rule(self, y2026):
        row = dict(y2026[0])["makar_sankranti"]
        assert "sunset rule" in (row["observance_note"] or "")
        assert row["is_convention_dependent"] is True


# ── Catalog integrity ────────────────────────────────────────────────────────

class TestCatalog:
    def test_slugs_are_unique(self):
        slugs = [f["slug"] for f in F.FESTIVALS]
        assert len(slugs) == len(set(slugs))
        assert len(F.FESTIVALS_BY_SLUG) == len(slugs)

    def test_both_regions_are_well_covered(self):
        def count(region):
            return sum(region in f["regions"] or F.PAN in f["regions"]
                       for f in F.FESTIVALS)
        assert count(F.NORTH) >= 30
        assert count(F.SOUTH) >= 30

    @pytest.mark.parametrize("festival", F.FESTIVALS, ids=lambda f: f["slug"])
    def test_rule_is_well_formed(self, festival):
        rule = festival["rule"]
        assert rule["type"] in F._MATCHERS
        assert festival["description"]
        assert set(festival["regions"]) <= {F.NORTH, F.SOUTH, F.PAN}

        if rule["type"] in ("lunar_tithi", "weekday_before_tithi"):
            assert rule["month"] in LUNAR_MONTHS
            assert rule["paksha"] in ("Shukla", "Krishna")
            assert 1 <= rule["tithi"] <= 15
            assert rule["reckoning"] in ("amanta", "purnimanta")
        if rule["type"] == "lunar_tithi":
            assert rule["at"] in F._AT_FIELDS or rule["at"] in F._KALA_WINDOWS
        if rule["type"] == "day_after_festival":
            assert rule["slug"] in F.FESTIVALS_BY_SLUG
        if rule["type"] == "solar_sankranti":
            assert 0 <= rule["sign"] <= 11
        if rule["type"] == "nakshatra_in_solar_month":
            assert rule["nakshatra"] in NAKSHATRAS
            assert 0 <= rule["sign"] <= 11

    def test_non_sunrise_rules_explain_themselves(self):
        """If a festival is not fixed at sunrise, the caller must be told."""
        for festival in F.FESTIVALS:
            if festival["rule"].get("at", "sunrise") != "sunrise":
                assert festival["observance_note"], festival["slug"]
                assert festival["is_convention_dependent"], festival["slug"]

    def test_amanta_purnimanta_ambiguity_is_flagged(self):
        """A note that names a naming split across the two lunar-month
        reckonings is, by definition, more than one defensible answer — the
        convention flag must say so, not just the prose."""
        for festival in F.FESTIVALS:
            note = (festival["observance_note"] or "").lower()
            if "amanta" in note and "purnimanta" in note:
                assert festival["is_convention_dependent"], festival["slug"]

    def test_catalog_rows_match_the_festivals_table(self):
        rows = F.catalog()
        assert len(rows) == len(F.FESTIVALS)
        required = {"slug", "name", "region", "tradition", "panchanga_rule"}
        assert all(required <= set(row) for row in rows)


# ── Query surface ────────────────────────────────────────────────────────────

class TestQueries:
    def test_every_festival_resolves_at_least_once_across_two_years(self):
        """A festival may skip a Gregorian year, but not two in a row."""
        seen = {r["slug"] for r in F.occurrences(2026, **CHENNAI)}
        seen |= {r["slug"] for r in F.occurrences(2027, **CHENNAI)}
        assert {f["slug"] for f in F.FESTIVALS} - seen == set()

    def test_results_are_sorted_and_carry_their_place(self, y2026):
        _, rows = y2026
        assert rows == sorted(rows, key=lambda r: (r["occurs_on"], r["slug"]))
        assert all(r["place"]["city"] == "Chennai" for r in rows)

    def test_upcoming_spans_a_year_boundary(self):
        rows = F.upcoming(date(2026, 12, 20), days=40, **CHENNAI)
        assert rows
        assert all(date(2026, 12, 20) <= r["occurs_on"] <= date(2027, 1, 29)
                   for r in rows)
        assert any(r["occurs_on"].year == 2027 for r in rows)

    def test_region_and_slug_filters(self):
        south = F.occurrences(2026, regions=[F.SOUTH], **CHENNAI)
        assert south and all(
            F.SOUTH in r["regions"] or F.PAN in r["regions"] for r in south
        )
        only = F.occurrences(2026, slugs=["diwali"], **CHENNAI)
        assert [r["slug"] for r in only] == ["diwali"]

    def test_dates_depend_on_place(self):
        """Longitude genuinely moves festival dates — that is not a bug."""
        chennai = F.occurrences(2026, slugs=["diwali", "makar_sankranti"], **CHENNAI)
        newyork = F.occurrences(2026, slugs=["diwali", "makar_sankranti"],
                                lat=40.71, lng=-74.01, tz_str="America/New_York")
        assert chennai and newyork
        assert {r["place"]["tz"] for r in newyork} == {"America/New_York"}


class TestMoonDays:
    """Full and new moon days for the widgets: the tithi at sunrise."""

    @pytest.fixture(scope="class")
    def moons(self):
        return F.moon_days(2026, **CHENNAI)

    def test_about_a_dozen_of_each_alternating(self, moons):
        full = [m for m in moons if m["moon"] == "full"]
        new = [m for m in moons if m["moon"] == "new"]
        assert 12 <= len(full) <= 13 and 12 <= len(new) <= 13
        # A kshaya or vriddhi tithi can skip or repeat a sunrise, so two of a
        # kind may sit a day apart, never further.
        for a, b in zip(moons, moons[1:]):
            if a["moon"] == b["moon"]:
                assert (b["date"] - a["date"]).days <= 2
        assert all(m["date"].year == 2026 for m in moons)

    def test_buddha_purnima_is_a_full_moon_day(self, moons, y2026):
        by_slug, _ = y2026
        full = {m["date"] for m in moons if m["moon"] == "full"}
        assert by_slug["buddha_purnima"]["occurs_on"] in full


class TestVratDays:
    """Monthly Ekadashi, Purnima, Amavasya and Pradosham for Calendar (U7)."""

    @pytest.fixture(scope="class")
    def vrats(self):
        return F.vrat_days(2026, **CHENNAI)

    def test_two_ekadashis_and_two_pradoshams_a_month(self, vrats):
        for kind in ("ekadashi", "pradosham"):
            rows = [r for r in vrats if r["kind"] == kind]
            assert 23 <= len(rows) <= 26
            assert {r["paksha"] for r in rows} == {"Shukla", "Krishna"}

    def test_moon_days_are_the_vrat_purnimas_and_amavasyas(self, vrats):
        moons = F.moon_days(2026, **CHENNAI)
        from_vrats = [(r["date"], "full" if r["kind"] == "purnima" else "new")
                      for r in vrats if r["kind"] in ("purnima", "amavasya")]
        assert [(m["date"], m["moon"]) for m in moons] == from_vrats

    def test_named_ekadashis_fall_on_a_vrat_ekadashi(self, vrats, y2026):
        _, rows = y2026
        ekadashi = {r["date"] for r in vrats if r["kind"] == "ekadashi"}
        named = [row for row in rows if row["slug"].endswith("_ekadashi")]
        assert named
        assert all(row["occurs_on"] in ekadashi for row in named)

    def test_every_kind_states_its_rule(self):
        assert set(F.VRAT_NOTES) == {"ekadashi", "purnima", "amavasya", "pradosham"}
        assert all(note.strip() for note in F.VRAT_NOTES.values())

    def test_a_skipped_tithi_still_gets_its_day(self):
        from datetime import date
        def fact(d, paksha, n):
            return {"date": date(2026, 1, d), "paksha": paksha, "tithi_number": n}
        # Sunrise jumps from Shukla 10 to Shukla 12: Ekadashi never holds at a
        # sunrise, so the day it falls inside (the 12 sunrise) is the day.
        facts = [fact(1, "Shukla", 10), fact(2, "Shukla", 12), fact(3, "Shukla", 13)]
        assert F._tithi_days(facts, "Shukla", 11) == [date(2026, 1, 2)]
        # Holding at two sunrises gives the first.
        facts = [fact(1, "Shukla", 11), fact(2, "Shukla", 11), fact(3, "Shukla", 12)]
        assert F._tithi_days(facts, "Shukla", 11) == [date(2026, 1, 1)]


def test_vrat_days_endpoint_carries_the_rule():
    from fastapi.testclient import TestClient
    from main import app
    from astrospace.api.auth import AuthUser, current_user

    app.dependency_overrides[current_user] = lambda: AuthUser(id="u", email="u@x.dev", role="dev")
    try:
        r = TestClient(app).get("/api/v1/festivals/vrat-days",
                                params={"city": "Chennai", "from_date": "2026-12-01", "days": 31})
    finally:
        app.dependency_overrides.pop(current_user, None)
    assert r.status_code == 200
    days = r.json()["days"]
    assert {d["kind"] for d in days} == {"ekadashi", "purnima", "amavasya", "pradosham"}
    assert all(d["is_convention_dependent"] and d["observance_note"] for d in days)
    assert all("2026-12-01" <= d["date"] <= "2026-12-31" for d in days)
