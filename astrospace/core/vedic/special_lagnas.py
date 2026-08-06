"""Special (non-rising) lagnas: Bhava, Hora, Ghati Lagna, Bhrigu Bindu, Indu Lagna.

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

Two further points, not time-based, added under T1.3
(docs/backend_astro_depth_checklist_2026-08-06.md):

- **Bhrigu Bindu**: the midpoint of Rahu and the Moon, on the shorter arc
  between them. Formula and usage widely and consistently described
  (checked via web research 2026-08-06) — a sensitive point commonly used
  for event timing by transit/dasha activation.
- **Indu Lagna** (Dhana/wealth lagna): from Uttara Kalamrita (Kalidasa) —
  each classical planet has a fixed "Kala" number (Sun 30, Moon 16, Mars 6,
  Mercury 8, Jupiter 10, Venus 12, Saturn 1). Sum the Kalas of the 9th-lord
  from Lagna and the 9th-lord from Moon, take that sum mod 12 (treating a
  zero remainder as 12), and count that many signs inclusively from the
  Moon sign — cross-checked against two independent secondary sources
  citing the same table; still marked convention_dependent since neither
  source is the primary text itself.

Sree Lagna and Pranapada Lagna are deliberately NOT implemented here:
secondary sources found in this pass disagreed with each other (and with
this codebase's general knowledge) on the exact scaling/anchor rule for
Sree Lagna, and gave no usable formula for Pranapada's day/night-birth
distinction. Shipping a guessed formula for a "fortune" or "life-force"
point is worse than not shipping it — see the checklist for what a future
pass needs before adding them.
"""
from __future__ import annotations

from .constants import SIGN_LORDS
from .positions import sign_index, sign_name, to_dms

# Uttara Kalamrita Kala numbers, used only for Indu Lagna.
INDU_KALA = {
    "Sun": 30, "Moon": 16, "Mars": 6, "Mercury": 8,
    "Jupiter": 10, "Venus": 12, "Saturn": 1,
}

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


def bhrigu_bindu(rahu_lon: float, moon_lon: float) -> dict:
    """Bhrigu Bindu — the midpoint of Rahu and the Moon, on the shorter arc.

    A sensitive point, not a rising point; used for event timing rather
    than as a chart anchor. Returns the same {longitude, sign, sign_name,
    dms} shape as the time-based special lagnas above.
    """
    delta = ((rahu_lon - moon_lon + 180.0) % 360.0) - 180.0
    midpoint = (moon_lon + delta / 2.0) % 360.0
    row = _lagna_row(midpoint)
    row["notes"] = [
        "Midpoint of Rahu and Moon on the shorter arc between them.",
        "Sensitive/event point, not a rising ascendant — used for transit "
        "and dasha-activation timing, not as a chart anchor.",
    ]
    return row


def indu_lagna(lagna_sign: int, moon_sign: int, positions: dict) -> dict:
    """Indu Lagna (Dhana Lagna, wealth point) — Uttara Kalamrita method.

    Sums the Kala numbers of the 9th-lord-from-Lagna and 9th-lord-from-Moon,
    then counts that many signs (mod 12, treating 0 as 12) inclusively from
    the Moon sign. See module docstring for the Kala table and sourcing.
    """
    lagna_ninth = (lagna_sign + 8) % 12
    moon_ninth = (moon_sign + 8) % 12
    lagna_ninth_lord = SIGN_LORDS[lagna_ninth]
    moon_ninth_lord = SIGN_LORDS[moon_ninth]

    kala_sum = INDU_KALA[lagna_ninth_lord] + INDU_KALA[moon_ninth_lord]
    remainder = kala_sum % 12
    if remainder == 0:
        remainder = 12
    sign = (moon_sign + remainder - 1) % 12

    return {
        "sign": sign,
        "sign_name": sign_name(sign),
        "ninth_from_lagna": {"sign": lagna_ninth, "sign_name": sign_name(lagna_ninth), "lord": lagna_ninth_lord},
        "ninth_from_moon": {"sign": moon_ninth, "sign_name": sign_name(moon_ninth), "lord": moon_ninth_lord},
        "kala_sum": kala_sum,
        "count": remainder,
        "source_status": "convention_dependent",
        "notes": [
            "Kala numbers from Uttara Kalamrita (Kalidasa): Sun 30, Moon 16, "
            "Mars 6, Mercury 8, Jupiter 10, Venus 12, Saturn 1.",
            "Counted inclusively from the Moon sign; a zero remainder is "
            "treated as 12, per the classical rule.",
        ],
    }
