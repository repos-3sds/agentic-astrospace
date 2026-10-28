"""Ask suggestions built from one profile's own chart.

The Ask home screen offers a few questions under "Suggested for you right
now", and one list per topic chip (Work, Marriage, Money, My child, Health).
Every suggestion here rests on a fact this chart actually has today: the
running major period and sub-period, the next sub-period if it starts soon,
Saturn and Jupiter moving over the houses that topic lives in, Sade Sati, and
a yoga the running period wakes up. The fact goes in `because`, so the reader
can see why the app is asking.

Rules the wording keeps:

- Simple English for Indian readers, first person, no jargon in the question.
  Terms (house numbers, yoga names) go in `because`, and only Practitioner
  sees house numbers.
- Nothing asks for a verdict. Money questions never ask what to buy or invest
  in; health questions are about energy and routine, never illness. Every
  prompt is checked against `refer_out_kind` in the tests.
- Nothing assumes a life the reader has not told us about. Marriage wording
  only says "married life" when the reader said they are married, and
  "my children" only appears when the reader said they have children.
  Otherwise the wording fits either way.
- Caution yogas are not offered as suggestions. That is not suppression: the
  chart screens still show them as flags. A suggestion is an invitation, and
  inviting a reader to worry is not one.

To add a topic (the family questions being designed for Ask will), add a
`Topic` to `TOPICS` with its houses, natural signifiers and phrase, and the
app picks it up from the response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .constants import SIGN_LORDS

Mode = str  # 'guided' | 'balanced' | 'practitioner'

# How far ahead a coming sub-period is worth naming.
UPCOMING_WINDOW = timedelta(days=270)
PER_TOPIC = 4
GENERAL = 3

HOUSE_WORDS = {
    1: "self and body", 2: "family wealth and savings", 3: "courage and effort",
    4: "home and mother", 5: "children and learning", 6: "daily work and health",
    7: "marriage and partners", 8: "sudden changes", 9: "luck and elders",
    10: "career", 11: "income and gains", 12: "expenses and rest",
}

ORDINAL = {1: "1st", 2: "2nd", 3: "3rd"}


def _ordinal(n: int) -> str:
    return ORDINAL.get(n, f"{n}th")


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    # Houses counted from the Lagna that this topic lives in.
    houses: tuple[int, ...]
    # Natural signifiers (karakas).
    karakas: tuple[str, ...]
    # How the topic reads inside a question: "What does my X period bring for {phrase}?"
    phrase: str
    # Active yoga categories that belong to this topic.
    yoga_words: tuple[str, ...] = ()
    karaka_note: dict[str, str] = field(default_factory=dict)


TOPICS: dict[str, Topic] = {
    t.id: t for t in (
        Topic("work", "Work", (10, 6), ("Saturn", "Sun"), "my work",
              ("Career", "Status", "Power"),
              {"Saturn": "the planet of hard work", "Sun": "the planet of status and authority"}),
        Topic("marriage", "Marriage", (7,), ("Venus",), "marriage and partnership", (),
              {"Venus": "the planet of marriage"}),
        Topic("money", "Money", (2, 11), ("Jupiter",), "money and savings", ("Wealth",),
              {"Jupiter": "the planet of growth and wealth"}),
        Topic("child", "My child", (5,), ("Jupiter",), "children", (),
              {"Jupiter": "the planet of children"}),
        Topic("health", "Health", (1, 6), ("Sun",), "my health and energy", (),
              {"Sun": "the planet of energy and vitality"}),
    )
}


@dataclass
class Facts:
    """Everything the builder reads, already pulled off the chart."""
    lagna_sign: int
    planet_house: dict[str, int]          # natal house from Lagna
    md: dict                              # running major period
    ad: dict                              # running sub-period
    upcoming: dict | None                 # next sub-period if it starts within UPCOMING_WINDOW
    upcoming_is_major: bool
    transit_house: dict[str, int]         # Jupiter/Saturn house from Lagna today
    sade_sati_phase: str | None           # 'first' | 'second' | 'third' | None
    ashtama_shani: bool
    kantaka_shani: bool
    guru_bala: bool                       # Jupiter favourable from the Moon
    yogas: list[dict]                     # active, non-caution yogas
    life: dict                            # reader's own facts: relationship_status, has_children, employment_status, ...


def _month(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%b %Y")


def facts_from_chart(chart, as_of: datetime | None = None, life: dict | None = None) -> Facts:
    as_of = as_of or datetime.now(chart.moment.dt_local.tzinfo)
    dashas = chart.dashas(as_of=as_of)
    current = dashas["current"]
    md, ad = current["mahadasha"], current["antardasha"]

    upcoming, upcoming_is_major = None, False
    sub = md.get("antardashas") or []
    idx = next((i for i, row in enumerate(sub) if row["lord"] == ad["lord"] and row["start"] == ad["start"]), None)
    if idx is not None and idx + 1 < len(sub):
        upcoming = sub[idx + 1]
    else:
        majors = dashas.get("mahadashas") or []
        m_idx = next((i for i, row in enumerate(majors) if row["start"] == md["start"]), None)
        if m_idx is not None and m_idx + 1 < len(majors):
            upcoming, upcoming_is_major = majors[m_idx + 1], True
    if upcoming and datetime.fromisoformat(upcoming["start"]) - as_of > UPCOMING_WINDOW:
        upcoming, upcoming_is_major = None, False

    lagna_sign = int(chart.lagna_lon // 30)
    planet_house = {
        name: (int(data["lon"] // 30) - lagna_sign) % 12 + 1
        for name, data in chart.positions.items() if "lon" in data
    }

    transit = chart.transit_context()
    gochara = transit["gochara_analysis"]
    transit_house = {
        planet: gochara["planets"][planet]["house_from_lagna"]
        for planet in ("Jupiter", "Saturn") if planet in gochara["planets"]
    }
    active_rules = {rule["id"] for rule in gochara.get("active_rules", [])}
    sade = gochara.get("sade_sati") or {}

    yogas = [
        y for y in chart.yogas().get("active", [])
        if not y.get("category", "").startswith(("Caution", "Nabhasa"))
        and y.get("implementation", "computed") == "computed"
    ]

    return Facts(
        lagna_sign=lagna_sign,
        planet_house=planet_house,
        md=md, ad=ad,
        upcoming=upcoming, upcoming_is_major=upcoming_is_major,
        transit_house=transit_house,
        sade_sati_phase=sade.get("phase") if sade.get("active") else None,
        ashtama_shani="gochara_ashtama_shani" in active_rules,
        kantaka_shani="gochara_kantaka_shani" in active_rules,
        guru_bala="gochara_guru_moon_support" in active_rules,
        yogas=yogas,
        life=life or {},
    )


# ── How a planet touches a topic ──────────────────────────────────────────────

def _rules(facts: Facts, planet: str) -> list[int]:
    return [h for h in range(1, 13) if SIGN_LORDS[(facts.lagna_sign + h - 1) % 12] == planet]


def _link(facts: Facts, planet: str, topic: Topic, mode: Mode) -> tuple[int, str] | None:
    """(strength, plain reason) when `planet` bears on `topic`, else None.

    Ruling a topic house is the strongest tie, sitting in one next, being
    the topic's natural signifier last."""
    ruled = [h for h in _rules(facts, planet) if h in topic.houses]
    if ruled:
        h = ruled[0]
        if mode == "practitioner":
            return 3, f"{planet} rules your {_ordinal(h)} house"
        return 3, f"{planet} looks after your {HOUSE_WORDS[h]}"
    sits = facts.planet_house.get(planet)
    if sits in topic.houses:
        if mode == "practitioner":
            return 2, f"{planet} sits in your {_ordinal(sits)} house"
        return 2, f"{planet} sits in your house of {HOUSE_WORDS[sits]}"
    if planet in topic.karakas:
        return 1, f"{planet} is {topic.karaka_note.get(planet, 'a natural signifier here')}"
    return None


