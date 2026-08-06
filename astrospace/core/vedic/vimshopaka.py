"""Vimshopaka Bala — weighted 20-point dignity score across a group of vargas.

Vargavimshopakam ("the twenty of the divisions") answers a narrower question
than Shadbala: not "how strong is this planet overall" but "how consistently
well-placed is it across its divisional charts". Four schemes are classical,
each summing its named vargas' weights to exactly 20:

  Shadvarga    (6 vargas):  D1, D2, D3, D9, D12, D30
  Saptavarga   (7 vargas):  D1, D2, D3, D7, D9, D12, D30
  Dashavarga  (10 vargas):  D1, D2, D3, D7, D9, D10, D12, D16, D30, D60
  Shodashavarga (16 vargas): all sixteen BPHS divisions (D1..D60)

Per-varga weights are the widely-published table (see WEIGHTS below); each
scheme's weights sum to 20 by construction — a useful self-check.

Dignity fraction table (how much of a division's weight a planet actually
earns): published secondary sources disagree on the exact fractions per
dignity step (Exalted/Moolatrikona/Own/Great Friend/Friend/Neutral/Enemy/
Great Enemy/Debilitated) — see docs/backend_astro_depth_checklist_2026-08-06.md
T1.1 for the sources checked. Rather than pick one contested fraction table
and present it as settled, AstroSpace reuses its own existing 0-100 dignity
ladder (:data:`strength.DIGNITY_SCORES`) as the fraction (score / 100) —
the same ladder every other dignity-aware calculation in this codebase
already uses. This is a deliberate internal-consistency convention, not a
transcribed classical fraction table, and is marked ``source_status:
convention_dependent`` for that reason.

Dignity per division is judged the same way :func:`strength.dignity_of`
judges it for D1 — exaltation/moolatrikona-sign/own-sign by direct sign
match, else the panchadha (five-fold) relation to that division's sign
lord, computed using *both* planets' positions translated into that same
division (not their D1 positions) — the technically correct reading of a
divisional-chart relationship, not a D1 shortcut.
"""
from __future__ import annotations

from .constants import EXALTATION, OWN_SIGNS, SIGN_LORDS
from .strength import DIGNITY_SCORES, dignity_of, panchadha_relation
from .vargas import VARGA_FUNCTIONS, VARGA_INFO

# Per-varga weights, cited to the commonly-published Vimshopaka table
# (see module docstring). Each scheme sums to exactly 20.
WEIGHTS: dict[str, dict[str, float]] = {
    "shadvarga": {"D1": 6, "D2": 2, "D3": 4, "D9": 5, "D12": 2, "D30": 1},
    "saptavarga": {"D1": 5, "D2": 2, "D3": 3, "D7": 2.5, "D9": 4.5, "D12": 2, "D30": 1},
    "dashavarga": {
        "D1": 3, "D2": 1.5, "D3": 1.5, "D7": 1.5, "D9": 1.5, "D10": 1.5,
        "D12": 1.5, "D16": 1.5, "D30": 1.5, "D60": 5,
    },
    "shodashavarga": {
        "D1": 3.5, "D2": 1, "D3": 1, "D4": 0.5, "D7": 0.5, "D9": 3, "D10": 0.5,
        "D12": 0.5, "D16": 2, "D20": 0.5, "D24": 0.5, "D27": 0.5, "D30": 1,
        "D40": 0.5, "D45": 0.5, "D60": 4,
    },
}

_NODES = {"Rahu", "Ketu"}

# Vimshopaka is defined for the seven classical grahas; nodes are commonly
# excluded in classical sources, but AstroSpace scores them at Neutral
# (matching strength.dignity_of's own nodal convention) rather than omitting
# them, so every planet in a chart gets a consistent payload shape.
SCORED_PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

BAND_LABELS = [
    (5.0, "incapable of producing results"),
    (10.0, "minimal results"),
    (15.0, "moderate results"),
    (20.0001, "full results"),
]


def _band(score: float) -> str:
    for ceiling, label in BAND_LABELS:
        if score < ceiling:
            return label
    return BAND_LABELS[-1][1]


