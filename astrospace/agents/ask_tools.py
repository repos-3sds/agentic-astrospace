"""Read-only chart tools for the exploring Ask agent (agents/explorer.py).

Ask's domain bundle (context/assembler.py) is a fixed slice of the chart:
family & property sees the 4th house, career sees the 10th and D10. These
tools let the model fetch what else a question needs — another house, a
divisional chart, the dasha running on a date, a variant dasha, the
Ashtakavarga of a sign, strengths, today's panchang, the classical patterns
for a life area, a passage from the classics — and nothing it does not.

Every tool is bound to one already-loaded chart, so the model never passes
birth details and cannot reach another reader's data. Each result is trimmed
to what a reading needs (the raw engine payloads run to 250 KB) and carries a
`ref` that the answer may cite; the verifier accepts exactly the refs this
turn's tools returned (see verifier.valid_sources and `explored`).
"""
from __future__ import annotations

import inspect
import json
import logging
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from ..context.assembler import _house_analysis
from ..core.vedic.favourable import functional_planets
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import sign_index, sign_name

log = logging.getLogger(__name__)

PATTERNS_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "patterns" / "patterns.json"
NAKSHATRA_LORE_PATH = PATTERNS_PATH.with_name("nakshatra_lore.json")
PATTERN_AREAS = (
    "career", "wealth", "education", "marriage", "children", "family_property",
    "health", "foreign", "litigation", "spirituality", "personality", "timing",
    "today", "techniques",
)

PLANETS = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")
VARGAS = ("D1", "D2", "D3", "D4", "D7", "D9", "D10", "D12", "D16", "D20",
          "D24", "D27", "D30", "D40", "D45", "D60")
DASHA_VARIANTS = ("kshema", "utpanna", "adhana", "d1_lagna", "d9_lagna", "d10_lagna", "tribhagi")

# Shown to the model while it explores: one line per tool.
TOOL_SPECS: list[dict] = [
    {"name": "chart_overview",
     "description": "Lagna and all nine planets: sign, house, nakshatra, dignity, retrograde, combustion, Baladi avastha, and the houses each planet rules.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "house",
     "description": "One house (1-12) counted from the Lagna (default), the Moon (Chandra lagna) or the Sun (Surya lagna): its sign, lord and where the lord sits (dignity, house), occupants, argala, and the sign's Sarvashtakavarga bindus.",
     "input_schema": {"type": "object", "properties": {
         "number": {"type": "integer", "minimum": 1, "maximum": 12},
         "view": {"type": "string", "enum": ["lagna", "moon", "sun"]}},
                      "required": ["number"]}},
    {"name": "varga",
     "description": "A divisional chart: its lagna and each planet's sign, house, dignity and vargottama. D9 marriage/dharma, D10 career, D7 children, D4 property, D2 wealth, D24 education, D12 parents, D20 spiritual, D30 difficulties.",
     "input_schema": {"type": "object", "properties": {"division": {"type": "string", "enum": list(VARGAS)}},
                      "required": ["division"]}},
    {"name": "dasha_at",
     "description": "Vimshottari maha, antar and pratyantar dasha running on a date (YYYY-MM-DD, default today), with start and end dates.",
     "input_schema": {"type": "object", "properties": {"date": {"type": "string"}}, "required": []}},
    {"name": "dasha_timeline",
     "description": "Vimshottari antardashas between two dates (YYYY-MM-DD), for 'when' questions. At most 15 years. Spans of 3 years or less also list each pratyantardasha (sub-sub period), for exact windows.",
     "input_schema": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
                      "required": ["start", "end"]}},
    {"name": "dasha_variant",
     "description": "A convention-dependent dasha for cross-checking timing: Vimshottari from a Tara start (kshema, utpanna, adhana), from a lagna (d1_lagna, d9_lagna, d10_lagna), tribhagi, or the yogini and chara dashas. Returns the running periods today.",
     "input_schema": {"type": "object", "properties": {"variant": {"type": "string", "enum": [*DASHA_VARIANTS, "yogini", "chara"]}},
                      "required": ["variant"]}},
    {"name": "transits",
     "description": "Where the planets are today, by house from Lagna and from Moon, with transit dignity and Ashtakavarga support; Sade Sati and Ashtama Shani status; the active transit periods.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "ashtakavarga",
     "description": "Sarvashtakavarga bindus for all 12 houses, and one planet's Bhinnashtakavarga if a planet is given. 28+ bindus is a supportive house.",
     "input_schema": {"type": "object", "properties": {"planet": {"type": "string", "enum": list(PLANETS[:7])}},
                      "required": []}},
    {"name": "strengths",
     "description": "Shadbala score and band per planet, Vimshopaka bala, and conditions (combust, planetary war, avastha) that weaken a planet.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "yogas_doshas",
     "description": "Active yogas with their triggers, and doshas as flags with their cancellations.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "jaimini",
     "description": "Chara karakas (Atmakaraka, Amatyakaraka, Darakaraka...), Arudha Lagna, Upapada, all arudha padas, Karakamsha.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "favourable",
     "description": "Functional benefics and malefics for this Lagna, yogakaraka, and the colours, days and gems of each planet. Use for colour, number, day and gem questions.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "panchang",
     "description": "The panchang for a date (YYYY-MM-DD, default today) at the birth place: tithi, nakshatra, yoga, karana, Rahu Kalam and other windows, plus this person's tarabala and chandrabala.",
     "input_schema": {"type": "object", "properties": {"date": {"type": "string"}}, "required": []}},
    {"name": "nakshatra",
     "description": "Birth stars of the Lagna and all nine planets: name, pada, star lord, deity, symbol, gana, yoni, nadi; the classical Moon-in-star traits (Brihat Jataka) with the rule that the Moon's strength scales them; and each star's deity story (modern practice, tier H).",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "remedies",
     "description": "This chart's personal remedy plan from Siddha's remedy corpus (at most three: one for the running dasha pair as BPHS names it, one for the life area the period stresses, one for a flag such as a debilitated dasha lord). Each with its mantra (Telugu and English letters), day, count and why. Remedies must come from here, never invented.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "classical_patterns",
     "description": "The classical reading rules for a life area, from our pattern book: each with an id, a tier (A = two or more classics agree, B = one classic, C = classic but not computed, H = practice or hypothesis) and the book behind it. Read these before judging an area, then check each rule against this chart with the other tools.",
     "input_schema": {"type": "object", "properties": {"area": {"type": "string", "enum": list(PATTERN_AREAS)}},
                      "required": ["area"]}},
    {"name": "classics",
     "description": "Search the OCR'd classics (BPHS, Phaladeepika, Saravali, Brihat Jataka, Uttara Kalamritam) for passages on a topic, e.g. 'lord of the 7th in the 12th'. Returns short passages with ids.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
]


