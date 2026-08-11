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

Cost profile: uses only cheap chart sections. Gochara's snapshot (sign,
house-from-moon/lagna, retrograde, active rules) is a single ephemeris call;
finding the active window's real start/end date additionally walks the
boundary (`gocharam/timeline.py`'s existing logic, reused rather than
duplicated) for whichever rules are already active for that domain's own
planets — moderate, not free; see `_gochara_windows_for_domain`'s docstring
for the actual cost shape. Pass include_gochara=False to skip gochara
entirely, or supply precomputed transit_positions to reuse a snapshot across
domains.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import swisseph as swe

from ..core.vedic.constants import PLANET_DHATU, PLANET_RASA, PLANET_VARNA, SIGN_LORDS
from ..core.vedic.gocharam import gochara_rules, gocharam_rule_timeline
from ..core.vedic.gocharam.strength import (
    apply_ashtakavarga_context,
    ashtakavarga_transit_support,
)
from ..core.vedic.nakshatra import nakshatra_of, nakshatra_traits
from ..core.vedic.positions import (
    degree_in_sign, house_from_lagna, sign_index, sign_name,
)
from ..core.vedic.strength import all_dignities, combustion_status
from ..core.vedic.positions import sidereal_positions
from ..core.vedic.dasha_phase import dasha_emphasis, emphasis_window
from ..core.vedic.vargas import varga_sign
from ..core.vedic.vimshopaka import WEIGHTS as _VIMSHOPAKA_SCHEMES
from ..core.vedic.vimshopaka import vimshopaka_bala
from ..core.vedic.argala import argala_of_house
from ..core.vedic.shashtyamsha import d60_deity
from .kb import get_knowledge_base
from .taxonomy import DomainSpec, get_domain, taxonomy_version
from .timeline import as_dt as _as_dt
from .timeline import build_timeline
from .validation import life_context_section

_KARAKA_NAMES = {
    "AK": "Atmakaraka", "AmK": "Amatyakaraka", "BK": "Bhratrikaraka",
    "MK": "Matrikaraka", "PK": "Putrakaraka", "PiK": "Pitrikaraka",
    "GK": "Gnatikaraka", "DK": "Darakaraka",
}


def _jd_from_dt(dt: datetime) -> float:
    dt_utc = dt.astimezone(timezone.utc)
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hour)


def _profile_facts(chart, as_of: datetime) -> dict:
    """Deterministic, backend-computed profile facts — the block Item 3
    calls for (docs/ask_context_engine_multi_agent_architecture_2026-08-07.md,
    "Update 2026-08-09"). The agent must not be left to derive age itself
    from birth data + `as_of`; that arithmetic belongs here, once, same
    category as every other precomputed bundle section.

    Deliberately minimal: only `age_years` is derivable from birth data
    alone. Life-stage flags (retired/working/student), relationship/gender
    context, and location facts named in the finding's follow-up require
    profile data this engine does not hold today — they are left out
    entirely rather than guessed, matching the finding's own principle that
    an unknown fact must not be invented."""
    birth_utc = chart.moment.dt_utc
    as_of_utc = as_of.astimezone(timezone.utc)
    age_years = (as_of_utc - birth_utc).days / 365.2425
    return {
        "age_years": round(age_years, 1),
        "birth_year": birth_utc.year,
        "as_of": as_of_utc.isoformat(),
    }