# ── Topic wording that depends on what the reader told us ─────────────────────

def _phrase(topic: Topic, life: dict) -> str:
    if topic.id == "marriage":
        status = life.get("relationship_status")
        if status == "married":
            return "my marriage"
        if status in ("single", "engaged") or life.get("planning_marriage"):
            return "my marriage plans"
    if topic.id == "child" and life.get("has_children") is True:
        return "my children"
    if topic.id == "work":
        status = life.get("employment_status")
        if status == "student":
            return "my studies and career"
        if status == "retired":
            return "my work and projects"
        if status == "unemployed" or life.get("looking_for_work"):
            return "finding work"
    return topic.phrase


def _period_word(level: str, mode: Mode) -> str:
    if mode == "practitioner":
        return {"md": "mahadasha", "ad": "antardasha"}[level]
    return {"md": "major period", "ad": "sub-period"}[level]


def _s(prompt: str, because: str, weight: int) -> dict:
    return {"prompt": prompt, "because": because, "_w": weight}


# ── Builders ─────────────────────────────────────────────────────────────────

def _dasha_items(facts: Facts, topic: Topic, phrase: str, mode: Mode) -> list[dict]:
    items = []
    ad, md = facts.ad["lord"], facts.md["lord"]
    ad_link = _link(facts, ad, topic, mode)
    md_link = _link(facts, md, topic, mode) if md != ad else None
    if ad_link:
        w, why = ad_link
        items.append(_s(
            f"What does my {ad} {_period_word('ad', 'balanced')} bring for {phrase}?",
            f"{why} · {ad} {_period_word('ad', mode)} runs until {_month(facts.ad['end'])}",
            10 + w,
        ))
    if md_link:
        w, why = md_link
        items.append(_s(
            f"How is my {md} major period shaping {phrase}?",
            f"{why} · {md} {_period_word('md', mode)} runs until {_month(facts.md['end'])}",
            8 + w,
        ))
    up = facts.upcoming
    if up:
        up_link = _link(facts, up["lord"], topic, mode)
        if up_link:
            w, why = up_link
            level = "md" if facts.upcoming_is_major else "ad"
            kind = "major period" if facts.upcoming_is_major else "sub-period"
            items.append(_s(
                f"What changes for {phrase} when my {up['lord']} {kind} starts in {_month(up['start'])}?",
                f"{why} · {up['lord']} {_period_word(level, mode)} begins {_month(up['start'])}",
                9 + w + (2 if facts.upcoming_is_major else 0),
            ))
    return items


