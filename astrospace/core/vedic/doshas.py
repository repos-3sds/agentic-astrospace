"""Common dosha calculations."""
from __future__ import annotations

from .positions import house_from_lagna, sign_index, sign_name
from ...knowledge.vedic_rules import enrich_rule_result

MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}

# Mars dignity signs used by manglik exceptions: own (Aries, Scorpio),
# exalted (Capricorn).
_MARS_STRONG_SIGNS = {0: "own sign (Aries)", 7: "own sign (Scorpio)", 9: "exalted (Capricorn)"}

# Severity downgrade ladder for manglik exceptions: one step, never below
# "mild" while references are active.
_SEVERITY_DOWNGRADE = {"strong": "moderate", "moderate": "mild", "mild": "mild", "none": "none"}

# ── Gandanta ─────────────────────────────────────────────────────────────────

PADA_SPAN = 10.0 / 3.0  # 3°20'
GANDANTA_SEVERE_ORB = 0.8      # 0°48'
GANDANTA_MODERATE_ORB = 5.0 / 3.0  # 1°40'

# Water→fire sign junctions (sidereal longitude of the junction point).
GANDANTA_JUNCTIONS = [
    {
        "lon": 120.0,
        "name": "Ashlesha–Magha",
        "signs": "Cancer→Leo",
        "abhukta_mula": False,
    },
    {
        "lon": 240.0,
        "name": "Jyeshtha–Moola",
        "signs": "Scorpio→Sagittarius",
        "abhukta_mula": True,
    },
    {
        "lon": 0.0,
        "name": "Revati–Ashwini",
        "signs": "Pisces→Aries",
        "abhukta_mula": False,
    },
]


def _gandanta_hit(body: str, lon: float) -> dict | None:
    """Return a gandanta hit record if lon falls in a gandanta zone."""
    for junction in GANDANTA_JUNCTIONS:
        # Signed offset from junction in (-180, 180]; negative = water side.
        delta = ((lon - junction["lon"] + 180.0) % 360.0) - 180.0
        if -PADA_SPAN <= delta < PADA_SPAN:
            dist = abs(delta)
            if dist <= GANDANTA_SEVERE_ORB:
                severity = "severe"
            elif dist <= GANDANTA_MODERATE_ORB:
                severity = "moderate"
            else:
                severity = "mild"
            side = "water (last pada)" if delta < 0 else "fire (first pada)"
            return {
                "body": body,
                "junction": junction["name"],
                "signs": junction["signs"],
                "side": side,
                "degrees_from_junction": round(dist, 4),
                "severity": severity,
                "abhukta_mula": junction["abhukta_mula"],
            }
    return None


def gandanta_dosha(positions: dict, lagna_lon: float) -> dict:
    """Gandanta: birth points at the water→fire sign/nakshatra junctions.

    Zones: last 3°20' (one pada) of the water sign and first 3°20' of the
    fire sign at Ashlesha→Magha, Jyeshtha→Moola, Revati→Ashwini.
    Checks Moon (primary), Lagna, and Sun.
    """
    bodies = [("Moon", positions["Moon"]["lon"]), ("Lagna", lagna_lon)]
    if "Sun" in positions:
        bodies.append(("Sun", positions["Sun"]["lon"]))

    hits = []
    for body, lon in bodies:
        hit = _gandanta_hit(body, lon)
        if hit:
            hits.append(hit)

    severity_rank = {"severe": 3, "moderate": 2, "mild": 1}
    overall = "none"
    if hits:
        overall = max(hits, key=lambda h: severity_rank[h["severity"]])["severity"]

    notes = []
    if any(h["abhukta_mula"] for h in hits):
        notes.append(
            "Jyeshtha–Moola gandanta (Abhukta Mula) is traditionally considered the most intense of the three junctions."
        )

    return enrich_rule_result("gandanta_dosha", {
        "name": "Gandanta Dosha",
        "active": bool(hits),
        "severity": overall,
        "hits": hits,
        "bodies_checked": [body for body, _lon in bodies],
        "rule": (
            "Moon, Lagna, or Sun within one pada (3°20') on either side of a "
            "water→fire junction: Ashlesha–Magha, Jyeshtha–Moola, Revati–Ashwini."
        ),
        "verified": False,
        "notes": notes,
    })


# ── Grahan (eclipse) dosha ───────────────────────────────────────────────────

GRAHAN_STRONG_ORB = 5.0
GRAHAN_MODERATE_ORB = 10.0


