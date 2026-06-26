"""
Astrological knowledge base for accurate AI readings.
Covers planet-in-sign, planet-in-house, aspect timing, and period archetypes.
"""

# ── Planet timing keywords (average transit durations) ───────────────────────
PLANET_TRANSIT_SPEED = {
    "Sun":     {"days": 30,    "keyword": "vitality, identity"},
    "Moon":    {"days": 2.5,   "keyword": "emotions, instincts"},
    "Mercury": {"days": 20,    "keyword": "communication, thinking"},
    "Venus":   {"days": 25,    "keyword": "love, beauty, values"},
    "Mars":    {"days": 57,    "keyword": "drive, action, desire"},
    "Jupiter": {"months": 12,  "keyword": "expansion, luck, growth"},
    "Saturn":  {"months": 30,  "keyword": "discipline, structure, karma"},
    "Uranus":  {"years": 7,    "keyword": "revolution, awakening, change"},
    "Neptune": {"years": 14,   "keyword": "spirituality, dreams, illusion"},
    "Pluto":   {"years": 20,   "keyword": "transformation, power, rebirth"},
}

# ── Planet in sign detailed meanings ─────────────────────────────────────────
PLANET_IN_SIGN = {
    ("Sun", "Aries"):       "Bold, pioneering spirit; initiates with confidence; natural leader who acts first and thinks later.",
    ("Sun", "Taurus"):      "Steady, sensual, and determined; values security and beauty; builds lasting foundations.",
    ("Sun", "Gemini"):      "Curious, adaptable, and witty; thrives on information exchange; embraces duality.",
    ("Sun", "Cancer"):      "Nurturing, intuitive, and protective; deeply connected to home and family; emotionally intelligent.",
    ("Sun", "Leo"):         "Radiant, generous, and dramatic; natural performer; leads with heart and demands recognition.",
    ("Sun", "Virgo"):       "Analytical, helpful, and precise; sees the details others miss; service-oriented perfectionist.",
    ("Sun", "Libra"):       "Diplomatic, fair, and aesthetically gifted; seeks harmony and partnership; weighs all options.",
    ("Sun", "Scorpio"):     "Intense, perceptive, and transformative; penetrates surface appearances; masters of depth and power.",
    ("Sun", "Sagittarius"): "Philosophical, adventurous, and optimistic; seeks truth and meaning; loves freedom and expansion.",
    ("Sun", "Capricorn"):   "Ambitious, disciplined, and practical; builds with patience; driven by status and achievement.",
    ("Sun", "Aquarius"):    "Innovative, humanitarian, and independent; ahead of their time; values collective progress.",
    ("Sun", "Pisces"):      "Compassionate, mystical, and imaginative; dissolves boundaries; deeply empathic and creative.",

    ("Moon", "Aries"):      "Emotional needs met through action and independence; quick emotional reactions; needs to feel first.",
    ("Moon", "Taurus"):     "Finds comfort in stability, sensory pleasure, and routine; slow to change emotionally; deeply loyal.",
    ("Moon", "Gemini"):     "Emotional wellbeing through mental stimulation and variety; talks through feelings; needs connection.",
    ("Moon", "Cancer"):     "Deeply intuitive and nurturing; home is emotional sanctuary; strong bond with mother/maternal figures.",
    ("Moon", "Leo"):        "Needs appreciation and creative expression for emotional security; warm-hearted and generous.",
    ("Moon", "Virgo"):      "Finds comfort in order and being useful; anxious if unable to help; analytical about emotions.",
    ("Moon", "Libra"):      "Needs harmony and partnership; emotionally distressed by conflict; gracious and socially attuned.",
    ("Moon", "Scorpio"):    "Intense emotional life; feels deeply and privately; attracted to transformative experiences.",
    ("Moon", "Sagittarius"):"Needs freedom and adventure to feel secure; optimistic emotional outlook; philosophical about pain.",
    ("Moon", "Capricorn"):  "Controls emotions with discipline; practical in expressing feelings; security through achievement.",
    ("Moon", "Aquarius"):   "Detached emotional style; needs intellectual stimulation and like-minded community; values freedom.",
    ("Moon", "Pisces"):     "Highly empathic and psychically sensitive; blurs boundaries; needs creative or spiritual outlet.",

    ("Venus", "Aries"):     "Loves boldly and impulsively; attracted to confidence; prefers the chase; passionate but impatient.",
    ("Venus", "Taurus"):    "Sensual, loyal, and devoted; loves beauty and comfort; slow to fall but deeply committed.",
    ("Venus", "Gemini"):    "Flirtatious and mentally stimulated; loves witty exchanges; needs variety in relationships.",
    ("Venus", "Cancer"):    "Deeply nurturing in love; romantic and protective; seeks emotional security in partnership.",
    ("Venus", "Leo"):       "Loves grandly and dramatically; wants to be adored; generous and warm with loved ones.",
    ("Venus", "Virgo"):     "Shows love through acts of service; selective in partners; appreciates intelligence and hygiene.",
    ("Venus", "Libra"):     "Natural romantic; seeks the ideal partnership; charming, diplomatic, and aesthetically refined.",
    ("Venus", "Scorpio"):   "Intense and all-or-nothing in love; magnetic sexuality; demands depth and transformation.",
    ("Venus", "Sagittarius"):"Values freedom and adventure in love; attracts with humor; needs philosophical connection.",
    ("Venus", "Capricorn"): "Traditional and loyal; attracted to status and reliability; love deepens slowly over time.",
    ("Venus", "Aquarius"):  "Unconventional love style; needs intellectual equality and friendship as foundation.",
    ("Venus", "Pisces"):    "Idealistic and selfless in love; deeply romantic; can merge completely with a partner.",

    ("Mars", "Aries"):      "Warrior energy at full power; acts decisively without hesitation; competitive and courageous.",
    ("Mars", "Taurus"):     "Slow and steady drive; persistent and determined; motivated by tangible, sensory rewards.",
    ("Mars", "Gemini"):     "Mental agility fuels action; multitasker; debates as a form of engagement.",
    ("Mars", "Cancer"):     "Indirect action; motivated by protection of family; passive-aggressive when threatened.",
    ("Mars", "Leo"):        "Dramatic and proud in action; performs best before an audience; fiercely defends loved ones.",
    ("Mars", "Virgo"):      "Meticulous and efficient; channels energy into useful work; sharp critical edge.",
    ("Mars", "Libra"):      "Diplomatically aggressive; debates and negotiates; procrastinates decisions.",
    ("Mars", "Scorpio"):    "Laser-focused willpower; strategic and relentless; master of psychological warfare.",
    ("Mars", "Sagittarius"):"Enthusiastic and adventurous drive; fights for beliefs; inspiration over details.",
    ("Mars", "Capricorn"):  "Disciplined ambition; works tirelessly toward long-term goals; excellent executive energy.",
    ("Mars", "Aquarius"):   "Revolutionary drive; fights for causes; independent and unconventional methods.",
    ("Mars", "Pisces"):     "Intuitive action; driven by empathy and imagination; energy fluctuates like tides.",

    ("Mercury", "Aries"):   "Quick, direct thinking; speaks before considering consequences; sharp and decisive mind.",
    ("Mercury", "Taurus"):  "Methodical, practical, and stubborn in thought; excellent long-term memory.",
    ("Mercury", "Gemini"):  "Brilliant multitasker; quick-witted wordsmith; may scatter focus across too many topics.",
    ("Mercury", "Cancer"):  "Thinks with feelings; excellent memory for emotional experiences; intuitive communicator.",
    ("Mercury", "Leo"):     "Dramatic storyteller; confident speaker; thinks in grand, creative terms.",
    ("Mercury", "Virgo"):   "Analytical genius; perfectionist communicator; excels at problem-solving and health topics.",
    ("Mercury", "Libra"):   "Balanced, diplomatic thinker; considers all angles; skilled mediator and writer.",
    ("Mercury", "Scorpio"): "Penetrating, investigative mind; uncovers hidden truths; strategic communicator.",
    ("Mercury", "Sagittarius"): "Big-picture thinker; philosophical mind; may overlook details while chasing ideals.",
    ("Mercury", "Capricorn"): "Practical, structured thinker; authoritative communicator; values tradition and results.",
    ("Mercury", "Aquarius"): "Innovative, futuristic mind; thinks in systems; brilliant but can be detached.",
    ("Mercury", "Pisces"):  "Intuitive, poetic, and imaginative; absorbs rather than analyzes; excellent for art.",
}

