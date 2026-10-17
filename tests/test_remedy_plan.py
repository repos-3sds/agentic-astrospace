"""Personal remedy plan: two or three remedies, chosen from the running
period and the life area it points at, with texts from the mantra corpus."""
from __future__ import annotations

import itertools
import re
from datetime import datetime

import pytest
import swisseph as swe

from astrospace.core.vedic import remedy_plan as rp
from astrospace.core.vedic.constants import PLANETS
from astrospace.core.vedic.dashas import vimshottari_dasha
from astrospace.core.vedic.positions import sidereal_lagna, sidereal_positions

BIRTH_JD = swe.julday(1991, 8, 14, 6 - 5.5 + 12 / 60)
BIRTH_DT = datetime(1991, 8, 14, 6, 12)


@pytest.fixture(scope="module")
def chart():
    positions = sidereal_positions(BIRTH_JD)
    return {
        "positions": positions,
        "lagna": sidereal_lagna(BIRTH_JD, 16.51, 80.63),
        "dasha": vimshottari_dasha(positions["Moon"]["lon"], BIRTH_DT, as_of=datetime(2026, 7, 25)),
    }


def _dasha(md, ad):
    return {"current": {"mahadasha": {"lord": md, "start": "2020-01-01", "end": "2039-01-01"},
                        "antardasha": {"lord": ad, "start": "2025-01-01", "end": "2027-01-01"}}}


BLAND = {p: {"lon": lon} for p, lon in dict(
    Sun=10.0, Moon=50.0, Mars=160.0, Mercury=200.0, Jupiter=130.0,
    Saturn=230.0, Rahu=280.0, Ketu=100.0, Venus=250.0).items()}

FORBIDDEN = re.compile(r"\b(death|die|longevity|disease|illness|cure|wealth guaranteed)\b", re.I)


def _texts(plan):
    for g in plan["groups"]:
        yield g["reason_short"]
        yield g["reason_practitioner"]
        yield g.get("observance_note") or ""
        for p in g["practices"]:
            yield p["instructions"]
            yield p.get("observance_note") or ""


def test_plan_is_two_or_three_for_reference_chart(chart):
    plan = rp.remedy_plan(chart["positions"], chart["lagna"], chart["dasha"])
    assert 2 <= plan["count"] <= 3 == rp.MAX_REMEDIES
    assert [g["slot"] for g in plan["groups"]][:2] == ["period", "life_area"]
    assert [g["priority"] for g in plan["groups"]] == list(range(1, plan["count"] + 1))


@pytest.mark.parametrize("md,ad", list(itertools.product(PLANETS, PLANETS)))
def test_every_dasha_pair_gets_a_short_open_mantra_in_three_scripts(md, ad):
    plan = rp.remedy_plan(BLAND, 15.0, _dasha(md, ad))
    assert 1 <= plan["count"] <= 3
    ids = [g["practices"][0]["mantra_id"] for g in plan["groups"]]
    assert len(ids) == len(set(ids)), "no mantra twice"
    for g in plan["groups"]:
        assert len(g["practices"]) == 1
        p = g["practices"][0]
        entry = rp.corpus()[p["mantra_id"]]
        assert entry["tier"] == "simple"
        assert p["mantra_id"] not in ("santana-gopala", "durga-navarna")
        assert all(p["text"][k] for k in ("te", "en", "sa", "iast"))
        assert re.search("[ఀ-౿]", p["text"]["te"])
        assert re.search("[ऀ-ॿ]", p["text"]["sa"])
        assert p["optional_cost"] is False
        assert g["safety_note"] and g["tradition_source"]
    for text in _texts(plan):
        assert not FORBIDDEN.search(text), text


def test_period_follows_bphs_and_names_the_fuller_text():
    # BPHS ch.52: Sun-Mercury -> Vishnu Sahasranama; counted as the Rama-nama verse.
    g = rp.remedy_plan(BLAND, 15.0, _dasha("Sun", "Mercury"))["groups"][0]
    p = g["practices"][0]
    assert p["mantra_id"] == "rama-nama-sahasranama-tulya"
    assert p["fuller_practice"]["mantra_id"] == "vishnu-sahasranama"
    assert "ch.52" in g["tradition_source"]
    assert g["convention_dependent"] is False


def test_period_without_a_bphs_mantra_uses_the_sub_period_lord():
    g = rp.remedy_plan(BLAND, 15.0, _dasha("Sun", "Moon"))["groups"][0]
    assert g["practices"][0]["mantra_id"] == "moon-nama"
    assert g["convention_dependent"] is True and g["observance_note"]


def test_life_area_comes_from_where_the_lords_sit_and_rule():
    # Lagna Aries. Saturn at 230 (Scorpio) sits in the 8th and rules 10/11;
    # Jupiter at 130 (Leo) sits in the 5th and rules 9/12.
    areas = rp.main_life_area(BLAND, 15.0, "Jupiter", "Saturn")
    assert areas[0]["house"] == 8 and areas[0]["score"] == 3
    plan = rp.remedy_plan(BLAND, 15.0, _dasha("Jupiter", "Saturn"))
    area = next(g for g in plan["groups"] if g["slot"] == "life_area")
    assert area["house"] == 8 and area["domain"] == "inner"
    assert "health" not in area["domain_label"].lower()


def test_flag_only_when_present():
    assert [g["slot"] for g in rp.remedy_plan(BLAND, 15.0, _dasha("Venus", "Venus"))["groups"]] \
        == ["period", "life_area"]
    debilitated = {**BLAND, "Saturn": {"lon": 29.0}}
    plan = rp.remedy_plan(debilitated, 15.0, _dasha("Venus", "Saturn"))
    flag = plan["groups"][-1]
    assert flag["slot"] == "flag" and flag["recommendation_id"] == "dignity-debilitated-saturn"
    assert "flag, not a verdict" in flag["safety_note"]


def test_no_dasha_still_returns_a_supportive_result():
    plan = rp.remedy_plan(BLAND, 15.0, None)
    assert plan["count"] == len(plan["groups"]) <= 1
    assert "not a guarantee" in plan["disclaimer"]


def test_recorded_mantra_gets_a_public_audio_url(monkeypatch):
    rp.recordings.cache_clear()
    monkeypatch.setattr(rp, "recordings", lambda: {"sun-nama": {
        "file": "mantras/sun-nama.mp3", "voice_start": 1.5, "voice_seconds": 6.2, "seconds": 10.2,
    }})
    monkeypatch.setenv("ASTROSPACE_PUBLIC_AUDIO_BASE", "https://example.test/audio/")
    sun = rp.corpus()["sun-nama"]
    block = rp._audio_block(sun, 108)
    assert block["audio_url"] == "https://example.test/audio/mantras/sun-nama.mp3"
    assert block["source_status"] == "tts_recitation"
    assert block["voice_start"] == 1.5 and block["voice_seconds"] == 6.2
    # Unrecorded mantras keep saying so rather than pointing at nothing.
    other = next(m for k, m in rp.corpus().items() if k != "sun-nama")
    assert rp._audio_block(other, 108)["audio_url"] is None
