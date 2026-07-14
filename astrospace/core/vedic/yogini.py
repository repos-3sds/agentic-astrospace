"""Yogini dasha from the Moon's sidereal longitude.

A 36-year nakshatra dasha (8 yoginis, years 1..8). The starting yogini
comes from the Moon's birth nakshatra: remainder (nakshatra_number + 3)
mod 8 maps 1=Mangala, 2=Pingala, ... 7=Siddha, 0=Sankata (Ashwini = 1).
The first period's balance is proportional to the untraversed part of
the nakshatra, exactly as in Vimshottari. Antardashas run the 8 yoginis
in cycle order starting from the mahadasha's own yogini, each sized
years/36 of the mahadasha. 365.25-day years for deterministic dates.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import NAKSHATRA_SPAN
from .nakshatra import nakshatra_of

# (yogini, planet, years) in cycle order.
YOGINIS = [
    ("Mangala", "Moon", 1),
    ("Pingala", "Sun", 2),
    ("Dhanya", "Jupiter", 3),
    ("Bhramari", "Mars", 4),
    ("Bhadrika", "Mercury", 5),
    ("Ulka", "Saturn", 6),
    ("Siddha", "Venus", 7),
    ("Sankata", "Rahu", 8),
]

CYCLE_YEARS = 36
DAYS_PER_YEAR = 365.25


def _add_years(dt: datetime, years: float) -> datetime:
    return dt + timedelta(days=years * DAYS_PER_YEAR)


def _period(idx: int, start: datetime, years: float, as_of: datetime | None) -> dict:
    name, planet, _ = YOGINIS[idx % 8]
    end = _add_years(start, years)
    return {
        "yogini": name,
        "planet": planet,
        "lord": planet,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "years": round(years, 6),
        "active": bool(as_of and start <= as_of < end),
    }


def _antardashas(md_idx: int, start: datetime, md_years: float,
                 as_of: datetime | None) -> list[dict]:
    out = []
    cursor = start
    for step in range(8):
        idx = (md_idx + step) % 8
        sub_years = md_years * YOGINIS[idx][2] / float(CYCLE_YEARS)
        p = _period(idx, cursor, sub_years, as_of)
        out.append(p)
        cursor = datetime.fromisoformat(p["end"])
    return out


def yogini_dasha(moon_lon: float, birth_dt: datetime,
                 as_of: datetime | None = None) -> dict:
    """Yogini mahadasha/antardasha timeline (three 36-year cycles).

    Starting yogini from the Moon's nakshatra number (Ashwini = 1):
    remainder (number + 3) mod 8, with 1 = Mangala .. 0 = Sankata. The
    first mahadasha's balance is proportional to the untraversed fraction
    of the nakshatra; its antardashas are spread proportionally over the
    balance (same simplification as vimshottari_dasha).
    """
    nak = nakshatra_of(moon_lon)
    rem = (nak["number"] + 3) % 8
    start_idx = (rem - 1) % 8
    elapsed_fraction = nak["degree_in_nakshatra"] / NAKSHATRA_SPAN
    balance_years = YOGINIS[start_idx][2] * (1.0 - elapsed_fraction)

    mahadashas = []
    cursor = birth_dt
    idx = start_idx
    first = True
    horizon_days = int(3 * CYCLE_YEARS * DAYS_PER_YEAR)  # 108 years
    while (cursor - birth_dt).days < horizon_days:
        years = balance_years if first else float(YOGINIS[idx % 8][2])
        if years > 0:
            p = _period(idx, cursor, years, as_of)
            p["antardashas"] = _antardashas(idx % 8, cursor, years, as_of)
            mahadashas.append(p)
            cursor = datetime.fromisoformat(p["end"])
        first = False
        idx += 1

    active_md = next((p for p in mahadashas if p["active"]), None)
    active_ad = None
    if active_md:
        active_ad = next((p for p in active_md["antardashas"] if p["active"]), None)

    return {
        "system": "Yogini",
        "cycle_years": CYCLE_YEARS,
        "birth_nakshatra": {
            "name": nak["name"],
            "number": nak["number"],
            "starting_yogini": YOGINIS[start_idx][0],
            "starting_planet": YOGINIS[start_idx][1],
            "pada": nak["pada"],
            "elapsed_fraction": round(elapsed_fraction, 8),
            "balance_years": round(balance_years, 6),
        },
        "as_of": as_of.isoformat() if as_of else None,
        "mahadashas": mahadashas,
        "current": {
            "mahadasha": active_md,
            "antardasha": active_ad,
        },
    }