def dignity_in_varga(planet: str, varga: str, positions: dict) -> str:
    """Dignity label of ``planet`` in the named divisional chart.

    For D1, delegates to strength.dignity_of() as-is — it already handles
    the moolatrikona degree-range correctly, and there is no reason to
    reimplement it. For every other division there is no published
    degree-range for "moolatrikona within a varga" (that refinement is a
    rashi-chart-only concept), so the varga ladder collapses to Exalted >
    Own > panchadha relation > Debilitated, judged on the varga sign, with
    the dispositor's position also translated into that same division
    (not its D1 sign) for the panchadha (five-fold) relation.
    """
    if planet in _NODES:
        return "Neutral"

    if varga == "D1":
        return dignity_of(planet, positions[planet]["lon"], positions)["dignity"]

    varga_fn = VARGA_FUNCTIONS[varga]
    sign = varga_fn(positions[planet]["lon"])

    exalt_sign, _deep = EXALTATION[planet]
    if sign == exalt_sign:
        return "Exalted"
    if sign == (exalt_sign + 6) % 12:
        return "Debilitated"
    if sign in OWN_SIGNS[planet]:
        return "Own"

    dispositor = SIGN_LORDS[sign]
    dispositor_sign = varga_fn(positions[dispositor]["lon"])
    return panchadha_relation(planet, sign, dispositor, dispositor_sign)


def _scheme_score(planet: str, scheme: str, positions: dict) -> dict:
    weights = WEIGHTS[scheme]
    breakdown = []
    total = 0.0
    for varga, weight in weights.items():
        dignity = dignity_in_varga(planet, varga, positions)
        fraction = DIGNITY_SCORES[dignity] / 100.0
        earned = round(weight * fraction, 4)
        total += earned
        breakdown.append({
            "varga": varga,
            "varga_name": VARGA_INFO[varga]["name"],
            "weight": weight,
            "dignity": dignity,
            "earned": earned,
        })
    total = round(total, 2)
    return {
        "scheme": scheme,
        "score": total,
        "max": 20.0,
        "band": _band(total),
        "breakdown": breakdown,
    }


def vimshopaka_bala(positions: dict, scheme: str = "shodashavarga") -> dict:
    """Vimshopaka Bala for every planet in ``positions``, in one scheme.

    Args:
        positions: sidereal positions dict (as produced by the chart engine)
            — must include every planet referenced by the chosen scheme's
            dispositor lookups (i.e. the full classical seven plus nodes).
        scheme: one of "shadvarga", "saptavarga", "dashavarga",
            "shodashavarga" (default — the full 16-varga reading).

    Returns ``{"scheme", "planets": {planet: {...}}, "source_status",
    "notes"}``. Each planet's entry has ``score`` (0-20), ``band`` (the
    classical 4-tier interpretation), and ``breakdown`` (per-varga dignity
    and points earned, so the working is inspectable, not just the total).
    """
    if scheme not in WEIGHTS:
        raise ValueError(f"Unknown Vimshopaka scheme {scheme!r}; options: {sorted(WEIGHTS)}")

    planets = {
        planet: _scheme_score(planet, scheme, positions)
        for planet in SCORED_PLANETS
        if planet in positions
    }
    return {
        "scheme": scheme,
        "planets": planets,
        "source_status": "convention_dependent",
        "notes": [
            "Per-varga weights follow the commonly-published Vimshopaka table "
            "(each scheme sums to 20); the dignity-to-fraction mapping reuses "
            "AstroSpace's existing 0-100 dignity ladder (strength.DIGNITY_SCORES) "
            "rather than a separately-sourced classical fraction table, since "
            "published fraction tables disagree across texts.",
            "Bands: <5 incapable of producing results, 5-10 minimal, "
            "10-15 moderate, 15-20 full — classical 4-tier interpretation.",
            "Rahu/Ketu are scored at a flat Neutral dignity in every division "
            "(nodal dignity conventions vary; classical Vimshopaka texts often "
            "omit nodes rather than score them) — treat node scores as "
            "indicative only, not a classical claim.",
        ],
    }


def all_schemes(positions: dict) -> dict:
    """Vimshopaka Bala under all four schemes, for comparison."""
    return {scheme: vimshopaka_bala(positions, scheme) for scheme in WEIGHTS}
