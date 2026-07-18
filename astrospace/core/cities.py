"""Offline city lookup with common cities, falls back to None (online GeoNames).

In addition to the curated worldwide table below, a complete GeoNames-derived
populated-places dataset for selected Indian states (currently Andhra Pradesh
and Telangana, ~36k villages/towns) is loaded lazily from
data/state_places.json.gz — regenerate with scripts/build_state_places.py.
"""

from __future__ import annotations

import gzip
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_STATE_PLACES_PATH = Path(__file__).parent / "data" / "state_places.json.gz"
_STATE_NAMES = {"AP": "Andhra Pradesh", "TS": "Telangana"}

# (city_lower, nation_lower) -> (lat, lng, timezone)
_CITIES: dict[tuple[str, str], tuple[float, float, str]] = {
    ("new york", "us"): (40.7128, -74.0060, "America/New_York"),
    ("los angeles", "us"): (34.0522, -118.2437, "America/Los_Angeles"),
    ("chicago", "us"): (41.8781, -87.6298, "America/Chicago"),
    ("houston", "us"): (29.7604, -95.3698, "America/Chicago"),
    ("phoenix", "us"): (33.4484, -112.0740, "America/Phoenix"),
    ("san francisco", "us"): (37.7749, -122.4194, "America/Los_Angeles"),
    ("seattle", "us"): (47.6062, -122.3321, "America/Los_Angeles"),
    ("boston", "us"): (42.3601, -71.0589, "America/New_York"),
    ("miami", "us"): (25.7617, -80.1918, "America/New_York"),
    ("atlanta", "us"): (33.7490, -84.3880, "America/New_York"),
    ("dallas", "us"): (32.7767, -96.7970, "America/Chicago"),
    ("denver", "us"): (39.7392, -104.9903, "America/Denver"),
    ("las vegas", "us"): (36.1699, -115.1398, "America/Los_Angeles"),
    ("portland", "us"): (45.5051, -122.6750, "America/Los_Angeles"),
    ("washington", "us"): (38.9072, -77.0369, "America/New_York"),
    ("mumbai", "in"): (19.0760, 72.8777, "Asia/Kolkata"),
    ("delhi", "in"): (28.6139, 77.2090, "Asia/Kolkata"),
    ("new delhi", "in"): (28.6139, 77.2090, "Asia/Kolkata"),
    ("bangalore", "in"): (12.9716, 77.5946, "Asia/Kolkata"),
    ("bengaluru", "in"): (12.9716, 77.5946, "Asia/Kolkata"),
    ("hyderabad", "in"): (17.3850, 78.4867, "Asia/Kolkata"),
    ("chennai", "in"): (13.0827, 80.2707, "Asia/Kolkata"),
    ("kolkata", "in"): (22.5726, 88.3639, "Asia/Kolkata"),
    ("pune", "in"): (18.5204, 73.8567, "Asia/Kolkata"),
    ("ahmedabad", "in"): (23.0225, 72.5714, "Asia/Kolkata"),
    ("visakhapatnam", "in"): (17.6868, 83.2185, "Asia/Kolkata"),
    ("vizag", "in"): (17.6868, 83.2185, "Asia/Kolkata"),
    ("vijayawada", "in"): (16.5062, 80.6480, "Asia/Kolkata"),
    ("guntur", "in"): (16.3067, 80.4365, "Asia/Kolkata"),
    ("rajahmundry", "in"): (17.0005, 81.8040, "Asia/Kolkata"),
    ("kakinada", "in"): (16.9891, 82.2475, "Asia/Kolkata"),
    ("nellore", "in"): (14.4426, 79.9865, "Asia/Kolkata"),
    ("kurnool", "in"): (15.8281, 78.0373, "Asia/Kolkata"),
    ("tirupati", "in"): (13.6288, 79.4192, "Asia/Kolkata"),
    ("warangal", "in"): (17.9689, 79.5941, "Asia/Kolkata"),
    ("surat", "in"): (21.1702, 72.8311, "Asia/Kolkata"),
    ("vadodara", "in"): (22.3072, 73.1812, "Asia/Kolkata"),
    ("rajkot", "in"): (22.3039, 70.8022, "Asia/Kolkata"),
    ("jaipur", "in"): (26.9124, 75.7873, "Asia/Kolkata"),
    ("jodhpur", "in"): (26.2389, 73.0243, "Asia/Kolkata"),
    ("udaipur", "in"): (24.5854, 73.7125, "Asia/Kolkata"),
    ("lucknow", "in"): (26.8467, 80.9462, "Asia/Kolkata"),
    ("kanpur", "in"): (26.4499, 80.3319, "Asia/Kolkata"),
    ("varanasi", "in"): (25.3176, 82.9739, "Asia/Kolkata"),
    ("prayagraj", "in"): (25.4358, 81.8463, "Asia/Kolkata"),
    ("allahabad", "in"): (25.4358, 81.8463, "Asia/Kolkata"),
    ("agra", "in"): (27.1767, 78.0081, "Asia/Kolkata"),
    ("meerut", "in"): (28.9845, 77.7064, "Asia/Kolkata"),
    ("ghaziabad", "in"): (28.6692, 77.4538, "Asia/Kolkata"),
    ("noida", "in"): (28.5355, 77.3910, "Asia/Kolkata"),
    ("gurgaon", "in"): (28.4595, 77.0266, "Asia/Kolkata"),
    ("gurugram", "in"): (28.4595, 77.0266, "Asia/Kolkata"),
    ("faridabad", "in"): (28.4089, 77.3178, "Asia/Kolkata"),
    ("nagpur", "in"): (21.1458, 79.0882, "Asia/Kolkata"),
    ("nashik", "in"): (19.9975, 73.7898, "Asia/Kolkata"),
    ("aurangabad", "in"): (19.8762, 75.3433, "Asia/Kolkata"),
    ("thane", "in"): (19.2183, 72.9781, "Asia/Kolkata"),
    ("solapur", "in"): (17.6599, 75.9064, "Asia/Kolkata"),
    ("indore", "in"): (22.7196, 75.8577, "Asia/Kolkata"),
    ("bhopal", "in"): (23.2599, 77.4126, "Asia/Kolkata"),
    ("gwalior", "in"): (26.2183, 78.1828, "Asia/Kolkata"),
    ("jabalpur", "in"): (23.1815, 79.9864, "Asia/Kolkata"),
    ("patna", "in"): (25.5941, 85.1376, "Asia/Kolkata"),
    ("ranchi", "in"): (23.3441, 85.3096, "Asia/Kolkata"),
    ("jamshedpur", "in"): (22.8046, 86.2029, "Asia/Kolkata"),
    ("raipur", "in"): (21.2514, 81.6296, "Asia/Kolkata"),
    ("bhubaneswar", "in"): (20.2961, 85.8245, "Asia/Kolkata"),
    ("cuttack", "in"): (20.4625, 85.8830, "Asia/Kolkata"),
    ("guwahati", "in"): (26.1445, 91.7362, "Asia/Kolkata"),
    ("shillong", "in"): (25.5788, 91.8933, "Asia/Kolkata"),
    ("siliguri", "in"): (26.7271, 88.3953, "Asia/Kolkata"),
    ("amritsar", "in"): (31.6340, 74.8723, "Asia/Kolkata"),
    ("ludhiana", "in"): (30.9010, 75.8573, "Asia/Kolkata"),
    ("chandigarh", "in"): (30.7333, 76.7794, "Asia/Kolkata"),
    ("dehradun", "in"): (30.3165, 78.0322, "Asia/Kolkata"),
    ("srinagar", "in"): (34.0837, 74.7973, "Asia/Kolkata"),
    ("mysore", "in"): (12.2958, 76.6394, "Asia/Kolkata"),
    ("mysuru", "in"): (12.2958, 76.6394, "Asia/Kolkata"),
    ("mangalore", "in"): (12.9141, 74.8560, "Asia/Kolkata"),
    ("hubli", "in"): (15.3647, 75.1240, "Asia/Kolkata"),
    ("coimbatore", "in"): (11.0168, 76.9558, "Asia/Kolkata"),
    ("madurai", "in"): (9.9252, 78.1198, "Asia/Kolkata"),
    ("salem", "in"): (11.6643, 78.1460, "Asia/Kolkata"),
    ("tiruchirappalli", "in"): (10.7905, 78.7047, "Asia/Kolkata"),
    ("trichy", "in"): (10.7905, 78.7047, "Asia/Kolkata"),
    ("kochi", "in"): (9.9312, 76.2673, "Asia/Kolkata"),
    ("thiruvananthapuram", "in"): (8.5241, 76.9366, "Asia/Kolkata"),
    ("trivandrum", "in"): (8.5241, 76.9366, "Asia/Kolkata"),
    ("panaji", "in"): (15.4909, 73.8278, "Asia/Kolkata"),
    ("goa", "in"): (15.4909, 73.8278, "Asia/Kolkata"),
    ("london", "gb"): (51.5074, -0.1278, "Europe/London"),
    ("paris", "fr"): (48.8566, 2.3522, "Europe/Paris"),
    ("berlin", "de"): (52.5200, 13.4050, "Europe/Berlin"),
    ("madrid", "es"): (40.4168, -3.7038, "Europe/Madrid"),
    ("rome", "it"): (41.9028, 12.4964, "Europe/Rome"),
    ("amsterdam", "nl"): (52.3676, 4.9041, "Europe/Amsterdam"),
    ("tokyo", "jp"): (35.6762, 139.6503, "Asia/Tokyo"),
    ("beijing", "cn"): (39.9042, 116.4074, "Asia/Shanghai"),
    ("shanghai", "cn"): (31.2304, 121.4737, "Asia/Shanghai"),
    ("sydney", "au"): (-33.8688, 151.2093, "Australia/Sydney"),
    ("melbourne", "au"): (-37.8136, 144.9631, "Australia/Melbourne"),
    ("toronto", "ca"): (43.6532, -79.3832, "America/Toronto"),
    ("vancouver", "ca"): (49.2827, -123.1207, "America/Vancouver"),
    ("peterborough", "ca"): (44.3091, -78.3197, "America/Toronto"),
    ("ottawa", "ca"): (45.4215, -75.6972, "America/Toronto"),
    ("montreal", "ca"): (45.5017, -73.5673, "America/Toronto"),
    ("quebec city", "ca"): (46.8139, -71.2080, "America/Toronto"),
    ("calgary", "ca"): (51.0447, -114.0719, "America/Edmonton"),
    ("edmonton", "ca"): (53.5461, -113.4938, "America/Edmonton"),
    ("winnipeg", "ca"): (49.8951, -97.1384, "America/Winnipeg"),
    ("hamilton", "ca"): (43.2557, -79.8711, "America/Toronto"),
    ("kitchener", "ca"): (43.4516, -80.4925, "America/Toronto"),
    ("london", "ca"): (42.9849, -81.2453, "America/Toronto"),
    ("mississauga", "ca"): (43.5890, -79.6441, "America/Toronto"),
    ("brampton", "ca"): (43.7315, -79.7624, "America/Toronto"),
    ("oshawa", "ca"): (43.8971, -78.8658, "America/Toronto"),
    ("kingston", "ca"): (44.2312, -76.4860, "America/Toronto"),
    ("barrie", "ca"): (44.3894, -79.6903, "America/Toronto"),
    ("halifax", "ca"): (44.6488, -63.5752, "America/Halifax"),
    ("victoria", "ca"): (48.4284, -123.3656, "America/Vancouver"),
    ("saskatoon", "ca"): (52.1332, -106.6700, "America/Regina"),
    ("regina", "ca"): (50.4452, -104.6189, "America/Regina"),
    ("st. john's", "ca"): (47.5615, -52.7126, "America/St_Johns"),
    ("st johns", "ca"): (47.5615, -52.7126, "America/St_Johns"),
    ("dubai", "ae"): (25.2048, 55.2708, "Asia/Dubai"),
    ("singapore", "sg"): (1.3521, 103.8198, "Asia/Singapore"),
    ("moscow", "ru"): (55.7558, 37.6173, "Europe/Moscow"),
    ("cairo", "eg"): (30.0444, 31.2357, "Africa/Cairo"),
    ("nairobi", "ke"): (-1.2921, 36.8219, "Africa/Nairobi"),
    ("johannesburg", "za"): (-26.2041, 28.0473, "Africa/Johannesburg"),
    ("mexico city", "mx"): (19.4326, -99.1332, "America/Mexico_City"),
    ("buenos aires", "ar"): (-34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
    ("sao paulo", "br"): (-23.5505, -46.6333, "America/Sao_Paulo"),
    ("rio de janeiro", "br"): (-22.9068, -43.1729, "America/Sao_Paulo"),
    ("istanbul", "tr"): (41.0082, 28.9784, "Europe/Istanbul"),
    ("seoul", "kr"): (37.5665, 126.9780, "Asia/Seoul"),
    ("bangkok", "th"): (13.7563, 100.5018, "Asia/Bangkok"),
    ("jakarta", "id"): (-6.2088, 106.8456, "Asia/Jakarta"),
    ("karachi", "pk"): (24.8607, 67.0011, "Asia/Karachi"),
    ("lahore", "pk"): (31.5204, 74.3587, "Asia/Karachi"),
    ("dhaka", "bd"): (23.8103, 90.4125, "Asia/Dhaka"),
    ("kathmandu", "np"): (27.7172, 85.3240, "Asia/Kathmandu"),
    ("colombo", "lk"): (6.9271, 79.8612, "Asia/Colombo"),
}

_INDIA_EXPANSION: dict[str, tuple[float, float]] = {
    "adoni": (15.6322, 77.2728),
    "agartala": (23.8315, 91.2868),
    "aizawl": (23.7271, 92.7176),
    "ajmer": (26.4499, 74.6399),
    "akola": (20.7002, 77.0082),
    "alappuzha": (9.4981, 76.3388),
    "aligarh": (27.8974, 78.0880),
    "alwar": (27.5530, 76.6346),
    "ambala": (30.3782, 76.7767),
    "anantapur": (14.6819, 77.6006),
    "asansol": (23.6739, 86.9524),
    "ayodhya": (26.7922, 82.1998),
    "bareilly": (28.3670, 79.4304),
    "bathinda": (30.2110, 74.9455),
    "belagavi": (15.8497, 74.4977),
    "belgaum": (15.8497, 74.4977),
    "bellary": (15.1394, 76.9214),
    "berhampur": (19.3149, 84.7941),
    "bhagalpur": (25.2425, 86.9842),
    "bharatpur": (27.2152, 77.5030),
    "bhavnagar": (21.7645, 72.1519),
    "bhilai": (21.1938, 81.3509),
    "bhilwara": (25.3407, 74.6313),
    "bhiwandi": (19.2813, 73.0483),
    "bikaner": (28.0229, 73.3119),
    "bilaspur": (22.0797, 82.1409),
    "bokaro": (23.6693, 86.1511),
    "burdwan": (23.2324, 87.8615),
    "chandrapur": (19.9705, 79.3036),
    "cochin": (9.9312, 76.2673),
    "davanagere": (14.4644, 75.9218),
    "dhanbad": (23.7957, 86.4304),
    "dharamshala": (32.2190, 76.3234),
    "dibrugarh": (27.4728, 94.9120),
    "dindigul": (10.3673, 77.9803),
    "durgapur": (23.5204, 87.3119),
    "eluru": (16.7107, 81.0952),
    "erode": (11.3410, 77.7172),
    "firozabad": (27.1592, 78.3957),
    "gandhinagar": (23.2156, 72.6369),
    "gangtok": (27.3314, 88.6138),
    "gorakhpur": (26.7606, 83.3732),
    "gulbarga": (17.3297, 76.8343),
    "kalaburagi": (17.3297, 76.8343),
    "guntur": (16.3067, 80.4365),
    "hisar": (29.1492, 75.7217),
    "hosur": (12.7409, 77.8253),
    "howrah": (22.5958, 88.2636),
    "imphal": (24.8170, 93.9368),
    "itanagar": (27.0844, 93.6053),
    "jhansi": (25.4484, 78.5685),
    "jalandhar": (31.3260, 75.5762),
    "jalgaon": (21.0077, 75.5626),
    "jamnagar": (22.4707, 70.0577),
    "jharsuguda": (21.8554, 84.0062),
    "jorhat": (26.7509, 94.2037),
    "kadapa": (14.4673, 78.8242),
    "cuddapah": (14.4673, 78.8242),
    "kannur": (11.8745, 75.3704),
    "karimnagar": (18.4386, 79.1288),
    "karnal": (29.6857, 76.9905),
    "karur": (10.9601, 78.0766),
    "khammam": (17.2473, 80.1514),
    "kolhapur": (16.7050, 74.2433),
    "kollam": (8.8932, 76.6141),
    "korba": (22.3595, 82.7501),
    "kota": (25.2138, 75.8648),
    "kozhikode": (11.2588, 75.7804),
    "calicut": (11.2588, 75.7804),
    "latur": (18.4088, 76.5604),
    "madgaon": (15.2832, 73.9862),
    "margao": (15.2832, 73.9862),
    "malappuram": (11.0510, 76.0711),
    "mathura": (27.4924, 77.6737),
    "moradabad": (28.8386, 78.7733),
    "muzaffarpur": (26.1209, 85.3647),
    "nadiad": (22.6916, 72.8634),
    "nagercoil": (8.1833, 77.4119),
    "nanded": (19.1383, 77.3210),
    "navi mumbai": (19.0330, 73.0297),
    "nizamabad": (18.6725, 78.0941),
    "ongole": (15.5057, 80.0499),
    "ooty": (11.4102, 76.6950),
    "udhagamandalam": (11.4102, 76.6950),
    "palakkad": (10.7867, 76.6548),
    "pali": (25.7711, 73.3234),
    "panipat": (29.3909, 76.9635),
    "patiala": (30.3398, 76.3869),
    "pondicherry": (11.9416, 79.8083),
    "puducherry": (11.9416, 79.8083),
    "porbandar": (21.6417, 69.6293),
    "port blair": (11.6234, 92.7265),
    "raichur": (16.2076, 77.3463),
    "rajapalayam": (9.4515, 77.5544),
    "ramagundam": (18.7638, 79.4750),
    "rourkela": (22.2604, 84.8536),
    "saharanpur": (29.9680, 77.5552),
    "sambalpur": (21.4669, 83.9812),
    "satara": (17.6805, 74.0183),
    "satna": (24.6005, 80.8322),
    "secunderabad": (17.4399, 78.4983),
    "shimla": (31.1048, 77.1734),
    "shivamogga": (13.9299, 75.5681),
    "shimoga": (13.9299, 75.5681),
    "sikar": (27.6094, 75.1399),
    "solan": (30.9045, 77.0967),
    "sonipat": (28.9931, 77.0151),
    "sri ganganagar": (29.9094, 73.8800),
    "srikakulam": (18.2969, 83.8974),
    "surendranagar": (22.7201, 71.6495),
    "tenali": (16.2430, 80.6400),
    "thanjavur": (10.7870, 79.1378),
    "thoothukudi": (8.7642, 78.1348),
    "tuticorin": (8.7642, 78.1348),
    "thrissur": (10.5276, 76.2144),
    "tirunelveli": (8.7139, 77.7567),
    "tiruppur": (11.1085, 77.3411),
    "tumakuru": (13.3409, 77.1010),
    "tumkur": (13.3409, 77.1010),
    "ujjain": (23.1765, 75.7885),
    "vapi": (20.3893, 72.9106),
    "vellore": (12.9165, 79.1325),
    "vijayanagaram": (18.1067, 83.3956),
    "vizianagaram": (18.1067, 83.3956),
    "yamunanagar": (30.1290, 77.2674),
}

for _city, (_lat, _lng) in _INDIA_EXPANSION.items():
    _CITIES.setdefault((_city, "in"), (_lat, _lng, "Asia/Kolkata"))


def _normalize(value: str) -> str:
    # Fold diacritics (GeoNames uses e.g. "Pithāpuram") so ASCII input matches.
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.strip().lower().replace(".", "")).strip()


