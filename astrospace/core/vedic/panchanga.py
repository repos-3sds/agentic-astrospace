"""
Panchanga — the five limbs of the Vedic day.

Tithi, Yoga and Karana are pure functions of the Sun/Moon sidereal
longitudes; Vara additionally needs sunrise (the Vedic weekday runs
sunrise to sunrise, not midnight to midnight).
"""
from datetime import datetime, timedelta

from .constants import (
    TITHI_NAMES, YOGA_NAMES, KARANA_MOVABLE, VARA_NAMES, VARA_LORDS,
)
from .nakshatra import nakshatra_of
from .positions import BirthMoment, local_sunrise


def tithi_of(sun_lon: float, moon_lon: float) -> dict:
    """Tithi from Moon-Sun elongation. Each tithi spans 12°."""
    angle = (moon_lon - sun_lon) % 360.0
    idx = min(int(angle // 12.0), 29)  # 0..29
    if idx == 14:
        name, paksha = "Purnima", "Shukla"
    elif idx == 29:
        name, paksha = "Amavasya", "Krishna"
    elif idx < 14:
        name, paksha = TITHI_NAMES[idx], "Shukla"
    else:
        name, paksha = TITHI_NAMES[idx - 15], "Krishna"
    return {
        "index": idx,
        "number": idx % 15 + 1,
        "name": name,
        "paksha": paksha,
        "display": name if idx in (14, 29) else f"{name} {paksha}",
        "elongation": angle,
    }


def yoga_of(sun_lon: float, moon_lon: float) -> dict:
    """Yoga from the sum of Sun and Moon longitudes; 27 divisions."""
    total = (sun_lon + moon_lon) % 360.0
    idx = min(int(total * 27.0 / 360.0), 26)  # multiply first: 360/27 is inexact
    return {"index": idx, "number": idx + 1, "name": YOGA_NAMES[idx]}


def karana_of(sun_lon: float, moon_lon: float) -> dict:
    """
    Karana (half-tithi), 60 per lunation: index 0 = Kimstughna,
    1-56 = seven movable karanas cycling, 57-59 = Shakuni, Chatushpada, Naga.
    """
    angle = (moon_lon - sun_lon) % 360.0
    idx = min(int(angle // 6.0), 59)
    if idx == 0:
        name = "Kimstughna"
    elif idx >= 57:
        name = ["Shakuni", "Chatushpada", "Naga"][idx - 57]
    else:
        name = KARANA_MOVABLE[(idx - 1) % 7]
    return {"index": idx, "name": name}


def vara_of(moment: BirthMoment) -> dict:
    """
    Vedic weekday. The day begins at sunrise: a birth before sunrise
    belongs to the previous vara. Falls back to the civil weekday if
    sunrise is unavailable (extreme latitudes).
    """
    civil_date = moment.dt_local.date()
    sunrise = local_sunrise(moment)
    date_for_vara = civil_date
    if sunrise is not None and moment.dt_local < sunrise:
        date_for_vara = civil_date - timedelta(days=1)
    # Python: Monday=0 ... Sunday=6 → Vedic: Sunday=0 ... Saturday=6
    idx = (date_for_vara.weekday() + 1) % 7
    return {
        "index": idx,
        "name": VARA_NAMES[idx],
        "lord": VARA_LORDS[idx],
        "sunrise_local": sunrise.isoformat() if sunrise else None,
    }


def panchanga_of(moment: BirthMoment, sun_lon: float, moon_lon: float) -> dict:
    """All five limbs for a birth moment."""
    return {
        "vara": vara_of(moment),
        "tithi": tithi_of(sun_lon, moon_lon),
        "nakshatra": nakshatra_of(moon_lon),
        "yoga": yoga_of(sun_lon, moon_lon),
        "karana": karana_of(sun_lon, moon_lon),
    }
