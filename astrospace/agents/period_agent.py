"""
PeriodAgent — generates daily / weekly / monthly / quarterly / yearly readings
using the natal chart + current transits + astrological knowledge base.
"""
import json
from datetime import datetime, timezone
from .base import BaseAstroAgent
from ..core.chart import BirthChart
from ..core.transits import TransitCalculator
from ..knowledge.astro_kb import (
    KNOWLEDGE_BASE, get_transit_window, get_period_focus, PLANET_IN_SIGN, PLANET_IN_HOUSE
)
from ..ai.prompts import SYSTEM_ASTROLOGER

PERIOD_SYSTEM = SYSTEM_ASTROLOGER + """

You specialise in time-based readings (daily, weekly, monthly, quarterly, yearly).
Always:
1. Call `get_natal_chart` to retrieve the person's natal positions.
2. Call `get_current_transits` to see where planets are NOW.
3. Call `get_transits_to_natal` to find active planetary aspects between NOW and NATAL chart.
4. Call `lookup_knowledge` with relevant planet/sign/aspect combos for interpretation depth.
5. Synthesise everything into a focused reading appropriate for the requested period.

Be specific, personal, and practical. Use vivid astrological language that non-experts can understand.
Structure your output clearly with section headers.
"""


class PeriodAgent(BaseAstroAgent):
    system_prompt = PERIOD_SYSTEM
    tools = [
        {
            "name": "get_natal_chart",
            "description": "Get the natal chart for a person from their birth details",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name":   {"type": "string"},
                    "year":   {"type": "integer"},
                    "month":  {"type": "integer"},
                    "day":    {"type": "integer"},
                    "hour":   {"type": "integer"},
                    "minute": {"type": "integer"},
                    "city":   {"type": "string"},
                    "nation": {"type": "string"},
                },
                "required": ["name", "year", "month", "day", "hour", "minute", "city", "nation"],
            },
        },
        {
            "name": "get_current_transits",
            "description": "Get current planetary positions (today's sky)",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_transits_to_natal",
            "description": "Get active aspects between today's transiting planets and a natal chart",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name":   {"type": "string"},
                    "year":   {"type": "integer"},
                    "month":  {"type": "integer"},
                    "day":    {"type": "integer"},
                    "hour":   {"type": "integer"},
                    "minute": {"type": "integer"},
                    "city":   {"type": "string"},
                    "nation": {"type": "string"},
                },
                "required": ["name", "year", "month", "day", "hour", "minute", "city", "nation"],
            },
        },
        {
            "name": "lookup_knowledge",
            "description": "Look up astrological meanings: planet-in-sign, planet-in-house, transit windows, aspect meanings",
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

    def _tool_get_natal_chart(self, name, year, month, day, hour, minute, city, nation="US"):
        return BirthChart(name, year, month, day, hour, minute, city, nation).to_dict()

    def _tool_get_current_transits(self):
        tc = TransitCalculator()
        return tc.get_current_transits()

    def _tool_get_transits_to_natal(self, name, year, month, day, hour, minute, city, nation="US"):
        tc = TransitCalculator()
        natal = BirthChart(name, year, month, day, hour, minute, city, nation).subject
        aspects = tc.get_transits_to_natal(natal)
        # enrich each aspect with a transit window description
        for a in aspects:
            a["interpretation"] = get_transit_window(
                a.get("transit_planet", ""),
                a.get("aspect", "").replace(" ", "_"),
                a.get("natal_planet", ""),
            )
        return aspects

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

    def generate_reading(
        self,
        period: str,
        name: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        city: str,
        nation: str = "US",
    ) -> str:
        now = datetime.now(timezone.utc)
        period_labels = {
            "daily":     f"today {now.strftime('%B %d, %Y')}",
            "weekly":    f"the week of {now.strftime('%B %d, %Y')}",
            "monthly":   f"{now.strftime('%B %Y')}",
            "quarterly": f"Q{((now.month - 1) // 3) + 1} {now.year}",
            "yearly":    f"the year {now.year}",
        }
        label = period_labels.get(period, period)

        prompt = (
            f"Generate a {period} astrological reading for {name} for {label}.\n\n"
            f"Birth details: {year}-{month:02d}-{day:02d} at {hour:02d}:{minute:02d}, {city}, {nation}.\n\n"
            "Steps:\n"
            "1. Use get_natal_chart to retrieve natal positions.\n"
            "2. Use get_current_transits to see today's planetary positions.\n"
            "3. Use get_transits_to_natal to find active planetary aspects now.\n"
            "4. Use lookup_knowledge to deepen interpretation of the most significant placements and transits.\n"
            f"5. Write a rich, structured {period} reading covering: overall theme, key areas of life "
            "(love/relationships, career/finances, health, spiritual growth), and specific guidance.\n\n"
            "Make the reading feel personal, insightful, and empowering. Use markdown headers."
        )
        return self.run(prompt)