@lru_cache(maxsize=1)
def _state_places() -> list[list]:
    """[name, lat, lng, district, state, population, alternates] rows,
    population-sorted."""
    if not _STATE_PLACES_PATH.exists():
        return []
    with gzip.open(_STATE_PLACES_PATH, "rt", encoding="utf-8") as fh:
        return json.load(fh)["places"]


@lru_cache(maxsize=1)
def _state_places_index() -> dict[str, tuple[float, float, str]]:
    """normalized name/alternate -> (lat, lng, tz); most populous wins."""
    index: dict[str, tuple[float, float, str]] = {}
    for row in _state_places():
        name, lat, lng = row[0], row[1], row[2]
        geo = (lat, lng, "Asia/Kolkata")
        index.setdefault(_normalize(name), geo)
        for alt in (row[6] if len(row) > 6 else []):
            index.setdefault(_normalize(alt), geo)
    return index


@lru_cache(maxsize=1)
def _state_places_keys() -> list[str]:
    """Index keys in population order, for prefix fallback in lookups."""
    return list(_state_places_index().keys())


def lookup_city(city: str, nation: str = "US") -> tuple[float, float, str] | None:
    """Return (lat, lng, tz_str) for a city or None if not found offline."""
    key = (_normalize(city), _normalize(nation))
    result = _CITIES.get(key)
    if result:
        return result
    # Try city-only match (first nation that matches)
    city_lower = _normalize(city)
    for (c, n), v in _CITIES.items():
        if c == city_lower:
            return v
    # Complete state-level dataset (AP/TS villages and towns).
    if _normalize(nation) in ("in", ""):
        index = _state_places_index()
        exact = index.get(city_lower)
        if exact:
            return exact
        # Telugu transliteration tolerance: trailing y<->i (Kamareddy/Kamareddi,
        # Metpally/Metpalli).
        if city_lower[-1:] in ("y", "i"):
            swapped = city_lower[:-1] + ("i" if city_lower.endswith("y") else "y")
            hit = index.get(swapped)
            if hit:
                return hit
        # Then accept a prefix match (e.g. "Sangareddy" -> "Sangareddypeta").
        if len(city_lower) >= 5:
            for key in _state_places_keys():
                if key.startswith(city_lower):
                    return index[key]
    return None


