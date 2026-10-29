"""Which classical rules one person's chart meets, section by section, for Your Story.

Hawk (2026-10-28): Your Story read as hardcoded, because it was. The old screen
picked one of two or three fixed paragraphs per card from just two planets'
houses, so most people read the same words. The story agent (story_agent.py)
now writes each section only through the rules picked here, the same way the
couple agent reads marriage only through compat_classics.py.

Two stores feed it:

* context/references.json, the reviewed rules already used by Ask and the
  couple agent: the 10th house for work, the 2nd and 11th for money, the 7th
  for relationships (through compat_classics), the lagna for vitality, and the
  dasha condition rules for the current chapter.
* context/placement_references.json, read from the books on 2026-10-28 for
  this screen: each rising sign (BPHS ch.4), the ascendant lord in each house
  (BPHS ch.26), the Moon in each sign (Brihat Jataka ch.XVII) and the Moon's
  star (Brihat Jataka ch.XVI). They live apart because a placement rule is
  only ever true of the charts that have that placement; see that file's notes.

Nothing here adds a rule. The code only decides which stored rule a chart
meets and says why, and fixes how a harsh rule is delivered (READ_AS). The
plain lines below are the code backup the screen shows when the agent is off
or fails, so the story is still built from this person's own placements.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..context.kb import get_knowledge_base
from ..core.vedic.constants import SIGN_LORDS, SIGNS
from .compat_classics import DUSTHANAS, STRONG, WEAK, classical_rules as marriage_rules

PLACEMENTS = Path(__file__).resolve().parent.parent / "context" / "placement_references.json"
KENDRA_TRIKONA = {1, 4, 5, 7, 9, 10}
NATURAL_BENEFICS = {"Jupiter", "Venus", "Mercury", "Moon"}
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
SECTIONS = ("personality", "work", "relationships", "money", "energy", "chapter")

# How a reader-facing line may carry a rule whose classical wording is harsh.
READ_AS = {
    "bj16_5_moon_star_ashlesha": "Read only as: shrewd and guarded, slow to trust. Never as dishonest or ungrateful.",
    "bj16_9_moon_star_vishakha": "Read as: a strong drive to win and to earn. Never as jealous or greedy.",
    "bj16_10_moon_star_jyeshtha": "Read as: content and generous, with a temper that rises fast and is worth watching.",
    "bj16_13_moon_star_shatabhisha": "Read 'hard to reconcile' as: hard to move once decided.",
    "bj16_13_moon_star_purva_bhadrapada": "Read as: skilful and careful with money, with worries that weigh more than they should. Never as a sad life.",
    "bj17_8_moon_in_scorpio": "Read as: intense, private, and independent early. Never as cruel or secretive in a bad sense.",
    "bj17_10_moon_in_capricorn": "Read the miserly and idle streak as: careful with money, and resting when they can. Never as a fault of character.",
    "bj17_11_moon_in_aquarius": "Read stubbornness as determination that can harden into stubbornness.",
    "bphs26_6_lagna_lord_in_6": "Read as: comfort comes through effort, and they grow by meeting competition head-on. Never as illness or enemies.",
    "bphs26_8_lagna_lord_in_8": "Read as: drawn to what is hidden and to deep study, with a fierce temper. Never as illness.",
    "bphs26_12_lagna_lord_in_12": "Read as: generous, sometimes to a fault; guarding energy and money helps. Never as loss.",
    "bphs_kemadruma_growth_area": "Read as: self-reliance, and a need to let people in. Never as loneliness or lack.",
    "bphs21_3_tenth_lord_weak": "Read as: work rewards patience and persistence more than speed. Never as failure.",
    "bphs22_11_eleventh_lord_afflicted": "Read as: gains come through steady effort rather than easily. Never as poverty.",
    "bphs13_6_yogas_for_poverty": "Read as: a reason to build savings carefully. Never as poverty.",
    "uk_1st_lagna_vitality": "Speak of energy, rest and routine only. Never of illness or the body failing.",
    "bphs47_5_dasha_lord_condition": "When the period runs less easily, read as: a period that asks for patience and steady effort. Never as bad luck.",
}

# ── Code backup: plain lines per placement ──────────────────────────────────

LAGNA_PLAIN = {
    "Aries": "You act quickly and like to get things moving. Your temper can flare, but it passes fast.",
    "Taurus": "You are steady and patient. You take your time to decide, then you hold your ground.",
    "Gemini": "You are lively and adaptable, as happy thinking a thing through as doing it.",
    "Cancer": "You are caring and quick to respond to what people need, with a calm, principled core.",
    "Leo": "You carry yourself with quiet dignity. You are principled and slow to change your mind.",
    "Virgo": "You are practical and grounded, and you adjust well when plans change.",
    "Libra": "You are active and outgoing, quick to start things and quick to forgive.",
    "Scorpio": "You feel things deeply and hold on to them. You are steady, private and hard to shake.",
    "Sagittarius": "You are open, principled and flexible, happy both to think and to act.",
    "Capricorn": "You are practical and hardworking, always moving toward the next goal.",
    "Aquarius": "You are steady and determined. Once you set your course, you keep to it.",
    "Pisces": "You are gentle, kind and adaptable, with a calm, principled heart.",
}
LAGNA_WORD = {
    "Aries": "Quick to act", "Taurus": "Steady and patient", "Gemini": "Lively and adaptable",
    "Cancer": "Caring and responsive", "Leo": "Dignified and principled", "Virgo": "Practical and grounded",
    "Libra": "Outgoing and quick to forgive", "Scorpio": "Deep and steady", "Sagittarius": "Open and principled",
    "Capricorn": "Hardworking and practical", "Aquarius": "Steady and determined", "Pisces": "Gentle and kind",
}
LAGNA_LORD_PLAIN = {
    1: "You are capable and thoughtful, though your mind likes to keep moving.",
    2: "You value learning, good conduct and building something that lasts.",
    3: "You have real courage and the drive to take things on yourself.",
    4: "Home and family are your anchor, and people find you warm.",
    5: "You are self-respecting and quick to react, and people in charge tend to notice you.",
    6: "You grow strong by handling problems and competition head-on.",
    7: "Your life opens up through other people and through travel.",
    8: "You are drawn to what lies under the surface and enjoy digging deep.",
    9: "You are lucky in good people, you speak well, and you have faith to lean on.",
    10: "You want to be known for your own work, and you earn your own way.",
    11: "You keep gaining, step by step, through good qualities and good contacts.",
    12: "You are generous, sometimes to a fault. Guarding your energy and money helps you.",
}
MOON_PLAIN = {
    "Aries": "You are brave and self-respecting. You get upset quickly, but you calm down just as fast.",
    "Taurus": "You are generous and patient, and your friendships last. Life tends to get better as you get older.",
    "Gemini": "You are witty and quick to understand people, with a gift for words and music.",
    "Cancer": "You are loyal to friends and moved by kindness. You love home, water and gardens.",
    "Leo": "You are generous and brave, with a firm mind. When hurt, you take time to let it go.",
    "Virgo": "You are modest, truthful and soft-spoken, with a gift for learning and the arts.",
    "Libra": "You are devout, clean in your ways and good at trade, and you help your relatives.",
    "Scorpio": "You are intense and private, and you learned early to stand on your own.",
    "Sagittarius": "You speak well, work hard and know right from wrong. Kind words win you over, force does not.",
    "Capricorn": "You care for your family and grasp things quickly. You are careful with money.",
    "Aquarius": "You are determined and keep many friends. You can bear a lot of strain when you have to.",
    "Pisces": "You love your family, enjoy fine things and learn well. You tend to come out ahead of rivals.",
}
MOON_WORD = {
    "Aries": "brave at heart", "Taurus": "generous at heart", "Gemini": "witty at heart",
    "Cancer": "loyal at heart", "Leo": "big-hearted", "Virgo": "modest at heart", "Libra": "fair at heart",
    "Scorpio": "intense at heart", "Sagittarius": "principled at heart", "Capricorn": "careful at heart",
    "Aquarius": "determined at heart", "Pisces": "warm at heart",
}
GROWTH_PLAIN = {
    "Aries": "Quick anger fades fast in you, but words said in it stay. Count to ten before you reply.",
    "Taurus": "Steady can turn stubborn. When a plan stops working, let yourself change course sooner.",
    "Gemini": "A busy mind can run late into the night. Write the worry down, then let it rest.",
    "Cancer": "You give a lot to the people you love. Ask for help too, before you are tired.",
    "Leo": "Hurt can stay with you a long time. Saying it out loud early lets it go sooner.",
    "Virgo": "You notice every small flaw, including your own. Good enough, done well, is often enough.",
    "Libra": "Keeping everyone happy is tiring. It is fine to say no kindly.",
    "Scorpio": "You keep a lot inside. Letting one trusted person in makes the load lighter.",
    "Sagittarius": "Your sense of right and wrong is strong. Leave room for people who see it differently.",
    "Capricorn": "Rest is part of the work, not a break from it. Plan it like any other task.",
    "Aquarius": "Determination can harden into stubbornness. Ask for one other view before you decide.",
    "Pisces": "You feel what others feel. Protect some quiet time just for yourself.",
}
STAR_PLAIN = {
    "Pushya": "You can control your impulses, and people respect your learning and generosity.",
    "Ashlesha": "You are shrewd and slow to trust. People who earn your trust find you loyal.",
    "Magha": "You are enterprising, and you respect elders and tradition.",
    "Purva Phalguni": "You are sweet-spoken, generous and love to travel.",
    "Uttara Phalguni": "You are well liked and build your own success.",
    "Hasta": "You are enterprising and clever with your hands and your mind.",
    "Chitra": "You have good taste and take care in how you present yourself.",
    "Swati": "You are polite, kind-hearted and generous, with a head for business.",
    "Vishakha": "You speak well and are good at earning, with a strong drive to win.",
    "Anuradha": "You are a natural leader who enjoys travel and may live far from home.",
    "Jyeshtha": "You are content with little and generous, with a small circle of friends.",
    "Moola": "You are proud, steady and enjoy life.",
    "Purva Ashadha": "You are proud and a steady, loyal friend.",
    "Uttara Ashadha": "You are polite, knowledgeable and grateful, with many friends.",
    "Shravana": "You are learned, generous and well regarded.",
    "Dhanishta": "You are generous and brave, and you love music.",
    "Shatabhisha": "You are plain-spoken and truthful, adventurous, and hard to move once decided.",
    "Purva Bhadrapada": "You are skilful and careful with money, though worries can weigh on you.",
    "Uttara Bhadrapada": "You speak well, are generous, and tend to come out ahead of opponents.",
    "Revati": "You are brave, clean in your ways and well liked.",
}
MAHAPURUSHA_PLAIN = {
    "Ruchaka": "You have a natural courage that shows when things get hard.",
    "Bhadra": "Your mind is sharp, and you explain things clearly.",
    "Hamsa": "People come to you for advice, and your judgement is sound.",
    "Malavya": "You have refined taste and make life around you more pleasant.",
    "Sasa": "You are disciplined and can carry responsibility for a long time.",
    "Shasha": "You are disciplined and can carry responsibility for a long time.",
}
AREA_TITLES = {"work": "Work & purpose", "relationships": "Relationships",
               "money": "Money", "energy": "Energy & routine"}
AREA_PLAIN = {
    ("work", "strong"): ("Your work tends to be noticed. Effort you put in is likely to be seen and rewarded.",
                         "Take on the task that others avoid. It is where you shine."),
    ("work", "steady"): ("Your work grows steadily with skill. Keep building, and recognition follows.",
                         "Learn one new skill this year that your work will need."),
    ("work", "gentle"): ("Work rewards patience more than speed for you. Progress is real, even when it feels slow.",
                         "Write down one thing you finished each week. It shows how far you have come."),
    ("relationships", "strong"): ("Close bonds come fairly naturally to you, and people feel secure around you.",
                                  "Say thank you out loud for small things."),
    ("relationships", "steady"): ("Your relationships deepen with time and clear talk.",
                                  "Share one plan for the week with the people closest to you."),
    ("relationships", "gentle"): ("Closeness asks for a little more care and patience from you. It grows when you give it time.",
                                  "When you feel hurt, say it calmly the same day."),
    ("money", "strong"): ("Money tends to come in through more than one door for you.",
                          "Put a fixed share of every gain into savings first."),
    ("money", "steady"): ("Your money grows the slow, sure way, through steady saving and good choices.",
                          "Before any big purchase, wait one week."),
    ("money", "gentle"): ("Money comes through steady effort rather than easily. Careful saving gives you a strong base.",
                          "Keep a small fund for surprises, and add to it every month."),
    ("energy", "strong"): ("You have good energy to draw on. Keep it with regular sleep and simple food.",
                           "Keep one hour each day free of screens."),
    ("energy", "steady"): ("Your energy stays good when your days have a rhythm.",
                           "Sleep and wake at the same time, even on holidays."),
    ("energy", "gentle"): ("Your energy needs looking after. Rest before you are tired, not after.",
                           "Take a short walk every day, and stop work at a fixed time."),
}
HOUSE_THEME = {
    1: "puts you and your own direction at the front",
    2: "puts family, savings and your words at the front",
    3: "puts courage, effort and your own initiative at the front",
    4: "puts home, mother and inner peace at the front",
    5: "puts learning, children and creative work at the front",
    6: "puts daily work, service and solving problems at the front",
    7: "puts partnership and dealings with others at the front",
    8: "puts change, research and what is hidden at the front",
    9: "puts faith, teachers and good fortune at the front",
    10: "puts work, duty and your standing at the front",
    11: "puts gains, friends and goals coming true at the front",
    12: "puts rest, giving and life away from home at the front",
}


@lru_cache(maxsize=1)
def _placements() -> dict[str, dict]:
    data = json.loads(PLACEMENTS.read_text(encoding="utf-8"))
    return {ref["ref_id"]: ref for ref in data["references"]}


@lru_cache(maxsize=1)
def _stored() -> dict[str, str]:
    """Every statement either store holds, by id."""
    statements = {ref.ref_id: ref.statement
                  for domain in ("personality", "career", "wealth", "health", "marriage")
                  for ref in get_knowledge_base().retrieve([domain], limit=500)}
    statements.update({ref_id: ref["statement"] for ref_id, ref in _placements().items()})
    return statements


def _sign_of_house(lagna_sign: str, house: int) -> str:
    return SIGNS[(SIGNS.index(lagna_sign) + house - 1) % 12]


def strength(dignity: str | None, house: int | None) -> str:
    """strong, gentle or steady, from the planet's dignity and house only."""
    if dignity in WEAK or house in DUSTHANAS:
        return "gentle"
    if dignity in STRONG:
        return "strong"
    return "steady"


