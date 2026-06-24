from .base import BaseAstroAgent
from ..core.chart import BirthChart
from ..core.planets import PLANET_MEANINGS, SIGN_MEANINGS, HOUSE_MEANINGS
from ..ai.prompts import SYSTEM_ASTROLOGER


class ReadingAgent(BaseAstroAgent):
    system_prompt = SYSTEM_ASTROLOGER
    tools = [
        {
            "name": "calculate_natal_chart",
            "description": "Calculate a person's natal chart with all planetary positions, houses, and aspects",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "year": {"type": "integer"},
                    "month": {"type": "integer"},
                    "day": {"type": "integer"},
                    "hour": {"type": "integer"},
                    "minute": {"type": "integer"},
                    "city": {"type": "string"},
                    "nation": {"type": "string", "description": "ISO country code, e.g. US, GB, IN"},
                },
                "required": ["name", "year", "month", "day", "hour", "minute", "city", "nation"],
            },
        },
        {
            "name": "get_placement_meaning",
            "description": "Get astrological meaning of a planet in a specific sign and house",
            "input_schema": {
                "type": "object",
                "properties": {
                    "planet": {"type": "string"},
                    "sign": {"type": "string"},
                    "house": {"type": "integer"},
                },
                "required": ["planet", "sign", "house"],
            },
        },
    ]

    def _tool_calculate_natal_chart(self, name, year, month, day, hour, minute, city, nation="US"):
        return BirthChart(name, year, month, day, hour, minute, city, nation).to_dict()

    def _tool_get_placement_meaning(self, planet: str, sign: str, house: int) -> dict:
        return {
            "planet_archetype": PLANET_MEANINGS.get(planet, {}).get("archetype", ""),
            "sign_traits": SIGN_MEANINGS.get(sign, {}).get("traits", ""),
            "sign_element": SIGN_MEANINGS.get(sign, {}).get("element", ""),
            "house_area": HOUSE_MEANINGS.get(house, {}).get("area", ""),
        }

    def get_full_reading(self, name: str, year: int, month: int, day: int,
                         hour: int, minute: int, city: str, nation: str = "US") -> str:
        prompt = (
            f"Provide a comprehensive natal chart reading for {name}, "
            f"born {year}-{month:02d}-{day:02d} at {hour:02d}:{minute:02d} in {city}, {nation}.\n\n"
            "Use calculate_natal_chart to get their chart, then provide:\n"
            "1. **Big Three** (Sun, Moon, Rising and how they interact)\n"
            "2. **Dominant Themes** (element/modality balance, chart shape)\n"
            "3. **Key Placements** (most significant planets and house positions)\n"
            "4. **Major Aspects** (powerful aspects shaping the personality)\n"
            "5. **Soul Purpose** (life path themes)\n"
            "6. **Opportunities & Challenges** (chart dynamics to work with)\n\n"
            "Make it personal, insightful, and empowering."
        )
        return self.run(prompt)