def city_for_timezone(tz_str: str) -> tuple[str, str, float, float, str] | None:
    """Return a representative city for an IANA timezone."""
    for (city, nation), (lat, lng, tz) in _CITIES.items():
        if tz == tz_str:
            return city.title(), nation.upper(), lat, lng, tz
    return None


def search_cities(query: str = "", limit: int = 80) -> list[dict]:
    """Search offline city entries for UI selectors."""
    q = _normalize(query)
    matches = []
    for (city, nation), geo in _CITIES.items():
        tz = geo[2]
        haystack = f"{city} {nation} {tz.lower()}"
        if q and q not in haystack:
            continue
        score = 3
        if q:
            if city == q or nation == q:
                score = 0
            elif city.startswith(q):
                score = 1
            elif any(part.startswith(q) for part in city.split()):
                score = 2
        matches.append((score, city, nation, geo))

    rows = []
    seen = set()
    for _, city, nation, (lat, lng, tz) in sorted(matches, key=lambda item: (item[0], item[2] != "in", item[1], item[2])):
        key = (city, nation)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "city": city.title(),
            "nation": nation.upper(),
            "timezone": tz,
            "lat": lat,
            "lng": lng,
            "label": f"{city.title()}, {nation.upper()} · {tz}",
        })
        if len(rows) >= limit:
            break

    if q and len(rows) < limit:
        rows.extend(_search_state_places(q, limit - len(rows),
                                         exclude={(r["city"].lower(), r["nation"].lower()) for r in rows}))
    return rows


