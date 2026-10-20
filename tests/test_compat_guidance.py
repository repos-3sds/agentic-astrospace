"""Plain couple guidance built from a Gun Milan result (compatibility_guidance.py).

The case that asked for it: a married tester whose report read Yoni 0/4,
Gana 1/6 (Deva with Rakshasa), Tara 1.5/3 and Vashya 1/2, with every term
left for the reader to decode.
"""
from __future__ import annotations

import re

from astrospace.core.vedic.compatibility import gun_milan
from astrospace.core.vedic.compatibility_guidance import (
    MAX_FOCUS_AREAS,
    couple_guidance,
)
from tests.test_dashakoota import StubChart


def _row(label, points, max_points, note="", verified=True):
    return {"label": label, "points": points, "max": max_points, "note": note, "verified": verified}


def _married_tester_result(**overrides) -> dict:
    result = {
        "rows": [
            _row("Varna", 1, 1, "Brahmin with Kshatriya"),
            _row("Vashya", 1, 2, "Manava with Chatushpada", verified=False),
            _row("Tara", 1.5, 3, "Jyeshtha ↔ Moola"),
            _row("Yoni", 0, 4, "Deer with Dog; sworn enemy"),
            _row("Graha Maitri", 5, 5, "Mars with Jupiter"),
            _row("Gana", 1, 6, "Deva with Rakshasa"),
            _row("Bhakoot", 7, 7, "Scorpio 2/12 Sagittarius; bhakoot dosha cancelled", verified=False),
            _row("Nadi", 8, 8, "Antya with Aadi"),
        ],
        "profiles": {
            "person1": {"name": "Kamalesh", "rashi": "Scorpio", "rashi_lord": "Mars", "gana": "Rakshasa"},
            "person2": {"name": "Sai Madhuri", "rashi": "Sagittarius", "rashi_lord": "Jupiter", "gana": "Deva"},
        },
        "safety_checks": {"manglik": {"match": True}},
        "dashakoota_extension": {"hard_blockers": []},
        "observance_note": "Traditions differ.",
    }
    result.update(overrides)
    return result


def _plain_text(guidance: dict) -> str:
    """Everything shown outside the "Why this?" fold."""
    parts = [guidance["closing_note"]]
    for item in guidance["strengths"]:
        parts += [item["area"], item["line"]]
    for item in guidance["focus_areas"]:
        parts += [item["area"], item["meaning"], *item["together"]]
    for person in guidance["for_each"]:
        parts.append(person["temperament"] or "")
    return " ".join(parts)


class TestFocusAreas:
    def test_weakest_kootas_come_first(self):
        guidance = couple_guidance(_married_tester_result())
        assert [item["key"] for item in guidance["focus_areas"]] == ["yoni", "gana", "vashya", "tara"]

    def test_full_score_kootas_are_strengths_not_focus(self):
        guidance = couple_guidance(_married_tester_result())
        assert {item["key"] for item in guidance["strengths"]} == {"varna", "graha_maitri", "bhakoot", "nadi"}

    def test_capped_so_the_screen_stays_short(self):
        result = _married_tester_result()
        for row in result["rows"]:
            row["points"] = 0
        assert len(couple_guidance(result)["focus_areas"]) == MAX_FOCUS_AREAS

    def test_flags_rank_ahead_of_kootas(self):
        result = _married_tester_result(
            safety_checks={"manglik": {"match": False}},
            dashakoota_extension={"hard_blockers": ["Rajju"]},
        )
        keys = [item["key"] for item in couple_guidance(result)["focus_areas"]]
        assert keys[:2] == ["rajju", "manglik"]

    def test_both_manglik_is_not_a_focus_area(self):
        keys = [item["key"] for item in couple_guidance(_married_tester_result())["focus_areas"]]
        assert "manglik" not in keys

    def test_every_focus_area_says_what_to_do_together(self):
        for item in couple_guidance(_married_tester_result())["focus_areas"]:
            assert item["together"], item["key"]
            assert item["why"], item["key"]


class TestForEachOfYou:
    def test_temperament_and_moon_sign_lord_practice_per_person(self):
        first, second = couple_guidance(_married_tester_result())["for_each"]
        assert first["name"] == "Kamalesh"
        assert "strong-willed" in first["temperament"]
        assert first["practice"]["day"] == "Tuesday"
        assert "Om Angarakaya Namah" in first["practice"]["instructions"]
        assert second["name"] == "Sai Madhuri"
        assert "gentle" in second["temperament"]
        assert second["practice"]["day"] == "Thursday"

    def test_missing_profile_degrades_without_inventing(self):
        first, _ = couple_guidance(_married_tester_result(profiles={}))["for_each"]
        assert first["practice"] is None and first["temperament"] is None


class TestPlainAndGentle:
    def test_terms_stay_under_the_why_fold(self):
        text = _plain_text(couple_guidance(_married_tester_result(
            safety_checks={"manglik": {"match": False}},
            dashakoota_extension={"hard_blockers": ["Rajju", "Vedha"]},
        )))
        for term in ("koota", "Varna", "Vashya", "Tara", "Yoni", "Graha Maitri", "Gana", "Bhakoot",
                     "Nadi", "Rajju", "Vedha", "Manglik", "nakshatra", "dosha"):
            assert term.lower() not in text.lower(), term

    def test_no_fear_words(self):
        result = _married_tester_result(
            safety_checks={"manglik": {"match": False}},
            dashakoota_extension={"hard_blockers": ["Rajju", "Vedha"]},
        )
        for row in result["rows"]:
            row["points"] = 0
        text = _plain_text(couple_guidance(result)).lower()
        for word in ("death", "die", "divorce", "danger", "doom", "disaster", "curse", "bad luck",
                     "separation", "widow", "illness", "disease"):
            assert not re.search(rf"\b{word}\b", text), word

    def test_practices_are_free(self):
        result = _married_tester_result(safety_checks={"manglik": {"match": False}})
        for row in result["rows"]:
            row["points"] = 0
        guidance = couple_guidance(result)
        practices = [item["practice"] for item in guidance["focus_areas"] if item["practice"]]
        practices += [person["practice"] for person in guidance["for_each"] if person["practice"]]
        for practice in practices:
            text = practice["instructions"].lower()
            assert "₹" not in text and "gem" not in text and "buy" not in text

    def test_convention_dependent_carries_the_note(self):
        guidance = couple_guidance(_married_tester_result())
        assert guidance["is_convention_dependent"] is True
        assert guidance["observance_note"] == "Traditions differ."


class TestGunMilanCarriesGuidance:
    def test_gun_milan_includes_guidance(self):
        result = gun_milan(StubChart("A", "Ashwini"), StubChart("B", "Bharani"))
        assert set(result["guidance"]) >= {"strengths", "focus_areas", "for_each", "closing_note"}
        assert [p["name"] for p in result["guidance"]["for_each"]] == ["A", "B"]

    def test_varna_note_is_not_garbled(self):
        result = gun_milan(StubChart("A", "Ashwini"), StubChart("B", "Bharani"))
        varna = next(row for row in result["rows"] if row["label"] == "Varna")
        assert varna["note"] == "Brahmin (groom's side) with Brahmin"

    def test_manglik_note_explains_itself(self):
        note = gun_milan(StubChart("A", "Ashwini"), StubChart("B", "Bharani"))["safety_checks"]["manglik"]["note"]
        assert note not in ("Both Manglik", "Both non-Manglik")
        assert len(note.split()) > 5
