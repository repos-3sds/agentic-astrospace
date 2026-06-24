from datetime import datetime
from .base import BaseAstroAgent
from ..core.transits import TransitCalculator
from ..ai.prompts import SYSTEM_DAILY_HOROSCOPE


class HoroscopeAgent(BaseAstroAgent):
    system_prompt = SYSTEM_DAILY_HOROSCOPE
    tools = [
        {
            "name": "get_current_transits",
            "description": "Get current planetary positions for today",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        }
    ]

    def _tool_get_current_transits(self) -> dict:
        return TransitCalculator().get_current_transits()

    def get_daily_horoscope(self, sun_sign: str) -> str:
        today = datetime.now().strftime("%B %d, %Y")
        return self.run(
            f"Generate a daily horoscope for {sun_sign} for {today}.\n\n"
            "First call get_current_transits, then write a horoscope with:\n"
            "- **Overview**: General energy for the day\n"
            "- **Love & Relationships**\n"
            "- **Career & Finances**\n"
            "- **Health & Wellbeing**\n"
            "- **Power Affirmation**\n"
            "- **Lucky Element**"
        )

    def get_weekly_horoscope(self, sun_sign: str) -> str:
        today = datetime.now().strftime("%B %d, %Y")
        return self.run(
            f"Generate a weekly horoscope for {sun_sign} starting {today}.\n\n"
            "First call get_current_transits, then write a weekly forecast with:\n"
            "- **Weekly Theme**\n"
            "- **Early Week (Mon-Wed)**\n"
            "- **Late Week (Thu-Sat)**\n"
            "- **Sunday Reset**\n"
            "- **Key Dates** this week\n"
            "- **Weekly Affirmation**"
        )
