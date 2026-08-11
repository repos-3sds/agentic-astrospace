"""
Vedic astrology constants and lookup tables.

Sources:
- Sign/planet lordships, exaltation/debilitation, moolatrikona, natural
  friendships: Brihat Parashara Hora Shastra (BPHS), ch. 3.
- Nakshatra names/lords: Vimshottari sequence, BPHS ch. 46.
- Gana/Yoni/Nadi/Varna tables: standard Muhurta/Melapak tables as published
  in common panchanga literature.
- Tables marked VERIFY follow the most common software convention
  (Horoscope Explorer / JHora family) and must be validated against the
  user-provided reference chart before being treated as authoritative.
"""

# ── Signs ────────────────────────────────────────────────────────────────────

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGNS_SANSKRIT = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
]

SIGN_LORDS = [
    "Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
    "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter",
]

# element index: 0=fire(Agni) 1=earth(Prithvi) 2=air(Vayu) 3=water(Jala)
SIGN_ELEMENTS = ["Fire", "Earth", "Air", "Water"] * 4  # by sign index % 4

# modality: 0=movable(Chara) 1=fixed(Sthira) 2=dual(Dwiswabhava)
SIGN_MODALITY = ["Movable", "Fixed", "Dual"] * 4  # by sign index % 3

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# ── Nakshatras ───────────────────────────────────────────────────────────────

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Moola", "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
]

# Vimshottari lords repeat in groups of 9 starting from Ashwini (Ketu).
NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
] * 3

VIMSHOTTARI_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

NAKSHATRA_SPAN = 360.0 / 27.0      # 13°20'
PADA_SPAN = 360.0 / 108.0          # 3°20'

# Presiding deity (devata) and symbol per nakshatra, indexed like NAKSHATRAS.
#
# Why these two and not a fuller trait table: a deity and a symbol are bare
# traditional facts — every source states them identically because nobody
# authored them. Interpretive "natives of X are..." prose is a different
# thing entirely: it is a modern writer's own expression and opinion, and
# ingesting it would smuggle uncited personal views into readings dressed as
# classical authority. The agent does the interpreting; this table exists so
# it has grounded, citable facts to interpret *from* rather than recalling
# them from training data with nothing in the bundle to cite.
#
# Cross-checked 2026-08-10 against two independent complete tables
# (en.wikipedia.org/wiki/List_of_Nakshatras and bhagyax.com/nakshatras):
# 27/27 deity agreement, differing only in transliteration (Ashvins /
# Ashwini Kumaras, Nirrti / Nirriti, Ajaikapada / Aja Ekapada). The same
# pass re-validated this file's own NAKSHATRA_LORDS against bhagyax's
# independent lord column — also 27/27.
#
# Symbols are given in their single canonical form. Several nakshatras
# carry a cluster of traditional alternates (Pushya: cow's udder, lotus,
# arrow, circle) which the sources list to differing depths; the most
# widely-cited one is used rather than reproducing any one source's full
# phrasing.
NAKSHATRA_DEITY = [
    "Ashwini Kumaras (divine physicians)", "Yama (lord of dharma and endings)",
    "Agni (fire)", "Brahma (the creator)", "Soma (the moon)",
    "Rudra (the storm)", "Aditi (the boundless mother)",
    "Brihaspati (guru of the gods)", "The Nagas (serpent beings)",
    "The Pitris (the ancestors)", "Bhaga (delight and fortune)",
    "Aryaman (patronage and contracts)", "Savitar (the vivifying sun)",
    "Vishwakarma (the divine craftsman)", "Vayu (the wind)",
    "Indra and Agni", "Mitra (friendship and compacts)",
    "Indra (king of the gods)", "Nirriti (dissolution)",
    "Apas (the waters)", "The Vishwadevas (the universal gods)",
    "Vishnu (the preserver)", "The Vasus (the eight elementals)",
    "Varuna (cosmic waters and oaths)", "Aja Ekapada (the one-footed goat)",
    "Ahir Budhnya (the serpent of the deep)", "Pushan (the nourisher)",
]

NAKSHATRA_SYMBOL = [
    "Horse's head", "Yoni", "Razor or flame", "Ox-cart", "Deer's head",
    "Teardrop", "Quiver of arrows", "Cow's udder", "Coiled serpent",
    "Royal throne", "Front legs of a bed", "Back legs of a bed", "Hand",
    "Bright jewel", "Shoot of a plant", "Triumphal arch", "Lotus",
    "Umbrella", "Bunch of tied roots", "Winnowing basket", "Elephant tusk",
    "Three footprints", "Drum", "Empty circle", "Front legs of a cot",
    "Back legs of a cot", "Pair of fish",
]

