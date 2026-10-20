"""Plain guidance for a couple, built from a Gun Milan result.

A tester who is already married read the koota breakdown and asked the only
question that matters once the wedding is done: what can each of us, and both
of us, do to make things better? This module answers that from the same rows
``gun_milan()`` scores. It adds no new astrology: every focus area is a koota
(or safety check) the engine already scored below full, turned into everyday
habits and one gentle traditional practice.

Rules this text keeps (design_principles.md §4 and §6, agents/style.py):

* Simple English for Indian readers. Terms appear only in each item's ``why``,
  which the screen keeps under a "Why this?" fold.
* No fear. A weak koota is "where a little effort helps", never a warning.
* Practices are traditional, free and optional. Nothing here is "pay to
  remove", and nothing promises an outcome.
* No health verdicts. Nadi is described as daily rhythm, and the note sends
  health questions to a doctor.

Deterministic on purpose: it costs nothing to compute, it is the same every
time the screen opens, and it can be tested line by line.
"""
from __future__ import annotations

from .remedies import GRAHA_REMEDIES

# Areas are shown weakest first; at most this many, so the screen stays short.
MAX_FOCUS_AREAS = 4

# One entry per koota: a plain area name, what a low score means in daily
# life, what to do together, an optional shared practice, what a full score
# means, and the term explained for the "Why this?" fold.
_KOOTA_TEXT: dict[str, dict] = {
    "Varna": {
        "area": "Work and duty",
        "meaning": "You may look at duty and work in different ways.",
        "together": [
            "Share home work by who is good at what, not by fixed roles.",
            "Respect each other's pace of work, even when it differs from yours.",
        ],
        "practice": None,
        "strength": "You look at duty and work in a similar way.",
        "term": "Varna groups each Moon sign by its outlook on work and duty.",
    },
    "Vashya": {
        "area": "Give and take",
        "meaning": "One of you may lead more often, and the other may feel pulled along.",
        "together": [
            "Take turns deciding small things like food, outings and weekend plans.",
            "For big decisions, let each person speak fully before you decide.",
        ],
        "practice": None,
        "strength": "Give and take comes easily to you.",
        "term": "Vashya is about who naturally leans on whom.",
    },
    "Tara": {
        "area": "Support in hard weeks",
        "meaning": "Some weeks one of you may feel low while the other feels fine.",
        "together": [
            "When one of you is low, the other takes the lead at home that week.",
            "Avoid big decisions on a day when either of you feels low.",
        ],
        "practice": {
            "title": "Monday prayer for the Moon",
            "day": "Monday",
            "instructions": "Offer water or milk at a Shiva temple or at home, and say Om Chandraya Namah 11 times.",
        },
        "strength": "Your birth stars support each other.",
        "term": "Tara counts from one birth star (nakshatra) to the other.",
    },
    "Yoni": {
        "area": "Closeness and affection",
        "meaning": "You may show love in different ways. One may want time together, the other words or help.",
        "together": [
            "Spend 15 minutes a day together with your phones away.",
            "Once a week, ask each other: what made you feel cared for this week?",
        ],
        "practice": {
            "title": "Friday prayer together",
            "day": "Friday",
            "instructions": "Pray together to Lakshmi and Narayana, or to Radha and Krishna if that is your family custom. Offer a sweet and share it.",
        },
        "strength": "Closeness and affection come easily to you.",
        "term": "Yoni compares the animal symbols of your two birth stars. It is read for comfort and closeness with each other.",
    },
    "Graha Maitri": {
        "area": "Friendship and understanding",
        "meaning": "Your minds do not always think alike, so small misunderstandings can grow.",
        "together": [
            "Before you reply, say back in one line what you heard.",
            "Do one thing together each week that you both enjoy.",
        ],
        "practice": None,
        "strength": "Your minds understand each other. Lean on this when you talk about harder things.",
        "term": "Graha Maitri is the friendship between the planets that rule your two Moon signs.",
    },
    "Gana": {
        "area": "How you each react",
        "meaning": "Your natures are different. What feels normal to one of you can feel hard to the other.",
        "together": [
            "When a talk gets heated, stop and come back to it after an hour.",
            "Keep one quiet time each day, like evening tea, to talk about the day.",
        ],
        "practice": {
            "title": "Monday lamp for Shiva and Parvati",
            "day": "Monday",
            "instructions": "Light a lamp together in the evening and say Om Namah Shivaya 11 times.",
        },
        "strength": "Your basic natures match well.",
        "term": "Gana is your basic nature: Deva (gentle), Manushya (practical) or Rakshasa (strong-willed).",
    },
    "Bhakoot": {
        "area": "Shared plans for the home",
        "meaning": "You may want different things at the same time, so plans need more talking.",
        "together": [
            "Write down your family plans for the year, together.",
            "Talk about money and family matters at a fixed calm time, never in the middle of a fight.",
        ],
        "practice": {
            "title": "Thursday prayer to Guru",
            "day": "Thursday",
            "instructions": "Pray together to Guru (Jupiter) and say Om Gurave Namah 11 times, or visit a temple together.",
        },
        "strength": "Your plans for home and family tend to line up.",
        "term": "Bhakoot looks at how your two Moon signs sit from each other.",
    },
    "Nadi": {
        "area": "Energy and daily rhythm",
        "meaning": "Your daily rhythms may be alike, so you may both get tired or restless at the same time.",
        "together": [
            "Plan rest days so both of you are not worn out together.",
            "Eat together at fixed times when you can.",
        ],
        "practice": {
            "title": "Monday prayer together",
            "day": "Monday",
            "instructions": "Say Om Namah Shivaya together 11 times.",
        },
        "strength": "Your energy and daily rhythms balance each other.",
        "term": "Nadi compares the energy type of your two birth stars. Tradition links it with family wellbeing; for any health question, please see a doctor.",
    },
}