def _ordinal(n: int) -> str:
    return f"{n}{'st' if n == 1 else 'nd' if n == 2 else 'rd' if n == 3 else 'th'}"


def _active_yogas(chart) -> list[dict]:
    return [y for y in (chart.yogas() or {}).get("active") or [] if y.get("active", True)]


def _lord(lagna: str, house: int, planets: dict, dignities: dict) -> dict:
    planet = SIGN_LORDS[SIGNS.index(_sign_of_house(lagna, house))]
    row = planets.get(planet) or {}
    dignity = (dignities.get(planet) or {}).get("dignity")
    return {"planet": planet, "sign": row.get("sign"), "house": row.get("house"), "dignity": dignity,
            "strength": strength(dignity, row.get("house"))}


def _running(chart, as_of) -> dict:
    current = (chart.dashas(as_of) or {}).get("current") or {}
    out = {}
    for level in ("mahadasha", "antardasha"):
        row = current.get(level)
        if row:
            out[level] = {"lord": row["lord"], "ends": str(row["end"])[:10]}
    return out


def chart_facts(chart, as_of=None) -> dict:
    """The placements each section reads, in one place."""
    planets = chart.planet_details()
    dignities = chart.dignities()
    lagna = chart.lagna_details()["sign"]
    moon = planets["Moon"]
    moon_dignity = (dignities.get("Moon") or {}).get("dignity")
    moon_sign_lord = SIGN_LORDS[SIGNS.index(moon["sign"])]
    yogas = _active_yogas(chart)
    lords = {house: _lord(lagna, house, planets, dignities) for house in (1, 2, 7, 10, 11)}
    with_lord = {house: [name for name, row in planets.items()
                         if name != lord["planet"] and row.get("sign") == lord["sign"]]
                 for house, lord in lords.items()}
    return {
        "lagna": lagna,
        "lords": lords,
        "with_lord": with_lord,
        "moon": {"sign": moon["sign"], "house": moon.get("house"), "star": moon.get("nakshatra"),
                 "dignity": moon_dignity, "sign_lord": moon_sign_lord,
                 "sign_lord_dignity": (dignities.get(moon_sign_lord) or {}).get("dignity")},
        "planets": {name: {"sign": row.get("sign"), "house": row.get("house"),
                           "dignity": (dignities.get(name) or {}).get("dignity")}
                    for name, row in planets.items()},
        "yogas": [{"name": y["name"], "strength": y.get("strength"),
                   "meaning": (y.get("reader") or {}).get("what") or y.get("lay_explanation")}
                  for y in yogas if y.get("verified") and y.get("lay_explanation")][:8],
        "yoga_names": [y["name"] for y in yogas],
        "running": _running(chart, as_of),
        "manglik": (chart.doshas() or {}).get("manglik") or {},
        "_planets_raw": planets,
        "_dignities": dignities,
    }