# ── Panchanga name tables ────────────────────────────────────────────────────

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
]
# index 0..29: 0-13 Shukla names above, 14=Purnima, 15-28 Krishna names, 29=Amavasya

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda",
    "Sukarman", "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyan",
    "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti",
]

KARANA_MOVABLE = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
# fixed karanas: index 0 = Kimstughna, 57 = Shakuni, 58 = Chatushpada, 59 = Naga

VARA_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
VARA_LORDS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

LUNAR_MONTHS = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwina", "Kartika", "Margashirsha", "Pausha", "Magha", "Phalguna",
]

# ── Dignity: exaltation / debilitation / moolatrikona / own (BPHS ch.3) ─────

# planet -> (exaltation sign idx, deep degree)
EXALTATION = {
    "Sun": (0, 10.0),      # Aries 10°
    "Moon": (1, 3.0),      # Taurus 3°
    "Mars": (9, 28.0),     # Capricorn 28°
    "Mercury": (5, 15.0),  # Virgo 15°
    "Jupiter": (3, 5.0),   # Cancer 5°
    "Venus": (11, 27.0),   # Pisces 27°
    "Saturn": (6, 20.0),   # Libra 20°
}
# Debilitation is the 7th sign from exaltation, same degree.

# planet -> (sign idx, degree_from, degree_to)
MOOLATRIKONA = {
    "Sun": (4, 0.0, 20.0),       # Leo 0-20
    "Moon": (1, 3.0, 30.0),      # Taurus 3-30
    "Mars": (0, 0.0, 12.0),      # Aries 0-12
    "Mercury": (5, 16.0, 20.0),  # Virgo 16-20
    "Jupiter": (8, 0.0, 10.0),   # Sagittarius 0-10
    "Venus": (6, 0.0, 15.0),     # Libra 0-15
    "Saturn": (10, 0.0, 20.0),   # Aquarius 0-20
}

OWN_SIGNS = {
    "Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5],
    "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10],
}

# Natural (naisargika) friendships — BPHS ch.3.
# planet -> {"friends": [...], "neutrals": [...], "enemies": [...]}
NATURAL_RELATIONS = {
    "Sun":     {"friends": ["Moon", "Mars", "Jupiter"], "neutrals": ["Mercury"], "enemies": ["Venus", "Saturn"]},
    "Moon":    {"friends": ["Sun", "Mercury"], "neutrals": ["Mars", "Jupiter", "Venus", "Saturn"], "enemies": []},
    "Mars":    {"friends": ["Sun", "Moon", "Jupiter"], "neutrals": ["Venus", "Saturn"], "enemies": ["Mercury"]},
    "Mercury": {"friends": ["Sun", "Venus"], "neutrals": ["Mars", "Jupiter", "Saturn"], "enemies": ["Moon"]},
    "Jupiter": {"friends": ["Sun", "Moon", "Mars"], "neutrals": ["Saturn"], "enemies": ["Mercury", "Venus"]},
    "Venus":   {"friends": ["Mercury", "Saturn"], "neutrals": ["Mars", "Jupiter"], "enemies": ["Sun", "Moon"]},
    "Saturn":  {"friends": ["Mercury", "Venus"], "neutrals": ["Jupiter"], "enemies": ["Sun", "Moon", "Mars"]},
}

# ── Avkahada lookup tables ───────────────────────────────────────────────────

# Varna by Moon sign element: Water=Brahmin, Fire=Kshatriya, Earth=Vaishya, Air=Shudra
VARNA_BY_ELEMENT = {"Water": "Brahmin", "Fire": "Kshatriya", "Earth": "Vaishya", "Air": "Shudra"}

# Vashya by Moon sign (whole-sign convention as used by common software).
# VERIFY: some texts split Sagittarius/Capricorn by half-degrees.
VASHYA_BY_SIGN = [
    "Chatushpada", "Chatushpada", "Manava", "Jalachara", "Vanachara", "Manava",
    "Manava", "Keeta", "Chatushpada", "Jalachara", "Manava", "Jalachara",
]

# Yoni (animal, gender) by nakshatra — standard Melapak table.
YONI_BY_NAKSHATRA = [
    ("Horse", "M"), ("Elephant", "M"), ("Sheep", "F"), ("Serpent", "M"),
    ("Serpent", "F"), ("Dog", "F"), ("Cat", "F"), ("Sheep", "M"),
    ("Cat", "M"), ("Rat", "M"), ("Rat", "F"), ("Cow", "M"),
    ("Buffalo", "F"), ("Tiger", "F"), ("Buffalo", "M"), ("Tiger", "M"),
    ("Deer", "F"), ("Deer", "M"), ("Dog", "M"), ("Monkey", "M"),
    ("Mongoose", "M"), ("Monkey", "F"), ("Lion", "F"), ("Horse", "F"),
    ("Lion", "M"), ("Cow", "F"), ("Elephant", "F"),
]

