"""Offline city lookup with common cities, falls back to None (online GeoNames).

In addition to the curated worldwide table below, a village-level
GeoNames-derived populated-places dataset for India (currently Andhra Pradesh
and Telangana, ~35k villages/towns; built for all of India once the dump is
downloaded) is loaded lazily from data/india_places.tsv.gz — regenerate with
scripts/build_india_places.py. Those places save as "Rampur, Bareilly".

Every populated place of 500+ people in the rest of India, the US and
Canada, the UK and Ireland, the Gulf, Singapore, Malaysia, Australia, New
Zealand and Europe (~124k, with the GeoNames timezone of each) is loaded the
same way from data/world_places.json.gz — regenerate with
scripts/build_world_places.py. Those places are stored with their region
("Springfield, IL", "Aurangabad, Bihar", "Perth, Scotland") so a saved profile
resolves to the same town it was picked as, not its most populous namesake.
"""

from __future__ import annotations

import gzip
import io
import json
import math
import re
import unicodedata
from array import array
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

_INDIA_PLACES_PATH = Path(__file__).parent / "data" / "india_places.tsv.gz"
# Bare names saved before the rest of India arrived meant these states.
_LEGACY_BARE_STATES = frozenset({"Andhra Pradesh", "Telangana"})
_WORLD_PLACES_PATH = Path(__file__).parent / "data" / "world_places.json.gz"
_REGION_NAMES: dict[str, dict[str, str]] = {
    "us": {
        "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
        "CA": "California", "CO": "Colorado", "CT": "Connecticut",
        "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida",
        "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
        "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky",
        "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
        "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
        "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
        "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
        "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
        "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
        "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
        "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
        "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
        "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
        "WI": "Wisconsin", "WY": "Wyoming",
    },
    "ca": {
        "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba",
        "NB": "New Brunswick", "NL": "Newfoundland and Labrador",
        "NS": "Nova Scotia", "ON": "Ontario", "PE": "Prince Edward Island",
        "QC": "Quebec", "SK": "Saskatchewan", "YT": "Yukon",
        "NT": "Northwest Territories", "NU": "Nunavut",
    },
}

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