def _search_state_places(q: str, limit: int, exclude: set) -> list[dict]:
    """Prefix/substring search over the state-level dataset. Entries are
    population-sorted, so bigger towns surface first; district + state in the
    label disambiguates same-named villages."""
    exact, prefix, contains = [], [], []
    for row in _state_places():
        name, lat, lng, district, state = row[0], row[1], row[2], row[3], row[4]
        alternates = row[6] if len(row) > 6 else []
        name_l = _normalize(name)
        alt_l = [_normalize(alt) for alt in alternates]
        if name_l == q or q in alt_l:
            bucket = exact
        elif name_l.startswith(q) or any(alt.startswith(q) for alt in alt_l):
            bucket = prefix
        elif q in name_l or any(q in alt for alt in alt_l):
            bucket = contains
        else:
            continue
        if (name_l, "in") in exclude:
            continue
        state_name = _STATE_NAMES.get(state, state)
        where = f"{district}, {state_name}" if district else state_name
        bucket.append({
            "city": name,
            "nation": "IN",
            "timezone": "Asia/Kolkata",
            "lat": lat,
            "lng": lng,
            "label": f"{name} · {where}",
        })
        if len(exact) + len(prefix) >= limit and bucket is not contains:
            break
    return (exact + prefix + contains)[:limit]
