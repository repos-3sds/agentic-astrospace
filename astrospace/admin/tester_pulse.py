"""Tester pulse: who has signed in, and who has asked, for the admin console.

Built for the friends-and-family test, where the question each morning is
whether an invite became a sign-in and a sign-in became a question. Pure
over rows the admin client already reads, so it is tested without a
database. Days are India days, which is when the testers live.

Each reader is named by their own birth chart (relation "self") when they
have made one, since that is the name they gave Siddha; otherwise by their
sign-in name. What anyone asked is never included, only when.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

TEAM_ZONE = ZoneInfo("Asia/Kolkata")
DAYS = 14


def _at(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        moment = value
    else:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00").replace(" ", "T", 1))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _day(moment: datetime | None) -> date | None:
    return moment.astimezone(TEAM_ZONE).date() if moment else None


def _iso(moment: datetime | None) -> str | None:
    return moment.astimezone(timezone.utc).isoformat() if moment else None


def tester_pulse(auth_users: list[dict], kundlis: list[dict], threads: list[dict],
                 questions: list[dict], now: datetime | None = None) -> dict:
    """`questions` are ask_messages rows with role 'user' (thread_id, created_at)."""
    now = _at(now) or datetime.now(timezone.utc)
    today = _day(now)

    charts = Counter()
    own_name: dict[str, str] = {}
    for row in kundlis:
        if row.get("archived_at") or row.get("kind", "profile") != "profile":
            continue
        charts[row["user_id"]] += 1
        if (row.get("relation") or "").lower() == "self" and row.get("name"):
            own_name.setdefault(row["user_id"], row["name"])

    owner = {row["id"]: row["user_id"] for row in threads}
    asked = Counter()
    last_asked: dict[str, datetime] = {}
    first_asked: dict[str, datetime] = {}
    per_day_questions = Counter()
    for row in questions:
        user_id = owner.get(row["thread_id"])
        moment = _at(row.get("created_at"))
        per_day_questions[_day(moment)] += 1
        if not user_id or not moment:
            continue
        asked[user_id] += 1
        if user_id not in last_asked or moment > last_asked[user_id]:
            last_asked[user_id] = moment
        if user_id not in first_asked or moment < first_asked[user_id]:
            first_asked[user_id] = moment

    people = []
    per_day_accounts = Counter()
    for row in auth_users:
        user_id = row["id"]
        created = _at(row.get("created_at"))
        last_sign_in = _at(row.get("last_sign_in_at"))
        per_day_accounts[_day(created)] += 1
        meta = row.get("user_metadata") or {}
        people.append({
            "id": user_id,
            "name": own_name.get(user_id) or meta.get("full_name") or meta.get("name"),
            "email": row.get("email"),
            "created_at": _iso(created),
            "last_sign_in_at": _iso(last_sign_in),
            "joined_today": _day(created) == today,
            "active_today": _day(last_sign_in) == today or _day(last_asked.get(user_id)) == today,
            "charts": charts[user_id],
            "questions": asked[user_id],
            "last_question_at": _iso(last_asked.get(user_id)),
        })
    people.sort(key=lambda p: p["last_sign_in_at"] or p["created_at"] or "", reverse=True)

    days = [today - timedelta(days=offset) for offset in range(DAYS - 1, -1, -1)]
    return {
        "as_of": _iso(now),
        "summary": {
            "accounts": len(people),
            "joined_today": sum(p["joined_today"] for p in people),
            "active_today": sum(p["active_today"] for p in people),
            "asked_ever": sum(1 for p in people if p["questions"]),
            "first_question_today": sum(1 for moment in first_asked.values() if _day(moment) == today),
            "questions_today": per_day_questions[today],
            "never_asked": sum(1 for p in people if not p["questions"]),
        },
        "daily": [
            {"day": day.isoformat(), "new_accounts": per_day_accounts[day],
             "questions": per_day_questions[day]}
            for day in days
        ],
        "people": people,
    }
