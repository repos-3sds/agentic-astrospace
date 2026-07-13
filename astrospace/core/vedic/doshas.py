"""Common dosha calculations."""
from __future__ import annotations

from .positions import house_from_lagna, sign_index, sign_name

MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}


def manglik_dosha(positions: dict, lagna_lon: float) -> dict:
    """Calculate Kuja/Manglik dosha from Lagna, Moon, and Venus references."""
    mars_sign = sign_index(positions["Mars"]["lon"])
    references = {
        "Lagna": sign_index(lagna_lon),
        "Moon": sign_index(positions["Moon"]["lon"]),
        "Venus": sign_index(positions["Venus"]["lon"]),
    }
    checks = []
    active_refs = []
    for ref, ref_sign in references.items():
        house = house_from_lagna(mars_sign, ref_sign)
        active = house in MANGLIK_HOUSES
        if active:
            active_refs.append(ref)
        checks.append({
            "reference": ref,
            "house": house,
            "active": active,
            "mars_sign": sign_name(mars_sign),
            "reference_sign": sign_name(ref_sign),
        })

    active_count = len(active_refs)
    severity = "none"
    if active_count == 1:
        severity = "mild"
    elif active_count == 2:
        severity = "moderate"
    elif active_count == 3:
        severity = "strong"

    return {
        "name": "Manglik / Kuja Dosha",
        "active": active_count > 0,
        "severity": severity,
        "active_references": active_refs,
        "checks": checks,
        "rule": "Mars in houses 1, 2, 4, 7, 8, or 12 from Lagna, Moon, or Venus.",
        "verified": True,
        "notes": [
            "Cancellation and exception rules are convention-dependent and not applied yet.",
            "Use this as a deterministic flag, not a final marriage judgement.",
        ],
    }


def dosha_summary(positions: dict, lagna_lon: float) -> dict:
    return {
        "manglik": manglik_dosha(positions, lagna_lon),
    }
