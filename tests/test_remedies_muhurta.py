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

def _positions(**lons):
    return {planet: {"lon": lon} for planet, lon in lons.items()}


# Synthetic chart with no active dasha, no dosha, no debilitation, no
# combustion — every planet sits in a bland, unremarkable placement.
NO_REMEDY_POSITIONS = _positions(
    Sun=10.0, Moon=50.0, Mars=160.0, Mercury=200.0, Jupiter=130.0,
    Saturn=230.0, Rahu=280.0, Ketu=100.0, Venus=250.0,
)
NO_REMEDY_LAGNA = 15.0

# Same base chart with Saturn moved into Aries (its debilitation sign,
# 7th from Libra 20° exaltation) — isolates the "debilitated planet" path.
# 29° keeps it well outside Saturn's 15° combustion orb from the Sun at 10°.
DEBILITATED_POSITIONS = {**NO_REMEDY_POSITIONS, "Saturn": {"lon": 29.0}}

# Same base chart with Mercury moved to 5° from the Sun (well inside its
# 14° combustion orb) — isolates the "combust planet" path.
COMBUST_POSITIONS = {**NO_REMEDY_POSITIONS, "Mercury": {"lon": 15.0}}

# Mars exalted in Capricorn, also in house 1 from Lagna and house 7 from
# Moon — two active references (severity "moderate") but Mars is in its own
# exception sign, so the classical cancellation rule downgrades net_severity
# to "mild". Isolates manglik + its cancellation ladder. Moon sits 13.5°
# from the Sun — outside its 12° combustion orb — so combustion stays inert.
MANGLIK_CANCELLED_POSITIONS = _positions(
    Sun=100.0, Moon=113.5, Mars=298.0, Mercury=200.0, Jupiter=140.0,
    Venus=40.0, Saturn=320.0, Rahu=10.0, Ketu=190.0,
)
MANGLIK_CANCELLED_LAGNA = 280.0


