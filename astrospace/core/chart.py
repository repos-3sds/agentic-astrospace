from kerykeion import AstrologicalSubject, NatalAspects
from dataclasses import dataclass
from .planets import SIGN_MEANINGS

_HOUSE_NAME_MAP = {
    "First_House": 1, "Second_House": 2, "Third_House": 3,
    "Fourth_House": 4, "Fifth_House": 5, "Sixth_House": 6,
    "Seventh_House": 7, "Eighth_House": 8, "Ninth_House": 9,
    "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12,
}

_ORDINALS = [
    "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
]

PLANET_ATTRS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune", "pluto",
]


@dataclass
class PlanetData:
    name: str
    sign: str
    house: int
    degree: float
    abs_pos: float
    retrograde: bool
    element: str
    modality: str


@dataclass
class AspectData:
    planet1: str
    planet2: str
    aspect_type: str
    orb: float


@dataclass
class HouseData:
    number: int
    sign: str
    degree: float


class BirthChart:
    def __init__(self, name: str, year: int, month: int, day: int,
                 hour: int, minute: int, city: str, nation: str = "US"):
        self.subject = AstrologicalSubject(
            name=name, year=year, month=month, day=day,
            hour=hour, minute=minute, city=city, nation=nation,
        )
        self.name = name

    def _house_to_int(self, val) -> int:
        if isinstance(val, int):
            return val
        return _HOUSE_NAME_MAP.get(str(val), 0)

    def get_planet(self, attr: str) -> PlanetData:
        p = getattr(self.subject, attr)
        sign_data = SIGN_MEANINGS.get(p.sign, {})
        return PlanetData(
            name=p.name,
            sign=p.sign,
            house=self._house_to_int(p.house),
            degree=round(float(p.pos), 2),
            abs_pos=round(float(p.abs_pos), 2),
            retrograde=bool(getattr(p, "retrograde", False)),
            element=sign_data.get("element", ""),
            modality=sign_data.get("modality", ""),
        )

    def get_all_planets(self) -> list:
        return [self.get_planet(attr) for attr in PLANET_ATTRS]

    def get_houses(self) -> list:
        houses = []
        for i, ordinal in enumerate(_ORDINALS, start=1):
            h = getattr(self.subject, f"{ordinal}_house")
            houses.append(HouseData(
                number=i,
                sign=h.sign,
                degree=round(float(h.pos), 2),
            ))
        return houses

    def get_aspects(self) -> list:
        natal = NatalAspects(self.subject)
        return [
            AspectData(
                planet1=a.get("p1_name", ""),
                planet2=a.get("p2_name", ""),
                aspect_type=a.get("aspect", ""),
                orb=round(float(a.get("orbit", 0)), 2),
            )
            for a in natal.all_aspects
        ]

    def to_dict(self) -> dict:
        planets = self.get_all_planets()
        sun = next((p for p in planets if p.name == "Sun"), None)
        moon = next((p for p in planets if p.name == "Moon"), None)
        return {
            "name": self.name,
            "birth_date": f"{self.subject.year}-{self.subject.month:02d}-{self.subject.day:02d}",
            "birth_time": f"{self.subject.hour:02d}:{self.subject.minute:02d}",
            "city": self.subject.city,
            "sun_sign": sun.sign if sun else "",
            "moon_sign": moon.sign if moon else "",
            "ascendant": self.subject.first_house.sign,
            "planets": [
                {"name": p.name, "sign": p.sign, "house": p.house,
                 "degree": p.degree, "retrograde": p.retrograde,
                 "element": p.element, "modality": p.modality}
                for p in planets
            ],
            "houses": [
                {"number": h.number, "sign": h.sign, "degree": h.degree}
                for h in self.get_houses()
            ],
            "aspects": [
                {"planet1": a.planet1, "planet2": a.planet2,
                 "type": a.aspect_type, "orb": a.orb}
                for a in self.get_aspects()
            ],
        }
