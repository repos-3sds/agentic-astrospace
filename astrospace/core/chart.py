from kerykeion import AstrologicalSubject, NatalAspects
from dataclasses import dataclass
from .cities import lookup_city

# kerykeion v5 uses 3-letter sign abbreviations
SIGN_ABBR = {
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer",
    "Leo": "Leo", "Vir": "Virgo", "Lib": "Libra", "Sco": "Scorpio",
    "Sag": "Sagittarius", "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces",
}

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


def _full_sign(abbr: str) -> str:
    return SIGN_ABBR.get(abbr, abbr)


def _house_to_int(val) -> int:
    if isinstance(val, int):
        return val
    if val is None:
        return 0
    return _HOUSE_NAME_MAP.get(str(val), 0)


def _make_subject(name, year, month, day, hour, minute, city, nation="US",
                  lat=None, lng=None, tz_str=None) -> AstrologicalSubject:
    """Create AstrologicalSubject, preferring offline lat/lng when available."""
    if lat is not None and lng is not None and tz_str:
        return AstrologicalSubject(
            name=name, year=year, month=month, day=day, hour=hour, minute=minute,
            lng=lng, lat=lat, tz_str=tz_str, online=False,
        )
    geo = lookup_city(city)
    if geo:
        lat, lng, tz = geo
        return AstrologicalSubject(
            name=name, year=year, month=month, day=day, hour=hour, minute=minute,
            lng=lng, lat=lat, tz_str=tz, online=False,
        )
    # Fall back to online GeoNames lookup
    return AstrologicalSubject(
        name=name, year=year, month=month, day=day, hour=hour, minute=minute,
        city=city, nation=nation,
    )


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
                 hour: int, minute: int, city: str, nation: str = "US",
                 lat: float = None, lng: float = None, tz_str: str = None):
        self.subject = _make_subject(name, year, month, day, hour, minute,
                                     city, nation, lat, lng, tz_str)
        self.name = name
        self.city = city

    def get_planet(self, attr: str) -> PlanetData:
        p = getattr(self.subject, attr)
        return PlanetData(
            name=p.name,
            sign=_full_sign(p.sign),
            house=_house_to_int(p.house),
            degree=round(float(p.position), 2),
            abs_pos=round(float(p.abs_pos), 2),
            retrograde=bool(p.retrograde) if p.retrograde is not None else False,
            element=p.element or "",
            modality=p.quality or "",
        )

    def get_all_planets(self) -> list:
        return [self.get_planet(attr) for attr in PLANET_ATTRS]

    def get_houses(self) -> list:
        houses = []
        for i, ordinal in enumerate(_ORDINALS, start=1):
            h = getattr(self.subject, f"{ordinal}_house")
            houses.append(HouseData(
                number=i,
                sign=_full_sign(h.sign),
                degree=round(float(h.position), 2),
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
        planet_list = [
            {"name": p.name, "sign": p.sign, "house": p.house,
             "degree": p.degree, "abs_pos": p.abs_pos,
             "retrograde": p.retrograde, "element": p.element, "modality": p.modality}
            for p in planets
        ]
        return {
            "name": self.name,
            "birth_date": f"{self.subject.year}-{self.subject.month:02d}-{self.subject.day:02d}",
            "birth_time": f"{self.subject.hour:02d}:{self.subject.minute:02d}",
            "city": self.city,
            "sun_sign": sun.sign if sun else "",
            "moon_sign": moon.sign if moon else "",
            "ascendant": _full_sign(self.subject.first_house.sign),
            "planets": {p["name"]: p for p in planet_list},
            "houses": {
                str(h.number): {"sign": h.sign, "degree": h.degree}
                for h in self.get_houses()
            },
            "aspects": [
                {"planet1": a.planet1, "planet2": a.planet2,
                 "type": a.aspect_type, "orb": a.orb}
                for a in self.get_aspects()
            ],
        }
