"""Upaya (remedy) engine — maps computed afflictions to traditional practices.

Design constraints this module enforces (design_principles.md §4, §6):

* Remedies are offered as **traditional practice, never as a guarantee**, and
  every recommendation carries its provenance and a convention-dependent flag.
* **No fear leverage.** Nothing here frames a remedy as averting disaster, and
  no remedy is gated behind payment. Gemstones in particular are marked as
  expensive and optional so they never read as a required purchase.
* **A dosha is a flag, not a verdict.** When a dosha has a classical
  cancellation the engine says so, and lowers rather than raises urgency.
* **Never medical, legal or financial.** Afflictions are described in terms of
  temperament and timing, never health outcomes, and never longevity.

Nothing in here predicts events; it answers "what is traditionally done about
this placement", which is the question six of the seven personas actually ask.
"""
from __future__ import annotations

from .constants import PLANETS
from .doshas import dosha_summary
from .strength import all_dignities, combustion_status

# ── Catalog ──────────────────────────────────────────────────────────────────
# Per-graha associations. These are the standard, widely-attested pairings
# (mantra, gem, day, donation, colour, deity). Regional traditions differ on
# detail, hence is_convention_dependent on the catalog entries.

GRAHA_REMEDIES: dict[str, dict] = {
    "Sun": {
        "mantra": "Om Suryaya Namah",
        "mantra_count": 108,
        "day": "Sunday",
        "gem": "Ruby",
        "metal": "Copper",
        "colour": "Deep red / saffron",
        "donation": "Wheat or jaggery",
        "deity": "Surya",
    },
    "Moon": {
        "mantra": "Om Chandraya Namah",
        "mantra_count": 108,
        "day": "Monday",
        "gem": "Pearl",
        "metal": "Silver",
        "colour": "White",
        "donation": "Rice, milk or white cloth",
        "deity": "Shiva",
    },
    "Mars": {
        "mantra": "Om Angarakaya Namah",
        "mantra_count": 108,
        "day": "Tuesday",
        "gem": "Red coral",
        "metal": "Copper",
        "colour": "Red",
        "donation": "Masoor dal or red cloth",
        "deity": "Hanuman",
    },
    "Mercury": {
        "mantra": "Om Budhaya Namah",
        "mantra_count": 108,
        "day": "Wednesday",
        "gem": "Emerald",
        "metal": "Bronze",
        "colour": "Green",
        "donation": "Green gram or green cloth",
        "deity": "Vishnu",
    },
    "Jupiter": {
        "mantra": "Om Gurave Namah",
        "mantra_count": 108,
        "day": "Thursday",
        "gem": "Yellow sapphire",
        "metal": "Gold",
        "colour": "Yellow",
        "donation": "Turmeric, chana dal or yellow cloth",
        "deity": "Brihaspati",
    },
    "Venus": {
        "mantra": "Om Shukraya Namah",
        "mantra_count": 108,
        "day": "Friday",
        "gem": "Diamond or white sapphire",
        "metal": "Silver",
        "colour": "White / pastel",
        "donation": "Rice, curd or white cloth",
        "deity": "Lakshmi",
    },
    "Saturn": {
        "mantra": "Om Sham Shanaishcharaya Namah",
        "mantra_count": 108,
        "day": "Saturday",
        "gem": "Blue sapphire",
        "metal": "Iron",
        "colour": "Dark blue / black",
        "donation": "Black sesame, mustard oil or black cloth",
        "deity": "Shani (and Hanuman)",
    },
    "Rahu": {
        "mantra": "Om Rahave Namah",
        "mantra_count": 108,
        "day": "Saturday",
        "gem": "Hessonite",
        "metal": "Lead",
        "colour": "Smoky grey",
        "donation": "Mustard, blankets",
        "deity": "Durga",
    },
    "Ketu": {
        "mantra": "Om Ketave Namah",
        "mantra_count": 108,
        "day": "Tuesday",
        "gem": "Cat's eye",
        "metal": "Mixed",
        "colour": "Multicolour / grey",
        "donation": "Sesame, blankets",
        "deity": "Ganesha",
    },
}

# Plain-language framing per graha. Deliberately about temperament and
# approach — never health, money or longevity outcomes.
GRAHA_THEME: dict[str, str] = {
    "Sun": "confidence and visibility",
    "Moon": "emotional steadiness",
    "Mars": "patience with conflict and haste",
    "Mercury": "clear communication and paperwork",
    "Jupiter": "perspective and good counsel",
    "Venus": "ease in relationships and comfort",
    "Saturn": "patience with slow, effortful stretches",
    "Rahu": "avoiding shortcuts and over-reach",
    "Ketu": "staying grounded when things feel scattered",
}

