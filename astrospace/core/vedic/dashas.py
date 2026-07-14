"""Vimshottari dasha calculations from the Moon's sidereal longitude."""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import NAKSHATRA_SPAN, VIMSHOTTARI_YEARS
from .nakshatra import nakshatra_of

VIMSHOTTARI_SEQUENCE = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
]

DAYS_PER_YEAR = 365.25


def _add_years(dt: datetime, years: float) -> datetime:
    return dt + timedelta(days=years * DAYS_PER_YEAR)


def _sequence_from(lord: str) -> list[str]:
    idx = VIMSHOTTARI_SEQUENCE.index(lord)
    return VIMSHOTTARI_SEQUENCE[idx:] + VIMSHOTTARI_SEQUENCE[:idx]


def _period(lord: str, start: datetime, years: float, as_of: datetime | None) -> dict:
    end = _add_years(start, years)
    return {
        "lord": lord,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "years": round(years, 6),
        "active": bool(as_of and start <= as_of < end),
    }


def _sub_periods(parent_lord: str, start: datetime, years: float,
                 as_of: datetime | None) -> list[dict]:
    out = []
    cursor = start
    for lord in _sequence_from(parent_lord):
        sub_years = years * VIMSHOTTARI_YEARS[lord] / 120.0
        p = _period(lord, cursor, sub_years, as_of)
        out.append(p)
        cursor = datetime.fromisoformat(p["end"])
    return out


def _attach_pratyantardashas(mahadashas: list[dict], as_of: datetime | None) -> None:
    for md in mahadashas:
        for ad in md["antardashas"]:
            start = datetime.fromisoformat(ad["start"])
            ad["pratyantardashas"] = _sub_periods(ad["lord"], start, ad["years"], as_of)


def vimshottari_dasha(moon_lon: float, birth_dt: datetime,
                      as_of: datetime | None = None) -> dict:
    """Return Vimshottari mahadasha/antardasha/pratyantardasha timeline.

    The birth nakshatra lord starts the sequence. The remaining balance of
    that mahadasha is proportional to the untraversed part of the Moon's
    nakshatra at birth. Durations use the traditional 120-year Vimshottari
    cycle with a 365.25-day civil year for deterministic date arithmetic.
    """
    nak = nakshatra_of(moon_lon)
    birth_lord = nak["lord"]
    elapsed_fraction = nak["degree_in_nakshatra"] / NAKSHATRA_SPAN
    balance_years = VIMSHOTTARI_YEARS[birth_lord] * (1.0 - elapsed_fraction)

    mahadashas = []
    cursor = birth_dt
    first = True
    for cycle in range(2):
        for lord in _sequence_from(birth_lord):
            years = balance_years if first else VIMSHOTTARI_YEARS[lord]
            if years <= 0:
                first = False
                continue
            p = _period(lord, cursor, years, as_of)
            p["antardashas"] = _sub_periods(lord, cursor, years, as_of)
            mahadashas.append(p)
            cursor = datetime.fromisoformat(p["end"])
            first = False
        if (cursor - birth_dt).days >= int(120 * DAYS_PER_YEAR):
            break

    _attach_pratyantardashas(mahadashas, as_of)

    active_md = next((p for p in mahadashas if p["active"]), None)
    active_ad = None
    pratyantardashas = []
    if active_md:
        active_ad = next((p for p in active_md["antardashas"] if p["active"]), None)
        if active_ad:
            pratyantardashas = active_ad["pratyantardashas"]
    active_pd = next((p for p in pratyantardashas if p["active"]), None)

    # Sookshma (4th) and prana (5th) levels only along the active chain —
    # expanding the full tree to five levels would explode the payload.
    sookshmadashas = []
    active_sd = None
    pranadashas = []
    active_prd = None
    if active_pd:
        sookshmadashas = _sub_periods(
            active_pd["lord"], datetime.fromisoformat(active_pd["start"]),
            active_pd["years"], as_of,
        )
        active_sd = next((p for p in sookshmadashas if p["active"]), None)
        if active_sd:
            pranadashas = _sub_periods(
                active_sd["lord"], datetime.fromisoformat(active_sd["start"]),
                active_sd["years"], as_of,
            )
            active_prd = next((p for p in pranadashas if p["active"]), None)

    return {
        "system": "Vimshottari",
        "cycle_years": 120,
        "birth_nakshatra": {
            "name": nak["name"],
            "lord": birth_lord,
            "pada": nak["pada"],
            "elapsed_fraction": round(elapsed_fraction, 8),
            "balance_years": round(balance_years, 6),
        },
        "as_of": as_of.isoformat() if as_of else None,
        "mahadashas": mahadashas,
        "current": {
            "mahadasha": active_md,
            "antardasha": active_ad,
            "pratyantardashas": pratyantardashas,
            "pratyantardasha": active_pd,
            "sookshmadashas": sookshmadashas,
            "sookshmadasha": active_sd,
            "pranadashas": pranadashas,
            "pranadasha": active_prd,
        },
    }