class TestRemedies:
    def test_detects_afflictions_for_reference_chart(self, chart):
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        assert found, "reference chart should surface at least one affliction"
        assert {f["kind"] for f in found} <= {"dasha", "dosha", "dignity", "combustion"}

    def test_active_mahadasha_lord_is_listed_first(self, chart):
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        current = chart["dasha"]["current"]
        assert found[0]["kind"] == "dasha"
        assert found[0]["level"] == "mahadasha"
        assert found[0]["planet"] == current["mahadasha"]["lord"]
        assert found[0]["evidence"]["start"] == current["mahadasha"]["start"]
        assert found[0]["source_status"] == "verified_common"

    def test_active_antardasha_lord_is_surfaced(self, chart):
        found = remedies.afflictions(chart["positions"], chart["lagna"], chart["dasha"])
        current = chart["dasha"]["current"]
        antardasha_items = [f for f in found if f["kind"] == "dasha" and f["level"] == "antardasha"]
        assert antardasha_items, "reference chart's antardasha lord should surface a remedy trigger"
        assert antardasha_items[0]["planet"] == current["antardasha"]["lord"]
        assert antardasha_items[0]["evidence"]["end"] == current["antardasha"]["end"]

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
        found = remedies.afflictions(
            chart["positions"], chart["lagna"], chart["dasha"], include_manglik=True
        )
        for item in found:
            if item["kind"] == "dosha":
                assert item["framing"] == "This is a flag, not a verdict."

    def test_debilitated_planet_triggers_dignity_remedy(self):
        found = remedies.afflictions(DEBILITATED_POSITIONS, NO_REMEDY_LAGNA)
        dignity_items = [f for f in found if f["kind"] == "dignity"]
        assert len(dignity_items) == 1
        item = dignity_items[0]
        assert item["planet"] == "Saturn"
        assert item["evidence"]["dignity"] == "Debilitated"
        assert item["evidence"]["sign"] == "Aries"
        assert item["source_status"] == "verified_common"

        out = remedies.recommend(DEBILITATED_POSITIONS, NO_REMEDY_LAGNA)
        assert out["count"] == 1
        assert out["groups"][0]["recommendation_id"] == "dignity-debilitated-saturn"
        assert out["groups"][0]["trigger"] == {"kind": "dignity", "planet": "Saturn"}

    def test_combust_planet_triggers_combustion_remedy(self):
        found = remedies.afflictions(COMBUST_POSITIONS, NO_REMEDY_LAGNA)
        combustion_items = [f for f in found if f["kind"] == "combustion"]
        assert len(combustion_items) == 1
        item = combustion_items[0]
        assert item["planet"] == "Mercury"
        assert item["evidence"]["active"] is True
        assert item["source_status"] == "convention_dependent"

        out = remedies.recommend(COMBUST_POSITIONS, NO_REMEDY_LAGNA)
        assert out["count"] == 1
        assert out["groups"][0]["recommendation_id"] == "combustion-mercury"

    def test_no_remedy_profile_returns_supportive_empty_state(self):
        found = remedies.afflictions(NO_REMEDY_POSITIONS, NO_REMEDY_LAGNA)
        assert found == []

        out = remedies.recommend(NO_REMEDY_POSITIONS, NO_REMEDY_LAGNA)
        assert out["groups"] == []
        assert out["count"] == 0
        assert out["note"] == "Nothing in your chart is asking for a remedy right now."

    def test_manglik_excluded_by_default(self):
        """Manglik is a compatibility flag, never a generic remedy card (US-PR-003)."""
        found = remedies.afflictions(MANGLIK_CANCELLED_POSITIONS, MANGLIK_CANCELLED_LAGNA)
        assert not [f for f in found if f.get("dosha") == "manglik"]

        out = remedies.recommend(MANGLIK_CANCELLED_POSITIONS, MANGLIK_CANCELLED_LAGNA)
        assert out["groups"] == []
        assert not [g for g in out["groups"] if g["trigger"].get("dosha") == "manglik"]

    def test_manglik_cancellation_surfaces_when_explicitly_included(self):
        found = remedies.afflictions(
            MANGLIK_CANCELLED_POSITIONS, MANGLIK_CANCELLED_LAGNA, include_manglik=True
        )
        manglik_items = [f for f in found if f.get("dosha") == "manglik"]
        assert len(manglik_items) == 1
        item = manglik_items[0]
        assert item["evidence"]["severity"] == "moderate"
        assert item["evidence"]["net_severity"] == "mild"
        assert item["cancelled"] is True
        assert item["framing"] == "This is a flag, not a verdict."

        out = remedies.recommend(
            MANGLIK_CANCELLED_POSITIONS, MANGLIK_CANCELLED_LAGNA, include_manglik=True
        )
        assert out["count"] == 1
        group = out["groups"][0]
        assert group["recommendation_id"] == "dosha-manglik"
        assert group["trigger"] == {"kind": "dosha", "planet": "Mars", "dosha": "manglik"}
        assert "flag, not a verdict" in group["safety_note"]

    def test_recommendations_are_grouped_and_disclaimed(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        assert out["count"] == len(out["groups"])
        assert "not a guarantee" in out["disclaimer"]
        # never medical/legal/financial advice
        assert "qualified professional" in out["disclaimer"]
        for group in out["groups"]:
            assert group["recommendation_id"]
            assert group["trigger"]["kind"]
            assert group["reason_short"]
            assert group["reason_practitioner"]
            assert group["evidence"] is not None
            assert group["source_status"]
            assert group["tradition_source"]
            assert group["convention_dependent"] is True
            assert group["safety_note"]
            assert group["priority"] >= 1
            assert group["practices"]
            for practice in group["practices"]:
                assert practice["practice_slug"]
                assert practice["type"]
                assert practice["is_convention_dependent"] is True
                assert practice["tradition_source"]

    def test_priority_matches_detection_order(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        priorities = [g["priority"] for g in out["groups"]]
        assert priorities == list(range(1, len(priorities) + 1))
        # Dasha triggers (most actionable) always outrank later kinds.
        dasha_priorities = [g["priority"] for g in out["groups"] if g["trigger"]["kind"] == "dasha"]
        other_priorities = [g["priority"] for g in out["groups"] if g["trigger"]["kind"] != "dasha"]
        if dasha_priorities and other_priorities:
            assert max(dasha_priorities) < min(other_priorities)

    def test_gemstones_can_be_excluded(self, chart):
        lean = remedies.recommend(
            chart["positions"], chart["lagna"], dasha=chart["dasha"], include_costly=False
        )
        types = {r["type"] for g in lean["groups"] for r in g["practices"]}
        assert "gem" not in types

    def test_gemstones_are_marked_optional_when_included(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        gems = [r for g in out["groups"] for r in g["practices"] if r["type"] == "gem"]
        assert gems, "reference chart should offer at least one gem"
        for gem in gems:
            assert gem["optional_cost"] is True
            assert "Optional" in gem["instructions"]

    def test_mantra_practice_carries_audio_metadata(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        mantras = [r for g in out["groups"] for r in g["practices"] if r["type"] == "mantra"]
        assert mantras
        for mantra in mantras:
            assert mantra["target_count"] == 108
            assert mantra["preferred_day"]
            audio = mantra["audio"]
            assert audio["text"]
            assert audio["count_target"] == 108
            # No real audio assets exist yet — the contract says so honestly
            # rather than fabricating a path.
            assert audio["audio_url"] is None
            assert audio["source_status"] == "pending_assets"

    def test_no_duplicate_affliction_groups(self, chart):
        out = remedies.recommend(chart["positions"], chart["lagna"], dasha=chart["dasha"])
        keys = [g["recommendation_id"] for g in out["groups"]]
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
        out = remedies.recommend(
            chart["positions"], chart["lagna"], dasha=chart["dasha"], include_manglik=True
        )

        content: list[str] = []
        for group in out["groups"]:
            content += [group["reason_short"], group["reason_practitioner"]]
            for remedy in group["practices"]:
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