# Gana by nakshatra — standard Melapak table.
_DEVA = {0, 4, 6, 7, 12, 14, 16, 21, 26}
_RAKSHASA = {2, 8, 9, 13, 15, 17, 18, 22, 23}
GANA_BY_NAKSHATRA = [
    "Deva" if i in _DEVA else ("Rakshasa" if i in _RAKSHASA else "Manushya")
    for i in range(27)
]

# Nadi by nakshatra — standard Melapak table (Aadi/Madhya/Antya).
_AADI = {0, 5, 6, 11, 12, 17, 18, 23, 24}
_MADHYA = {1, 4, 7, 10, 13, 16, 19, 22, 25}
NADI_BY_NAKSHATRA = [
    "Aadi" if i in _AADI else ("Madhya" if i in _MADHYA else "Antya")
    for i in range(27)
]

# Tatwa cycles through the 5 elements by nakshatra number.
# VERIFY: convention consistent with Horoscope Explorer-style outputs.
TATWA_CYCLE = ["Prithvi", "Jala", "Agni", "Vayu", "Akasha"]

# Namakshara (name syllables) per nakshatra pada — standard 108-syllable table.
NAME_SYLLABLES = [
    ["Chu", "Che", "Cho", "La"], ["Li", "Lu", "Le", "Lo"], ["A", "I", "U", "E"],
    ["O", "Va", "Vi", "Vu"], ["Ve", "Vo", "Ka", "Ki"], ["Ku", "Gha", "Nga", "Chha"],
    ["Ke", "Ko", "Ha", "Hi"], ["Hu", "He", "Ho", "Da"], ["Di", "Du", "De", "Do"],
    ["Ma", "Mi", "Mu", "Me"], ["Mo", "Ta", "Ti", "Tu"], ["Te", "To", "Pa", "Pi"],
    ["Pu", "Sha", "Na", "Tha"], ["Pe", "Po", "Ra", "Ri"], ["Ru", "Re", "Ro", "Ta"],
    ["Ti", "Tu", "Te", "To"], ["Na", "Ni", "Nu", "Ne"], ["No", "Ya", "Yi", "Yu"],
    ["Ye", "Yo", "Bha", "Bhi"], ["Bhu", "Dha", "Pha", "Dha"], ["Bhe", "Bho", "Ja", "Ji"],
    ["Khi", "Khu", "Khe", "Kho"], ["Ga", "Gi", "Gu", "Ge"], ["Go", "Sa", "Si", "Su"],
    ["Se", "So", "Da", "Di"], ["Du", "Tha", "Jha", "Na"], ["De", "Do", "Cha", "Chi"],
]

# Paya (metal of the birth "foot") from Moon's whole-sign house from lagna.
# VERIFY: rule family used by common Hindi kundli software.
PAYA_BY_MOON_HOUSE = {
    1: "Copper", 6: "Copper", 11: "Copper",
    2: "Silver", 5: "Silver", 9: "Silver",
    3: "Gold", 7: "Gold", 10: "Gold",
    4: "Iron", 8: "Iron", 12: "Iron",
}

# Vihaga (bird) — nakshatra group + paksha. Shukla order below; Krishna reversed.
# VERIFY: Pancha-Pakshi convention; groups 1-5, 6-11, 12-16, 17-21, 22-27.
VIHAGA_BIRDS_SHUKLA = ["Bharunda", "Karanda", "Kaka", "Kukkuta", "Mayura"]
VIHAGA_GROUPS = [(0, 4), (5, 10), (11, 15), (16, 20), (21, 26)]  # inclusive nakshatra idx

# ── Planet associations (gem / metal / direction / day) ──────────────────────

PLANET_GEMS = {
    "Sun": "Ruby", "Moon": "Pearl", "Mars": "Red Coral", "Mercury": "Emerald",
    "Jupiter": "Yellow Sapphire", "Venus": "Diamond", "Saturn": "Blue Sapphire",
    "Rahu": "Hessonite", "Ketu": "Cat's Eye",
}

PLANET_METALS = {
    "Sun": "Copper", "Moon": "Silver", "Mars": "Copper", "Mercury": "Bronze",
    "Jupiter": "Gold", "Venus": "Silver", "Saturn": "Iron",
    "Rahu": "Lead", "Ketu": "Lead",
}