def grahan_dosha(positions: dict) -> dict:
    """Grahan dosha: Sun or Moon conjunct Rahu or Ketu in the same sign."""
    hits = []
    for luminary in ("Sun", "Moon"):
        if luminary not in positions:
            continue
        lum_lon = positions[luminary]["lon"]
        for node in ("Rahu", "Ketu"):
            if node not in positions:
                continue
            node_lon = positions[node]["lon"]
            if sign_index(lum_lon) != sign_index(node_lon):
                continue
            orb = abs(((lum_lon - node_lon + 180.0) % 360.0) - 180.0)
            if orb < GRAHAN_STRONG_ORB:
                severity = "strong"
            elif orb < GRAHAN_MODERATE_ORB:
                severity = "moderate"
            else:
                severity = "mild"
            hits.append({
                "luminary": luminary,
                "node": node,
                "sign": sign_name(sign_index(lum_lon)),
                "orb": round(orb, 4),
                "severity": severity,
            })

    severity_rank = {"strong": 3, "moderate": 2, "mild": 1}
    overall = "none"
    if hits:
        overall = max(hits, key=lambda h: severity_rank[h["severity"]])["severity"]

    return enrich_rule_result("grahan_dosha", {
        "name": "Grahan (Eclipse) Dosha",
        "active": bool(hits),
        "severity": overall,
        "hits": hits,
        "rule": (
            "Sun or Moon in the same sign as Rahu or Ketu. "
            "Orb grading: <5° strong, <10° moderate, else mild (same sign but wide)."
        ),
        "verified": False,
        "notes": [],
    })


# ── Manglik ──────────────────────────────────────────────────────────────────

def _manglik_exceptions(positions: dict, mars_sign: int) -> list[dict]:
    """Widely published Manglik cancellation/weakening rules.

    All are convention-dependent; sources disagree on the exact lists, so each
    entry is tagged source_status="convention_dependent".
    """
    exceptions = []

    # (a) Mars in own sign or exalted.
    dignity = _MARS_STRONG_SIGNS.get(mars_sign)
    exceptions.append({
        "rule": "Mars in own sign (Aries, Scorpio) or exalted (Capricorn)",
        "applies": dignity is not None,
        "detail": (
            f"Mars in {sign_name(mars_sign)} — {dignity}; dosha weakened."
            if dignity else f"Mars in {sign_name(mars_sign)} — neither own sign nor exalted."
        ),
        "source_status": "convention_dependent",
    })

    # (b) Jupiter aspects Mars by graha drishti (Mars in Jupiter's 5/7/9).
    jupiter = positions.get("Jupiter")
    if jupiter is None:
        exceptions.append({
            "rule": "Jupiter aspects Mars (graha drishti 5/7/9)",
            "applies": False,
            "detail": "Jupiter position unavailable; aspect not evaluated.",
            "source_status": "convention_dependent",
        })
    else:
        jupiter_sign = sign_index(jupiter["lon"])
        drishti_house = house_from_lagna(mars_sign, jupiter_sign)
        applies = drishti_house in {5, 7, 9}
        exceptions.append({
            "rule": "Jupiter aspects Mars (graha drishti 5/7/9)",
            "applies": applies,
            "detail": (
                f"Mars is {drishti_house} signs from Jupiter "
                f"({sign_name(jupiter_sign)} → {sign_name(mars_sign)})"
                + ("; Jupiter's drishti falls on Mars, dosha weakened." if applies
                   else "; no Jupiter drishti on Mars.")
            ),
            "source_status": "convention_dependent",
        })

    # (c) Mars conjunct Moon in the same sign.
    moon_sign = sign_index(positions["Moon"]["lon"])
    conj = moon_sign == mars_sign
    exceptions.append({
        "rule": "Mars conjunct Moon in the same sign",
        "applies": conj,
        "detail": (
            f"Mars and Moon both in {sign_name(mars_sign)}; dosha weakened."
            if conj else "Mars and Moon in different signs."
        ),
        "source_status": "convention_dependent",
    })

    return exceptions


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

    exceptions = _manglik_exceptions(positions, mars_sign)
    any_exception = any(exc["applies"] for exc in exceptions)

    # Net severity: raw severity downgraded one step when any exception
    # applies, never below "mild" while references are active.
    net_severity = severity
    if any_exception and severity != "none":
        net_severity = _SEVERITY_DOWNGRADE[severity]
        if active_refs and net_severity == "none":
            net_severity = "mild"

    notes = []
    if any_exception:
        applied = [exc["rule"] for exc in exceptions if exc["applies"]]
        notes.append(
            "Exception rules applied (convention-dependent): " + "; ".join(applied) + ". "
            "Raw severity is kept in 'severity'; 'net_severity' is downgraded one step "
            "and never below 'mild' while any reference is active."
        )
    else:
        notes.append("No cancellation/exception rule applies; net_severity equals severity.")

    return enrich_rule_result("manglik_dosha", {
        "name": "Manglik / Kuja Dosha",
        "active": active_count > 0,
        "severity": severity,
        "net_severity": net_severity,
        "active_references": active_refs,
        "checks": checks,
        "exceptions": exceptions,
        "rule": "Mars in houses 1, 2, 4, 7, 8, or 12 from Lagna, Moon, or Venus.",
        "verified": True,
        "notes": notes,
    })


def dosha_summary(positions: dict, lagna_lon: float) -> dict:
    return {
        "manglik": manglik_dosha(positions, lagna_lon),
        "gandanta": gandanta_dosha(positions, lagna_lon),
        "grahan": grahan_dosha(positions),
    }
