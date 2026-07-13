"""
Kala engine — auspicious and inauspicious windows of the day, all derived
from sunrise/sunset and the weekday.

Conventions (all VERIFY against DrikPanchang before treating as final):
- Rahu Kalam / Yamaganda / Gulika: daytime (sunrise→sunset) split into 8
  equal parts; the weekday selects which eighth. Standard tables below.
- Muhurtas: daytime split into 15 (each ~48 min on an equinox day).
  Durmuhurta muhurta numbers per weekday from Muhurta Chintamani;
  Tuesday additionally has a night durmuhurta (7th of 15 night muhurtas).
- Brahma Muhurta: 14th muhurta of the NIGHT — from sunrise minus two
  night-muhurtas to sunrise minus one.
- Abhijit: 8th muhurta of the day; traditionally not observed on Wednesday.
- Choghadiya: day and night each split into 8; sequence cycles from the
  weekday-lord's block.
- Hora: day and night each split into 12; Chaldean lord sequence starting
  from the weekday lord.

Weekday index everywhere: 0=Sunday .. 6=Saturday (Vedic vara index).
"""
from .positions import jd_to_local

# eighth-of-day (1-based) per vara
RAHU_KALAM_PART = {0: 8, 1: 2, 2: 7, 3: 5, 4: 6, 5: 4, 6: 3}
YAMAGANDA_PART = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 7, 6: 6}
GULIKA_PART = {0: 7, 1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}

# day-muhurta numbers (1-based of 15) per vara  — VERIFY
DURMUHURTA_DAY = {0: [14], 1: [9, 12], 2: [4], 3: [8], 4: [6, 12], 5: [4, 9], 6: [1, 2]}
DURMUHURTA_NIGHT = {2: [7]}  # Tuesday night — VERIFY

CHOGHADIYA_ORDER = ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"]
CHOGHADIYA_DAY_START = {0: "Udveg", 1: "Amrit", 2: "Rog", 3: "Labh", 4: "Shubh", 5: "Chal", 6: "Kaal"}
CHOGHADIYA_NIGHT_START = {0: "Shubh", 1: "Chal", 2: "Kaal", 3: "Udveg", 4: "Amrit", 5: "Rog", 6: "Labh"}
CHOGHADIYA_NATURE = {
    "Amrit": "good", "Shubh": "good", "Labh": "good", "Chal": "neutral",
    "Udveg": "bad", "Kaal": "bad", "Rog": "bad",
}

HORA_SEQUENCE = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
VARA_LORD_BY_INDEX = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
HORA_NATURE = {
    "Sun": "neutral", "Moon": "good", "Mars": "bad", "Mercury": "good",
    "Jupiter": "good", "Venus": "good", "Saturn": "bad",
}


def _window(start_jd: float, end_jd: float, tz_str: str, name: str,
            kind: str, note: str = None) -> dict:
    w = {
        "name": name,
        "kind": kind,  # "auspicious" | "inauspicious" | "neutral"
        "start": jd_to_local(start_jd, tz_str).strftime("%H:%M"),
        "end": jd_to_local(end_jd, tz_str).strftime("%H:%M"),
        "start_iso": jd_to_local(start_jd, tz_str).isoformat(),
        "end_iso": jd_to_local(end_jd, tz_str).isoformat(),
    }
    if note:
        w["note"] = note
    return w


def _eighth(rise: float, sets: float, part: int) -> tuple[float, float]:
    step = (sets - rise) / 8.0
    return rise + (part - 1) * step, rise + part * step


def _day_muhurta(rise: float, sets: float, n: int) -> tuple[float, float]:
    step = (sets - rise) / 15.0
    return rise + (n - 1) * step, rise + n * step


def _night_muhurta(sets: float, next_rise: float, n: int) -> tuple[float, float]:
    step = (next_rise - sets) / 15.0
    return sets + (n - 1) * step, sets + n * step


def kala_windows(rise: float, sets: float, next_rise: float,
                 vara_idx: int, tz_str: str) -> dict:
    """All named day windows. Returns {"auspicious": [...], "inauspicious": [...]}."""
    inauspicious = []
    auspicious = []

    for name, table in (("Rahu Kalam", RAHU_KALAM_PART),
                        ("Yamaganda", YAMAGANDA_PART),
                        ("Gulika Kalam", GULIKA_PART)):
        s, e = _eighth(rise, sets, table[vara_idx])
        inauspicious.append(_window(s, e, tz_str, name, "inauspicious"))

    for n in DURMUHURTA_DAY[vara_idx]:
        s, e = _day_muhurta(rise, sets, n)
        inauspicious.append(_window(s, e, tz_str, "Durmuhurta", "inauspicious"))
    for n in DURMUHURTA_NIGHT.get(vara_idx, []):
        s, e = _night_muhurta(sets, next_rise, n)
        inauspicious.append(_window(s, e, tz_str, "Durmuhurta (night)", "inauspicious"))

    # Brahma muhurta belongs to the night that ENDS at this sunrise: use the
    # previous night's length approximated by tonight's (error < 1 min/day drift).
    night_step = (next_rise - sets) / 15.0
    auspicious.append(_window(rise - 2 * night_step, rise - night_step, tz_str,
                              "Brahma Muhurta", "auspicious"))

    s, e = _day_muhurta(rise, sets, 8)
    abhijit_note = "Not observed on Wednesday" if vara_idx == 3 else None
    auspicious.append(_window(s, e, tz_str, "Abhijit Muhurta", "auspicious", abhijit_note))

    # Godhuli — the muhurta straddling sunset (last day muhurta into dusk)
    auspicious.append(_window(sets - (sets - rise) / 30.0, sets + night_step / 2,
                              tz_str, "Godhuli", "auspicious"))

    return {"auspicious": auspicious, "inauspicious": inauspicious}


def choghadiya(rise: float, sets: float, next_rise: float,
               vara_idx: int, tz_str: str) -> dict:
    def blocks(start: float, end: float, first_name: str) -> list:
        step = (end - start) / 8.0
        i0 = CHOGHADIYA_ORDER.index(first_name)
        out = []
        for i in range(8):
            name = CHOGHADIYA_ORDER[(i0 + i) % 7]
            out.append(_window(start + i * step, start + (i + 1) * step, tz_str,
                               name, CHOGHADIYA_NATURE[name]))
        return out

    return {
        "day": blocks(rise, sets, CHOGHADIYA_DAY_START[vara_idx]),
        "night": blocks(sets, next_rise, CHOGHADIYA_NIGHT_START[vara_idx]),
    }


def horas(rise: float, sets: float, next_rise: float,
          vara_idx: int, tz_str: str) -> list:
    """24 planetary horas (12 day + 12 night), Chaldean sequence from the day lord."""
    lord0 = HORA_SEQUENCE.index(VARA_LORD_BY_INDEX[vara_idx])
    out = []
    day_step = (sets - rise) / 12.0
    night_step = (next_rise - sets) / 12.0
    for i in range(24):
        lord = HORA_SEQUENCE[(lord0 + i) % 7]
        if i < 12:
            s, e = rise + i * day_step, rise + (i + 1) * day_step
        else:
            j = i - 12
            s, e = sets + j * night_step, sets + (j + 1) * night_step
        out.append(_window(s, e, tz_str, f"{lord} Hora", HORA_NATURE[lord]))
    return out
