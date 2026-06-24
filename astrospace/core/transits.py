from kerykeion import AstrologicalSubject
from datetime import datetime, timezone

try:
    from kerykeion import SynastryAspects
except ImportError:
    from kerykeion.aspects import SynastryAspects

PLANET_ATTRS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]


class TransitCalculator:
    def __init__(self, city: str = "London", nation: str = "GB"):
        self.city = city
        self.nation = nation

    def _now_subject(self) -> AstrologicalSubject:
        now = datetime.now(timezone.utc)
        return AstrologicalSubject(
            "Transits", now.year, now.month, now.day,
            now.hour, now.minute, self.city, self.nation,
        )

    def get_current_transits(self) -> dict:
        subject = self._now_subject()
        result = {}
        for attr in PLANET_ATTRS:
            p = getattr(subject, attr)
            result[p.name] = {
                "sign": p.sign,
                "degree": round(float(p.pos), 2),
                "abs_pos": round(float(p.abs_pos), 2),
                "retrograde": bool(getattr(p, "retrograde", False)),
            }
        return result

    def get_transits_to_natal(self, natal_subject: AstrologicalSubject) -> list:
        transit = self._now_subject()
        synastry = SynastryAspects(transit, natal_subject)
        return [
            {
                "transit_planet": a.get("p1_name", ""),
                "natal_planet": a.get("p2_name", ""),
                "aspect": a.get("aspect", ""),
                "orb": round(float(a.get("orbit", 0)), 2),
            }
            for a in synastry.all_aspects
        ]