# The South Indian checks and Manglik, only when they are flagged.
_FLAG_TEXT: dict[str, dict] = {
    "Rajju": {
        "area": "Patience with each other",
        "meaning": "Tradition reads this before a wedding. For a couple already together, it simply asks for extra patience and care.",
        "together": ["Check in with each other every day, even for two minutes."],
        "practice": {
            "title": "Monday lamp for Shiva and Parvati",
            "day": "Monday",
            "instructions": "Light a lamp together in the evening and say Om Namah Shivaya 11 times.",
        },
        "term": "Rajju: both your birth stars fall in the same Rajju group. South Indian practice reads it as a caution, not a verdict.",
    },
    "Vedha": {
        "area": "Pulling in one direction",
        "meaning": "At times you may pull in different directions.",
        "together": ["Pick one shared goal at a time and finish it together."],
        "practice": {
            "title": "Ganesha before shared plans",
            "day": None,
            "instructions": "Before starting any shared plan, pray to Ganesha together.",
        },
        "term": "Vedha: your two birth stars are a traditional 'blocking' pair. South Indian practice reads it as a caution, not a verdict.",
    },
    "Manglik": {
        "area": "Heat in arguments",
        "meaning": "Strong energy can show as a quick temper or impatience, mostly in one of you.",
        "together": [
            "Do something active together, like a morning or evening walk.",
            "Agree that nobody shouts. Take a short break instead.",
        ],
        "practice": {
            "title": "Tuesday Hanuman Chalisa",
            "day": "Tuesday",
            "instructions": "Read the Hanuman Chalisa together on Tuesdays, or visit a Hanuman temple.",
        },
        "term": "Manglik: Mars in certain houses from the rising sign. Only one of you is Manglik. It is a traditional flag, not a verdict, and several classic exceptions cancel it.",
    },
}

_GANA_TEMPERAMENT = {
    "Deva": "You are gentle by nature and keep the peace. Say what you need early, kindly and clearly. Do not keep it inside.",
    "Manushya": "You are practical and balanced by nature. You can be the bridge: name the problem calmly and suggest one small next step.",
    "Rakshasa": "You are strong-willed and direct by nature. Before you react, take three slow breaths. Say sorry quickly after a sharp word.",
}

