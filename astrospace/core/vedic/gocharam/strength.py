"""Ashtakavarga weighting for canonical Gocharam results."""

from __future__ import annotations

from ..ashtakavarga import AV_PLANETS
from ..positions import degree_in_sign, sign_index, sign_name

KAKSHYA_LORDS = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Lagna"]
KAKSHYA_SPAN_DEG = 3.75


def _bav_support(bindus: int) -> str:
    if bindus >= 5:
        return "strong"
    if bindus == 4:
        return "average"
    return "weak"


def _sav_support(sav: int) -> str:
    if sav >= 30:
        return "strong"
    if sav >= 25:
        return "average"
    return "weak"


def _kakshya_of(lon: float) -> tuple[int, str]:
    idx = min(int(degree_in_sign(lon) // KAKSHYA_SPAN_DEG), 7)
    return idx + 1, KAKSHYA_LORDS[idx]


def _effective_severity(severity: str, active: bool, bav_support: str | None) -> str:
    if not active or bav_support is None:
        return severity
    if severity in {"high", "medium"} and bav_support == "strong":
        return {"high": "medium", "medium": "low"}[severity]
    if severity == "supportive" and bav_support == "weak":
        return "diluted"
    return severity


def ashtakavarga_transit_support(natal_av: dict, transit_positions: dict) -> dict:
    rows: dict[str, dict] = {}
    for planet in AV_PLANETS:
        if planet not in transit_positions:
            continue
        lon = transit_positions[planet]["lon"]
        transit_sign = sign_index(lon)
        bindus = natal_av["bav"][planet][transit_sign]
        sav = natal_av["sav"][transit_sign]
        kakshya_index, kakshya_lord = _kakshya_of(lon)
        bindu_given = natal_av["source_breakdown"][planet][kakshya_lord][transit_sign] == 1
        rows[planet] = {
            "planet": planet,
            "transit_sign": sign_name(transit_sign),
            "transit_sign_index": transit_sign,
            "bindus": bindus,
            "bav_support": _bav_support(bindus),
            "sav": sav,
            "sav_support": _sav_support(sav),
            "kakshya": {
                "kakshya_index": kakshya_index,
                "kakshya_lord": kakshya_lord,
                "bindu_given": bindu_given,
            },
        }
    return {
        "planets": rows,
        "note": (
            "A transit is weighted with the planet's natal BAV bindus, the transit sign's SAV total, "
            "and the occupied 3 degree 45 minute kakshya. BAV 5+ is treated as strong and 3 or fewer "
            "as weak; SAV 30+ is strong and below 25 is weak."
        ),
        "source_status": "classical_calculation_with_configured_thresholds",
    }


def apply_ashtakavarga_context(gochara: dict, support: dict) -> None:
    """Attach AV evidence to canonical rules without changing rule activation."""
    rows = support["planets"]
    for rule in gochara["rules"]:
        row = rows.get(rule["planet"])
        rule["av_context"] = (
            {
                "bindus": row["bindus"],
                "bav_support": row["bav_support"],
                "sav": row["sav"],
                "sav_support": row["sav_support"],
                "kakshya": row["kakshya"],
            }
            if row
            else None
        )
        effective = _effective_severity(
            rule["severity"], rule["active"], row["bav_support"] if row else None
        )
        rule["effective_severity"] = effective
        if effective == rule["severity"]:
            continue
        if effective == "diluted":
            rule["note"] += (
                f" Ashtakavarga: {rule['planet']} has {row['bindus']} BAV bindus in this sign, "
                "so the supportive indication is treated as diluted."
            )
        else:
            rule["note"] += (
                f" Ashtakavarga: {rule['planet']} has {row['bindus']} BAV bindus in this sign, "
                "so the challenging indication is softened by one level."
            )
