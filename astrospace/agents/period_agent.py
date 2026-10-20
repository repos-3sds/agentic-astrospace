"""
PeriodAgent — generates daily / weekly / monthly / quarterly / yearly readings
from the person's sidereal (Vedic) chart, the running Vimshottari dasha and
today's gochara, with the same output-side safety net the Ask surface uses.

Until 2026-10-14 this agent computed its natal and transit positions with
kerykeion's tropical `AstrologicalSubject`, so a Readings screen that sits next
to a sidereal Kundli told the same person their Sun was in Leo on one tab and
Cancer on the other. It was also the one LLM surface with no safety layer at
all: `prohibited_verdict()` and `dosha_overclaim_kind()` were never run on what
it produced. Both are fixed here; see `reading_boundary()` and the route.
"""
from datetime import datetime, timedelta, timezone

from .base import BaseAstroAgent
from .style import PLAIN_INDIAN_ENGLISH
from .safety import dosha_overclaim_kind, prohibited_verdict
from ..core.vedic.chart import VedicChart
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import sidereal_positions, sign_index, sign_name
from ..core.vedic.transits import _jd_from_dt
from ..knowledge.astro_kb import (
    KNOWLEDGE_BASE, get_transit_window, get_period_focus, PLANET_IN_SIGN, PLANET_IN_HOUSE
)

PERIOD_SYSTEM = """You are AstroSpace's Vedic period-reading specialist. You write daily,
weekly, monthly, quarterly and yearly readings for one specific person whose verified
sidereal chart data you fetch with tools. Every position you cite is sidereal (Lahiri
ayanamsha, whole-sign houses from the lagna); never restate it in tropical terms.

Always:
1. Call `get_natal_chart` for the lagna, the nine grahas and the running dasha.
2. Call `get_current_transits` for where the grahas are now, counted from the natal
   lagna and the natal Moon.
3. Call `get_transits_to_natal` for the gochara rules that are active and the strongest
   transit-to-natal contacts.
4. Call `lookup_knowledge` to deepen the most significant placements and contacts.
5. Synthesise everything into a focused reading for the requested period, grounded in
   the dasha lord and the active gochara rather than generic sign lore.

Boundaries — non-negotiable:
- Never predict death, lifespan or longevity, for the person or anyone in their life.
- Never diagnose illness, predict a medical outcome, or recommend treatment. Health
  stays at the level of energy and rest; anything beyond that refers to a doctor.
- Never give a legal or investment verdict; frame these as timing and tendency and
  refer the person to a qualified professional.
- A dosha or yoga is a flag, not a verdict: never say a marriage will fail, that the
  person cannot marry, or that any outcome is certain or unavoidable.
- Remedies, when mentioned, are traditional practice, never something to pay for.

Be specific, personal and practical. Use plain language a non-expert can follow, and
structure the reading with markdown section headers.
""" + PLAIN_INDIAN_ENGLISH

READING_GUARD_RETRY_NOTE = (
    "\n\nIMPORTANT: your previous draft crossed a boundary ({kind}). Rewrite the "
    "reading without any statement about death, lifespan, medical outcomes, legal "
    "outcomes, investments, or a dosha as a fixed verdict."
)


def reading_boundary(content: str) -> str | None:
    """Which boundary a generated reading crosses, or None when it is clean.

    This is the output-side net Ask already runs through its verifier. A
    reading has no user question for `refer_out_kind()` to gate, so the output
    check is the only layer that can catch a verdict the model produced on
    its own — which is exactly why it must run before anything is persisted.
    """
    return prohibited_verdict(content) or dosha_overclaim_kind(content)


def _trim_dasha(dasha: dict | None) -> dict:
    """Lord and window for each running level, without the nested tables."""
    if not dasha:
        return {}
    out = {}
    for level in ("mahadasha", "antardasha", "pratyantardasha"):
        row = dasha.get(level)
        if row:
            out[level] = {"lord": row["lord"], "start": row["start"][:10], "end": row["end"][:10]}
    return out


