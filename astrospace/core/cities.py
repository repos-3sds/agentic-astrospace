"""Offline city lookup with common cities, falls back to None (online GeoNames)."""

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


def lookup_city(city: str, nation: str = "US") -> tuple[float, float, str] | None:
    """Return (lat, lng, tz_str) for a city or None if not found offline."""
    key = (city.strip().lower(), nation.strip().lower())
    result = _CITIES.get(key)
    if result:
        return result
    # Try city-only match (first nation that matches)
    city_lower = city.strip().lower()
    for (c, n), v in _CITIES.items():
        if c == city_lower:
            return v
    return None


def city_for_timezone(tz_str: str) -> tuple[str, str, float, float, str] | None:
    """Return a representative city for an IANA timezone."""
    for (city, nation), (lat, lng, tz) in _CITIES.items():
        if tz == tz_str:
            return city.title(), nation.upper(), lat, lng, tz
    return None


def search_cities(query: str = "", limit: int = 80) -> list[dict]:
    """Search offline city entries for UI selectors."""
    q = query.strip().lower()
    rows = []
    seen = set()
    for (city, nation), (lat, lng, tz) in sorted(_CITIES.items()):
        if q and q not in city and q not in nation and q not in tz.lower():
            continue
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
    return rows