# ── Planet in house meanings ──────────────────────────────────────────────────
PLANET_IN_HOUSE = {
    ("Sun", 1):  "Strong identity and presence; life is about self-expression and personal development.",
    ("Sun", 2):  "Identity tied to material security; success through building wealth and values.",
    ("Sun", 3):  "Shine through communication and learning; neighborhood and siblings are central themes.",
    ("Sun", 4):  "Home, family, and roots define identity; private nature with deep emotional core.",
    ("Sun", 5):  "Life energy channeled through creativity, children, romance, and play.",
    ("Sun", 6):  "Purpose found through daily work, health routines, and service to others.",
    ("Sun", 7):  "Self discovered through relationships; natural diplomat; partnerships are life's center.",
    ("Sun", 8):  "Drawn to transformation, shared resources, and the occult; deep psychological power.",
    ("Sun", 9):  "Higher learning, philosophy, travel, and spiritual seeking define the path.",
    ("Sun", 10): "Career-oriented; public recognition is essential; natural authority figure.",
    ("Sun", 11): "Community, friendships, and humanitarian causes are central to life purpose.",
    ("Sun", 12): "Private and introspective; spiritual depth; themes of solitude and inner work.",

    ("Moon", 1):  "Wears emotions openly; highly intuitive; mood affects physical appearance.",
    ("Moon", 4):  "Deep roots and nesting instinct; home is sanctuary; strong ancestral connection.",
    ("Moon", 7):  "Emotional fulfillment through partnerships; nurtures relationships instinctively.",
    ("Moon", 10): "Public reputation shaped by emotional expression; career may involve nurturing or public.",

    ("Jupiter", 1):  "Optimistic, generous presence; life naturally expands; strong intuition and faith.",
    ("Jupiter", 2):  "Financial abundance potential; generous with resources; values lead to growth.",
    ("Jupiter", 4):  "Blessed home life; family is source of growth and luck; real estate benefits.",
    ("Jupiter", 5):  "Luck in creativity, romance, and children; joyful self-expression multiplied.",
    ("Jupiter", 7):  "Benefits through partnerships; abundant social life; growth through others.",
    ("Jupiter", 9):  "Natural teacher and philosopher; travel and education bring luck.",
    ("Jupiter", 10): "Career expansion and public recognition; success in authority roles.",
    ("Jupiter", 11): "Many friends and connections; humanitarian goals succeed; group endeavors prosper.",

    ("Saturn", 1):  "Serious demeanor; life lessons around self-discipline and identity; late bloomer.",
    ("Saturn", 4):  "Family carries karmic weight; structure needed at home; lessons around roots.",
    ("Saturn", 7):  "Partnerships require serious commitment; may marry late; loyalty tested.",
    ("Saturn", 10): "Hard-won career success; takes decades to reach peak; lasting legacy built.",

    ("Mars", 1):   "High energy, assertive presence; natural leader; competitive drive is obvious.",
    ("Mars", 7):   "Attracted to assertive partners; conflict may arise in relationships; dynamic unions.",
    ("Mars", 10):  "Career-driven and ambitious; willing to fight for professional goals.",

    ("Venus", 1):  "Charming, beautiful presence; naturally draws others; artistic and lovable.",
    ("Venus", 5):  "Romantic, creative, and playful; loves love; artistic talents expressed joyfully.",
    ("Venus", 7):  "Partnership-oriented; naturally harmonious in relationships; attracts beautiful people.",
    ("Venus", 10): "Charm aids career; may work in beauty, arts, or diplomacy; well-liked publicly.",
}

