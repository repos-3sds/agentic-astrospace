"""
Context Engine assembler.

Given a VedicChart and one or more domains, produce a ContextBundle: the
curated, domain-scoped slice of the chart a specialist astrologer would put on
the table before judging — house lords and occupants, karaka condition,
domain-varga placements, only the yogas/doshas that speak to this domain, the
dasha chain's relevance, current gochara for the domain's planets, arudhas,
and the KB references that authorize the reading.

Everything returned is a plain dict (JSON-serializable) so the bundle drops
straight into agent state (LangGraph checkpointing) or an API payload.

Cost profile: uses only cheap chart sections. Gochara uses a single ephemeris
snapshot (no 365-day scans); pass include_gochara=False to skip it entirely,
or supply precomputed transit_positions to reuse a snapshot across domains.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import swisseph as swe

from ..core.vedic.constants import SIGN_LORDS
from ..core.vedic.gocharam import gochara_rules
from ..core.vedic.gocharam.strength import (
    apply_ashtakavarga_context,
    ashtakavarga_transit_support,
)
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import (
    degree_in_sign, house_from_lagna, sign_index, sign_name,
)
from ..core.vedic.strength import all_dignities, combustion_status
from ..core.vedic.positions import sidereal_positions
from ..core.vedic.vargas import varga_sign
from .kb import get_knowledge_base
from .taxonomy import DomainSpec, get_domain, taxonomy_version

_KARAKA_NAMES = {
    "AK": "Atmakaraka", "AmK": "Amatyakaraka", "BK": "Bhratrikaraka",
    "MK": "Matrikaraka", "PK": "Putrakaraka", "PiK": "Pitrikaraka",
    "GK": "Gnatikaraka", "DK": "Darakaraka",
}


def _jd_from_dt(dt: datetime) -> float:
    dt_utc = dt.astimezone(timezone.utc)
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)


def _planet_brief(planet: str, positions: dict, lagna_sign: int,
                  dignities: dict) -> dict:
    lon = positions[planet]["lon"]
    s = sign_index(lon)
    nak = nakshatra_of(lon)
    combust = combustion_status(planet, positions)
    return {
        "planet": planet,
        "sign": sign_name(s),
        "degree_in_sign": round(degree_in_sign(lon), 2),
        "house": house_from_lagna(s, lagna_sign),
        "nakshatra": nak["name"],
        "dignity": dignities.get(planet, {}).get("dignity"),
        "retrograde": bool(positions[planet].get("retrograde")),
        "combust": bool(combust.get("active")),
    }


def _house_analysis(house: int, lagna_sign: int, positions: dict,
                    dignities: dict, tier: str) -> dict:
    house_sign = (lagna_sign + house - 1) % 12
    lord = SIGN_LORDS[house_sign]
    occupants = [
        planet for planet, data in positions.items()
        if house_from_lagna(sign_index(data["lon"]), lagna_sign) == house
    ]
    lord_brief = _planet_brief(lord, positions, lagna_sign, dignities)
    return {
        "house": house,
        "tier": tier,
        "sign": sign_name(house_sign),
        "lord": lord,
        "lord_placement": lord_brief,
        "lord_in_dusthana": lord_brief["house"] in (6, 8, 12),
        "occupants": occupants,
    }


def _varga_placements(spec: DomainSpec, focus_planets: list[str],
                      positions: dict, lagna_lon: float) -> dict:
    out: dict[str, Any] = {}
    for varga in spec.all_vargas:
        lagna_v = varga_sign(varga, lagna_lon)
        rows = {}
        for planet in focus_planets:
            s = varga_sign(varga, positions[planet]["lon"])
            rows[planet] = {
                "sign": sign_name(s),
                "house": house_from_lagna(s, lagna_v),
                "own_or_exalted_hint": SIGN_LORDS[s] == planet,
            }
        out[varga] = {
            "tier": "primary" if varga in spec.vargas_primary else "supporting",
            "lagna_sign": sign_name(lagna_v),
            "planets": rows,
        }
    return out


def _filter_rules(rows: list[dict], spec: DomainSpec) -> list[dict]:
    categories = set(spec.yoga_categories)
    rule_ids = set(spec.rule_ids)
    picked = []
    for row in rows:
        if row.get("category") in categories or row.get("rule_id") in rule_ids:
            picked.append({
                "name": row.get("name"),
                "rule_id": row.get("rule_id"),
                "category": row.get("category"),
                "active": row.get("active"),
                "strength": row.get("strength"),
                "triggers": row.get("triggers", []),
                "planets": row.get("planets", []),
                "verified": row.get("verified"),
            })
    # Active first, then by name for stable output.
    picked.sort(key=lambda r: (not r["active"], r.get("name") or ""))
    return picked


def _filter_doshas(doshas: dict, spec: DomainSpec) -> list[dict]:
    picked = []
    for key, row in doshas.items():
        if not isinstance(row, dict):
            continue
        if row.get("rule_id") in set(spec.rule_ids):
            picked.append({
                "name": row.get("name", key),
                "rule_id": row.get("rule_id"),
                "active": row.get("active"),
                "severity": row.get("net_severity", row.get("severity")),
                "verified": row.get("verified"),
            })
    return picked


def _dasha_relevance(dashas: dict, spec: DomainSpec, domain_planets: set[str],
                     domain_house_lords: set[str]) -> dict:
    current = dashas.get("current", {})
    chain = []
    for level in ("mahadasha", "antardasha", "pratyantardasha",
                  "sookshmadasha", "pranadasha"):
        period = current.get(level)
        if not period:
            continue
        lord = period.get("lord")
        chain.append({
            "level": level,
            "lord": lord,
            "start": period.get("start"),
            "end": period.get("end"),
            "is_domain_karaka": lord in domain_planets,
            "is_domain_house_lord": lord in domain_house_lords,
        })
    relevant = [row for row in chain if row["is_domain_karaka"] or row["is_domain_house_lord"]]
    return {
        "chain": chain,
        "domain_relevant_lords": [row["lord"] for row in relevant],
        "relevance": "direct" if relevant else "indirect",
    }


def _gochara_for_domain(spec: DomainSpec, chart, transit_positions: dict | None,
                        as_of: datetime) -> dict:
    if transit_positions is None:
        transit_positions = sidereal_positions(
            _jd_from_dt(as_of), chart.ayanamsha, chart.node_type,
        )
    lagna_sign = sign_index(chart.lagna_lon)
    moon_sign = sign_index(chart.positions["Moon"]["lon"])
    gochara = gochara_rules(transit_positions, chart.positions, lagna_sign, moon_sign)
    av_support = ashtakavarga_transit_support(chart.ashtakavarga(), transit_positions)
    apply_ashtakavarga_context(gochara, av_support)
    planets = {
        planet: {
            "sign": row["sign"],
            "house_from_moon": row["house_from_moon"],
            "house_from_lagna": row["house_from_lagna"],
            "retrograde": row["retrograde"],
            "classical": gochara["classical_gochara"].get(planet),
            "ashtakavarga": av_support["planets"].get(planet),
        }
        for planet, row in gochara["planets"].items()
        if planet in spec.gochara_planets
    }
    rules = [
        {
            "name": rule["name"],
            "rule_id": rule["id"],
            "planet": rule["planet"],
            "active": rule["active"],
            "severity": rule.get("effective_severity", rule.get("severity")),
            "trigger": rule["trigger"],
            "source_status": rule["source_status"],
        }
        for rule in gochara["rules"]
        if rule["planet"] in spec.gochara_planets and rule["active"]
    ]
    return {
        "schema_version": "gocharam.ce-projection.v1",
        "as_of": as_of.isoformat(),
        "planets": planets,
        "active_rules": rules,
    }


def assemble_domain(chart, domain_id: str, *, tier: str = "primary",
                    include_gochara: bool = True,
                    transit_positions: dict | None = None,
                    as_of: datetime | None = None,
                    kb_limit: int = 12,
                    question: str | None = None) -> dict:
    """Domain-scoped context for one domain. `chart` is a VedicChart."""
    spec = get_domain(domain_id)
    as_of = as_of or datetime.now(timezone.utc)
    positions = chart.positions
    lagna_sign = sign_index(chart.lagna_lon)
    dignities = all_dignities(positions)

    houses = [
        _house_analysis(h, lagna_sign, positions, dignities,
                        "primary" if h in spec.houses_primary else "secondary")
        for h in spec.all_houses
    ]
    domain_house_lords = {row["lord"] for row in houses}

    karakas = {
        planet: _planet_brief(planet, positions, lagna_sign, dignities)
        for planet in spec.karakas_naisargika
    }
    jaimini_karakas = {}
    if spec.karakas_jaimini:
        chara = chart.jaimini()["chara_karakas"]["karakas"]
        for code in spec.karakas_jaimini:
            row = chara.get(code)
            if row:
                jaimini_karakas[code] = {
                    "karaka": _KARAKA_NAMES.get(code, code),
                    **_planet_brief(row["planet"], positions, lagna_sign, dignities),
                }

    focus_planets = list(dict.fromkeys(
        [*spec.karakas_naisargika, *domain_house_lords,
         *[row["planet"] for row in jaimini_karakas.values()]]
    ))

    arudhas = {}
    if spec.arudhas:
        padas = chart.jaimini()["arudha_padas"]["padas"]
        upapada = chart.jaimini()["upapada"]
        for code in spec.arudhas:
            if code == "UL":
                arudhas["UL"] = {"sign_name": upapada.get("sign_name")}
            elif code in padas:
                arudhas[code] = {"sign_name": padas[code].get("sign_name")}

    yogas_payload = chart.yogas()
    doshas_payload = chart.doshas()
    domain_planets = set(spec.karakas_naisargika) | {
        row["planet"] for row in jaimini_karakas.values()
    }

    kb = get_knowledge_base()
    references = [
        ref.to_dict()
        for ref in kb.retrieve([domain_id], subdomains=list(spec.subdomains),
                               limit=kb_limit)
    ]
    source_passages = []
    try:
        from .source_retriever import get_source_retriever
        retrieval_query = question or f"{spec.name}: {spec.description}"
        source_passages = [
            passage.to_dict()
            for passage in get_source_retriever().retrieve(
                retrieval_query, [domain_id], limit=min(kb_limit, 8),
            )
        ]
    except Exception:
        # The source corpus is additive; a retrieval outage must not break CE.
        source_passages = []

    return {
        "domain": domain_id,
        "domain_name": spec.name,
        "tier": tier,
        "houses": houses,
        "karakas": karakas,
        "jaimini_karakas": jaimini_karakas,
        "arudhas": arudhas,
        "vargas": _varga_placements(spec, focus_planets, positions, chart.lagna_lon),
        "yogas": _filter_rules(yogas_payload.get("all", []), spec),
        "doshas": _filter_doshas(doshas_payload, spec),
        "dasha_relevance": _dasha_relevance(chart.dashas(), spec,
                                            domain_planets, domain_house_lords),
        "gochara": (_gochara_for_domain(spec, chart, transit_positions, as_of)
                    if include_gochara else None),
        "references": references,
        "source_passages": source_passages,
        "convention_flags": list(spec.convention_flags),
        "exclusions": list(spec.exclusions),
    }


def assemble(chart, domains: list[str], *, question: str | None = None,
             include_gochara: bool = True, as_of: datetime | None = None) -> dict:
    """Full ContextBundle for one or more domains (first = primary).

    Returns a JSON-serializable dict ready to be embedded in agent state.
    """
    as_of = as_of or datetime.now(timezone.utc)
    transit_positions = None
    if include_gochara:
        transit_positions = sidereal_positions(
            _jd_from_dt(as_of), chart.ayanamsha, chart.node_type,
        )
    sections = []
    for i, domain_id in enumerate(domains):
        sections.append(assemble_domain(
            chart, domain_id,
            tier="primary" if i == 0 else "secondary",
            include_gochara=include_gochara,
            transit_positions=transit_positions,
            as_of=as_of,
            question=question,
        ))
    lagna_sign = sign_index(chart.lagna_lon)
    moon_sign = sign_index(chart.positions["Moon"]["lon"])
    return {
        "engine": "AstroSpace Context Engine",
        "taxonomy_version": taxonomy_version(),
        "question": question,
        "as_of": as_of.isoformat(),
        "chart_identity": {
            "name": chart.name,
            "lagna": sign_name(lagna_sign),
            "moon_sign": sign_name(moon_sign),
            "moon_nakshatra": nakshatra_of(chart.positions["Moon"]["lon"])["name"],
            "ayanamsha": chart.ayanamsha,
        },
        "domains": sections,
        "provenance": {
            "assembly": "deterministic domain-scoped selection; the agent explains, it does not recalculate",
            "houses": "whole-sign from lagna",
        },
    }