PLANET_DIRECTIONS = {
    "Sun": "East", "Moon": "North-West", "Mars": "South", "Mercury": "North",
    "Jupiter": "North-East", "Venus": "South-East", "Saturn": "West",
    "Rahu": "South-West", "Ketu": "South-West",
}

PLANET_DAYS = {
    "Sun": "Sunday", "Moon": "Monday", "Mars": "Tuesday", "Mercury": "Wednesday",
    "Jupiter": "Thursday", "Venus": "Friday", "Saturn": "Saturday",
}

# Governing bodily tissue (dhatu) and taste (rasa) per graha — standard
# classical associations, published consistently across independent
# secondary sources, not transcribed from any single translation's wording.
# Rahu/Ketu are deliberately absent: neither classical source consulted
# assigns them a dhatu or rasa (they are shadow points, not physical
# bodies, and most texts treat this pairing as reserved for the seven
# classical grahas only) — omitted rather than guessed.
PLANET_DHATU = {
    "Sun": "Bones (Asthi)", "Moon": "Blood (Rakta)", "Mars": "Bone marrow (Majja)",
    "Mercury": "Skin (Twak)", "Jupiter": "Fat tissue (Vasa/Meda)",
    "Venus": "Reproductive fluid (Shukra)", "Saturn": "Nerves and ligaments (Snayu)",
}

PLANET_RASA = {
    "Sun": "Pungent (Katu)", "Moon": "Salty (Lavana)", "Mars": "Bitter (Tikta)",
    "Mercury": "Mixed/varied (Mishra)", "Jupiter": "Sweet (Madhura)",
    "Venus": "Sour (Amla)", "Saturn": "Astringent (Kashaya)",
}

# Naisargika (natural) planetary varna — NOT the same system as
# VARNA_BY_ELEMENT above, which classifies a *native's* Varna Koota by the
# Moon's sign element for Ashtakoota compatibility. This is a separate,
# static per-graha attribute (temperament/role, not a compatibility score),
# cross-checked 2026-08-10 against multiple independent sources which
# converge on this exact mapping for the 7 classical grahas; Rahu/Ketu are
# a commonly-cited but less universally fixed extension (some traditions
# give Rahu/Ketu a mixed or unclassified varna instead) — included since
# our engine already treats the nodes as full participants elsewhere
# (Jaimini Gnatikaraka, dignity, etc.), but flagged for that reason.
PLANET_VARNA = {
    "Sun": "Kshatriya", "Moon": "Vaishya", "Mars": "Kshatriya",
    "Mercury": "Vaishya", "Jupiter": "Brahmin", "Venus": "Brahmin",
    "Saturn": "Shudra", "Rahu": "Chandala (outcast)", "Ketu": "Jatyantara (mixed)",
}

# Traditional colour association per graha (name, hex for the swatch).
# Used for the "colour of the day", keyed to the weekday (vara) lord and the
# day's supportive/challenging transiting graha.
PLANET_COLORS = {
    "Sun": ("Deep Orange", "#E8632A"),
    "Moon": ("Pearl White", "#EDE6D6"),
    "Mars": ("Coral Red", "#D0342C"),
    "Mercury": ("Emerald Green", "#2F8F5B"),
    "Jupiter": ("Golden Yellow", "#D8A128"),
    "Venus": ("Blush Pink", "#E58BA6"),
    "Saturn": ("Deep Blue", "#365B9E"),
    "Rahu": ("Smoky Grey", "#6B6E76"),
    "Ketu": ("Earth Brown", "#8A5A34"),
}

# Numerology number ruled by each graha — the inverse of NUMEROLOGY below.
# (Sun 1, Moon 2, Jupiter 3, Rahu 4, Mercury 5, Venus 6, Ketu 7, Saturn 8, Mars 9.)
PLANET_NUMBER = {
    "Sun": 1, "Moon": 2, "Jupiter": 3, "Rahu": 4, "Mercury": 5,
    "Venus": 6, "Ketu": 7, "Saturn": 8, "Mars": 9,
}

# ── Functional benefics/malefics per lagna (Parashari) ───────────────────────
# VERIFY: standard published lists; yogakaraka noted separately.