CLOSING_NOTE = (
    "No couple scores full marks. These are small habits and free, traditional "
    "practices, not fixes you must pay for. If things feel very hard, talk to a "
    "trusted elder or a family counsellor."
)


def _ratio(row: dict) -> float:
    return row["points"] / max(row["max"], 1)


def _score_line(row: dict) -> str:
    points = row["points"]
    shown = int(points) if float(points).is_integer() else points
    return f"{row['label']} {shown} of {row['max']}"


def _why(row: dict, term: str) -> str:
    note = (row.get("note") or "").strip()
    return f"{_score_line(row)}" + (f" ({note})" if note else "") + f". {term}"


def _person(profile: dict | None, fallback: str) -> dict:
    profile = profile or {}
    name = profile.get("name") or fallback
    lord = profile.get("rashi_lord")
    gana = profile.get("gana")
    remedy = GRAHA_REMEDIES.get(lord or "")
    practice = None
    if remedy:
        practice = {
            "title": f"{lord} mantra",
            "day": remedy["day"],
            "instructions": f"Say {remedy['mantra']} 11 times on {remedy['day']}s.",
        }
    return {
        "name": name,
        "temperament": _GANA_TEMPERAMENT.get(gana or ""),
        "practice": practice,
        "why": (
            f"{lord} rules your Moon sign ({profile.get('rashi') or 'Moon sign'}), the sign that shapes how you feel."
            if remedy else None
        ),
    }


def _focus(key: str, text: dict, why: str) -> dict:
    return {
        "key": key,
        "area": text["area"],
        "meaning": text["meaning"],
        "together": list(text["together"]),
        "practice": text["practice"],
        "why": why,
    }


def couple_guidance(result: dict) -> dict:
    """Turn a ``gun_milan()`` result into plain, practical guidance.

    Returns ``strengths`` (what already works), ``focus_areas`` (weakest
    first, each with what to do together and an optional shared practice),
    ``for_each`` (one line on temperament and one personal practice for each
    person), and a ``closing_note``.
    """
    rows = result.get("rows") or []
    strengths = [
        {"key": row["label"].lower().replace(" ", "_"), "area": _KOOTA_TEXT[row["label"]]["area"],
         "line": _KOOTA_TEXT[row["label"]]["strength"],
         "why": _why(row, _KOOTA_TEXT[row["label"]]["term"])}
        for row in sorted(rows, key=_ratio, reverse=True)
        if row["label"] in _KOOTA_TEXT and _ratio(row) >= 1
    ]

    focus: list[tuple[float, dict]] = []
    for row in rows:
        text = _KOOTA_TEXT.get(row["label"])
        if text and row["points"] < row["max"]:
            focus.append((_ratio(row), _focus(row["label"].lower().replace(" ", "_"), text, _why(row, text["term"]))))

    # Flags rank ahead of every koota: they are the checks tradition weighs most.
    flags: list[dict] = []
    extension = result.get("dashakoota_extension") or {}
    for label in extension.get("hard_blockers") or []:
        if label in _FLAG_TEXT:
            text = _FLAG_TEXT[label]
            flags.append(_focus(label.lower(), text, text["term"]))
    manglik = (result.get("safety_checks") or {}).get("manglik") or {}
    if manglik and not manglik.get("match", True):
        text = _FLAG_TEXT["Manglik"]
        flags.append(_focus("manglik", text, text["term"]))

    focus.sort(key=lambda item: item[0])
    focus_areas = (flags + [item for _, item in focus])[:MAX_FOCUS_AREAS]

    profiles = result.get("profiles") or {}
    return {
        "strengths": strengths,
        "focus_areas": focus_areas,
        "for_each": [
            _person(profiles.get("person1"), "First person"),
            _person(profiles.get("person2"), "Second person"),
        ],
        "closing_note": CLOSING_NOTE,
        "is_convention_dependent": True,
        "observance_note": result.get("observance_note"),
    }
