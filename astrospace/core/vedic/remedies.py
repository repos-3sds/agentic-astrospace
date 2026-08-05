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
* **Manglik is not a generic remedy.** It is a marriage-compatibility flag,
  not a graha-shanti trigger like an active dasha or a debilitation — so it
  is only emitted when a caller explicitly opts in via ``include_manglik``
  (compatibility/dosha-detail contexts), never in the default remedy feed.

Nothing in here predicts events; it answers "what is traditionally done about
this placement", which is the question six of the seven personas actually ask.

Recommendation contract (consumed by the mobile client):
  Each group in ``recommend()["groups"]`` carries a stable
  ``recommendation_id``, a structured ``trigger``, a short and a
  practitioner-depth reason, the raw ``evidence`` behind the reason, a
  ``source_status`` for the *detection* (separate from the practice's own
  convention-dependence), ``tradition_source``, ``convention_dependent``,
  a ``safety_note``, an integer ``priority`` (1 = most relevant, matching
  detection order), and a list of ``practices``. Each practice carries a
  stable ``practice_slug``, ``type``, ``title``, ``instructions``,
  ``cadence``, ``target_count``, ``preferred_day``, ``optional_cost``, and —
  for mantra practices — an ``audio`` metadata block (text/transliteration
  are populated; the actual audio asset is a pending content-production
  task, so ``audio_url`` is null and ``source_status`` says so explicitly
  rather than inventing a path that doesn't exist).
"""
from __future__ import annotations

from .constants import PLANETS
from .doshas import dosha_summary
from .positions import sign_index, sign_name
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

SAFETY_NOTE = (
    "Traditional practice, not a guarantee. Offered as something you may "
    "choose to do — never as a fix you must buy. For health, legal or "
    "financial concerns, please speak to a qualified professional."
)
DOSHA_SAFETY_NOTE = SAFETY_NOTE + " This is a flag, not a verdict."

# Detection source_status by trigger kind, for triggers that are not
# themselves routed through the doshas.py rule KB (which already carries its
# own enrich_rule_result-derived source_status per dosha).
_TRIGGER_SOURCE_STATUS = {
    # An active dasha/antardasha lord is a deterministic Vimshottari
    # computation from the Moon's nakshatra — not convention-dependent.
    "dasha": "verified_common",
    # Debilitation sign is the undisputed 7th-from-exaltation rule.
    "dignity": "verified_common",
    # Combustion orb thresholds vary by classical text and software
    # convention (see strength.COMBUSTION_ORBS).
    "combustion": "convention_dependent",
}

# Remedy types that cost money — surfaced as optional so they never read as a
# required purchase (design_principles.md §4: no manipulation).
_COSTLY_TYPES = {"gem"}


# ── Affliction detection ─────────────────────────────────────────────────────

def afflictions(positions: dict, lagna_lon: float, dasha: dict | None = None,
                include_manglik: bool = False) -> list[dict]:
    """Detect what a remedy could reasonably address.

    Sources, in descending relevance:
      1. the active dasha/antardasha lords — what is live *right now*
      2. classical doshas: gandanta and grahan always; manglik only when
         ``include_manglik=True`` (compatibility/dosha-detail contexts —
         see module docstring)
      3. debilitated planets
      4. combust planets

    Returns a list of dicts with a stable ``kind``/``planet``/``severity``
    shape, plus ``reason_short``, ``reason_practitioner``, ``evidence`` and
    ``source_status``. Severity is only ever "mild" | "moderate" — never
    "severe" — because the product does not escalate; it informs.
    """
    found: list[dict] = []

    # 1. Active periods — most actionable, so listed first.
    current = (dasha or {}).get("current") or {}
    for level, label in (("mahadasha", "main period"), ("antardasha", "sub-period")):
        period = current.get(level) or {}
        lord = period.get("lord")
        if lord in GRAHA_REMEDIES:
            start, end = period.get("start"), period.get("end")
            found.append({
                "kind": "dasha",
                "planet": lord,
                "level": level,
                "severity": "mild",
                "reason_short": f"{lord} is running as your {label}",
                "reason_practitioner": (
                    f"{lord} {level} runs {start} to {end}; traditional practice "
                    f"emphasizes the ruling graha while its period is active."
                ),
                "theme": GRAHA_THEME[lord],
                "period": {"start": start, "end": end},
                "evidence": {"level": level, "lord": lord, "start": start, "end": end},
                "source_status": _TRIGGER_SOURCE_STATUS["dasha"],
            })

    # 2. Doshas — always reported together with their cancellation status.
    doshas = dosha_summary(positions, lagna_lon)

    if include_manglik:
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
                "reason_short": (
                    "A Manglik influence is present, and your chart meets a classical "
                    "exception that offsets it"
                    if cancelled else
                    "A Manglik influence is present — commonly flagged in matching"
                ),
                "reason_practitioner": (
                    f"Mars is active from {len(manglik.get('active_references', []))} of "
                    "3 reference points (Lagna/Moon/Venus); raw severity "
                    f"'{manglik.get('severity')}', net severity "
                    f"'{manglik.get('net_severity')}' after applying "
                    "convention-dependent exception rules."
                ),
                "theme": GRAHA_THEME["Mars"],
                "framing": "This is a flag, not a verdict.",
                "evidence": manglik,
                "source_status": manglik.get("source_status", "convention_dependent"),
            })

    gandanta = doshas.get("gandanta") or {}
    if gandanta.get("active"):
        found.append({
            "kind": "dosha",
            "dosha": "gandanta",
            "planet": "Ketu",
            "severity": "mild",
            "reason_short": "A gandanta (junction) placement is present",
            "reason_practitioner": (
                "One or more of Moon/Lagna/Sun falls within one pada of a "
                "water→fire sign junction: " +
                ", ".join(h["junction"] for h in gandanta.get("hits", [])) + "."
            ),
            "theme": "settling into transitions",
            "framing": "This is a flag, not a verdict.",
            "evidence": gandanta,
            "source_status": gandanta.get("source_status", "convention_dependent"),
        })

    grahan = doshas.get("grahan") or {}
    if grahan.get("active"):
        found.append({
            "kind": "dosha",
            "dosha": "grahan",
            "planet": "Rahu",
            "severity": "mild",
            "reason_short": "A grahan (eclipse) combination is present",
            "reason_practitioner": (
                "Sun or Moon shares a sign with Rahu or Ketu: " +
                ", ".join(
                    f"{h['luminary']}–{h['node']} in {h['sign']} ({h['orb']}° orb)"
                    for h in grahan.get("hits", [])
                ) + "."
            ),
            "theme": GRAHA_THEME["Rahu"],
            "framing": "This is a flag, not a verdict.",
            "evidence": grahan,
            "source_status": grahan.get("source_status", "convention_dependent"),
        })

    # 3 & 4. Weak placements.
    dignities = all_dignities(positions)
    for planet in PLANETS:
        if planet not in positions or planet not in GRAHA_REMEDIES:
            continue

        dignity = dignities.get(planet) or {}
        if dignity.get("dignity") == "Debilitated":
            planet_sign = sign_name(sign_index(positions[planet]["lon"]))
            found.append({
                "kind": "dignity",
                "planet": planet,
                "severity": "moderate",
                "reason_short": f"{planet} is debilitated",
                "reason_practitioner": (
                    f"{planet} occupies {planet_sign}, its sign of debilitation; "
                    "classical texts treat this as reduced functional strength for "
                    f"{planet}'s significations."
                ),
                "theme": GRAHA_THEME[planet],
                "evidence": {
                    "planet": planet, "sign": planet_sign, "dignity": "Debilitated",
                    "longitude": round(positions[planet]["lon"] % 360.0, 4),
                },
                "source_status": _TRIGGER_SOURCE_STATUS["dignity"],
            })

        # The Sun cannot be combust — combustion is proximity *to* the Sun.
        if planet not in ("Sun", "Rahu", "Ketu"):
            combust = combustion_status(planet, positions) or {}
            if combust.get("active"):
                found.append({
                    "kind": "combustion",
                    "planet": planet,
                    "severity": "mild",
                    "reason_short": f"{planet} is combust (close to the Sun)",
                    "reason_practitioner": (
                        f"{planet} is {combust.get('orb')}° from the Sun "
                        f"(threshold {combust.get('threshold')}° for this graha) — "
                        "classical texts call this combustion, weakening the graha's "
                        "significations while so placed."
                    ),
                    "theme": GRAHA_THEME[planet],
                    "evidence": combust,
                    "source_status": _TRIGGER_SOURCE_STATUS["combustion"],
                })

    return found


# ── Recommendation ───────────────────────────────────────────────────────────

def _recommendation_id(item: dict) -> str:
    """Stable id for an affliction, independent of detection order."""
    if item["kind"] == "dasha":
        return f"dasha-{item['level']}-{item['planet'].lower()}"
    if item["kind"] == "dosha":
        return f"dosha-{item['dosha']}"
    if item["kind"] == "dignity":
        return f"dignity-debilitated-{item['planet'].lower()}"
    if item["kind"] == "combustion":
        return f"combustion-{item['planet'].lower()}"
    return f"{item['kind']}-{item.get('planet', 'unknown').lower()}"


def _practices_for(planet: str, affliction: dict) -> list[dict]:
    """Build the concrete practices offered for one affliction."""
    entry = GRAHA_REMEDIES[planet]
    slug_base = planet.lower()
    applies_to = {
        k: v for k, v in (
            ("planet", planet),
            ("dosha", affliction.get("dosha")),
            ("kind", affliction.get("kind")),
        ) if v
    }
    out = [
        {
            "practice_slug": f"{slug_base}-mantra",
            "type": "mantra",
            "title": entry["mantra"],
            "instructions": (
                f"Chant {entry['mantra_count']} times, ideally on {entry['day']} morning."
            ),
            "cadence": "weekly",
            "target_count": entry["mantra_count"],
            "preferred_day": entry["day"],
            "optional_cost": False,
            "audio": {
                "text": entry["mantra"],
                "transliteration": entry["mantra"],
                "language": "sa",
                "count_target": entry["mantra_count"],
                "loop_seconds": None,
                "audio_url": None,
                "source_status": "pending_assets",
                "note": "Text/transliteration are final; recorded audio is a pending content task.",
            },
        },
        {
            "practice_slug": f"{slug_base}-donation",
            "type": "donation",
            "title": f"Donate {entry['donation'].lower()}",
            "instructions": f"Offered on {entry['day']}, according to your means.",
            "cadence": "weekly",
            "target_count": None,
            "preferred_day": entry["day"],
            "optional_cost": False,
        },
        {
            "practice_slug": f"{slug_base}-colour",
            "type": "colour",
            "title": f"Wear {entry['colour'].lower()}",
            "instructions": f"Especially on {entry['day']}.",
            "cadence": "weekly",
            "target_count": None,
            "preferred_day": entry["day"],
            "optional_cost": False,
        },
        {
            "practice_slug": f"{slug_base}-deity",
            "type": "deity",
            "title": f"Prayer to {entry['deity']}",
            "instructions": "A simple prayer at home counts — this is about intention.",
            "cadence": "weekly",
            "target_count": None,
            "preferred_day": None,
            "optional_cost": False,
        },
        {
            "practice_slug": f"{slug_base}-gem",
            "type": "gem",
            "title": entry["gem"],
            "instructions": (
                "Traditionally worn set in "
                f"{entry['metal'].lower()}. Optional, and worth a second opinion "
                "before buying — gemstones are expensive and traditions differ."
            ),
            "cadence": "once",
            "target_count": None,
            "preferred_day": None,
            "optional_cost": True,
        },
    ]

    for practice in out:
        practice.update({
            "planet": planet,
            "applies_to": applies_to,
            "tradition_source": TRADITION_SOURCE,
            "is_convention_dependent": True,
        })
    return out


def recommend(positions: dict, lagna_lon: float, dasha: dict | None = None,
              include_costly: bool = True, include_manglik: bool = False,
              limit: int | None = None) -> dict:
    """Recommend remedies for a chart.

    Args:
        positions: sidereal positions dict (as produced by the chart engine).
        lagna_lon: ascendant longitude.
        dasha: optional ``vimshottari_dasha()`` output — when supplied, the
            active period lords are treated as the most relevant afflictions.
        include_costly: set False to omit gemstones entirely.
        include_manglik: set True only for compatibility/dosha-detail
            contexts. Manglik is a marriage-matching flag, not a general
            graha-shanti trigger, so the default remedy feed never includes
            it (see module docstring and US-PR-003).
        limit: cap the number of affliction groups returned.

    Returns a dict with ``groups`` (trigger + its practices) and a
    ``disclaimer``. Never returns an empty-handed result: a chart with no
    affliction gets a supportive note rather than manufactured problems.
    """
    found = afflictions(positions, lagna_lon, dasha, include_manglik=include_manglik)

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
    for priority, item in enumerate(unique, start=1):
        planet = item.get("planet")
        if planet not in GRAHA_REMEDIES:
            continue
        practices = _practices_for(planet, item)
        if not include_costly:
            practices = [p for p in practices if p["type"] not in _COSTLY_TYPES]

        trigger = {
            k: item[k] for k in ("kind", "planet", "dosha", "level") if k in item
        }
        groups.append({
            "recommendation_id": _recommendation_id(item),
            "trigger": trigger,
            "reason_short": item["reason_short"],
            "reason_practitioner": item["reason_practitioner"],
            "evidence": item["evidence"],
            "source_status": item["source_status"],
            "tradition_source": TRADITION_SOURCE,
            "convention_dependent": True,
            "safety_note": DOSHA_SAFETY_NOTE if item["kind"] == "dosha" else SAFETY_NOTE,
            "priority": priority,
            "practices": practices,
        })

    return {
        "groups": groups,
        "count": len(groups),
        "note": (
            None if groups else
            "Nothing in your chart is asking for a remedy right now."
        ),
        "disclaimer": SAFETY_NOTE,
    }


def catalog() -> list[dict]:
    """The full remedy catalog in a shape that maps onto the ``remedies`` table.

    Useful for seeding; keeps the canonical associations in one place instead
    of duplicating them in a migration. Field names here (``slug``,
    ``remedy_type``) match ``astrospace.db.models.Remedy`` columns exactly —
    do not rename without a matching migration.
    """
    rows: list[dict] = []
    for planet in GRAHA_REMEDIES:
        for practice in _practices_for(planet, {"kind": "graha"}):
            rows.append({
                "slug": practice["practice_slug"],
                "title": practice["title"],
                "remedy_type": practice["type"],
                "instructions": practice["instructions"],
                "applies_to": {"planet": planet},
                "tradition_source": TRADITION_SOURCE,
                "default_target_count": practice["target_count"],
                "cadence": practice["cadence"],
                "is_convention_dependent": True,
                "language": "en",
            })
    return rows
