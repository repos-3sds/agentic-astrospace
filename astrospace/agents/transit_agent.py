from .base import BaseAstroAgent
from ..core.chart import BirthChart
from ..core.transits import TransitCalculator
from ..ai.prompts import SYSTEM_TRANSIT


class TransitAgent(BaseAstroAgent):
    system_prompt = SYSTEM_TRANSIT
    tools = [
        {
            "name": "calculate_natal_chart",
            "description": "Calculate a person's natal chart",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}, "year": {"type": "integer"},
                    "month": {"type": "integer"}, "day": {"type": "integer"},
                    "hour": {"type": "integer"}, "minute": {"type": "integer"},
                    "city": {"type": "string"}, "nation": {"type": "string"},
                },
                "required": ["name", "year", "month", "day", "hour", "minute", "city", "nation"],
            },
        },
        {
            "name": "get_transits_to_natal",
            "description": "Get current planetary transits aspecting the natal chart",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}, "year": {"type": "integer"},
                    "month": {"type": "integer"}, "day": {"type": "integer"},
                    "hour": {"type": "integer"}, "minute": {"type": "integer"},
                    "city": {"type": "string"}, "nation": {"type": "string"},
                },
                "required": ["name", "year", "month", "day", "hour", "minute", "city", "nation"],
            },
        },
    ]

    def _tool_calculate_natal_chart(self, name, year, month, day, hour, minute, city, nation="US"):
        return BirthChart(name, year, month, day, hour, minute, city, nation).to_dict()

    def _tool_get_transits_to_natal(self, name, year, month, day, hour, minute, city, nation="US"):
        chart = BirthChart(name, year, month, day, hour, minute, city, nation)
        calc = TransitCalculator()
        return {
            "natal_name": name,
            "transits": calc.get_transits_to_natal(chart.subject),
        }

    def get_transit_reading(self, name: str, year: int, month: int, day: int,
                             hour: int, minute: int, city: str, nation: str = "US") -> str:
        return self.run(
            f"Provide a transit reading for {name}.\n\n"
            "First use calculate_natal_chart, then get_transits_to_natal. Provide:\n"
            "1. **Current Cosmic Weather** (what's happening in the sky now)\n"
            "2. **Major Active Transits** (significant outer planet transits)\n"
            "3. **Next 30 Days** (key windows and dates)\n"
            "4. **Growth Themes** (what the universe is inviting you to work on)\n"
            "5. **Opportunities** (favorable transit windows)\n"
            "6. **Navigate With Care** (challenging transits and how to work with them)\n"
            "7. **Power Periods** (your peak energy windows)"
        )