TRADITION_SOURCE = "Classical graha-shanti practice (regional variants exist)"

# Remedy types that cost money — surfaced as optional so they never read as a
# required purchase (design_principles.md §4: no manipulation).
_COSTLY_TYPES = {"gem"}


# ── Affliction detection ─────────────────────────────────────────────────────

def afflictions(positions: dict, lagna_lon: float,
                dasha: dict | None = None) -> list[dict]:
    """Detect what a remedy could reasonably address.

    Sources, in descending relevance:
      1. the active dasha/antardasha lords — what is live *right now*
      2. classical doshas (manglik, gandanta, grahan), with cancellation status
      3. debilitated planets
      4. combust planets

    Returns a list of dicts with a stable ``kind``/``planet``/``severity``
    shape. Severity is only ever "mild" | "moderate" — never "severe" — because
    the product does not escalate; it informs.
    """
    found: list[dict] = []

    # 1. Active periods — most actionable, so listed first.
    current = (dasha or {}).get("current") or {}
    for level, label in (("mahadasha", "main period"), ("antardasha", "sub-period")):
        period = current.get(level) or {}
        lord = period.get("lord")
        if lord in GRAHA_REMEDIES:
            found.append({
                "kind": "dasha",
                "planet": lord,
                "severity": "mild",
                "reason": f"{lord} is running as your {label}",
                "theme": GRAHA_THEME[lord],
                "period": {"start": period.get("start"), "end": period.get("end")},
            })

    # 2. Doshas — always reported together with their cancellation status.
    doshas = dosha_summary(positions, lagna_lon)

    manglik = doshas.get("manglik") or {}
    if manglik.get("active"):
        # net_severity already reflects the exception ladder in doshas.py; a
        # downgrade to "none" means the classical exception fully offsets it.
        cancelled = (
            manglik.get("net_severity") == "none"
            or manglik.get("net_severity") != manglik.get("severity")
        )
        found.append({
            "kind": "dosha",
            "dosha": "manglik",
            "planet": "Mars",
            "severity": "mild" if cancelled else "moderate",
            "cancelled": cancelled,
            "reason": (
                "A Manglik influence is present, and your chart meets a classical "
                "exception that offsets it"
                if cancelled else
                "A Manglik influence is present — commonly flagged in matching"
            ),
            "theme": GRAHA_THEME["Mars"],
            "framing": "This is a flag, not a verdict.",
        })

    gandanta = doshas.get("gandanta") or {}
    if gandanta.get("active"):
        found.append({
            "kind": "dosha",
            "dosha": "gandanta",
            "planet": "Ketu",
            "severity": "mild",
            "reason": "A gandanta (junction) placement is present",
            "theme": "settling into transitions",
            "framing": "This is a flag, not a verdict.",
        })

    grahan = doshas.get("grahan") or {}
    if grahan.get("active"):
        found.append({
            "kind": "dosha",
            "dosha": "grahan",
            "planet": "Rahu",
            "severity": "mild",
            "reason": "A grahan (eclipse) combination is present",
            "theme": GRAHA_THEME["Rahu"],
            "framing": "This is a flag, not a verdict.",
        })

    # 3 & 4. Weak placements.
    dignities = all_dignities(positions)
    for planet in PLANETS:
        if planet not in positions or planet not in GRAHA_REMEDIES:
            continue

        if (dignities.get(planet) or {}).get("dignity") == "Debilitated":
            found.append({
                "kind": "dignity",
                "planet": planet,
                "severity": "moderate",
                "reason": f"{planet} is debilitated",
                "theme": GRAHA_THEME[planet],
            })

        # The Sun cannot be combust — combustion is proximity *to* the Sun.
        if planet not in ("Sun", "Rahu", "Ketu"):
            combust = combustion_status(planet, positions) or {}
            if combust.get("active"):
                found.append({
                    "kind": "combustion",
                    "planet": planet,
                    "severity": "mild",
                    "reason": f"{planet} is combust (close to the Sun)",
                    "theme": GRAHA_THEME[planet],
                })

    return found


# ── Recommendation ───────────────────────────────────────────────────────────