def _transit_items(facts: Facts, topic: Topic, phrase: str, mode: Mode) -> list[dict]:
    items = []
    jup = facts.transit_house.get("Jupiter")
    sat = facts.transit_house.get("Saturn")

    def where(h: int) -> str:
        return f"your {_ordinal(h)} house from the Lagna" if mode == "practitioner" else f"your house of {HOUSE_WORDS[h]}"

    if jup in topic.houses:
        items.append(_s(
            f"Jupiter is now passing the part of my chart for {phrase}. What can I make the most of?",
            f"Jupiter is passing {where(jup)} now",
            11,
        ))
    if sat in topic.houses:
        items.append(_s(
            f"Saturn is now passing the part of my chart for {phrase}. Where do I need patience?",
            f"Saturn is passing {where(sat)} now",
            11,
        ))

    # Saturn from the Moon: felt most in work, money and energy.
    if topic.id in ("work", "money", "health"):
        if facts.sade_sati_phase:
            phase = {"first": "first", "second": "middle", "third": "last"}[facts.sade_sati_phase]
            items.append(_s(
                f"How do I handle {phrase} calmly during my Sade Sati?",
                f"Sade Sati is running, {phase} phase" if mode != "guided"
                else f"Saturn's 7½-year Sade Sati is running ({phase} phase)",
                12,
            ))
        elif facts.ashtama_shani:
            items.append(_s(
                f"Saturn is 8th from my Moon. How do I keep {phrase} steady?",
                "Ashtama Shani is running" if mode == "practitioner" else "Saturn is 8th from your Moon sign (Ashtama Shani)",
                12,
            ))
        elif facts.kantaka_shani and topic.id in ("work", "health"):
            items.append(_s(
                f"Saturn is 4th from my Moon. How do I keep {phrase} on track?",
                "Kantaka Shani is running" if mode == "practitioner" else "Saturn is 4th from your Moon sign (Kantaka Shani)",
                10,
            ))

    # Jupiter supporting the Moon sign helps growth topics.
    if facts.guru_bala and topic.id in ("marriage", "child", "money"):
        items.append(_s(
            f"Jupiter is supporting my Moon sign this year. What does this mean for {phrase}?",
            "Guru bala from the Moon is active" if mode == "practitioner" else "Jupiter is in a helpful place from your Moon sign",
            9,
        ))
    return items


def _yoga_label(yoga: dict) -> str:
    name = yoga["name"]
    return "a Raja Yoga" if name.startswith("Raja Yoga") else name


def _yoga_items(facts: Facts, topic: Topic, phrase: str, mode: Mode) -> list[dict]:
    running = {facts.md["lord"], facts.ad["lord"]}
    items = []
    for yoga in facts.yogas:
        planets = set(yoga.get("planets") or [])
        if not planets & running or len(planets) > 3:
            continue
        if not any(word in yoga.get("category", "") for word in topic.yoga_words):
            continue
        lord = facts.ad["lord"] if facts.ad["lord"] in planets else facts.md["lord"]
        label = _yoga_label(yoga)
        items.append(_s(
            f"My {lord} period wakes up {label} in my chart. What does it bring for {phrase}?",
            f"{yoga['name']}: {', '.join(yoga.get('triggers') or [yoga.get('rule', '')])}"
            if mode == "practitioner" else f"{label} formed by {' and '.join(sorted(planets))}, and {lord} is running now",
            9,
        ))
        break
    return items