FUNCTIONAL_BY_LAGNA = {
    0:  {"benefics": ["Jupiter", "Sun", "Moon", "Mars"], "malefics": ["Mercury", "Venus", "Saturn"], "yogakaraka": None},
    1:  {"benefics": ["Saturn", "Sun", "Mercury", "Venus"], "malefics": ["Moon", "Mars", "Jupiter"], "yogakaraka": "Saturn"},
    2:  {"benefics": ["Venus", "Mercury", "Saturn"], "malefics": ["Mars", "Jupiter", "Sun"], "yogakaraka": None},
    3:  {"benefics": ["Mars", "Moon", "Jupiter"], "malefics": ["Mercury", "Venus", "Saturn"], "yogakaraka": "Mars"},
    4:  {"benefics": ["Mars", "Sun", "Jupiter"], "malefics": ["Mercury", "Venus", "Saturn"], "yogakaraka": "Mars"},
    5:  {"benefics": ["Venus", "Mercury"], "malefics": ["Mars", "Jupiter", "Moon"], "yogakaraka": None},
    6:  {"benefics": ["Saturn", "Mercury", "Venus"], "malefics": ["Jupiter", "Sun", "Mars"], "yogakaraka": "Saturn"},
    7:  {"benefics": ["Jupiter", "Moon", "Sun", "Mars"], "malefics": ["Mercury", "Venus", "Saturn"], "yogakaraka": None},
    8:  {"benefics": ["Sun", "Mars", "Jupiter"], "malefics": ["Venus", "Saturn", "Mercury"], "yogakaraka": None},
    9:  {"benefics": ["Venus", "Mercury", "Saturn"], "malefics": ["Mars", "Jupiter", "Moon"], "yogakaraka": "Venus"},
    10: {"benefics": ["Venus", "Saturn", "Mercury"], "malefics": ["Moon", "Mars", "Jupiter"], "yogakaraka": "Venus"},
    11: {"benefics": ["Moon", "Mars", "Jupiter"], "malefics": ["Sun", "Venus", "Saturn", "Mercury"], "yogakaraka": None},
}

# ── Numerology (root number = digital root of birth day-of-month) ────────────
# VERIFY: convention-dependent; follows common Indian numerology tables.

NUMEROLOGY = {
    1: {"planet": "Sun",     "good": [1, 2, 3, 9], "evil": [6, 8]},
    2: {"planet": "Moon",    "good": [1, 2, 5],    "evil": [8, 9]},
    3: {"planet": "Jupiter", "good": [1, 3, 6, 9], "evil": [5, 8]},
    4: {"planet": "Rahu",    "good": [1, 7, 9],    "evil": [2, 8]},
    5: {"planet": "Mercury", "good": [1, 5, 6],    "evil": [2, 8]},
    6: {"planet": "Venus",   "good": [3, 6, 9],    "evil": [1, 8]},
    7: {"planet": "Ketu",    "good": [1, 2, 7],    "evil": [8, 9]},
    8: {"planet": "Saturn",  "good": [3, 5, 8],    "evil": [1, 2]},
    9: {"planet": "Mars",    "good": [3, 6, 9],    "evil": [2, 8]},
}

# ── Ghatak Chakra (by janma rashi / Moon sign) ───────────────────────────────
# Columns with None require a verified source before exposure as authoritative.
# VERIFY: month/tithi/day/nakshatra/lagna follow the standard published table;
# chandra = 4th from janma rashi per common tables; yoga/karana/prahar pending.

TITHI_GROUPS = {
    "Nanda": [1, 6, 11], "Bhadra": [2, 7, 12], "Jaya": [3, 8, 13],
    "Rikta": [4, 9, 14], "Purna": [5, 10, 15],
}

GHATAK_CHAKRA = {
    # rashi idx: (lunar month, tithi group, weekday, nakshatra, ghatak lagna idx)
    0:  ("Kartika",      "Nanda",  "Sunday",    "Magha",       0),
    1:  ("Margashirsha", "Purna",  "Saturday",  "Hasta",       1),
    2:  ("Phalguna",     "Bhadra", "Monday",    "Swati",       2),
    3:  ("Chaitra",      "Bhadra", "Wednesday", "Anuradha",    3),
    4:  ("Jyeshtha",     "Jaya",   "Saturday",  "Moola",       4),
    5:  ("Bhadrapada",   "Purna",  "Saturday",  "Shravana",    5),
    6:  ("Jyeshtha",     "Rikta",  "Thursday",  "Shatabhisha", 6),
    7:  ("Ashadha",      "Nanda",  "Friday",    "Revati",      7),
    8:  ("Shravana",     "Jaya",   "Friday",    "Bharani",     8),
    9:  ("Ashwina",      "Rikta",  "Tuesday",   "Rohini",      9),
    10: ("Chaitra",      "Jaya",   "Thursday",  "Ardra",       10),
    11: ("Bhadrapada",   "Purna",  "Friday",    "Ashlesha",    11),
}
