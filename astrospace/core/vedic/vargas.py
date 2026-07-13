"""
Divisional (varga) chart engine — D1 to D60.

Every function maps a sidereal longitude to a sign index (0=Aries..11=Pisces)
per the rules of Brihat Parashara Hora Shastra ch. 6 for the classical
shodashavarga set. D5, D6, D8 and D11 are not defined in BPHS; the rules
here follow the JHora/Maitreya conventions and are marked VERIFY — each is
a small standalone function so a correction is a one-line change once the
reference chart arrives.

Vocabulary used below:
  s = sign index of the longitude (0..11)
  d = degree within the sign (0..30)
  m = division index within the sign, floor(d / (30/n)), clamped to n-1
  odd sign  = Aries, Gemini, Leo ... (s % 2 == 0)
  movable/fixed/dual = s % 3 == 0 / 1 / 2
  element fire/earth/air/water = s % 4 == 0 / 1 / 2 / 3
"""


def _parts(lon: float, n: int) -> tuple[int, int]:
    """(sign index, division index) of a longitude for an n-fold varga."""
    lon = lon % 360.0
    s = int(lon // 30)
    d = lon % 30.0
    # multiply before dividing: 30/n is inexact for n=7,9,11... and exact
    # division boundaries (3°20' etc.) would bucket low
    m = min(int(d * n / 30.0), n - 1)
    return s, m


def d1(lon: float) -> int:
    """Rashi — the sign itself."""
    return _parts(lon, 1)[0]


def d2(lon: float) -> int:
    """Hora (BPHS): odd signs 0-15° Leo then Cancer; even signs reversed."""
    s, m = _parts(lon, 2)
    if s % 2 == 0:
        return 4 if m == 0 else 3
    return 3 if m == 0 else 4


def d3(lon: float) -> int:
    """Drekkana (BPHS): parts fall in the sign, its 5th, its 9th."""
    s, m = _parts(lon, 3)
    return (s + 4 * m) % 12


def d4(lon: float) -> int:
    """Chaturthamsha (BPHS): the sign, its 4th, 7th, 10th."""
    s, m = _parts(lon, 4)
    return (s + 3 * m) % 12


def d5(lon: float) -> int:
    """
    Panchamamsha (JHora): odd signs → Aries, Aquarius, Sagittarius, Gemini,
    Libra; even signs → Taurus, Virgo, Pisces, Capricorn, Scorpio. VERIFY.
    """
    s, m = _parts(lon, 5)
    odd = [0, 10, 8, 2, 6]
    even = [1, 5, 11, 9, 7]
    return odd[m] if s % 2 == 0 else even[m]


def d6(lon: float) -> int:
    """Shashthamsha: continuous zodiacal count from Aries (each 5°). VERIFY."""
    s, m = _parts(lon, 6)
    return (s * 6 + m) % 12


def d7(lon: float) -> int:
    """Saptamamsha (BPHS): odd signs count from the sign, even from its 7th."""
    s, m = _parts(lon, 7)
    start = s if s % 2 == 0 else (s + 6) % 12
    return (start + m) % 12


def d8(lon: float) -> int:
    """Ashtamamsha: movable from Aries, fixed from Leo, dual from Sagittarius. VERIFY."""
    s, m = _parts(lon, 8)
    return ((s % 3) * 4 + m) % 12


def d9(lon: float) -> int:
    """
    Navamsha (BPHS): fire signs count from Aries, earth from Capricorn,
    air from Libra, water from Cancer. Equivalent to movable-from-self,
    fixed-from-9th, dual-from-5th.
    """
    s, m = _parts(lon, 9)
    return ((s % 4) * 9 + m) % 12


def d10(lon: float) -> int:
    """Dashamsha (BPHS): odd signs count from the sign, even from its 9th."""
    s, m = _parts(lon, 10)
    start = s if s % 2 == 0 else (s + 8) % 12
    return (start + m) % 12


def d11(lon: float) -> int:
    """Rudramsha (JHora): count anti-zodiacally from the 12th of the sign. VERIFY."""
    s, m = _parts(lon, 11)
    return (s - 1 - m) % 12


def d12(lon: float) -> int:
    """Dwadashamsha (BPHS): count from the sign itself."""
    s, m = _parts(lon, 12)
    return (s + m) % 12


def d16(lon: float) -> int:
    """Shodashamsha (BPHS): movable from Aries, fixed from Leo, dual from Sagittarius."""
    s, m = _parts(lon, 16)
    return ((s % 3) * 4 + m) % 12


def d20(lon: float) -> int:
    """Vimshamsha (BPHS): movable from Aries, fixed from Sagittarius, dual from Leo."""
    s, m = _parts(lon, 20)
    start = [0, 8, 4][s % 3]
    return (start + m) % 12


def d24(lon: float) -> int:
    """Chaturvimshamsha (BPHS): odd signs count from Leo, even from Cancer."""
    s, m = _parts(lon, 24)
    start = 4 if s % 2 == 0 else 3
    return (start + m) % 12


def d27(lon: float) -> int:
    """Bhamsha (BPHS): fire from Aries, earth from Cancer, air from Libra, water from Capricorn."""
    s, m = _parts(lon, 27)
    return ((s % 4) * 3 + m) % 12


def d30(lon: float) -> int:
    """
    Trimshamsha (BPHS) — unequal divisions.
    Odd signs:  0-5 Aries(Mars), 5-10 Aquarius(Saturn), 10-18 Sagittarius(Jupiter),
                18-25 Gemini(Mercury), 25-30 Libra(Venus).
    Even signs: 0-5 Taurus(Venus), 5-12 Virgo(Mercury), 12-20 Pisces(Jupiter),
                20-25 Capricorn(Saturn), 25-30 Scorpio(Mars).
    """
    lon = lon % 360.0
    s = int(lon // 30)
    d = lon % 30.0
    if s % 2 == 0:
        for limit, sign in ((5, 0), (10, 10), (18, 8), (25, 2)):
            if d < limit:
                return sign
        return 6
    for limit, sign in ((5, 1), (12, 5), (20, 11), (25, 9)):
        if d < limit:
            return sign
    return 7


def d40(lon: float) -> int:
    """Khavedamsha (BPHS): odd signs count from Aries, even from Libra."""
    s, m = _parts(lon, 40)
    start = 0 if s % 2 == 0 else 6
    return (start + m) % 12


def d45(lon: float) -> int:
    """Akshavedamsha (BPHS): movable from Aries, fixed from Leo, dual from Sagittarius."""
    s, m = _parts(lon, 45)
    return ((s % 3) * 4 + m) % 12


def d60(lon: float) -> int:
    """Shashtiamsha (BPHS): each 0.5° advances one sign from the sign itself."""
    lon = lon % 360.0
    s = int(lon // 30)
    d = lon % 30.0
    m = min(int(d * 2), 59)
    return (s + m) % 12


VARGA_FUNCTIONS = {
    "D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6, "D7": d7,
    "D8": d8, "D9": d9, "D10": d10, "D11": d11, "D12": d12, "D16": d16,
    "D20": d20, "D24": d24, "D27": d27, "D30": d30, "D40": d40,
    "D45": d45, "D60": d60,
}

VARGA_INFO = {
    "D1":  {"name": "Rashi",            "signifies": "Physical self, all life matters"},
    "D2":  {"name": "Hora",             "signifies": "Wealth, financial prosperity"},
    "D3":  {"name": "Drekkana",         "signifies": "Siblings, courage, initiative"},
    "D4":  {"name": "Chaturthamsha",    "signifies": "Property, fortune, fixed assets"},
    "D5":  {"name": "Panchamamsha",     "signifies": "Spiritual merit, authority"},
    "D6":  {"name": "Shashthamsha",     "signifies": "Health, disease, obstacles"},
    "D7":  {"name": "Saptamamsha",      "signifies": "Children, progeny"},
    "D8":  {"name": "Ashtamamsha",      "signifies": "Longevity, sudden events"},
    "D9":  {"name": "Navamsha",         "signifies": "Spouse, dharma, inner strength"},
    "D10": {"name": "Dashamsha",        "signifies": "Career, profession, status"},
    "D11": {"name": "Rudramsha",        "signifies": "Gains, fulfilment of desires"},
    "D12": {"name": "Dwadashamsha",     "signifies": "Parents, lineage"},
    "D16": {"name": "Shodashamsha",     "signifies": "Vehicles, comforts, happiness"},
    "D20": {"name": "Vimshamsha",       "signifies": "Spiritual practice, devotion"},
    "D24": {"name": "Chaturvimshamsha", "signifies": "Education, learning"},
    "D27": {"name": "Bhamsha",          "signifies": "Strength, vitality"},
    "D30": {"name": "Trimshamsha",      "signifies": "Misfortunes, adversity"},
    "D40": {"name": "Khavedamsha",      "signifies": "Auspicious/inauspicious karma (maternal)"},
    "D45": {"name": "Akshavedamsha",    "signifies": "Character, conduct (paternal)"},
    "D60": {"name": "Shashtiamsha",     "signifies": "Past-life karma, finest analysis"},
}

# Vargas whose rules are not from BPHS and await reference-chart validation.
UNVERIFIED_VARGAS = {"D5", "D6", "D8", "D11"}


def varga_sign(varga: str, lon: float) -> int:
    """Sign index of a longitude in the named varga (e.g. 'D9')."""
    try:
        return VARGA_FUNCTIONS[varga](lon)
    except KeyError:
        raise ValueError(f"Unknown varga {varga!r}; options: {sorted(VARGA_FUNCTIONS)}")


def all_vargas(lon: float) -> dict:
    """{varga: sign index} for every implemented varga."""
    return {v: fn(lon) for v, fn in VARGA_FUNCTIONS.items()}