def _fallback_items(facts: Facts, topic: Topic, phrase: str, mode: Mode) -> list[dict]:
    """Still this chart's: the running periods, without a claimed link."""
    ad, md = facts.ad["lord"], facts.md["lord"]
    running = f"{ad} {_period_word('ad', mode)} in the {md} {_period_word('md', mode)}" if ad != md \
        else f"{md} {_period_word('md', mode)}"
    items = [
        _s(f"Which months in the coming year look better for {phrase}?",
           f"Read from your {running} and the year's transits", 3),
        _s(f"What should I keep in mind about {phrase} during my {ad} sub-period?",
           f"{running} is running until {_month(facts.ad['end'])}", 2),
    ]
    if topic.id == "health":
        items.append(_s("What simple daily routine suits my health right now?",
                        f"Read from your {running}", 1))
    elif topic.id == "child" and facts.life.get("has_children") is True:
        items.append(_s("How can I best support my children this year?",
                        "Read from your 5th house and Jupiter" if mode == "practitioner"
                        else "Read from your house of children and Jupiter", 1))
    elif topic.id == "child":
        items.append(_s("What does my chart say about children?",
                        "Read from your 5th house and Jupiter" if mode == "practitioner"
                        else "Read from your house of children and Jupiter", 1))
    elif topic.id == "marriage":
        items.append(_s("What does my chart say about my partner's nature?",
                        "Read from your 7th house and Venus" if mode == "practitioner"
                        else "Read from your house of marriage and Venus", 1))
    elif topic.id == "money":
        items.append(_s("Where does money come to me most easily, by my chart?",
                        "Read from your 2nd and 11th houses" if mode == "practitioner"
                        else "Read from your houses of savings and income", 1))
    else:
        items.append(_s("What kind of work suits my chart best?",
                        "Read from your 10th house" if mode == "practitioner"
                        else "Read from your house of career", 1))
    return items


def _pick(items: list[dict], n: int) -> list[dict]:
    seen, out = set(), []
    for item in sorted(items, key=lambda s: -s["_w"]):
        if item["prompt"] in seen:
            continue
        seen.add(item["prompt"])
        out.append({"prompt": item["prompt"], "because": item["because"]})
        if len(out) == n:
            break
    return out


def topic_suggestions(facts: Facts, topic_id: str, mode: Mode = "balanced") -> list[dict]:
    topic = TOPICS[topic_id]
    phrase = _phrase(topic, facts.life)
    items = (_dasha_items(facts, topic, phrase, mode)
             + _transit_items(facts, topic, phrase, mode)
             + _yoga_items(facts, topic, phrase, mode))
    picked = _pick(items, PER_TOPIC)
    if len(picked) < 3:
        picked = _pick(items + _fallback_items(facts, topic, phrase, mode), 3)
    return picked


def general_suggestions(facts: Facts, mode: Mode = "balanced") -> list[dict]:
    """The list shown before any chip is chosen: the strongest few across
    every topic, at most one per topic. Each names its topic, so the answer
    pipeline never has to ask which area the reader meant."""
    best: list[dict] = []
    for topic in TOPICS.values():
        phrase = _phrase(topic, facts.life)
        items = (_dasha_items(facts, topic, phrase, mode) + _transit_items(facts, topic, phrase, mode)
                 + _yoga_items(facts, topic, phrase, mode))
        if items:
            best.append(max(items, key=lambda s: s["_w"]))
    picked = _pick(best, GENERAL)
    if len(picked) < GENERAL:
        picked = _pick(best + _fallback_items(facts, TOPICS["work"], TOPICS["work"].phrase, mode), GENERAL)
    return picked


def ask_suggestions(chart, *, mode: Mode = "balanced", as_of: datetime | None = None,
                    life: dict | None = None) -> dict:
    facts = facts_from_chart(chart, as_of=as_of, life=life)
    return {
        "as_of": (as_of or datetime.now(chart.moment.dt_local.tzinfo)).isoformat(),
        "topics": [{"id": t.id, "label": t.label} for t in TOPICS.values()],
        "general": general_suggestions(facts, mode),
        "by_topic": {t: topic_suggestions(facts, t, mode) for t in TOPICS},
    }