@lru_cache(maxsize=1)
def nakshatra_lore() -> dict:
    try:
        return json.loads(NAKSHATRA_LORE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.exception("nakshatra lore unreadable at %s", NAKSHATRA_LORE_PATH)
        return {"rules": [], "nakshatras": []}


@lru_cache(maxsize=1)
def pattern_cards() -> list[dict]:
    try:
        return json.loads(PATTERNS_PATH.read_text(encoding="utf-8"))["cards"]
    except (OSError, ValueError, KeyError):
        log.exception("pattern book unreadable at %s", PATTERNS_PATH)
        return []


def _day(value: str | None) -> str:
    return str(value or "")[:10]


def _parse_date(value: str | None, tz: str) -> datetime:
    if value:
        y, m, d = (int(part) for part in str(value)[:10].split("-"))
        return datetime(y, m, d, 12, 0, tzinfo=ZoneInfo(tz))
    return datetime.now(ZoneInfo(tz))


def _period(row: dict, *extra: str) -> dict:
    out = {"lord": row.get("lord"), "start": _day(row.get("start")), "end": _day(row.get("end"))}
    for key in extra:
        if row.get(key) is not None:
            out[key] = row[key]
    return out


def _running(rows: list[dict], when: datetime) -> dict | None:
    for row in rows or []:
        try:
            start = datetime.fromisoformat(str(row["start"]))
            end = datetime.fromisoformat(str(row["end"]))
        except (KeyError, ValueError):
            continue
        if start <= when < end:
            return row
    return None


class ChartTools:
    """The tools, bound to one chart. `calls` records every call this turn
    made, in order, with the trimmed result the model saw."""

    def __init__(self, chart, timezone: str = "Asia/Kolkata", source_retriever=None):
        self.chart = chart
        self.tz = timezone
        self._retriever = source_retriever
        self.calls: list[dict] = []
        self.passages: list[dict] = []
        self._lagna_sign = sign_index(chart.lagna_lon)

    # Dispatch --------------------------------------------------------------

    def call(self, name: str, args: dict) -> dict:
        method = getattr(self, f"tool_{name}", None)
        if method is None:
            return {"error": f"Unknown tool {name}"}
        try:
            result = method(**(args or {}))
        except Exception as exc:  # the model sees the failure and adapts
            log.exception("ask tool %s failed", name)
            result = {"error": f"{name} failed: {type(exc).__name__}"}
        ref = self._ref(name, args or {})
        result = {"ref": ref, **result}
        self.calls.append({"ref": ref, "tool": name, "args": args or {}, "result": result})
        return result

    def _ref(self, name: str, args: dict) -> str:
        """One spelling per look-up: arguments in signature order, defaults
        left out, so house(1) and house(number=1, view="lagna") share a ref."""
        method = getattr(self, f"tool_{name}", None)
        values = list((args or {}).values())
        if method is not None:
            try:
                params = list(inspect.signature(method).parameters.values())
                bound = inspect.signature(method).bind(**(args or {}))
                bound.apply_defaults()
                values = [bound.arguments[p.name] for p in params
                          if p.name in bound.arguments and bound.arguments[p.name] != p.default]
            except TypeError:
                pass
        if not values:
            return f"tool:{name}"
        return f"tool:{name}({','.join(str(v) for v in values)})"[:120]


    # Birth chart -----------------------------------------------------------

    def tool_chart_overview(self) -> dict:
        details = self.chart.planet_details()
        dignities = self.chart.dignities()
        conditions = (self.chart.planetary_conditions() or {}).get("rows") or {}
        planets = {}
        for planet in PLANETS:
            row = details.get(planet) or {}
            cond = conditions.get(planet) or {}
            house_signs = [((self._lagna_sign + h - 1) % 12, h) for h in range(1, 13)]
            planets[planet] = {
                "sign": row.get("sign"), "house": row.get("house"),
                "degree": round(float(row.get("degree_in_sign") or 0), 2),
                "nakshatra": f"{row.get('nakshatra')} {row.get('nakshatra_pada')}",
                "dignity": (dignities.get(planet) or {}).get("dignity"),
                "retrograde": bool(row.get("retrograde")),
                "combust": bool((cond.get("combustion") or {}).get("active")),
                "avastha": (cond.get("avastha") or {}).get("name"),
                "rules_houses": [h for s, h in house_signs if _sign_lord(s) == planet],
            }
        return {"lagna": self.chart.lagna_details(), "planets": planets}

    def tool_house(self, number: int, view: str = "lagna") -> dict:
        number = int(number)
        if not 1 <= number <= 12:
            return {"error": "house must be 1-12"}
        bodies = {"moon": "Moon", "sun": "Sun"}
        if view in bodies:
            base = sign_index(self.chart.positions[bodies[view]]["lon"])
        elif view == "lagna":
            base = self._lagna_sign
        else:
            return {"error": "view must be lagna, moon or sun"}
        analysis = _house_analysis(number, base, self.chart.positions,
                                   self.chart.dignities(), "explored", verbose=True)
        analysis["view"] = view
        sign = (base + number - 1) % 12
        sav = (self.chart.ashtakavarga() or {}).get("sav") or []
        analysis["sav_bindus"] = sav[sign] if len(sav) == 12 else None
        return analysis

    def tool_varga(self, division: str) -> dict:
        division = str(division).upper().strip()
        if division not in VARGAS:
            return {"error": f"Unknown division; use one of {', '.join(VARGAS)}"}
        chart = self.chart.varga_chart(division)
        return {
            "division": division, "name": chart.get("name"), "signifies": chart.get("signifies"),
            "lagna": (chart.get("lagna") or {}).get("sign"),
            "planets": {
                planet: {key: row.get(key) for key in ("sign", "house", "dignity", "vargottama")}
                for planet, row in (chart.get("planets") or {}).items()
            },
        }

    def tool_yogas_doshas(self) -> dict:
        yogas = [
            {"name": y.get("name"), "strength": y.get("strength"), "triggers": y.get("triggers")}
            for y in (self.chart.yogas() or {}).get("active") or []
        ]
        doshas = {}
        for name, row in (self.chart.doshas() or {}).items():
            if not isinstance(row, dict):
                continue
            doshas[name] = {
                key: row.get(key) for key in
                ("active", "severity", "net_severity", "cancellations", "from")
                if row.get(key) not in (None, [], {})
            }
        return {"yogas": yogas, "doshas": doshas,
                "note": "A dosha is a flag, not a verdict: always mention its cancellations."}

    def tool_strengths(self) -> dict:
        shadbala = self.chart.shadbala() or {}
        vimshopaka = (self.chart.vimshopaka_bala() or {}).get("planets") or {}
        conditions = (self.chart.planetary_conditions() or {}).get("rows") or {}
        out = {}
        for row in shadbala.get("ranking") or []:
            planet = row["planet"]
            cond = conditions.get(planet) or {}
            out[planet] = {
                "shadbala_score": row.get("score"), "band": row.get("band"),
                "vimshopaka": (vimshopaka.get(planet) or {}).get("score"),
                "vimshopaka_band": (vimshopaka.get(planet) or {}).get("band"),
                "combust": bool((cond.get("combustion") or {}).get("active")),
                "planetary_war": bool((cond.get("planetary_war") or {}).get("active")),
                "avastha": (cond.get("avastha") or {}).get("name"),
            }
        return {"planets": out, "scale": "Shadbala here is a 0-100 score; strong / moderate / weak bands."}

    def tool_ashtakavarga(self, planet: str | None = None) -> dict:
        data = self.chart.ashtakavarga() or {}
        sav = data.get("sav") or []
        by_house = {h: sav[(self._lagna_sign + h - 1) % 12] for h in range(1, 13)} if len(sav) == 12 else {}
        out = {"sav_by_house": by_house, "total": sum(sav) if sav else None}
        if planet:
            bav = (data.get("bav") or {}).get(planet) or []
            if len(bav) == 12:
                out["bav_by_house"] = {h: bav[(self._lagna_sign + h - 1) % 12] for h in range(1, 13)}
                out["planet"] = planet
        return out

    def tool_jaimini(self) -> dict:
        data = self.chart.jaimini() or {}
        karakas = ((data.get("chara_karakas") or {}).get("karakas")) or {}
        padas = ((data.get("arudha_padas") or {}).get("padas")) or {}
        return {
            "karakas": {key: row.get("planet") for key, row in karakas.items()},
            "scheme": (data.get("chara_karakas") or {}).get("scheme"),
            "arudha_lagna": (data.get("arudha_lagna") or {}).get("sign_name"),
            "upapada": (data.get("upapada") or {}).get("sign_name"),
            "padas": {key: row.get("sign_name") for key, row in padas.items()},
            "karakamsha": data.get("karakamsha"),
        }

    def tool_favourable(self) -> dict:
        functional = functional_planets(self._lagna_sign)
        fav = self.chart.favourable() or {}
        return {
            "functional": functional,
            "lucky_days": fav.get("lucky_days"),
            "convention": "Functional nature by Lagna follows BPHS ch.34-36 as encoded; schools differ for some lagnas (e.g. Saturn for Virgo).",
        }

    # Time ------------------------------------------------------------------

    def tool_dasha_at(self, date: str | None = None) -> dict:
        when = _parse_date(date, self.tz)
        data = self.chart.dashas()
        md = _running(data.get("mahadashas"), when)
        if not md:
            return {"error": "no dasha covers that date"}
        ad = _running(md.get("antardashas"), when) or {}
        pd = _running(ad.get("pratyantardashas"), when) or {}
        return {"date": when.date().isoformat(), "mahadasha": _period(md),
                "antardasha": _period(ad) if ad else None,
                "pratyantardasha": _period(pd) if pd else None,
                "birth_nakshatra": data.get("birth_nakshatra")}

    def tool_dasha_timeline(self, start: str, end: str) -> dict:
        lo, hi = _parse_date(start, self.tz), _parse_date(end, self.tz)
        if hi <= lo:
            return {"error": "end must be after start"}
        if (hi - lo).days > 15 * 366:
            hi = lo.replace(year=lo.year + 15)
        rows = []
        for md in self.chart.dashas().get("mahadashas") or []:
            for ad in md.get("antardashas") or []:
                a_start = datetime.fromisoformat(str(ad["start"]))
                a_end = datetime.fromisoformat(str(ad["end"]))
                if a_end > lo and a_start < hi:
                    row = {"mahadasha": md["lord"], **_period(ad)}
                    if (hi - lo).days <= 3 * 366:
                        row["pratyantardashas"] = [
                            _period(pd) for pd in ad.get("pratyantardashas") or []
                            if datetime.fromisoformat(str(pd["end"])) > lo
                            and datetime.fromisoformat(str(pd["start"])) < hi
                        ]
                    rows.append(row)
        return {"from": lo.date().isoformat(), "to": hi.date().isoformat(), "antardashas": rows}

    def tool_dasha_variant(self, variant: str) -> dict:
        now = datetime.now(ZoneInfo(self.tz))
        if variant == "yogini":
            data = self.chart.yogini_dashas()
        elif variant == "chara":
            data = self.chart.chara_dasha()
        elif variant in DASHA_VARIANTS:
            data = self.chart.dasha_variant(variant)
        else:
            return {"error": f"Unknown variant {variant}"}
        current = data.get("current") or {}
        md = current.get("mahadasha") or {}
        ad = _running(md.get("antardashas"), now) or {}
        return {
            "variant": variant,
            "mahadasha": _period(md, "sign_name", "yogini"),
            "antardasha": _period(ad, "sign_name", "yogini") if ad else None,
            "is_convention_dependent": True,
            "note": data.get("observance_note") or "A cross-check only; standard Vimshottari leads.",
        }

    def tool_transits(self) -> dict:
        context = self.chart.transit_context() or {}
        planets = ((context.get("gochara_analysis") or {}).get("planets")) or {}
        rows = {}
        for planet, row in planets.items():
            rows[planet] = {
                "sign": row.get("sign"), "house_from_lagna": row.get("house_from_lagna"),
                "house_from_moon": row.get("house_from_moon"),
                "retrograde": row.get("retrograde"),
                "transit_dignity": (row.get("transit_dignity") or {}).get("dignity"),
            }
        periods = [
            {key: p.get(key) for key in ("rule", "planet", "start_date", "end_date", "tone", "trigger")}
            for p in (self.chart.transits() or {}).get("gocharam_periods") or []
            if p.get("status") in ("active", "upcoming")
        ][:12]
        return {"as_of": _day((context.get("as_of") or {}).get("birth_date")), "planets": rows,
                "sade_sati": context.get("sade_sati"), "periods": periods}

    def tool_panchang(self, date: str | None = None) -> dict:
        from ..core.vedic.panchanga_day import daily_panchanga, personal_panchanga

        meta = self.chart.meta() or {}
        city, lat, lng, tz_str = meta.get("place"), meta.get("latitude"), meta.get("longitude"), meta.get("timezone")
        if lat is None or lng is None or not tz_str:
            return {"error": "birth place not resolvable for the panchang"}
        nation = "IN"
        when = _parse_date(date, tz_str)
        day = daily_panchanga(when.year, when.month, when.day, city, nation, lat, lng, tz_str)
        moon_lon = self.chart.positions["Moon"]["lon"]
        personal = personal_panchanga(day, janma_nakshatra_index=nakshatra_of(moon_lon)["index"],
                                      janma_rashi_index=sign_index(moon_lon),
                                      ghatak_moon_sign=sign_index(moon_lon))
        elements = {
            key: [{"name": row.get("name"), "upto": row.get("upto")} for row in rows or []]
            for key, rows in (day.get("elements") or {}).items()
        }
        windows = {
            kind: [{"name": w.get("name"), "start": w.get("start"), "end": w.get("end")} for w in rows or []]
            for kind, rows in (day.get("windows") or {}).items()
        }
        return {"place": city, "date": day.get("date"), "vara": (day.get("vara") or {}).get("name"),
                "sunrise": day.get("sunrise"), "sunset": day.get("sunset"), "masa": day.get("masa"),
                "elements": elements, "windows": windows, "personal": personal}

    def tool_nakshatra(self) -> dict:
        from ..core.vedic.nakshatra import nakshatra_traits

        lore = nakshatra_lore()
        by_index = {row["index"]: row for row in lore.get("nakshatras") or []}
        bodies = {"Lagna": self.chart.lagna_lon,
                  **{p: self.chart.positions[p]["lon"] for p in PLANETS if p in self.chart.positions}}
        stars = {}
        for body, lon in bodies.items():
            nak = nakshatra_of(lon)
            row = by_index.get(nak["index"]) or {}
            entry = {**nakshatra_traits(nak["index"]), "pada": nak["pada"],
                     "story_gloss": row.get("story_gloss")}
            if body == "Moon":
                entry["classical_traits"] = row.get("classical_traits")
                entry["classical_checked_in_print"] = row.get("classical_checked_in_print")
            stars[body] = entry
        return {"stars": stars, "rules": lore.get("rules") or [],
                "note": "Classical traits belong to the Moon's star only. Deity stories are practice: say so."}

    def tool_remedies(self) -> dict:
        from ..core.vedic.remedy_plan import remedy_plan

        plan = remedy_plan(self.chart.positions, self.chart.lagna_lon, self.chart.dashas())
        out = []
        for group in plan.get("groups") or []:
            practice = (group.get("practices") or [{}])[0]
            out.append({
                "slot": group.get("slot"), "for": group.get("reason_short"),
                "why": group.get("reason_plain"), "trigger": group.get("trigger"),
                "practice": practice.get("title"), "mantra_id": practice.get("mantra_id"),
                "mantra": {k: (practice.get("text") or {}).get(k) for k in ("te", "en")},
                "how": practice.get("instructions"), "day": practice.get("preferred_day"),
                "convention_dependent": bool(group.get("convention_dependent")),
                "observance_note": group.get("observance_note"),
            })
        return {"plan": out, "rules": "Traditional practice, never 'pay to remove'. Pick 1-2 that fit "
                "this reader's situation and say why in their terms; never frame a remedy against "
                "illness or death."}

    # Knowledge -------------------------------------------------------------

    def tool_classical_patterns(self, area: str) -> dict:
        cards = [c for c in pattern_cards() if c.get("area") == area]
        order = {"A": 0, "B": 1, "C": 2, "H": 3}
        cards.sort(key=lambda c: order.get(c.get("tier"), 9))
        return {"area": area, "patterns": [
            {"id": f"pattern:{c['id']}", "tier": c.get("tier"), "rule": c.get("rule"),
             "books": sorted({(s.get("book") or "").split(" (")[0] for s in c.get("sources") or [] if s.get("book")})}
            for c in cards[:16]
        ], "note": "Tier H rules are practice or hypothesis: say so if you use one. Never show book names to the reader."}

    def tool_classics(self, query: str) -> dict:
        if self._retriever is None:
            return {"error": "classics search is not available on this server"}
        rows = self._retriever.retrieve(str(query)[:200], domains=[], limit=4)
        out = []
        for passage in rows:
            item = passage.to_dict() if hasattr(passage, "to_dict") else dict(passage)
            self.passages.append(item)
            out.append({"chunk_id": item.get("chunk_id"), "book": item.get("book"),
                        "text": (item.get("content") or "")[:900]})
        return {"query": query, "passages": out}


def _sign_lord(sign: int) -> str:
    from ..core.vedic.constants import SIGN_LORDS
    return SIGN_LORDS[sign]


def summarize_call(name: str, args: dict) -> str:
    """The reader-facing progress line for one tool call."""
    if name == "house":
        return f"Looking at your {_ordinal(int(args.get('number') or 0))} house…"
    if name == "varga":
        return f"Reading your {args.get('division')} chart…"
    if name in ("dasha_at", "dasha_timeline"):
        return "Checking your dasha periods…"
    if name == "dasha_variant":
        return "Cross-checking the timing with another dasha…"
    if name == "transits":
        return "Checking today's planets against your chart…"
    if name == "ashtakavarga":
        return "Counting Ashtakavarga bindus…"
    if name == "strengths":
        return "Weighing planet strengths…"
    if name == "yogas_doshas":
        return "Checking yogas and doshas…"
    if name == "jaimini":
        return "Reading Jaimini karakas and arudhas…"
    if name == "favourable":
        return "Finding your good and avoid planets…"
    if name == "panchang":
        return "Reading the panchang…"
    if name == "remedies":
        return "Choosing remedies for you…"
    if name == "nakshatra":
        return "Reading your birth stars…"
    if name in ("classical_patterns", "classics"):
        return "Checking the classical rules…"
    return "Looking at your chart…"


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def ref_aliases(ref: str) -> set[str]:
    """Other spellings the writer uses for a house look-up: the default view
    named ("house(1,lagna)") or the arguments swapped ("house(lagna,1)")."""
    match = re.fullmatch(r"tool:house\((\d{1,2})(?:,(moon|sun))?\)", ref)
    if not match:
        return set()
    number, view = match.group(1), match.group(2) or "lagna"
    return {f"tool:house({number},{view})", f"tool:house({view},{number})"} - {ref}
