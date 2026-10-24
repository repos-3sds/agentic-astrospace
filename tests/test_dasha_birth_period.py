"""Sub-periods of the dasha running at birth start before birth, not at it.

The birth mahadasha began when the Moon entered its nakshatra. Its
antardashas run from that notional start in full proportion; those over at
birth are dropped and the running one is clipped to birth. Before the fix
they were squeezed into the balance, which put a child born in 2022 in
Saturn-Rahu in late 2026 instead of Saturn-Jupiter (reported against other
software for "T Viraj", 2026-10-24).

Expected dates were worked independently with Swiss Ephemeris + Lahiri and
match Jagannatha Hora's convention to within a day (it uses 365.2425-day
years; Siddha uses 365.25).
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from astrospace.core.vedic.chart import VedicChart
from astrospace.core.vedic.constants import NAKSHATRA_SPAN, VIMSHOTTARI_YEARS
from astrospace.core.vedic.dashas import vimshottari_dasha
from astrospace.core.vedic.yogini import yogini_dasha

NY = ZoneInfo("America/New_York")
AS_OF = datetime(2026, 10, 24, tzinfo=NY)


@pytest.fixture(scope="module")
def viraj():
    # 19 Apr 2022 08:54 EDT, Harrisburg PA: Moon Anuradha pada 3, 67% gone.
    return VedicChart("T Viraj", 2022, 4, 19, 8, 54,
                      lat=40.2737, lng=-76.8844, tz_str="America/New_York")


def _day(iso: str) -> str:
    return iso[:10]


def test_viraj_runs_saturn_jupiter_now(viraj):
    d = viraj.dashas(as_of=AS_OF)
    assert d["birth_nakshatra"]["name"] == "Anuradha"
    cur = d["current"]
    assert cur["mahadasha"]["lord"] == "Saturn"
    assert cur["antardasha"]["lord"] == "Jupiter"
    assert _day(cur["antardasha"]["start"]) == "2026-01-09"
    assert _day(cur["antardasha"]["end"]) == "2028-07-22"


def test_viraj_birth_mahadasha_keeps_only_the_antardashas_after_birth(viraj):
    md = viraj.dashas(as_of=AS_OF)["mahadashas"][0]
    assert md["lord"] == "Saturn"
    assert md["start"] == viraj.moment.dt_local.isoformat()
    assert _day(md["end"]) == "2028-07-22"
    rows = [(a["lord"], _day(a["start"]), _day(a["end"])) for a in md["antardashas"]]
    assert rows == [
        ("Mars", "2022-04-19", "2023-03-05"),     # clipped: began 24 Jan 2022
        ("Rahu", "2023-03-05", "2026-01-09"),
        ("Jupiter", "2026-01-09", "2028-07-22"),
    ]
    assert sum(a["years"] for a in md["antardashas"]) == pytest.approx(md["years"], abs=1e-5)


def test_viraj_next_mahadashas_are_unchanged(viraj):
    mds = viraj.dashas(as_of=AS_OF)["mahadashas"]
    assert [(m["lord"], _day(m["start"])) for m in mds[1:3]] == [
        ("Mercury", "2028-07-22"), ("Ketu", "2045-07-22"),
    ]
    assert mds[1]["antardashas"][0]["lord"] == "Mercury"


def test_clipped_antardasha_keeps_its_own_pratyantar_dates(viraj):
    mars = viraj.dashas(as_of=AS_OF)["mahadashas"][0]["antardashas"][0]
    pds = mars["pratyantardashas"]
    # Mars antar began before birth; its first pratyantars were already over.
    assert pds[0]["lord"] == "Jupiter"
    assert pds[0]["start"] == mars["start"]
    assert pds[-1]["lord"] == "Moon"
    # years are rounded to 6 places (~30 s) before pratyantars are laid out
    gap = datetime.fromisoformat(pds[-1]["end"]) - datetime.fromisoformat(mars["end"])
    assert abs(gap) < timedelta(minutes=1)


@pytest.mark.parametrize("fraction", [0.0, 0.1, 0.5, 0.9, 0.999])
def test_birth_antardashas_are_the_tail_of_the_full_sequence(fraction):
    birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
    moon = (5 + fraction) * NAKSHATRA_SPAN  # Ardra, a Rahu star
    d = vimshottari_dasha(moon, birth, birth)
    md = d["mahadashas"][0]
    assert md["lord"] == "Rahu"
    assert md["years"] == pytest.approx(18 * (1 - fraction), abs=1e-5)
    notional = birth - timedelta(days=18 * fraction * 365.25)
    full = ["Rahu", "Jupiter", "Saturn", "Mercury", "Ketu", "Venus", "Sun", "Moon", "Mars"]
    ends, cursor = [], notional
    for lord in full:
        cursor += timedelta(days=18 * VIMSHOTTARI_YEARS[lord] / 120 * 365.25)
        ends.append((lord, cursor))
    expected = [(lord, end) for lord, end in ends if end > birth]
    got = [(a["lord"], datetime.fromisoformat(a["end"])) for a in md["antardashas"]]
    assert [g[0] for g in got] == [e[0] for e in expected]
    for (_, g), (_, e) in zip(got, expected):
        assert abs(g - e) < timedelta(seconds=1)
    assert md["antardashas"][0]["start"] == birth.isoformat()


def test_nothing_is_active_before_birth():
    birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
    d = vimshottari_dasha(100.0, birth, birth - timedelta(days=30))
    assert d["current"]["mahadasha"] is None


def test_viraj_yogini_birth_period(viraj):
    y = viraj.yogini_dashas()
    md = y["mahadashas"][0]
    assert md["yogini"] == "Bhramari"  # Anuradha (17): (17 + 3) % 8 = 4
    assert _day(md["end"]) == "2023-08-13"
    # Bhramari's antars from 13 Aug 2019: Bhramari..Siddha over before birth.
    assert [a["yogini"] for a in md["antardashas"]] == ["Sankata", "Mangala", "Pingala", "Dhanya"]
    assert md["antardashas"][0]["start"] == md["start"]
    assert _day(md["antardashas"][0]["end"]) == "2022-12-13"
    assert y["mahadashas"][1]["yogini"] == "Bhadrika"
    assert _day(y["mahadashas"][1]["start"]) == "2023-08-13"


def test_yogini_balance_still_matches_the_first_period():
    birth = datetime(2000, 1, 1, tzinfo=timezone.utc)
    y = yogini_dasha(0.5 * NAKSHATRA_SPAN, birth, birth)  # Ashwini half gone
    md = y["mahadashas"][0]
    assert md["years"] == pytest.approx(y["birth_nakshatra"]["balance_years"], abs=1e-5)
    assert sum(a["years"] for a in md["antardashas"]) == pytest.approx(md["years"], abs=1e-5)