# ── Aspect meanings ───────────────────────────────────────────────────────────
ASPECT_MEANINGS = {
    "conjunction": "Powerful merging of energies; planets intensify each other; new beginnings.",
    "opposition":  "Tension between opposing forces; awareness through relationship and projection.",
    "trine":       "Harmonious, flowing energy; natural talents; ease and opportunity.",
    "square":      "Friction and challenge; drives growth through difficulty; motivating tension.",
    "sextile":     "Cooperative opportunity; talents activated with effort; creative potential.",
    "quincunx":    "Adjustment required; mismatched energies must find a new balance.",
}

# ── Period-specific archetypes and focus areas ────────────────────────────────
PERIOD_ARCHETYPES = {
    "daily": {
        "moon_emphasis": True,
        "focus": "Today's Moon placement and transiting Moon aspects drive the emotional tone.",
        "key_planets": ["Moon", "Sun", "Mercury"],
        "template": (
            "For today ({date}):\n"
            "- Moon is moving through {moon_sign} — {moon_meaning}\n"
            "- Key themes: {themes}\n"
            "- Best focus: {focus_area}\n"
            "- Watch for: {caution}\n"
            "- Affirmation: {affirmation}"
        ),
    },
    "weekly": {
        "moon_emphasis": True,
        "focus": "Track Moon phases (New/Full) and fast-moving planet transits this week.",
        "key_planets": ["Moon", "Sun", "Mercury", "Venus", "Mars"],
        "template": (
            "Week of {date}:\n"
            "- Theme: {theme}\n"
            "- Love & relationships: {love}\n"
            "- Work & productivity: {work}\n"
            "- Health & wellbeing: {health}\n"
            "- Key dates: {key_dates}\n"
            "- Spiritual message: {spiritual}"
        ),
    },
    "monthly": {
        "moon_emphasis": False,
        "focus": "Solar themes dominate; Mars and Venus transits shape the month.",
        "key_planets": ["Sun", "Mercury", "Venus", "Mars", "Jupiter"],
        "template": (
            "{month_name} {year} for {name}:\n"
            "- Overall theme: {theme}\n"
            "- Career & ambitions: {career}\n"
            "- Love & social life: {love}\n"
            "- Finances: {finances}\n"
            "- Personal growth: {growth}\n"
            "- Challenges to navigate: {challenges}\n"
            "- Power dates: {power_dates}"
        ),
    },
    "quarterly": {
        "moon_emphasis": False,
        "focus": "Jupiter and Saturn transits; seasonal turning points; eclipse impacts.",
        "key_planets": ["Sun", "Jupiter", "Saturn", "Uranus"],
        "template": (
            "Q{quarter} {year} Forecast for {name}:\n"
            "- Quarter theme: {theme}\n"
            "- Major planetary influences: {planets}\n"
            "- Career trajectory: {career}\n"
            "- Relationships: {relationships}\n"
            "- Spiritual evolution: {spiritual}\n"
            "- Financial outlook: {finances}\n"
            "- Eclipse impact (if any): {eclipses}\n"
            "- Advice: {advice}"
        ),
    },
    "yearly": {
        "moon_emphasis": False,
        "focus": "Jupiter return/transit themes; Saturn cycle phase; nodal axis.",
        "key_planets": ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"],
        "template": (
            "{year} Annual Forecast for {name}:\n"
            "- Year theme: {theme}\n"
            "- Jupiter's gift: {jupiter}\n"
            "- Saturn's lesson: {saturn}\n"
            "- Career & life path: {career}\n"
            "- Love & relationships: {love}\n"
            "- Finance & abundance: {finances}\n"
            "- Health & vitality: {health}\n"
            "- Spiritual growth: {spiritual}\n"
            "- Key turning points: {turning_points}\n"
            "- Overall guidance: {guidance}"
        ),
    },
}