class PeriodAgent(BaseAstroAgent):
    system_prompt = PERIOD_SYSTEM
    tools = [
        {
            "name": "get_natal_chart",
            "description": "The person's sidereal birth chart: lagna, all 9 grahas with sign/house/nakshatra, dignities, and the running Vimshottari dasha",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_current_transits",
            "description": "Current sidereal positions of all 9 grahas with houses from the natal lagna and from the natal Moon, plus sade-sati status",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_transits_to_natal",
            "description": "Active gochara rules for this chart and the strongest transit-to-natal contacts right now",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "lookup_knowledge",
            "description": "Look up astrological meanings: planet-in-sign, planet-in-house, transit windows, aspect meanings, period focus",
            "input_schema": {
                "type": "object",
                "properties": {
                    "lookup_type": {
                        "type": "string",
                        "enum": ["planet_in_sign", "planet_in_house", "transit_window", "aspect_meaning", "period_focus"],
                    },
                    "planet":      {"type": "string", "description": "Planet name e.g. Sun, Moon, Mars"},
                    "sign":        {"type": "string", "description": "Zodiac sign e.g. Aries, Cancer"},
                    "house":       {"type": "integer", "description": "House number 1-12"},
                    "aspect":      {"type": "string", "description": "Aspect type e.g. conjunction, trine"},
                    "natal_planet":{"type": "string", "description": "Natal planet for transit window lookups"},
                    "period":      {"type": "string", "description": "Period type: daily/weekly/monthly/quarterly/yearly"},
                },
                "required": ["lookup_type"],
            },
        },
    ]

    def __init__(self, chart: VedicChart, api_key: str = None):
        super().__init__(api_key)
        self.chart = chart

    # ── tools ────────────────────────────────────────────────────────────────

    def _tool_get_natal_chart(self):
        chart = self.chart
        return {
            "zodiac": "sidereal",
            "ayanamsha": chart.ayanamsha,
            "house_system": "whole-sign from lagna",
            "person": chart.meta(),
            "lagna": chart.lagna_details(),
            "planets": chart.planet_details(),
            "dignities": chart.dignities(),
            "current_dasha": _trim_dasha(chart.dashas().get("current")),
        }

    def _tool_get_current_transits(self):
        chart = self.chart
        now = datetime.now(timezone.utc)
        current = sidereal_positions(_jd_from_dt(now), chart.ayanamsha, chart.node_type)
        lagna_sign = sign_index(chart.lagna_lon)
        moon_sign = sign_index(chart.positions["Moon"]["lon"])
        gochara = {}
        for planet, data in current.items():
            s = sign_index(data["lon"])
            gochara[planet] = {
                "sign": sign_name(s),
                "nakshatra": nakshatra_of(data["lon"])["name"],
                "house_from_lagna": (s - lagna_sign) % 12 + 1,
                "house_from_moon": (s - moon_sign) % 12 + 1,
                "retrograde": data["retrograde"],
            }
        sat_from_moon = gochara["Saturn"]["house_from_moon"]
        return {
            "zodiac": "sidereal",
            "as_of_utc": now.isoformat(),
            "gochara": gochara,
            "sade_sati": {
                "active": sat_from_moon in (12, 1, 2),
                "phase": {12: "first (rising)", 1: "second (peak)", 2: "third (setting)"}.get(sat_from_moon),
                "saturn_house_from_moon": sat_from_moon,
            },
        }

    def _tool_get_transits_to_natal(self):
        analysis = self.chart.transits()
        rules = [
            {k: row.get(k) for k in ("name", "planet", "anchor", "house", "severity", "tone", "trigger", "explanation")}
            for row in analysis["gochara"].get("rules", []) if row.get("active")
        ]
        aspects = []
        for row in analysis["active_aspects"][:8]:
            aspect = dict(row)
            aspect["interpretation"] = get_transit_window(
                row["transit_planet"], row["aspect"].lower(), row["natal_planet"],
            )
            aspects.append(aspect)
        return {
            "zodiac": "sidereal",
            "as_of": analysis["as_of"],
            "natal": analysis["natal"],
            "active_gochara_rules": rules,
            "active_aspects": aspects,
        }

    def _tool_lookup_knowledge(self, lookup_type, planet=None, sign=None, house=None,
                               aspect=None, natal_planet=None, period=None):
        if lookup_type == "planet_in_sign" and planet and sign:
            return PLANET_IN_SIGN.get((planet, sign), f"No specific entry for {planet} in {sign}.")
        if lookup_type == "planet_in_house" and planet and house:
            return PLANET_IN_HOUSE.get((planet, house), f"No specific entry for {planet} in house {house}.")
        if lookup_type == "transit_window" and planet and aspect and natal_planet:
            return get_transit_window(planet, aspect.replace(" ", "_"), natal_planet)
        if lookup_type == "aspect_meaning" and aspect:
            return KNOWLEDGE_BASE["aspect_meanings"].get(aspect.lower(), "")
        if lookup_type == "period_focus" and period:
            return get_period_focus(period)
        return "No result found for the given parameters."

    # ── entry point ──────────────────────────────────────────────────────────

    def reading_prompt(self, period: str, now: datetime) -> str:
        chart = self.chart
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        period_labels = {
            "daily":     f"today {now.strftime('%B %d, %Y')}",
            # The calendar week the reading is filed under (Monday to
            # Sunday, see reading_routes._period_label), not the seven days
            # from whenever it was asked for.
            "weekly":    (
                f"the week of {week_start.strftime('%B')} {week_start.day} to "
                f"{week_end.strftime('%B')} {week_end.day}, {week_end.year} "
                f"(today is {now.strftime('%A')}, {now.strftime('%B')} {now.day})"
            ),
            "monthly":   f"{now.strftime('%B %Y')}",
            "quarterly": f"Q{((now.month - 1) // 3) + 1} {now.year}",
            "yearly":    f"the year {now.year}",
        }
        label = period_labels.get(period, period)
        m = chart.moment
        return (
            f"Generate a {period} Vedic reading for {chart.name} for {label}.\n\n"
            f"Birth details: {m.dt_local.strftime('%Y-%m-%d %H:%M')} local time, "
            f"{chart.city or 'given coordinates'} (sidereal, {chart.ayanamsha} ayanamsha).\n\n"
            "Steps:\n"
            "1. Use get_natal_chart for the lagna, grahas and running dasha.\n"
            "2. Use get_current_transits for today's gochara from lagna and Moon.\n"
            "3. Use get_transits_to_natal for the active gochara rules and contacts.\n"
            "4. Use lookup_knowledge to deepen the most significant placements and transits.\n"
            f"5. Write a rich, structured {period} reading covering: overall theme, key areas of life "
            "(love/relationships, career/finances, energy and rest, spiritual growth), and specific guidance.\n\n"
            "Make the reading feel personal, insightful, and empowering. Use markdown headers. "
            "Stay within the boundaries in your instructions."
        )

    def generate_reading(self, period: str, now: datetime | None = None) -> tuple[str, str | None]:
        """Return `(content, crossed)`.

        `crossed` is None when the reading is clean. When the first draft
        crosses a boundary the model is asked once more with the boundary
        named; if that draft also crosses, the caller gets the kind and must
        not publish the content. The agent never returns a cleaned-up
        fragment of a bad reading — a reading is cheap to regenerate and a
        half-redacted one still carries the framing that produced the verdict.
        """
        now = now or datetime.now(self.chart.moment.dt_local.tzinfo)
        prompt = self.reading_prompt(period, now)
        content = self.run(prompt)
        crossed = reading_boundary(content)
        if crossed is None:
            return content, None
        content = self.run(prompt + READING_GUARD_RETRY_NOTE.format(kind=crossed))
        return content, reading_boundary(content)
