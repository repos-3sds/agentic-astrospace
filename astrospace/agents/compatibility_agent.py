from .base import BaseAstroAgent
from ..core.chart import BirthChart
from ..ai.prompts import SYSTEM_COMPATIBILITY

try:
    from kerykeion import SynastryAspects
except ImportError:
    from kerykeion.aspects import SynastryAspects


class CompatibilityAgent(BaseAstroAgent):
    system_prompt = SYSTEM_COMPATIBILITY
    tools = [
        {
            "name": "calculate_synastry",
            "description": "Calculate astrological synastry aspects between two people",
            "input_schema": {
                "type": "object",
                "properties": {
                    "p1_name": {"type": "string"}, "p1_year": {"type": "integer"},
                    "p1_month": {"type": "integer"}, "p1_day": {"type": "integer"},
                    "p1_hour": {"type": "integer"}, "p1_minute": {"type": "integer"},
                    "p1_city": {"type": "string"}, "p1_nation": {"type": "string"},
                    "p2_name": {"type": "string"}, "p2_year": {"type": "integer"},
                    "p2_month": {"type": "integer"}, "p2_day": {"type": "integer"},
                    "p2_hour": {"type": "integer"}, "p2_minute": {"type": "integer"},
                    "p2_city": {"type": "string"}, "p2_nation": {"type": "string"},
                },
                "required": [
                    "p1_name", "p1_year", "p1_month", "p1_day", "p1_hour", "p1_minute", "p1_city", "p1_nation",
                    "p2_name", "p2_year", "p2_month", "p2_day", "p2_hour", "p2_minute", "p2_city", "p2_nation",
                ],
            },
        }
    ]

    def _tool_calculate_synastry(self, p1_name, p1_year, p1_month, p1_day, p1_hour, p1_minute, p1_city, p1_nation,
                                  p2_name, p2_year, p2_month, p2_day, p2_hour, p2_minute, p2_city, p2_nation):
        c1 = BirthChart(p1_name, p1_year, p1_month, p1_day, p1_hour, p1_minute, p1_city, p1_nation)
        c2 = BirthChart(p2_name, p2_year, p2_month, p2_day, p2_hour, p2_minute, p2_city, p2_nation)
        synastry = SynastryAspects(c1.subject, c2.subject)
        return {
            "person1": {"name": p1_name, "sun": c1.subject.sun.sign,
                        "moon": c1.subject.moon.sign, "ascendant": c1.subject.first_house.sign},
            "person2": {"name": p2_name, "sun": c2.subject.sun.sign,
                        "moon": c2.subject.moon.sign, "ascendant": c2.subject.first_house.sign},
            "synastry_aspects": [
                {"p1_planet": a.get("p1_name", ""), "p2_planet": a.get("p2_name", ""),
                 "aspect": a.get("aspect", ""), "orb": round(float(a.get("orbit", 0)), 2)}
                for a in synastry.all_aspects
            ],
        }

    def get_compatibility_reading(self,
                                   name1, year1, month1, day1, hour1, minute1, city1, nation1,
                                   name2, year2, month2, day2, hour2, minute2, city2, nation2) -> str:
        return self.run(
            f"Analyze astrological compatibility between {name1} and {name2}.\n\n"
            "Use calculate_synastry to get their data, then provide:\n"
            "1. **Compatibility Score** (0-100) with overall summary\n"
            "2. **Soul Connection** (karmic ties, North Node links)\n"
            "3. **Love & Romance** (Venus-Mars connections)\n"
            "4. **Emotional Bond** (Sun-Moon connections)\n"
            "5. **Communication** (Mercury connections)\n"
            "6. **Growth Challenges** (squares and oppositions to work through)\n"
            "7. **Relationship Strengths** (harmonious aspects)\n"
            "8. **Guidance** (practical advice for thriving together)"
        )
