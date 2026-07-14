"""Special (non-rising) lagnas: Bhava, Hora and Ghati Lagna.

BPHS ch. 5 ("Special Ascendants") defines three time-based lagnas that
start from the Sun's sidereal longitude at sunrise and advance at fixed
rates with clock time:

Ghati definitions (1 civil day = 60 ghatis, so 1 ghati = 24 minutes and
2.5 ghatis = 1 hour):

- Bhava Lagna (BL): one sign per 5 ghatis (= 2 hours), i.e. 15°/hour.
- Hora Lagna (HL): one sign per 2.5 ghatis (= 1 hour), i.e. 30°/hour.
- Ghati Lagna (GL, Ghatika Lagna): one sign per 1 ghati (= 24 minutes),
  i.e. 1.25°/minute = 75°/hour.

At the moment of sunrise all three coincide with the Sun's longitude.
The caller supplies the sunrise julian day and the Sun's sidereal
longitude at that sunrise (positions.py has sunrise helpers); nothing is
computed from ephemerides here.
"""
from __future__ import annotations

from .positions import sign_index, sign_name, to_dms

GHATI_MINUTES = 24.0            # 1 ghati = 24 minutes; 60 ghatis per day
BHAVA_DEG_PER_HOUR = 15.0       # 30° per 5 ghatis (2 hours)
HORA_DEG_PER_HOUR = 30.0        # 30° per 2.5 ghatis (1 hour)
GHATI_DEG_PER_HOUR = 75.0       # 30° per ghati (24 min) = 1.25°/minute


def _lagna_row(lon: float) -> dict:
    lon %= 360.0
    idx = sign_index(lon)
    return {
        "longitude": lon,
        "sign": idx,
        "sign_name": sign_name(idx),
        "dms": to_dms(lon % 30.0),
    }


def special_lagnas(jd_ut: float, sunrise_jd: float, sun_lon_at_sunrise: float,
                   lagna_lon: float | None = None) -> dict:
    """Bhava, Hora and Ghati Lagna for a birth instant.

    jd_ut: birth instant (UT julian day). sunrise_jd: sunrise of the birth's
    Vedic day (UT julian day, caller-provided). sun_lon_at_sunrise: Sun's
    sidereal longitude at that sunrise. lagna_lon: optional rising lagna
    longitude, echoed back for convenience.

    Returns {"hours_since_sunrise", "ghatis_since_sunrise",
             "bhava_lagna" | "hora_lagna" | "ghati_lagna":
                 {longitude, sign, sign_name, dms}, ...}.
    """
    hours = (jd_ut - sunrise_jd) * 24.0
    base = sun_lon_at_sunrise % 360.0
    out = {
        "hours_since_sunrise": hours,
        "ghatis_since_sunrise": hours * 60.0 / GHATI_MINUTES,
        "bhava_lagna": _lagna_row(base + hours * BHAVA_DEG_PER_HOUR),
        "hora_lagna": _lagna_row(base + hours * HORA_DEG_PER_HOUR),
        "ghati_lagna": _lagna_row(base + hours * GHATI_DEG_PER_HOUR),
        "notes": [
            "All three lagnas equal the Sun's longitude at sunrise and advance at "
            "15°/h (BL), 30°/h (HL) and 75°/h (GL); 1 ghati = 24 minutes.",
        ],
    }
    if lagna_lon is not None:
        out["lagna"] = _lagna_row(lagna_lon)
    if hours < 0:
        out["notes"].append(
            "Birth instant precedes the supplied sunrise; pass the sunrise of the "
            "Vedic day (previous sunrise for pre-dawn births)."
        )
    return out