# ── Transit window descriptions ───────────────────────────────────────────────
TRANSIT_WINDOWS = {
    "Jupiter_conjunction_Sun":  "Major year of expansion, opportunity, and confidence. Health and vitality improve.",
    "Jupiter_trine_Sun":        "Smooth flow of luck and opportunities; doors open with minimal effort.",
    "Jupiter_square_Sun":       "Overconfidence risk; growth through challenge; avoid excess.",
    "Saturn_conjunction_Sun":   "Major life restructuring; time for serious commitments and hard work; maturation.",
    "Saturn_opposition_Sun":    "Opposition cycle peak; relationships and career face reality checks.",
    "Saturn_return":            "Ages 28-30 and 57-60; life audit and major restructuring of identity and goals.",
    "Uranus_conjunction_Sun":   "Radical life change and awakening; unexpected events reshape identity.",
    "Neptune_conjunction_Sun":  "Spiritual awakening; confusion may precede clarity; creative peak.",
    "Pluto_conjunction_Sun":    "Complete transformation of identity; death and rebirth of the ego.",
    "Jupiter_conjunction_Moon": "Emotional abundance; family joy; nurturing expansion.",
    "Saturn_conjunction_Moon":  "Emotional restrictions; past wounds surface; deep inner work required.",
    "Mars_conjunction_Sun":     "High energy and drive; take bold action; risk of conflict.",
    "Venus_conjunction_Sun":    "Charm and attraction heightened; excellent for love, art, and social events.",
    "Mercury_retrograde":       "Review, revise, reconnect; avoid major contracts, travel disruptions likely.",
    "Venus_retrograde":         "Relationship review; past loves may return; financial caution advised.",
    "Mars_retrograde":          "Energy turns inward; reevaluate goals; avoid new ventures.",
}

# Main knowledge base dict for agent access
KNOWLEDGE_BASE = {
    "planet_in_sign":    PLANET_IN_SIGN,
    "planet_in_house":   PLANET_IN_HOUSE,
    "aspect_meanings":   ASPECT_MEANINGS,
    "transit_windows":   TRANSIT_WINDOWS,
    "period_archetypes": PERIOD_ARCHETYPES,
    "planet_speed":      PLANET_TRANSIT_SPEED,
}


def get_transit_window(transit_planet: str, aspect: str, natal_planet: str) -> str:
    key = f"{transit_planet}_{aspect}_{natal_planet}"
    return TRANSIT_WINDOWS.get(key, "")


def get_period_focus(period: str) -> dict:
    return PERIOD_ARCHETYPES.get(period, PERIOD_ARCHETYPES["monthly"])