def _retrospect(chart, as_of: datetime) -> dict:
    """The reader's own dated past, so a reading can open by anchoring to a
    real transition instead of a cold-read generality.

    This exists to make *honest* past-validation possible. The compelling
    version of "you've had money slip through your fingers" is a Barnum
    line — true of nearly everyone, asserted about a life we cannot see.
    The honest version is anchored and falsifiable: a real dated period
    boundary from this chart, what that period classically tends to bring,
    and an explicit invitation for the reader to confirm or deny it. That
    is why every entry here carries a date and an age and nothing about
    what actually happened — the engine supplies the *when*, the agent
    supplies the *tends to*, and the reader supplies the *did it*.

    Ages are included because "when you were 32" is checkable in a way
    "in late 2022" is not — people remember their lives by age.
    """
    dashas = chart.dashas(as_of)
    mahadashas = dashas.get("mahadashas") or []
    birth_utc = chart.moment.dt_utc
    as_of_utc = as_of.astimezone(timezone.utc)

    def age_at(value) -> float | None:
        moment = _as_dt(value)
        if moment is None:
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return round((moment - birth_utc).days / 365.2425, 1)

    def span(row: dict) -> dict:
        out = {
            "lord": row.get("lord"),
            "start": str(row.get("start"))[:10],
            "end": str(row.get("end"))[:10],
            "age_at_start": age_at(row.get("start")),
            "age_at_end": age_at(row.get("end")),
        }
        # Where inside the period its weight falls (BPHS 47.3-4). Without this
        # a sixteen-year mahadasha is narrated as one undifferentiated block,
        # which is what makes a long period read as a generality. Absent rather
        # than defaulted when the lord has no natal position, so the agent can
        # tell "not computable" from "falls early".
        natal = (chart.positions or {}).get(row.get("lord"))
        if natal and "lon" in natal:
            emphasis = dasha_emphasis(natal["lon"], bool(natal.get("retrograde")))
            start, end = row.get("start"), row.get("end")
            if start and end:
                try:
                    window = emphasis_window(start, end, emphasis["phase"])
                    # Dates only, matching the rest of this block. A dasha third
                    # is a multi-year span; a timestamp on it implies a precision
                    # the rule does not have, and reads as false exactness.
                    emphasis["window"] = {k: v[:10] for k, v in window.items()}
                except ValueError:
                    pass
            out["emphasis"] = emphasis
        return out

    def contains_now(row: dict) -> bool:
        start, end = _as_dt(row.get("start")), _as_dt(row.get("end"))
        if start is None or end is None:
            return False
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return start <= as_of_utc < end

    current_index = next((i for i, m in enumerate(mahadashas) if contains_now(m)), None)
    if current_index is None:
        return {"available": False,
                "note": "No mahadasha covers this instant; retrospect omitted."}

    current = mahadashas[current_index]
    started = _as_dt(current.get("start"))
    if started is not None and started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    total_years = float(current.get("years") or 0.0)
    elapsed_years = round((as_of_utc - started).days / 365.2425, 1) if started else None

    sub_periods = current.get("antardashas") or []
    elapsed_subs = [span(s) for s in sub_periods
                    if (_as_dt(s.get("end")) or as_of_utc.replace(tzinfo=None))
                    and not contains_now(s)
                    and str(s.get("end"))[:10] < as_of_utc.date().isoformat()]
    current_sub = next((span(s) for s in sub_periods if contains_now(s)), None)

    return {
        "available": True,
        "current_chapter": {
            **span(current),
            "years_total": total_years,
            "years_elapsed": elapsed_years,
            "years_remaining": (round(total_years - elapsed_years, 1)
                                if elapsed_years is not None else None),
        },
        "previous_chapter": span(mahadashas[current_index - 1]) if current_index else None,
        "current_sub_period": current_sub,
        "elapsed_sub_periods": elapsed_subs,
        "note": (
            "Dated boundaries only — this block says WHEN the reader's periods "
            "turned and how old they were, never what happened to them. Use it "
            "to anchor a checkable question, not to assert a life event."
        ),
    }


