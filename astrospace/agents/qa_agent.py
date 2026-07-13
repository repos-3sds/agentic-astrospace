"""
VedicQAAgent — answers free-form questions about a specific person,
grounded in the computed Vedic engine outputs.

Unlike the other agents, its tools are BOUND to one kundli at construction:
the model never passes birth details, it just asks for chart sections.
This guarantees every answer is grounded in the same verified data the
UI displays.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from .base import BaseAstroAgent
from ..core.cities import lookup_city
from ..core.vedic.chart import VedicChart
from ..core.vedic.vargas import VARGA_FUNCTIONS, VARGA_INFO
from ..core.vedic.panchanga_day import daily_panchanga, personal_panchanga
from ..core.vedic.positions import sidereal_positions, sign_index, sign_name
from ..core.vedic.nakshatra import nakshatra_of
import swisseph as swe

QA_SYSTEM = """You are AstroSpace's Vedic astrology assistant. You answer questions
about one specific person whose verified sidereal chart data you can fetch with tools.

Grounding rules — non-negotiable:
1. NEVER answer from generic astrology knowledge alone. Fetch the relevant data first:
   - personality/life overview → get_birth_chart
   - career/status → get_birth_chart + get_varga_chart(D10)
   - marriage/relationships → get_birth_chart + get_varga_chart(D9)
   - health → get_varga_chart(D6); wealth → D2; children → D7; education → D24
   - "is today good for X" / muhurta / timing → get_today_panchanga
   - current planetary influences / sade sati → get_current_gochara
2. End every answer with a short "Astrological basis:" section listing the exact
   placements you used (planet, sign, house, dignity, varga).
3. If the data doesn't clearly support an answer, say so honestly.
4. Never predict death, diagnose illness, or give directive medical/legal/financial
   advice — frame those as tendencies and suggest professional consultation.
5. Be warm, practical, and concise (under ~350 words unless asked for depth).
6. The engine's D5/D6/D8/D11 varga rules and some panchanga tables await
   validation — if you rely on one, add a one-line caveat.
"""


class VedicQAAgent(BaseAstroAgent):
    system_prompt = QA_SYSTEM
    tools = [
        {
            "name": "get_birth_chart",
            "description": "The person's sidereal birth chart: lagna, all 9 grahas with sign/house/nakshatra/dignity, and Avkahada details",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
        {
            "name": "get_varga_chart",
            "description": "A divisional chart (D1-D60) with planet placements and varga lagna. Use D9 for marriage, D10 for career, D6 health, D2 wealth, D7 children, D24 education",
            "input_schema": {
                "type": "object",
                "properties": {"varga": {"type": "string", "description": "e.g. D9, D10"}},
                "required": ["varga"],
            },
        },
        {
            "name": "get_today_panchanga",
            "description": "Today's panchanga at the person's location with personal indicators: tithi/nakshatra with end times, auspicious windows (Abhijit, Amrit Kalam, Brahma Muhurta, Choghadiya), inauspicious windows (Rahu Kalam, Yamaganda, Gulika, Durmuhurta, Varjya), tarabala, chandrabala, ghatak alerts",
            "input_schema": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "YYYY-MM-DD, default today"}},
                "required": [],
            },
        },
        {
            "name": "get_current_gochara",
            "description": "Current transit (gochara) positions of all 9 grahas with houses from natal lagna AND from natal Moon, plus sade-sati status",
            "input_schema": {"type": "object", "properties": {}, "required": []},
        },
    ]

    def __init__(self, kundli, api_key: str = None):
        super().__init__(api_key)
        self.kundli = kundli
        self.chart = VedicChart(
            kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
            kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation,
        )

    # ── tools ────────────────────────────────────────────────────────────────

    def _tool_get_birth_chart(self):
        return {
            "person": self.chart.meta(),
            "lagna": self.chart.lagna_details(),
            "planets": self.chart.planet_details(),
            "dignities": self.chart.dignities(),
            "avkahada": self.chart.avkahada(),
        }

    def _tool_get_varga_chart(self, varga: str):
        varga = varga.upper().strip()
        if varga not in VARGA_FUNCTIONS:
            return {"error": f"Unknown varga {varga}; options: {sorted(VARGA_FUNCTIONS)}"}
        return self.chart.varga_chart(varga)

    def _tool_get_today_panchanga(self, date: str = None):
        k = self.kundli
        geo = lookup_city(k.birth_city, k.birth_nation)
        if not geo:
            return {"error": f"City {k.birth_city!r} not resolvable offline."}
        lat, lng, tz_str = geo
        if date:
            y, m, d = (int(x) for x in date.split("-"))
        else:
            now = datetime.now(ZoneInfo(tz_str))
            y, m, d = now.year, now.month, now.day
        payload = daily_panchanga(y, m, d, k.birth_city, k.birth_nation, lat, lng, tz_str)
        moon_lon = self.chart.positions["Moon"]["lon"]
        payload["personal"] = personal_panchanga(
            payload,
            janma_nakshatra_index=nakshatra_of(moon_lon)["index"],
            janma_rashi_index=sign_index(moon_lon),
            ghatak_moon_sign=sign_index(moon_lon),
        )
        payload.pop("horas", None)  # trim tokens; choghadiya covers timing granularity
        return payload

    def _tool_get_current_gochara(self):
        now = datetime.utcnow()
        jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute / 60.0)
        current = sidereal_positions(jd)
        lagna_sign = sign_index(self.chart.lagna_lon)
        moon_sign = sign_index(self.chart.positions["Moon"]["lon"])

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
        sade_sati = {
            "active": sat_from_moon in (12, 1, 2),
            "phase": {12: "first (rising)", 1: "second (peak)", 2: "third (setting)"}.get(sat_from_moon),
            "saturn_house_from_moon": sat_from_moon,
        }
        return {"as_of_utc": now.isoformat(), "gochara": gochara, "sade_sati": sade_sati}
