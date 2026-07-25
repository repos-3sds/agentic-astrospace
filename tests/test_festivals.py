"""Tests for the Hindu festival calendar.

The valuable assertions here are the *anchors*: a handful of 2026 dates that
are independently known, chosen because each one breaks a different way if a
rule is wrong. Maha Shivaratri catches nishita-vs-sunrise, Diwali catches
pradosh, Holi catches amanta-vs-purnimanta, Ugadi catches kshaya tithi, and
Pongal catches the Sankranti sunset rule. Every one of those started out wrong.

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
        ("holika_dahan", date(2026, 3, 3), "Phalguna Purnima"),
        ("holi", date(2026, 3, 4), "purnimanta Chaitra Krishna Pratipada"),
        ("ugadi", date(2026, 3, 19), "kshaya tithi — Pratipada touches no sunrise"),
        ("tulsi_vivah", date(2026, 11, 21), "kshaya tithi — Dwadashi is skipped"),
        ("makar_sankranti", date(2026, 1, 14), "Sankranti before sunset"),
        ("tamil_puthandu", date(2026, 4, 14), "Mesha ingress before sunset"),
        ("krishna_janmashtami", date(2026, 9, 4), "amanta Shravana Krishna Ashtami"),
        ("ganesh_chaturthi", date(2026, 9, 15), "Bhadrapada Shukla Chaturthi"),
        ("vijayadashami", date(2026, 10, 21), "Ashwina Shukla Dashami"),
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

    def test_hartalika_teej_precedes_ganesh_chaturthi(self, y2026):
        assert _on(y2026, "hartalika_teej") < _on(y2026, "ganesh_chaturthi")

    def test_festivals_sharing_a_tithi_share_a_date(self, y2026):
        """Guru Nanak Jayanti and Kartika Purnima are the same tithi."""
        assert _on(y2026, "guru_nanak_jayanti") == _on(y2026, "kartika_purnima")
        assert _on(y2026, "vat_savitri") == _on(y2026, "shani_jayanti")


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
            assert rule["at"] in F._AT_FIELDS
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