def _planet_brief(planet: str, positions: dict, lagna_sign: int,
                  dignities: dict, vimshopaka_scores: dict | None = None,
                  shayanadi_avasthas: dict | None = None) -> dict:
    lon = positions[planet]["lon"]
    s = sign_index(lon)
    nak = nakshatra_of(lon)
    combust = combustion_status(planet, positions)
    dignity = dignities.get(planet, {})
    brief = {
        "planet": planet,
        "sign": sign_name(s),
        "degree_in_sign": round(degree_in_sign(lon), 2),
        "house": house_from_lagna(s, lagna_sign),
        "nakshatra": nak["name"],
        # The nakshatra's own classical attributes, so the agent can ground a
        # reading in them instead of recalling them from training data with no
        # bundle field to cite. Bare facts only — deity, symbol, lord and the
        # three temperament axes; no interpretive prose (see
        # constants.NAKSHATRA_DEITY). `pada` matters interpretively in its own
        # right: it selects the navamsa the placement matures into.
        "nakshatra_detail": {**nakshatra_traits(nak["index"]), "pada": nak["pada"]},
        "dignity": dignity.get("dignity"),
        "retrograde": bool(positions[planet].get("retrograde")),
        "combust": bool(combust.get("active")),
        # Shashtyamsha (D-60) sign — the finest-grained classical division,
        # cited as the tie-breaker for an otherwise-ambiguous placement.
        # Deity-per-division is a separate, not-yet-implemented layer (see
        # docs/context_engine_taxonomy.md's ground-truth section) — only the
        # sign itself, which vargas.d60() already computes correctly, is
        # exposed here.
        "d60_sign": sign_name(varga_sign("D60", lon)),
        # D-60 ruling deity + benefic/malefic nature — cross-checked
        # against two independent secondary sources agreeing on all 60
        # names (see core/vedic/shashtyamsha.py's module docstring); a
        # third source that diverged from ~division 48 onward was
        # excluded as unreliable. Still convention_dependent: no primary
        # BPHS verse was located, only secondary-source agreement.
        "d60_deity": d60_deity(lon),
    }
    if vimshopaka_scores and planet in vimshopaka_scores:
        # Precise 0-20 float strength per scheme, replacing what used to be
        # a bare "is this planet in its own/exaltation sign" boolean hint —
        # lets the agent cite exactly how strong a placement is, not just
        # whether it clears a single threshold. All four schemes computed
        # from the same validated vimshopaka.py weights this session's
        # ground-truth pass confirmed against BPHS.
        brief["vimshopaka_bala"] = vimshopaka_scores[planet]
    if shayanadi_avasthas and planet in shayanadi_avasthas:
        # Shayanadi avastha — a 12-state condition distinct from the Baladi
        # avastha and Cheshta avastha this codebase already computes
        # elsewhere. Formula cross-checked against three independent
        # secondary sources (see core/vedic/shayanadi.py's module
        # docstring); no primary verse located, so source_status travels
        # with the value rather than being asserted as settled fact.
        row = shayanadi_avasthas[planet]
        brief["shayanadi_avastha"] = {
            "name": row["name"],
            "source_status": row["source_status"],
        }
    # Governing tissue (dhatu) and taste (rasa) — the classical Ayurvedic-
    # constitution associations Health & Longevity's own taxonomy scope
    # already claims to cover but previously had no data for. Static per
    # planet, not chart-position-dependent, so every planet either has both
    # or neither (Rahu/Ketu genuinely have neither — see PLANET_DHATU's
    # docstring) rather than a partial entry.
    if planet in PLANET_DHATU:
        brief["dhatu"] = PLANET_DHATU[planet]
        brief["rasa"] = PLANET_RASA[planet]
    # Naisargika (natural) planetary varna — a static per-graha attribute,
    # distinct from VARNA_BY_ELEMENT (which scores a native's own Varna
    # Koota from the Moon's sign element for Ashtakoota compatibility).
    # Cross-checked against multiple independent sources for the 7
    # classical grahas; Rahu/Ketu's varna is a real but less universally
    # fixed extension across traditions (see constants.py's docstring).
    if planet in PLANET_VARNA:
        brief["varna"] = PLANET_VARNA[planet]
    # The reasoning behind `dignity`, not just the label — only present when
    # dignity actually came from a dispositor relationship (Exalted/
    # Debilitated/Moolatrikona/Own/nodal-neutral have no dispositor to
    # reason about). Lets the agent cite *why* a compound relationship
    # landed where it did, e.g. "natural friend, but temporarily hostile
    # from this house, giving Neutral" instead of only asserting "Neutral".
    if dignity.get("dispositor"):
        brief["dignity_reasoning"] = {
            "dispositor": dignity["dispositor"],
            "natural_relation": dignity.get("natural_relation"),
            "temporal_relation": dignity.get("temporal_relation"),
        }
    return brief