def _moon_strength(facts: dict) -> str:
    moon = facts["moon"]
    strong = sum(d in STRONG for d in (moon["dignity"], moon["sign_lord_dignity"]))
    weak = sum(d in WEAK for d in (moon["dignity"], moon["sign_lord_dignity"]))
    if strong == 2:
        return "the Moon and its sign's lord are both strong, so these show fully"
    if weak:
        return "the Moon or its sign's lord is weak, so these show only in part"
    return "the Moon is of middling strength, so these show in part"


def personality_picks(facts: dict) -> list[tuple[str, str]]:
    lagna, lord, moon = facts["lagna"], facts["lords"][1], facts["moon"]
    star = (moon.get("star") or "").lower().replace(" ", "_")
    star_id = next((ref_id for ref_id in _placements() if ref_id.startswith("bj16_") and ref_id.endswith(f"_{star}")), None)
    moon_id = next(ref_id for ref_id in _placements() if ref_id.endswith(f"_moon_in_{moon['sign'].lower()}"))
    picks = [
        ("bphs_lagna_core_temperament", f"{lagna} rising; its lord {lord['planet']} in the {_ordinal(lord['house'])} house, {lord['dignity']}"),
        (f"bphs4_lagna_{lagna.lower()}", f"{lagna} rising"),
        (f"bphs26_{lord['house']}_lagna_lord_in_{lord['house']}", f"ascendant lord {lord['planet']} in the {_ordinal(lord['house'])} house"),
        ("uk_moon_emotional_nature", f"Moon in {moon['sign']}, {_ordinal(moon['house'])} house"),
        (moon_id, f"Moon in {moon['sign']}; {_moon_strength(facts)}"),
    ]
    if star_id:
        picks.append((star_id, f"Moon in {moon['star']}; {_moon_strength(facts)}"))
    mahapurusha = [name.split()[0] for name in facts["yoga_names"]
                   if name.split()[0] in MAHAPURUSHA_PLAIN]
    if mahapurusha:
        picks.append(("bphs_pancha_mahapurusha_strengths", f"{', '.join(mahapurusha)} yoga active"))
    if any(name.startswith("Kemadruma") for name in facts["yoga_names"]):
        picks.append(("bphs_kemadruma_growth_area", "no planets on either side of the Moon"))
    faculties = "; ".join(f"{p} {facts['planets'][p]['dignity']}" for p in ("Mercury", "Jupiter", "Moon"))
    picks.append(("saravali4_planetary_faculty_karakas", faculties))
    return picks


