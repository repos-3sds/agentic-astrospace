"""Tests for the remedy engine and the goal-based muhurta finder.

Beyond the mechanics, these lock in the safety rules from
design_principles.md §4 — no fear framing, no guarantees, dosha cancellations
surfaced, and health/legal/financial intents referred out rather than timed.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest
import swisseph as swe

from astrospace.core.vedic import muhurta, remedies
from astrospace.core.vedic.constants import NAKSHATRAS
from astrospace.core.vedic.dashas import vimshottari_dasha
from astrospace.core.vedic.nakshatra import nakshatra_of
from astrospace.core.vedic.positions import (
    sidereal_lagna,
    sidereal_positions,
    sign_index,
)

# Reference chart: 14 Aug 1991, 06:12 IST, Vijayawada (16.51N, 80.63E).
BIRTH_JD = swe.julday(1991, 8, 14, 6 - 5.5 + 12 / 60)
BIRTH_DT = datetime(1991, 8, 14, 6, 12)
LAT, LNG = 16.51, 80.63


@pytest.fixture(scope="module")
def chart():
    positions = sidereal_positions(BIRTH_JD)
    moon = positions["Moon"]["lon"]
    return {
        "positions": positions,
        "lagna": sidereal_lagna(BIRTH_JD, LAT, LNG),
        "moon": moon,
        "nak_index": NAKSHATRAS.index(nakshatra_of(moon)["name"]),
        "rashi_index": sign_index(moon),
        "dasha": vimshottari_dasha(moon, BIRTH_DT, as_of=datetime(2026, 7, 25)),
    }


# ── Remedies ─────────────────────────────────────────────────────────────────

class TestRemedies:
    def test_detects_afflictions_for_reference_chart(self, chart):
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        assert found, "reference chart should surface at least one affliction"
        assert {f["kind"] for f in found} <= {"dasha", "dosha", "dignity", "combustion"}

    def test_active_dasha_lords_are_listed_first(self, chart):
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        current = chart["dasha"]["current"]
        assert found[0]["kind"] == "dasha"
        assert found[0]["planet"] == current["mahadasha"]["lord"]

    def test_sun_is_never_reported_combust(self, chart):
        """Combustion is proximity *to* the Sun — the Sun cannot be combust."""
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        assert not [
            f for f in found if f["kind"] == "combustion" and f["planet"] == "Sun"
        ]

    def test_severity_never_escalates_beyond_moderate(self, chart):
        """The product informs; it does not alarm."""
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        assert {f["severity"] for f in found} <= {"mild", "moderate"}

    def test_doshas_carry_flag_not_verdict_framing(self, chart):
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        for item in found:
            if item["kind"] == "dosha":
                assert item["framing"] == "This is a flag, not a verdict."

    def test_recommendations_are_grouped_and_disclaimed(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        assert out["count"] == len(out["groups"])
        assert "not a guarantee" in out["disclaimer"]
        # never medical/legal/financial advice
        assert "qualified professional" in out["disclaimer"]
        for group in out["groups"]:
            assert group["remedies"]
            for remedy in group["remedies"]:
                assert remedy["is_convention_dependent"] is True
                assert remedy["tradition_source"]

    def test_gemstones_can_be_excluded(self, chart):
        lean = remedies.recommend(
            chart["positions"], chart["lagna"], dasha=chart["dasha"], include_costly=False
        )
        types = {r["remedy_type"] for g in lean["groups"] for r in g["remedies"]}
        assert "gem" not in types

    def test_gemstones_are_marked_optional_when_included(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        gems = [r for g in out["groups"] for r in g["remedies"] if r["remedy_type"] == "gem"]
        assert gems, "reference chart should offer at least one gem"
        for gem in gems:
            assert gem["optional_cost"] is True
            assert "Optional" in gem["instructions"]

    def test_no_duplicate_affliction_groups(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        keys = [
            (g["affliction"]["kind"], g["affliction"].get("planet"),
             g["affliction"].get("dosha"))
            for g in out["groups"]
        ]
        assert len(keys) == len(set(keys))

    def test_limit_caps_groups(self, chart):
        out = remedies.recommend(
            chart["positions"], chart["lagna"], dasha=chart["dasha"], limit=2
        )
        assert out["count"] <= 2

    def test_catalog_shape_matches_remedies_table(self):
        rows = remedies.catalog()
        assert len(rows) == len(remedies.GRAHA_REMEDIES) * 5
        required = {
            "slug", "title", "remedy_type", "instructions", "applies_to",
            "tradition_source", "cadence", "is_convention_dependent", "language",
        }
        assert all(required <= set(row) for row in rows)
        assert len({r["slug"] for r in rows}) == len(rows), "slugs must be unique"

    def test_no_fear_language_in_user_facing_content(self, chart):
        """Guards design_principles.md §4 — remedies are never sold on fear.

        Scoped to the content the user reads as advice (reasons, titles,
        instructions). The disclaimer is excluded on purpose: it legitimately
        contains negated phrasing such as "never as a fix you must buy", which
        a naive substring scan would flag.
        """
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])

        content: list[str] = []
        for group in out["groups"]:
            affliction = group["affliction"]
            content += [affliction.get("reason", ""), affliction.get("theme", "")]
            for remedy in group["remedies"]:
                content += [remedy["title"], remedy["instructions"]]
        blob = " ".join(content).lower()

        for banned in ("disaster", "danger", "curse", "doom", "death",
                       "suffer", "guaranteed", "will fail", "must buy"):
            assert banned not in blob, f"fear/guarantee language leaked: {banned}"


# ── Muhurta ──────────────────────────────────────────────────────────────────

class TestMuhurta:
    def _find(self, chart, goal="sign_contract", start=date(2026, 7, 26),
              end=date(2026, 8, 10), **kw):
        return muhurta.find(
            goal, start, end,
            janma_nakshatra_index=chart["nak_index"],
            janma_rashi_index=chart["rashi_index"],
            city="Vijayawada", nation="IN", **kw,
        )

    def test_returns_ranked_windows(self, chart):
        out = self._find(chart)
        assert out["results"], "expected at least one window over two weeks"
        scores = [r["score"] for r in out["results"]]
        assert scores == sorted(scores, reverse=True), "results must be rank-ordered"

    def test_every_result_explains_itself(self, chart):
        for result in self._find(chart)["results"]:
            assert result["why"]["supports"] or result["why"]["against"]
            assert result["quality"] in {"best", "good", "workable"}
            assert result["duration_minutes"] >= 20

    def test_windows_are_trimmed_clear_of_inauspicious_ones(self, chart):
        """A trimmed window must not overlap what it was trimmed away from."""
        out = self._find(chart)
        trimmed = [r for r in out["results"] if r["trimmed"]]
        assert trimmed, "expected at least one trimmed window in this range"
        for result in trimmed:
            assert result["start_iso"] < result["end_iso"]
            assert any("Trimmed to avoid" in a for a in result["why"]["against"])

    def test_amrit_kalam_base_matches_despite_nakshatra_suffix(self):
        """Windows arrive as 'Amrit Kalam (Uttara Ashadha)' — prefix match."""
        assert muhurta._base_for("Amrit Kalam (Uttara Ashadha)") == 32
        assert muhurta._base_for("Abhijit Muhurta") == 34
        assert muhurta._base_for("Something Unknown") == 18

    @pytest.mark.parametrize("goal", sorted(muhurta.GOALS))
    def test_all_catalog_goals_run(self, chart, goal):
        out = self._find(chart, goal=goal, end=date(2026, 8, 3))
        assert out["goal"] == goal
        assert out["days_scanned"] > 0

    @pytest.mark.parametrize("intent,domain", [
        ("medical_treatment", "health"),
        ("surgery", "health"),
        ("litigation", "legal"),
        ("court_case", "legal"),
        ("investment", "financial"),
    ])
    def test_excluded_intents_refer_out(self, chart, intent, domain):
        """Health/legal/financial are referred out, never timed."""
        with pytest.raises(muhurta.ExcludedGoalError) as exc:
            self._find(chart, goal=intent)
        assert exc.value.domain == domain

    def test_rejects_inverted_range(self, chart):
        with pytest.raises(ValueError, match="must not be before"):
            self._find(chart, start=date(2026, 8, 10), end=date(2026, 7, 1))

    def test_rejects_oversized_range(self, chart):
        with pytest.raises(ValueError, match="Range too large"):
            self._find(chart, start=date(2026, 1, 1), end=date(2026, 12, 31))

    def test_rejects_unknown_goal(self, chart):
        with pytest.raises(ValueError, match="Unknown goal"):
            self._find(chart, goal="nonsense")

    def test_disclaimer_disclaims_outcome_and_scope(self, chart):
        out = self._find(chart)
        assert "decision" in out["disclaimer"]
        assert "qualified professional" in out["disclaimer"]
        assert out["is_convention_dependent"] is True

    def test_goal_catalog_shape_matches_muhurta_goals_table(self):
        rows = muhurta.goal_catalog()
        assert {"slug", "label", "description", "rules", "is_active"} <= set(rows[0])
        assert len({r["slug"] for r in rows}) == len(rows)
        assert set(muhurta.GOALS) == {r["slug"] for r in rows}