class _IndiaPlaces:
    """The village-level India layer, held compactly: ~15x the old
    AP/Telangana layer as Python lists would not fit a 1 GiB instance.

    Names live in two newline-joined strings, as written and normalized, so
    a search is a C-speed str.find rather than a loop over rows; row numbers
    come back from the match offset by bisection. Rows are population-sorted,
    so the first match is the biggest place.
    """

    def __init__(self, path: Path):
        self.lat, self.lng = array("d"), array("d")
        self.pop, self.district = array("L"), array("L")
        self.districts: list[tuple[str, str]] = []
        names, norms, alts = io.StringIO(), io.StringIO(), io.StringIO()
        self._name_at, self._norm_at, self._alt_at = array("L"), array("L"), array("L")
        self._alt_row = array("L")
        norms.write("\n")
        alts.write("\n")
        name_pos, norm_pos, alt_pos = 0, 1, 1
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as fh:
                meta = json.loads(fh.readline()[2:])
                self.districts = [tuple(pair) for pair in meta["districts"]]
                for row, line in enumerate(fh):
                    name, lat, lng, district, pop, alternates = line.rstrip("\n").split("\t")
                    self.lat.append(float(lat))
                    self.lng.append(float(lng))
                    self.district.append(int(district))
                    self.pop.append(int(pop))
                    self._name_at.append(name_pos)
                    names.write(name + "\n")
                    name_pos += len(name) + 1
                    norm = _normalize(name)
                    self._norm_at.append(norm_pos)
                    norms.write(norm + "\n")
                    norm_pos += len(norm) + 1
                    for alt in alternates.split("|") if alternates else ():
                        alt = _normalize(alt)
                        self._alt_at.append(alt_pos)
                        self._alt_row.append(row)
                        alts.write(alt + "\n")
                        alt_pos += len(alt) + 1
        self._name_at.append(name_pos)
        self._names, self._norms, self._alts = names.getvalue(), norms.getvalue(), alts.getvalue()
        # A district name two states share (Aurangabad, Bilaspur, Hamirpur)
        # needs its state in the saved place name to come back to the same one.
        seen: dict[str, set[str]] = {}
        for district, state in self.districts:
            seen.setdefault(_normalize(district), set()).add(state)
        self._shared_districts = {name for name, states in seen.items() if len(states) > 1}

    def __len__(self) -> int:
        return len(self.lat)

    def name(self, row: int) -> str:
        return self._names[self._name_at[row]:self._name_at[row + 1] - 1]

    def where(self, row: int) -> tuple[str, str]:
        """(district, state); district may be ""."""
        return self.districts[self.district[row]]

    def geo(self, row: int) -> tuple[float, float, str]:
        return (self.lat[row], self.lng[row], "Asia/Kolkata")

    def city(self, row: int) -> str:
        """The place as a profile saves it: "Rampur, Bareilly", or the state
        where the district says nothing more ("Nagpur, Maharashtra"), with
        both for a district name two states share."""
        name, (district, state) = self.name(row), self.where(row)
        if not district or _normalize(district) == _normalize(name):
            return f"{name}, {state}"
        if _normalize(district) in self._shared_districts:
            return f"{name}, {district}, {state}"
        return f"{name}, {district}"

    def _rows(self, blob: str, starts: array, needle: str, limit: int,
              inside: bool = False, owner: array | None = None) -> list[int]:
        """Rows whose name (or alternate, with `owner`) contains `needle`,
        in row order, at most `limit`. `needle` carries its own newlines for
        whole-name and prefix matches; `inside` skips matches at the start of
        a name. str.find with that check beats a look-behind regex ~10x over
        all of India, even for a common prefix ("ram") that starts tens of
        thousands of names."""
        rows: list[int] = []
        seen: set[int] = set()
        skip = 1 if needle.startswith("\n") else 0
        positions = self._find_all(blob, needle)
        if inside:
            positions = (pos for pos in positions if blob[pos - 1] != "\n")
        for pos in positions:
            index = bisect_right(starts, pos + skip) - 1
            row = owner[index] if owner is not None else index
            if row not in seen:
                seen.add(row)
                rows.append(row)
                if len(rows) >= limit:
                    break
        return rows

    @staticmethod
    def _find_all(blob: str, needle: str):
        pos = blob.find(needle)
        while pos != -1:
            yield pos
            pos = blob.find(needle, pos + 1)

    def _matching(self, needle: str, limit: int, inside: bool = False) -> list[int]:
        names = self._rows(self._norms, self._norm_at, needle, limit, inside)
        alts = self._rows(self._alts, self._alt_at, needle, limit, inside, self._alt_row)
        return sorted(set(names) | set(alts))[:limit]

    def named(self, name: str, written_first: bool = True) -> list[int]:
        """Rows named `name` (normalized) in population order: by default the
        written name before any alternate spelling, since that is what a
        profile saves; otherwise both alike, as the AP/Telangana lookup has
        always ranked them."""
        if not name or "\n" in name:
            return []
        needle = f"\n{name}\n"
        primary = self._rows(self._norms, self._norm_at, needle, len(self) or 1)
        alternate = self._rows(self._alts, self._alt_at, needle, len(self) or 1,
                               owner=self._alt_row)
        if not written_first:
            return sorted(set(primary) | set(alternate))
        taken = set(primary)
        return primary + [row for row in alternate if row not in taken]

    def lookup(self, city: str) -> int | None:
        """The row for a saved or typed place: "Rampur, Bareilly",
        "Aurangabad, Bihar", "Rampur, Bareilly, Uttar Pradesh", or a bare name.
        A bare name keeps answering an AP/Telangana village first: profiles
        saved before the rest of India arrived hold those as bare names."""
        parts = [part.strip() for part in city.split(",")]
        if len(parts) > 1:
            qualifiers = {part for part in parts[1:] if part}
            for row in self.named(parts[0]):
                district, state = self.where(row)
                if qualifiers <= {_normalize(district), _normalize(state)}:
                    return row
            return None
        # Ranked as before, so a chart saved then does not move.
        rows = self.named(parts[0], written_first=False)
        for row in rows:
            if self.where(row)[1] in _LEGACY_BARE_STATES:
                return row
        return rows[0] if rows else None

    def search(self, q: str, limit: int) -> tuple[list[int], list[int], list[int]]:
        """(exact, prefix, contains) rows for a normalized query."""
        if not q or "\n" in q:
            return [], [], []
        exact = self._matching(f"\n{q}\n", limit)
        taken = set(exact)
        prefix = [row for row in self._matching(f"\n{q}", limit + len(exact))
                  if row not in taken][:limit]
        taken.update(prefix)
        contains = [row for row in self._matching(q, limit + len(taken), inside=True)
                    if row not in taken][:limit]
        return exact, prefix, contains

    def legacy_rows(self, needle: str) -> list[int]:
        """AP/Telangana rows matching a newline-delimited needle, for the
        lookup fallbacks that predate the rest of India."""
        rows = self._matching(needle, len(self) or 1)
        return [row for row in rows if self.where(row)[1] in _LEGACY_BARE_STATES]