def _lord_in_house_id(lord_no: int, house: int, prefix: str = "bphs24_") -> str | None:
    """The stored 'lord of N in house M' rule, found by its tags."""
    for ref in get_knowledge_base().retrieve(["career", "wealth"], limit=500):
        if ref.ref_id.startswith(prefix) and f"lord:{lord_no}" in ref.tags and f"house:{house}" in ref.tags:
            return ref.ref_id
    return None


def work_picks(facts: dict) -> list[tuple[str, str]]:
    lord = facts["lords"][10]
    where = f"10th lord {lord['planet']} in the {_ordinal(lord['house'])} house, {lord['dignity']}"
    picks = [("uk4_tenth_bhava_scope", where)]
    if lord["strength"] == "strong":
        picks.append(("bphs21_2_tenth_lord_strong", where))
    elif lord["strength"] == "gentle":
        picks.append(("bphs21_3_tenth_lord_weak", where))
    benefic_with = [p for p in facts["with_lord"][10] if p in NATURAL_BENEFICS]
    if benefic_with or (lord["house"] in KENDRA_TRIKONA and lord["strength"] != "gentle"):
        picks.append(("bphs21_4_tenth_lord_benefic", where + (f", with {', '.join(benefic_with)}" if benefic_with else "")))
    if lord["house"] == 10:
        picks.append(("bphs24_118_tenth_lord_in_tenth", where))
    field = _lord_in_house_id(10, lord["house"], prefix="bphs_g26_")
    if field:
        picks.append((field, where))
    if any(name.startswith("Amala") for name in facts["yoga_names"]):
        picks.append(("bphs_amala_career_reputation", "Amala yoga active"))
    for level, row in facts["running"].items():
        if row["lord"] == lord["planet"]:
            picks.append(("bphs48_tenth_lord_dasha", f"running {level} of the 10th lord {lord['planet']}"))
            break
    return picks


