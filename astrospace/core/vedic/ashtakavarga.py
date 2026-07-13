"""Classical Bhinna and Sarvashtakavarga bindu calculations."""
from __future__ import annotations

from .constants import SIGNS
from .positions import sign_index

AV_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
AV_SOURCES = AV_PLANETS + ["Lagna"]
TRIKONA_GROUPS = [(0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)]
OWNERSHIP_PAIRS = [(0, 7), (1, 6), (2, 5), (8, 11), (9, 10)]
RASHI_GUNAKARA = [7, 10, 8, 4, 10, 5, 7, 8, 9, 5, 11, 12]
GRAHA_GUNAKARA = {
    "Sun": 5,
    "Moon": 5,
    "Mars": 8,
    "Mercury": 5,
    "Jupiter": 10,
    "Venus": 7,
    "Saturn": 5,
}

# Benefic houses (1-based from each source planet/Lagna) for each target planet.
BAV_RULES = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [3, 4, 6, 10, 11, 12],
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11],
        "Moon": [1, 3, 6, 7, 10, 11],
        "Mars": [2, 3, 5, 6, 9, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 4, 7, 8, 10, 11, 12],
        "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [3, 6, 10, 11],
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 3, 6, 10, 11],
    },
    "Mercury": {
        "Sun": [5, 6, 9, 11, 12],
        "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Lagna": [1, 2, 4, 6, 8, 10, 11],
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
        "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12],
        "Lagna": [1, 2, 4, 5, 6, 7, 9, 10, 11],
    },
    "Venus": {
        "Sun": [8, 11, 12],
        "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 5, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11],
        "Lagna": [1, 2, 3, 4, 5, 8, 9, 11],
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11],
        "Lagna": [1, 3, 4, 6, 10, 11],
    },
}


def _source_signs(positions: dict, lagna_lon: float) -> dict[str, int]:
    signs = {planet: sign_index(positions[planet]["lon"]) for planet in AV_PLANETS}
    signs["Lagna"] = sign_index(lagna_lon)
    return signs


def trikona_shodhana(scores: list[int]) -> list[int]:
    """Apply Trikona Shodhana to one planet's BAV row."""
    reduced = scores.copy()
    for group in TRIKONA_GROUPS:
        values = [reduced[i] for i in group]
        if 0 in values:
            continue
        minimum = min(values)
        for i in group:
            reduced[i] -= minimum
    return reduced


def ekadhipatya_shodhana(scores: list[int], occupied_signs: set[int]) -> list[int]:
    """Apply Ekadhipatya Shodhana after Trikona Shodhana."""
    reduced = scores.copy()
    for first, second in OWNERSHIP_PAIRS:
        first_score = reduced[first]
        second_score = reduced[second]
        if first_score == 0 or second_score == 0:
            continue

        first_occupied = first in occupied_signs
        second_occupied = second in occupied_signs

        if first_occupied and second_occupied:
            continue

        if not first_occupied and not second_occupied:
            if first_score == second_score:
                reduced[first] = 0
                reduced[second] = 0
            else:
                reduced[first] = min(first_score, second_score)
                reduced[second] = min(first_score, second_score)
            continue

        if first_occupied and not second_occupied:
            reduced[second] = second_score - first_score if first_score < second_score else 0
        elif second_occupied and not first_occupied:
            reduced[first] = first_score - second_score if second_score < first_score else 0

    return reduced


def shodhya_pinda(scores: list[int], graha_signs: dict[str, int]) -> dict[str, int]:
    """Calculate Rashi, Graha, and total Shodhya Pinda."""
    rashi_pinda = sum(score * RASHI_GUNAKARA[i] for i, score in enumerate(scores))
    graha_pinda = sum(scores[graha_signs[planet]] * GRAHA_GUNAKARA[planet] for planet in AV_PLANETS)
    return {
        "rashi_pinda": rashi_pinda,
        "graha_pinda": graha_pinda,
        "shodhya_pinda": rashi_pinda + graha_pinda,
    }


def ashtakavarga(positions: dict, lagna_lon: float) -> dict:
    """Compute BAV by planet and SAV by sign.

    Rahu/Ketu are intentionally excluded: the classical SAV total of 337 uses
    Sun through Saturn plus Lagna contributions.
    """
    sources = _source_signs(positions, lagna_lon)
    bav: dict[str, list[int]] = {}
    source_breakdown: dict[str, dict[str, list[int]]] = {}

    for target, rules in BAV_RULES.items():
        scores = [0] * 12
        source_breakdown[target] = {}
        for source, houses in rules.items():
            source_scores = [0] * 12
            start = sources[source]
            for house in houses:
                idx = (start + house - 1) % 12
                scores[idx] += 1
                source_scores[idx] = 1
            source_breakdown[target][source] = source_scores
        bav[target] = scores

    sav = [sum(bav[planet][i] for planet in AV_PLANETS) for i in range(12)]
    graha_signs = {planet: sources[planet] for planet in AV_PLANETS}
    occupied_signs = set(graha_signs.values())
    shodhana = {}
    pinda = {}
    for planet in AV_PLANETS:
        trikona = trikona_shodhana(bav[planet])
        ekadhipatya = ekadhipatya_shodhana(trikona, occupied_signs)
        shodhana[planet] = {
            "trikona": trikona,
            "ekadhipatya": ekadhipatya,
            "total_after_trikona": sum(trikona),
            "total_after_ekadhipatya": sum(ekadhipatya),
        }
        pinda[planet] = shodhya_pinda(ekadhipatya, graha_signs)

    pinda_rank = sorted(
        [{"planet": planet, **values} for planet, values in pinda.items()],
        key=lambda row: row["shodhya_pinda"],
        reverse=True,
    )
    signs = [
        {
            "index": i,
            "sign": SIGNS[i],
            "sav": sav[i],
            "bav": {planet: bav[planet][i] for planet in AV_PLANETS},
        }
        for i in range(12)
    ]
    return {
        "planets": AV_PLANETS,
        "sources": AV_SOURCES,
        "bav": bav,
        "source_breakdown": source_breakdown,
        "prastara": source_breakdown,
        "sav": sav,
        "signs": signs,
        "raw": {
            "bav": bav,
            "sav": sav,
            "signs": signs,
        },
        "shodhana": shodhana,
        "pinda": pinda,
        "pinda_rank": pinda_rank,
        "totals": {
            "bav": {planet: sum(scores) for planet, scores in bav.items()},
            "sav": sum(sav),
        },
    }