@lru_cache(maxsize=1)
def _india_places() -> _IndiaPlaces:
    return _IndiaPlaces(_INDIA_PLACES_PATH)


def _india_place_dict(places: _IndiaPlaces, row: int) -> dict:
    name, (district, state) = places.name(row), places.where(row)
    where = f"{district}, {state}" if district else state
    return {
        "city": places.city(row),
        "nation": "IN",
        "timezone": "Asia/Kolkata",
        "lat": places.lat[row],
        "lng": places.lng[row],
        "label": f"{name} · {where}",
    }


def lookup_city(city: str, nation: str = "US") -> tuple[float, float, str] | None:
    """Return (lat, lng, tz_str) for a city or None if not found offline."""
    key = (_normalize(city), _normalize(nation))
    result = _CITIES.get(key)
    if result:
        return result
    city_lower = _normalize(city)
    nation_lower = _normalize(nation)
    india = _india_places() if nation_lower in ("in", "") else None
    # Village-level India: "Rampur, Bareilly", "Aurangabad, Bihar", or a bare
    # name. With no nation given, only a bare AP/Telangana name answers here,
    # as before the rest of India arrived; others wait for the curated table.
    if india is not None:
        row = india.lookup(city_lower)
        if row is not None and (nation_lower == "in" or "," not in city_lower and
                                india.where(row)[1] in _LEGACY_BARE_STATES):
            return india.geo(row)
    # Country-level dataset: "Springfield, IL", "Perth, Scotland" or "Austin".
    world = _lookup_world_place(city_lower, nation_lower)
    if world:
        return world
    # Try city-only match (first nation that matches)
    for (c, n), v in _CITIES.items():
        if c == city_lower:
            return v
    if india is not None and city_lower:
        if row is not None:
            return india.geo(row)
        # Telugu transliteration tolerance, AP/Telangana only as before:
        # trailing y<->i (Kamareddy/Kamareddi, Metpally/Metpalli).
        if city_lower[-1:] in ("y", "i"):
            swapped = city_lower[:-1] + ("i" if city_lower.endswith("y") else "y")
            hits = india.legacy_rows(f"\n{swapped}\n")
            if hits:
                return india.geo(hits[0])
        # Then accept a prefix match (e.g. "Sangareddy" -> "Sangareddypeta").
        if len(city_lower) >= 5:
            hits = india.legacy_rows(f"\n{city_lower}")
            if hits:
                return india.geo(hits[0])
    return None


