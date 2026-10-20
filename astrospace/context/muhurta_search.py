"""Real muhurta windows for Ask, when a question asks for a good time.

Ask's bundle otherwise only knows today's panchang, so "when should I take
delivery of my car next week?" could be answered only in general terms. When
the question is plainly a muhurta question, this runs the same finder the
Muhurta screen uses (core/vedic/muhurta.py) over the next two weeks, at the
birth place, and hands the agent the exact slots to offer. Two weeks matches
the tester horizon, so Ask never shows more than the Muhurta screen would.

Refer-out topics never reach here: the orchestrator's safety check runs first,
and the finder raises for them anyway, which this treats as "no section".
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..core.vedic import muhurta
from ..core.vedic.nakshatra import nakshatra_of
from ..core.vedic.positions import sign_index

SEARCH_DAYS = 14

_MUHURTA_QUESTION = re.compile(
    r"\b(muhurt\w*|muhurat\w*|mahurat\w*|shubh (time|day|date|muhurat)|auspicious"
    r"|(good|best|right|lucky|favourable|favorable) (time|day|date|hour)s?"
    r"( to| for)?)\b"
)


def is_muhurta_question(question: str | None) -> bool:
    return bool(question and _MUHURTA_QUESTION.search(question.lower()))


def muhurta_section(chart, question: str | None, *, today=None) -> dict | None:
    """The bundle's `muhurta_search` section, or None for other questions."""
    if not is_muhurta_question(question):
        return None
    moment = chart.moment
    tz = moment.tz_str
    start = today or datetime.now(ZoneInfo(tz)).date()
    moon = chart.positions["Moon"]["lon"]
    try:
        out = muhurta.find(
            "general", start, start + timedelta(days=SEARCH_DAYS - 1),
            janma_nakshatra_index=nakshatra_of(moon)["index"],
            janma_rashi_index=sign_index(moon),
            ghatak_moon_sign=sign_index(moon),
            intent=question,
            lat=moment.lat, lng=moment.lng, tz_str=tz, limit=5,
        )
    except (muhurta.ExcludedGoalError, ValueError):
        return None
    return {
        "purpose": out["rules_label"],
        "place": f"{chart.city or 'birth place'} (birth place), times in {tz}",
        "searched": f"{out['date_from']} to {out['date_to']}",
        "slots": [
            {
                "date": r["date"], "weekday": r["vara"],
                "from": r["start"], "to": r["end"],
                "standing": r["label"],
                "special": r["badges"],
                "why": r["why"]["supports"][:3],
                "care": r["why"]["against"][:2],
            }
            for r in out["results"]
        ],
        "notes": out["notes"],
        "observance_note": out["observance_note"],
        "how_to_use": (
            "Offer these exact slots, best first, in plain words. Do not invent "
            "other times. Say the times are for the birth place and that the "
            "Muhurta screen can search another city or more dates."
        ),
    }