def money_picks(facts: dict) -> list[tuple[str, str]]:
    second, eleventh = facts["lords"][2], facts["lords"][11]
    picks = [
        ("uk_wealth_2nd_11th", f"2nd lord {second['planet']} in the {_ordinal(second['house'])}; 11th lord {eleventh['planet']} in the {_ordinal(eleventh['house'])}"),
        ("bphs13_1_second_lord_placement_wealth", f"2nd lord {second['planet']} in the {_ordinal(second['house'])} house, {second['dignity']}"),
    ]
    for lord_no, lord in ((2, second), (11, eleventh)):
        found = _lord_in_house_id(lord_no, lord["house"])
        if found:
            picks.append((found, f"{_ordinal(lord_no)} lord {lord['planet']} in the {_ordinal(lord['house'])} house"))
    if eleventh["house"] in KENDRA_TRIKONA | {11} or eleventh["dignity"] == "Exalted":
        picks.append(("bphs22_2_eleventh_lord_strong_placement", f"11th lord {eleventh['planet']} in the {_ordinal(eleventh['house'])}, {eleventh['dignity']}"))
    elif eleventh["dignity"] == "Debilitated" or eleventh["house"] in DUSTHANAS:
        picks.append(("bphs22_11_eleventh_lord_afflicted", f"11th lord {eleventh['planet']} in the {_ordinal(eleventh['house'])}, {eleventh['dignity']}"))
    exchange = second["house"] == 11 and eleventh["house"] == 2
    together = second["sign"] == eleventh["sign"] and second["house"] in KENDRA_TRIKONA
    if exchange or together:
        picks.append(("bphs13_4_second_eleventh_exchange", "2nd and 11th lords exchanged or together in an angle or trine"))
    dhana = [name for name in facts["yoga_names"] if name.startswith("Dhana Yoga")]
    if dhana:
        picks.append(("bphs_dhana_yoga_wealth", "; ".join(dhana[:3])))
    return picks