@lru_cache(maxsize=1)
def _world_payload() -> dict:
    if not _WORLD_PLACES_PATH.exists():
        return {"countries": [], "places": []}
    with gzip.open(_WORLD_PLACES_PATH, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _world_places() -> list[list]:
    """[name, lat, lng, region, country, population, tz] rows in search
    order (see _search_weight)."""
    return _world_payload()["places"]


@lru_cache(maxsize=1)
def _world_countries() -> frozenset[str]:
    return frozenset(cc.lower() for cc in _world_payload()["countries"])


@lru_cache(maxsize=1)
def _world_places_index() -> dict[tuple, list]:
    """(name, country) and (name, region, country) -> row, all normalized;
    the most populous namesake wins the region-less key."""
    index: dict[tuple, list] = {}
    for row in _world_places():
        name, region, country = _normalize(row[0]), _normalize(row[3]), row[4].lower()
        index.setdefault((name, country), row)
        index.setdefault((name, region, country), row)
    return index


@lru_cache(maxsize=1)
def _world_search_rows() -> list[tuple[str, list]]:
    return [(_normalize(row[0]), row) for row in _world_places()]


def _region_key(region: str, country: str) -> str:
    """The index key for a region as typed: US/Canada codes or names ('IL',
    'Illinois' -> 'il'); elsewhere the region name itself ('maharashtra')."""
    region = region.strip()
    names = _REGION_NAMES.get(country)
    if names is None:
        return region
    if region.upper() in names:
        return region.lower()
    for code, full in names.items():
        if _normalize(full) == region:
            return code.lower()
    return ""


def _lookup_world_place(city: str, nation: str) -> tuple[float, float, str] | None:
    if nation not in _world_countries():
        return None
    index = _world_places_index()
    row = None
    if "," in city:
        name, region = (part.strip() for part in city.rsplit(",", 1))
        key = _region_key(region, nation)
        if key:
            row = index.get((name, key, nation))
    if row is None:
        row = index.get((city, nation))
    return (row[1], row[2], row[6]) if row else None


def _world_place_dict(row: list) -> dict:
    name, lat, lng, region, country, _, tz = row
    region_name = _REGION_NAMES.get(country.lower(), {}).get(region, region)
    # "Dubai, Dubai" says nothing twice; the bare name resolves to this row.
    # Not in India, where a bare name may belong to an AP/TS village first.
    if region and country != "IN" and _normalize(region) == _normalize(name) and \
            _world_places_index().get((_normalize(name), country.lower())) is row:
        region = ""
    return {
        "city": f"{name}, {region}" if region else name,
        "nation": country,
        "timezone": tz,
        "lat": lat,
        "lng": lng,
        "label": f"{region_name}, {country} · {tz}" if region else f"{country} · {tz}",
    }


# Old zone names that phones still send. Android's WebView reports India as
# "Asia/Calcutta" (ICU keeps the old name), but Debian trixie, which the
# server image is built on, moved those names into tzdata-legacy and does not
# install them, so ZoneInfo("Asia/Calcutta") failed on Cloud Run and every
# timing screen refused the request. Mapping them here also lets
# city_for_timezone() find the city, which only knows the current names.
_LEGACY_TIMEZONES = {
    "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Katmandu": "Asia/Kathmandu",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "Asia/Rangoon": "Asia/Yangon",
    "Asia/Dacca": "Asia/Dhaka",
    "Asia/Thimbu": "Asia/Thimphu",
    "Asia/Ulan_Bator": "Asia/Ulaanbaatar",
    "Asia/Macao": "Asia/Macau",
    "Asia/Ujung_Pandang": "Asia/Makassar",
    "Europe/Kiev": "Europe/Kyiv",
    "Atlantic/Faeroe": "Atlantic/Faroe",
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
    "America/Indianapolis": "America/Indiana/Indianapolis",
    "America/Louisville": "America/Kentucky/Louisville",
    "Pacific/Truk": "Pacific/Chuuk",
    "Pacific/Ponape": "Pacific/Pohnpei",
    "US/Eastern": "America/New_York",
    "US/Central": "America/Chicago",
    "US/Mountain": "America/Denver",
    "US/Pacific": "America/Los_Angeles",
    "Canada/Eastern": "America/Toronto",
    "Canada/Pacific": "America/Vancouver",
}


def canonical_timezone(tz_str: str | None) -> str | None:
    """The current IANA name for ``tz_str``, or None when it is not a zone.

    Old names are mapped to the ones the server's tz database ships, so a
    phone that reports "Asia/Calcutta" gets "Asia/Kolkata".
    """
    if not tz_str or not tz_str.strip():
        return None
    name = tz_str.strip()
    name = _LEGACY_TIMEZONES.get(name, name)
    try:
        ZoneInfo(name)
    except Exception:
        return None
    return name


def city_for_timezone(tz_str: str) -> tuple[str, str, float, float, str] | None:
    """Return a representative city for an IANA timezone."""
    tz_str = _LEGACY_TIMEZONES.get(tz_str, tz_str)
    for (city, nation), (lat, lng, tz) in _CITIES.items():
        if tz == tz_str:
            return city.title(), nation.upper(), lat, lng, tz
    return None


def _km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance; the haversine is cheap enough for 50k rows."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(a)))


def nearest_city(lat: float, lng: float) -> dict | None:
    """The nearest place the offline databases know, as a search_cities() row
    plus `distance_km`, for "Use my location".

    Only a place that lookup_city() resolves back to the same spot is
    returned: the timing routes look places up by name, and a village whose
    name a bigger namesake owns would otherwise give that namesake's sunrise.
    """
    candidates: list[tuple[float, dict]] = []
    for (city, nation), (c_lat, c_lng, tz) in _CITIES.items():
        candidates.append((_km(lat, lng, c_lat, c_lng), {
            "city": city.title(), "nation": nation.upper(), "timezone": tz,
            "lat": c_lat, "lng": c_lng, "label": f"{city.title()}, {nation.upper()} · {tz}",
        }))
    india = _india_places()
    # Half a degree is ~55 km: a box first, so the haversine runs on a few
    # hundred villages, not all of India.
    for row, (p_lat, p_lng) in enumerate(zip(india.lat, india.lng)):
        if abs(p_lat - lat) < 0.5 and abs(p_lng - lng) < 0.5:
            candidates.append((_km(lat, lng, p_lat, p_lng), _india_place_dict(india, row)))
    world = [row for row in _world_places() if _near(lat, lng, row, 0.5)]
    if not world and len(candidates) == len(_CITIES):
        world = _world_places()  # nothing within ~55 km: widen to everywhere
    for row in world:
        candidates.append((_km(lat, lng, row[1], row[2]), _world_place_dict(row)))
    candidates.sort(key=lambda item: item[0])
    for distance, row in candidates[:25]:
        geo = lookup_city(row["city"], row["nation"])
        if geo and _km(geo[0], geo[1], row["lat"], row["lng"]) < 5:
            return {**row, "distance_km": round(distance, 1)}
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
    # Among same-named cities, the one its timezone is named after leads:
    # London, GB (Europe/London) before London, CA, which came first only
    # alphabetically (regression 2026-10-17, R3). India stays ahead after that.
    def tz_named(city: str, tz: str) -> bool:
        return tz.rsplit("/", 1)[-1].replace("_", " ").lower() == city

    ranked = sorted(matches, key=lambda item: (
        item[0], not tz_named(item[1], item[3][2]), item[2] != "in", item[1], item[2]))
    for _, city, nation, (lat, lng, tz) in ranked:
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
        remaining = limit - len(rows)
        state = _search_india_places(q, remaining, curated=rows)
        world = _search_world_places(q, remaining, curated=rows)
        # Exact names first, then prefixes, then substrings; within each, by
        # population with Indian places weighted up (see _search_weight).
        for bucket in range(3):
            ranked_bucket = sorted(state[bucket] + world[bucket], key=lambda pair: -pair[0])
            rows.extend(place for _, place in ranked_bucket)
        rows = rows[:limit]
    return rows


def _search_weight(population: int, nation: str) -> int:
    """Rank within a search bucket: population, with Indian places counted 20x
    and never below 2,500, since GeoNames leaves most villages at 0. Dublin
    (1.2M) then leads "dub" over AP villages, while a Telugu village still
    leads a small foreign town (Dubbapalli before Dubbo, NSW). The world file
    is pre-sorted by the same weight in scripts/build_world_places.py."""
    return max(population, 2500) * 20 if nation in ("IN", "in") else population


def _near(lat: float, lng: float, row: list, degrees: float) -> bool:
    return abs(lat - row[1]) < degrees and abs(lng - row[2]) < degrees


def _search_world_places(q: str, limit: int, curated: list[dict]) -> tuple[list, list, list]:
    """Prefix/substring search over the country-level dataset, as
    (weight, place) pairs in search order. A curated entry hides its
    duplicate: one at the same spot (~2 km; "New York" covers GeoNames' "New
    York City"), or of the same name nearby (~30 km; the table's Nanded and
    GeoNames' sit 3 km apart)."""
    taken = [(_normalize(r["city"]), r["nation"].lower(), r["lat"], r["lng"]) for r in curated]
    names_taken = {(r["city"].lower(), r["nation"].lower()) for r in curated}
    exact, prefix, contains = [], [], []
    for name_l, row in _world_search_rows():
        if name_l == q:
            bucket = exact
        elif name_l.startswith(q):
            bucket = prefix
        elif q in name_l:
            bucket = contains
        else:
            continue
        country = row[4].lower()
        if any(n == country and _near(lat, lng, row, 0.3 if c == name_l else 0.02)
               for c, n, lat, lng in taken):
            continue
        place = _world_place_dict(row)
        # Same label as a curated row (Dubai, AE): the curated one is what
        # lookup_city returns for it, so this one would be a dead duplicate.
        if (place["city"].lower(), country) in names_taken:
            continue
        bucket.append((_search_weight(row[5], row[4]), place))
        if len(exact) + len(prefix) >= limit and bucket is not contains:
            break
    return exact[:limit], prefix[:limit], contains[:limit]


def _search_india_places(q: str, limit: int, curated: list[dict]) -> tuple[list, list, list]:
    """Search over the village-level India layer as (exact, prefix,
    contains), each a list of (weight, place) pairs, biggest first; district
    and state in the label tell same-named villages apart. A curated Indian
    city hides its duplicate here as in _search_world_places."""
    india = _india_places()
    taken = [(_normalize(r["city"]), r["lat"], r["lng"]) for r in curated if r["nation"] == "IN"]
    buckets = []
    for rows in india.search(q, limit):
        bucket = []
        for row in rows:
            name, lat, lng = _normalize(india.name(row)), india.lat[row], india.lng[row]
            if any(abs(lat - c_lat) < (0.3 if c == name else 0.02) and
                   abs(lng - c_lng) < (0.3 if c == name else 0.02)
                   for c, c_lat, c_lng in taken):
                continue
            bucket.append((_search_weight(india.pop[row], "IN"), _india_place_dict(india, row)))
        buckets.append(bucket)
    return buckets[0], buckets[1], buckets[2]