def _house_analysis(house: int, lagna_sign: int, positions: dict,
                    dignities: dict, tier: str,
                    vimshopaka_scores: dict | None = None,
                    shayanadi_avasthas: dict | None = None) -> dict:
    house_sign = (lagna_sign + house - 1) % 12
    lord = SIGN_LORDS[house_sign]
    occupants = [
        planet for planet, data in positions.items()
        if house_from_lagna(sign_index(data["lon"]), lagna_sign) == house
    ]
    lord_brief = _planet_brief(lord, positions, lagna_sign, dignities,
                                vimshopaka_scores, shayanadi_avasthas)
    return {
        "house": house,
        "tier": tier,
        "sign": sign_name(house_sign),
        "lord": lord,
        "lord_placement": lord_brief,
        "lord_in_dusthana": lord_brief["house"] in (6, 8, 12),
        "occupants": occupants,
        # Argala/Argala-Bhanga — which houses' occupants support this
        # house's significations and which obstruct that support. Source-
        # checked against two independent secondary sources (see
        # core/vedic/argala.py's module docstring); source_status travels
        # with the payload.
        "argala": argala_of_house(house, lagna_sign, positions),
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


def _gochara_windows_for_domain(spec: DomainSpec, chart, gochara: dict,
                                as_of: datetime) -> dict[str, dict]:
    """Real ingress/exit dates for this domain's currently-active gochara
    rules, keyed by rule_id.

    Reuses `gocharam/timeline.py`'s existing `gocharam_rule_timeline` — the
    same date-range computation already wired into `chart.gocharam()` and
    `transits.py` — rather than reimplementing the transit-boundary walk
    here. Scoped to only the rules already active for this domain's planets
    (`gochara["active_rules"]` pre-filtered below) so the boundary search
    only runs for planets this domain actually cares about, and called with
    `scan_days=1` to skip the full previous/next-365-day *event* scan
    `chart.gocharam()` produces for the dedicated transits screen — the CE
    bundle only needs the active window's own start/end.

    That said, `scan_days` does NOT bound the boundary walk itself: finding
    each active rule's actual start/end date is `gocharam_rule_timeline`'s
    own `_active_rule_start`/`_active_rule_end`, gated by the separate
    `GOCHARA_ACTIVE_WINDOW_DAYS` constant (currently 10 years), stepped one
    week at a time — a real ephemeris recomputation per step, once per
    active rule. For a long-running transit (Saturn/Rahu/Ketu commonly run
    1.5-7.5 years) this is on the order of 100-300+ ephemeris calls per
    active rule, on every Ask request for a domain whose gochara is
    currently active. Measured cost against a real chart is moderate
    (roughly 0.1s/request after ephemeris warm-up per the same-day
    independent review that flagged this docstring's earlier, inaccurate
    "bounded by scan_days" claim) — acceptable for now since it is the same
    per-rule cost `chart.gocharam()` already pays elsewhere in the app, not
    a new cost class. If this becomes a real hot path, the fix is bounding
    `GOCHARA_ACTIVE_WINDOW_DAYS`'s walk itself, not this function."""
    domain_active_rules = [
        rule for rule in gochara["active_rules"]
        if rule["planet"] in spec.gochara_planets
    ]
    if not domain_active_rules:
        return {}
    lagna_sign = sign_index(chart.lagna_lon)
    moon_sign = sign_index(chart.positions["Moon"]["lon"])
    timeline = gocharam_rule_timeline(
        as_of, chart.positions, lagna_sign, moon_sign,
        chart.ayanamsha, chart.node_type,
        {**gochara, "active_rules": domain_active_rules},
        scan_days=1,
    )
    return {window["rule_id"]: window for window in timeline["active_windows"]}


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
    windows_by_rule_id = _gochara_windows_for_domain(spec, chart, gochara, as_of)
    rules = [
        {
            "name": rule["name"],
            "rule_id": rule["id"],
            "planet": rule["planet"],
            "active": rule["active"],
            "severity": rule.get("effective_severity", rule.get("severity")),
            "trigger": rule["trigger"],
            "source_status": rule["source_status"],
            "start_date": windows_by_rule_id.get(rule["id"], {}).get("start_date"),
            "end_date": windows_by_rule_id.get(rule["id"], {}).get("end_date"),
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
                    question: str | None = None,
                    validation_probes: list[dict] | None = None) -> dict:
    """Domain-scoped context for one domain. `chart` is a VedicChart.

    `validation_probes` are this reader's answered validation turns (see
    context/validation.py). They are the one input here that is NOT derived
    from the chart — everything else in the bundle is computed, this is
    reported — which is why they arrive as an explicit argument rather than
    being fetched: the assembler has no database and should not grow one."""
    spec = get_domain(domain_id)
    as_of = as_of or datetime.now(timezone.utc)
    positions = chart.positions
    lagna_sign = sign_index(chart.lagna_lon)
    dignities = all_dignities(positions)
    # Computed once per bundle (4 scheme calls, each scoring every planet in
    # one pass) rather than per-planet-brief, which would recompute the
    # whole chart's Vimshopaka scores on every call.
    vimshopaka_scores = {
        planet: {
            scheme: vimshopaka_bala(positions, scheme=scheme)["planets"][planet]["score"]
            for scheme in _VIMSHOPAKA_SCHEMES
        }
        for planet in positions
    }
    # Computed once per bundle for the same reason as vimshopaka_scores
    # above: it needs a sunrise search, not free to redo per planet brief.
    # A circumpolar-sunrise chart returns {"error": ...} with no per-planet
    # keys, which _planet_brief's `planet in shayanadi_avasthas` guard
    # already handles by simply omitting the field.
    shayanadi_avasthas = chart.shayanadi_avasthas()

    houses = [
        _house_analysis(h, lagna_sign, positions, dignities,
                        "primary" if h in spec.houses_primary else "secondary",
                        vimshopaka_scores, shayanadi_avasthas)
        for h in spec.all_houses
    ]
    domain_house_lords = {row["lord"] for row in houses}

    karakas = {
        planet: _planet_brief(planet, positions, lagna_sign, dignities,
                              vimshopaka_scores, shayanadi_avasthas)
        for planet in spec.karakas_naisargika
    }
    chara_karakas_full = chart.jaimini()["chara_karakas"]["karakas"]
    jaimini_karakas = {}
    if spec.karakas_jaimini:
        for code in spec.karakas_jaimini:
            row = chara_karakas_full.get(code)
            if row:
                jaimini_karakas[code] = {
                    "karaka": _KARAKA_NAMES.get(code, code),
                    **_planet_brief(row["planet"], positions, lagna_sign, dignities,
                                     vimshopaka_scores, shayanadi_avasthas),
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

    # Hoisted out of the return dict below because `timeline` needs the same
    # object — computing it twice would double this bundle's most expensive
    # section (see _gochara_windows_for_domain's cost note).
    gochara = (_gochara_for_domain(spec, chart, transit_positions, as_of)
               if include_gochara else None)

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

    # Full 8-karaka Jaimini array (Atmakaraka through Darakaraka, including
    # Rahu's Gnatikaraka slot), not just this domain's own relevant one —
    # cross-domain significators matter everywhere (a marriage reading can
    # reference the Atmakaraka's condition, a career reading the
    # Darakaraka's, etc.), so this is domain-independent and always present,
    # same as dasha_relevance. `jaimini_karakas` above stays as-is: the
    # domain-scoped subset with full planet detail for whichever karaka(s)
    # this specific domain cares about.
    jaimini_karaka_array = {
        code: {
            "karaka": _KARAKA_NAMES.get(code, code),
            "planet": row["planet"],
            "degree_in_sign": round(row["degree_in_sign"], 2),
        }
        for code, row in chara_karakas_full.items()
    }

    return {
        "domain": domain_id,
        "domain_name": spec.name,
        "tier": tier,
        "profile_facts": _profile_facts(chart, as_of),
        # The reader's dated past — enables anchored, checkable
        # past-validation instead of cold-read generalities. See _retrospect.
        "retrospect": _retrospect(chart, as_of),
        # The same boundaries `retrospect` and `dasha_relevance` carry, plus
        # this domain's active transit windows, flattened into one sorted,
        # scannable list so "where am I, what turns next" is read off the
        # bundle rather than re-derived in prose. See timeline.py.
        "timeline": build_timeline(chart, gochara, as_of,
                                   domain_lords=domain_planets | domain_house_lords),
        # What the reader themselves reported, from answered validation turns
        # — the only section here the chart did not produce. See
        # context/validation.py's life_context_section.
        "life_context": life_context_section(validation_probes or []),
        "houses": houses,
        "karakas": karakas,
        "jaimini_karakas": jaimini_karakas,
        "jaimini_karaka_array": jaimini_karaka_array,
        "arudhas": arudhas,
        "vargas": _varga_placements(spec, focus_planets, positions, chart.lagna_lon),
        "yogas": _filter_rules(yogas_payload.get("all", []), spec),
        "doshas": _filter_doshas(doshas_payload, spec),
        "dasha_relevance": _dasha_relevance(chart.dashas(), spec,
                                            domain_planets, domain_house_lords),
        "gochara": gochara,
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