def energy_picks(facts: dict) -> list[tuple[str, str]]:
    lord = facts["lords"][1]
    return [("uk_1st_lagna_vitality",
             f"ascendant lord {lord['planet']} in the {_ordinal(lord['house'])} house, {lord['dignity']}")]


def chapter_picks(facts: dict) -> list[tuple[str, str]]:
    period = (facts["running"].get("mahadasha") or {}).get("lord")
    if not period:
        return []
    row = facts["planets"].get(period) or {}
    where = f"running {period} period; {period} in the {_ordinal(row.get('house') or 0)} house, {row.get('dignity')}"
    return [("bphs47_5_dasha_lord_condition", where), ("bphs48_1_dignity_over_nature", where)]


def relationship_rules(facts: dict) -> list[dict]:
    """The marriage rules this chart meets, picked by the couple agent's code."""
    lord = facts["lords"][7]
    return marriage_rules(facts["_planets_raw"], facts["_dignities"], lord["planet"], facts["manglik"],
                          facts["running"])


def _rules(picks: list[tuple[str, str]]) -> list[dict]:
    statements = _stored()
    out, seen = [], set()
    for ref_id, because in picks:
        if not ref_id or ref_id in seen or ref_id not in statements:
            continue
        seen.add(ref_id)
        rule = {"id": ref_id, "rule": statements[ref_id], "applies_because": because}
        if ref_id in READ_AS:
            rule["read_as"] = READ_AS[ref_id]
        out.append(rule)
    return out


