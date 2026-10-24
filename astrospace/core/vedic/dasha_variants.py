"""Vimshottari variants for Practitioner: other starting points, and Tribhagi.

Standard Vimshottari starts from the Moon's nakshatra. Practitioners also
read the same 120-year sequence started from a different point. Each
variant here only changes the longitude handed to ``vimshottari_dasha``
(or its scale), so periods, sub-periods and dates come from the one tested
engine.

- Tara starts. Kshema is the 4th nakshatra from the birth star, Utpanna
  the 5th and Adhana the 8th (BPHS dasha chapter; the same counting as
  Tarabala in panchanga_day). The Moon's longitude is moved forward by
  3, 4 or 7 nakshatras, so the elapsed share of the star, and with it the
  balance of the first period, stays the Moon's own.
- Lagna starts. The lagna's longitude in D1, D9 or D10 seeds the dasha.
  A varga lagna needs a full longitude, not only a sign; see
  ``vargas.varga_longitude`` for the convention.
- Tribhagi. Every mahadasha is a third of its Vimshottari length, a 40-year
  cycle that runs three times over a 120-year life.

All of these are convention-dependent. Which starting point to read, and
when, varies by teacher; the payload says what was used.
"""
from __future__ import annotations

from datetime import datetime

from .constants import NAKSHATRA_SPAN
from .dashas import vimshottari_dasha
from .vargas import varga_longitude

# key -> (label, how the start is found)
TARA_STEPS = {"kshema": ("Kshema Tara", 3), "utpanna": ("Utpanna Tara", 4), "adhana": ("Adhana Tara", 7)}
LAGNA_VARGAS = {"d1_lagna": "D1", "d9_lagna": "D9", "d10_lagna": "D10"}

VARIANTS = {
    "tribhagi": "Vimshottari Tribhagi",
    **{key: f"Vimshottari from {label}" for key, (label, _) in TARA_STEPS.items()},
    **{key: f"Vimshottari from {varga} Lagna" for key, varga in LAGNA_VARGAS.items()},
}

OBSERVANCE_NOTE = (
    "One of several Vimshottari variants used by practitioners. "
    "Which one to read, and for what, depends on the teacher. Read it "
    "beside the standard Moon-star dasha, not instead of it."
)


def vimshottari_variant(variant: str, moon_lon: float, lagna_lon: float,
                        birth_dt: datetime, as_of: datetime | None = None) -> dict:
    """The Vimshottari timeline for one variant key in ``VARIANTS``."""
    if variant not in VARIANTS:
        raise ValueError(f"Unknown dasha variant: {variant}")
    label = VARIANTS[variant]
    if variant == "tribhagi":
        seed_lon, seed = moon_lon, "Moon"
        payload = vimshottari_dasha(seed_lon, birth_dt, as_of, scale=1 / 3, system=label)
    else:
        if variant in TARA_STEPS:
            name, steps = TARA_STEPS[variant]
            seed_lon, seed = (moon_lon + steps * NAKSHATRA_SPAN) % 360.0, name
        else:
            varga = LAGNA_VARGAS[variant]
            seed_lon, seed = varga_longitude(lagna_lon, varga), f"{varga} Lagna"
        payload = vimshottari_dasha(seed_lon, birth_dt, as_of, system=label)
    payload["variant"] = variant
    payload["seed"] = {"point": seed, "longitude": round(seed_lon, 6)}
    payload["is_convention_dependent"] = True
    payload["observance_note"] = OBSERVANCE_NOTE
    return payload


def variant_catalog() -> list[dict]:
    return [{"key": key, "label": label} for key, label in VARIANTS.items()]