def _remedies_for(planet: str, affliction: dict) -> list[dict]:
    """Build the concrete practices offered for one affliction."""
    entry = GRAHA_REMEDIES[planet]
    slug_base = planet.lower()
    out = [
        {
            "slug": f"{slug_base}-mantra",
            "remedy_type": "mantra",
            "title": entry["mantra"],
            "instructions": (
                f"Chant {entry['mantra_count']} times, ideally on {entry['day']} morning."
            ),
            "cadence": "weekly",
            "optional_cost": False,
        },
        {
            "slug": f"{slug_base}-donation",
            "remedy_type": "donation",
            "title": f"Donate {entry['donation'].lower()}",
            "instructions": f"Offered on {entry['day']}, according to your means.",
            "cadence": "weekly",
            "optional_cost": False,
        },
        {
            "slug": f"{slug_base}-colour",
            "remedy_type": "colour",
            "title": f"Wear {entry['colour'].lower()}",
            "instructions": f"Especially on {entry['day']}.",
            "cadence": "weekly",
            "optional_cost": False,
        },
        {
            "slug": f"{slug_base}-deity",
            "remedy_type": "deity",
            "title": f"Prayer to {entry['deity']}",
            "instructions": "A simple prayer at home counts — this is about intention.",
            "cadence": "weekly",
            "optional_cost": False,
        },
        {
            "slug": f"{slug_base}-gem",
            "remedy_type": "gem",
            "title": entry["gem"],
            "instructions": (
                "Traditionally worn set in "
                f"{entry['metal'].lower()}. Optional, and worth a second opinion "
                "before buying — gemstones are expensive and traditions differ."
            ),
            "cadence": "once",
            "optional_cost": True,
        },
    ]

    for remedy in out:
        remedy.update({
            "planet": planet,
            "applies_to": {
                k: v for k, v in (
                    ("planet", planet),
                    ("dosha", affliction.get("dosha")),
                    ("kind", affliction.get("kind")),
                ) if v
            },
            "tradition_source": TRADITION_SOURCE,
            "is_convention_dependent": True,
        })
    return out


def recommend(positions: dict, lagna_lon: float, dasha: dict | None = None,
              include_costly: bool = True, limit: int | None = None) -> dict:
    """Recommend remedies for a chart.

    Args:
        positions: sidereal positions dict (as produced by the chart engine).
        lagna_lon: ascendant longitude.
        dasha: optional ``vimshottari_dasha()`` output — when supplied, the
            active period lords are treated as the most relevant afflictions.
        include_costly: set False to omit gemstones entirely.
        limit: cap the number of affliction groups returned.

    Returns a dict with ``groups`` (affliction + its practices) and a
    ``disclaimer``. Never returns an empty-handed result: a chart with no
    affliction gets a supportive note rather than manufactured problems.
    """
    found = afflictions(positions, lagna_lon, dasha)

    # De-duplicate by (kind, planet, dosha) while preserving detection order.
    seen: set[tuple] = set()
    unique: list[dict] = []
    for item in found:
        key = (item["kind"], item.get("planet"), item.get("dosha"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    if limit is not None:
        unique = unique[:limit]

    groups = []
    for item in unique:
        planet = item.get("planet")
        if planet not in GRAHA_REMEDIES:
            continue
        practices = _remedies_for(planet, item)
        if not include_costly:
            practices = [p for p in practices if p["remedy_type"] not in _COSTLY_TYPES]
        groups.append({"affliction": item, "remedies": practices})

    return {
        "groups": groups,
        "count": len(groups),
        "note": (
            None if groups else
            "Nothing in your chart is asking for a remedy right now."
        ),
        "disclaimer": (
            "Traditional practice, not a guarantee. These are offered as "
            "something you may choose to do — never as a fix you must buy. "
            "For health, legal or financial concerns, please speak to a "
            "qualified professional."
        ),
    }


def catalog() -> list[dict]:
    """The full remedy catalog in a shape that maps onto the ``remedies`` table.

    Useful for seeding; keeps the canonical associations in one place instead
    of duplicating them in a migration.
    """
    rows: list[dict] = []
    for planet in GRAHA_REMEDIES:
        for remedy in _remedies_for(planet, {"kind": "graha"}):
            rows.append({
                "slug": remedy["slug"],
                "title": remedy["title"],
                "remedy_type": remedy["remedy_type"],
                "instructions": remedy["instructions"],
                "applies_to": {"planet": planet},
                "tradition_source": TRADITION_SOURCE,
                "default_target_count": (
                    GRAHA_REMEDIES[planet]["mantra_count"]
                    if remedy["remedy_type"] == "mantra" else None
                ),
                "cadence": remedy["cadence"],
                "is_convention_dependent": True,
                "language": "en",
            })
    return rows