def section_rules(facts: dict) -> dict[str, list[dict]]:
    return {
        "personality": _rules(personality_picks(facts)),
        "work": _rules(work_picks(facts)),
        "relationships": relationship_rules(facts),
        "money": _rules(money_picks(facts)),
        "energy": _rules(energy_picks(facts)),
        "chapter": _rules(chapter_picks(facts)),
    }


def area_tones(facts: dict) -> dict[str, str]:
    """The badge each area carries, from the house lord's real strength.

    Money takes the weaker of the 2nd and 11th lords only when both lean the
    same way; one strong and one weak lord reads as steady."""
    lords = facts["lords"]
    money = {lords[2]["strength"], lords[11]["strength"]}
    return {
        "work": lords[10]["strength"],
        "relationships": lords[7]["strength"],
        "money": money.pop() if len(money) == 1 else "steady",
        "energy": lords[1]["strength"],
    }


def fallback_story(facts: dict) -> dict:
    """The code backup: the same shape the agent fills, from plain lines per placement."""
    lagna, lord, moon = facts["lagna"], facts["lords"][1], facts["moon"]
    traits = [LAGNA_PLAIN[lagna], LAGNA_LORD_PLAIN[lord["house"]], MOON_PLAIN[moon["sign"]]]
    if moon.get("star") in STAR_PLAIN:
        traits.append(STAR_PLAIN[moon["star"]])
    for name in facts["yoga_names"]:
        line = MAHAPURUSHA_PLAIN.get(name.split()[0])
        if line and line not in traits:
            traits.append(line)
    tones = area_tones(facts)
    areas = []
    for key in ("work", "relationships", "money", "energy"):
        text, tip = AREA_PLAIN[(key, tones[key])]
        areas.append({"key": key, "title": AREA_TITLES[key], "text": text, "tip": tip, "tone": tones[key]})
    chapter = None
    period = facts["running"].get("mahadasha")
    if period:
        house = (facts["planets"].get(period["lord"]) or {}).get("house")
        theme = HOUSE_THEME.get(house, "brings its own lessons")
        chapter = f"You are in a {period['lord']} period until {period['ends'][:4]}. This chapter {theme}."
    return {
        "headline": f"{LAGNA_WORD[lagna]}, {MOON_WORD[moon['sign']]}.",
        "summary": None,
        "traits": [{"title": None, "detail": line} for line in traits[:6]],
        "growth": GROWTH_PLAIN[moon["sign"]],
        "areas": areas,
        "chapter": chapter,
    }
