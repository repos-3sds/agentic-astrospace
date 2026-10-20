"""The second set of reader emails: outlooks, lessons and tips.

Scheduled by `email_jobs.schedule_emails` beside the daily and festival
emails, on the same queue and with the same consent check at send time.

- Weekly outlook (`weekly_email`): the week ahead, Monday 07:00 local.
- Monthly outlook (`monthly_email`): the month ahead, on the 1st at 07:30.
  Both are written by the period-reading agent with a plain-words style
  note, from the evening before until 11:00 on the day, a few per run so a
  worker run stays inside its budget. A draft that crosses a boundary twice
  is not sent; the next run tries again.
- Learn your chart (`lessons_email`): eight short lessons, one every three
  days at 08:00, each built from the reader's own chart with no model call.
- Tips (`tips_email`): a note after two weeks away, with what is coming up
  at their place (once a month at most); and once, a week after sign-up, an
  invitation to try compatibility if they have only their own profile.

Copy follows the app's rules: plain words, no fear, no verdicts. Astrology
terms appear only where a lesson is teaching that term.
"""
from __future__ import annotations

import logging
import re
import time as _time
from datetime import date, datetime, time, timedelta
from typing import Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import crud, crud_mobile as cm
from ..db.models import NotificationJob, NotificationPreference, PushToken, UserDevice
from .email import EmailContent
from .morning_brief import _primary_kundli, _zone

log = logging.getLogger("astrospace.notifications")

WEEKLY_SEND_TIME = time(7, 0)
MONTHLY_SEND_TIME = time(7, 30)
LESSON_SEND_TIME = time(8, 0)
TIPS_SEND_TIME = time(10, 0)
# Outlooks are written from this time the evening before, and not after this
# time on the day: a week's outlook at teatime on Monday is not worth sending.
OUTLOOK_WRITE_FROM = time(18, 0)
OUTLOOK_GIVE_UP_AT = time(11, 0)
MAX_OUTLOOKS_PER_RUN = 6
OUTLOOK_BUDGET_SECONDS = 240
LESSON_GAP_DAYS = 3
AWAY_DAYS = 14
AWAY_REPEAT_DAYS = 30
COMPAT_AFTER_DAYS = 7


def _utc(local: datetime) -> datetime:
    from zoneinfo import ZoneInfo

    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def _queue(db, user_id, category, when_utc, content, dedupe_key, **fields):
    from .email_jobs import _queue as queue

    return queue(db, user_id, category, when_utc, content, dedupe_key, **fields)


def _exists(db: Session, dedupe_key: str) -> bool:
    return db.query(NotificationJob.id).filter(NotificationJob.dedupe_key == dedupe_key).first() is not None


def _local_now(db: Session, recipient, now: datetime | None):
    from .email_jobs import _tz_for

    zone = _zone(_tz_for(db, recipient))
    return zone, (now.astimezone(zone) if now else datetime.now(zone))


def _chart(kundli):
    from ..core.vedic.chart import VedicChart

    return VedicChart(kundli.name, kundli.birth_year, kundli.birth_month, kundli.birth_day,
                      kundli.birth_hour, kundli.birth_minute, kundli.birth_city, kundli.birth_nation)


# ── Weekly and monthly outlooks ───────────────────────────────────────────────

OUTLOOK_SECTIONS = ("The theme", "Love and people", "Work and money", "Energy and rest",
                    "Something to try", "Why")

OUTLOOK_STYLE = (
    "\n\nThis reading goes out by email to someone who may know nothing about astrology. "
    "Write it in plain, warm words. In every section but the last, use no Sanskrit terms, "
    "no house numbers, no degrees, and no names of signs, stars or planetary periods. "
    "Use exactly these markdown headers, in this order: "
    + ", ".join(f"## {s}" for s in OUTLOOK_SECTIONS)
    + ". Keep each section to two or three short sentences, and the whole reading under 300 "
    "words. 'Something to try' is one small, concrete thing to do. 'Why' may name the planets "
    "and the period at work, in one or two sentences a beginner can follow."
)

_OUTLOOK = {
    "weekly": {"category": "weekly_email", "send": WEEKLY_SEND_TIME, "eyebrow": "Your week ahead",
               "button": "Open your calendar", "path": "/m/calendar"},
    "monthly": {"category": "monthly_email", "send": MONTHLY_SEND_TIME, "eyebrow": "Your month ahead",
                "button": "Open your calendar", "path": "/m/calendar"},
}


def _clean(text: str) -> str:
    text = re.sub(r"\*\*|__|`", "", text)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if re.match(r"^[-*•]\s+", line):
            line = "• " + re.sub(r"^[-*•]\s+", "", line)
        lines.append(line)
    text = "\n".join(lines)
    # The email renders a blank line as a new paragraph and a single newline
    # as a space, so each bullet gets its own paragraph.
    text = re.sub(r"\n+(?=• )", "\n\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def outlook_sections(markdown: str) -> list[tuple[str, str]]:
    """[(heading, body), ...] from the agent's markdown, in order. Text
    before the first header becomes an untitled section."""
    sections: list[tuple[str, str]] = []
    heading, body = "", []
    for line in markdown.splitlines():
        match = re.match(r"^\s*#{1,6}\s+(.*)$", line)
        if match:
            if heading or "".join(body).strip():
                sections.append((heading, _clean("\n".join(body))))
            heading, body = _clean(match.group(1)).rstrip(":"), []
        else:
            body.append(line)
    if heading or "".join(body).strip():
        sections.append((heading, _clean("\n".join(body))))
    return [(h, b) for h, b in sections if b]


def outlook_window(period: str, day: date) -> tuple[date, date]:
    if period == "weekly":
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6)
    start = day.replace(day=1)
    following = (start + timedelta(days=32)).replace(day=1)
    return start, following - timedelta(days=1)


def outlook_content(period: str, markdown: str, start: date, end: date) -> EmailContent:
    spec = _OUTLOOK[period]
    sections = outlook_sections(markdown)
    by_name = {h.lower(): b for h, b in sections}
    theme = by_name.pop("the theme", None) or (sections[0][1] if sections else "")
    blocks: list[dict] = []
    for heading, body in sections:
        key = heading.lower()
        if key == "the theme" or body == theme:
            continue
        if key == "something to try":
            blocks.append({"type": "callout", "heading": "Something to try", "body": body})
        elif key == "why":
            blocks.append({"type": "text", "heading": "Why this outlook", "body": body})
        else:
            blocks.append({"type": "text", "heading": heading or None, "body": body})
    first_line = re.split(r"(?<=[.!?])\s", theme, maxsplit=1)[0] if theme else ""
    if period == "weekly":
        span = (f"{start.day} {start:%B} to {end.day} {end:%B}" if start.month != end.month
                else f"{start.day} to {end.day} {end:%B}")
        subject = f"Your week ahead, {span}"
    else:
        subject = f"Your month ahead: {start:%B}"
    return EmailContent(
        subject=subject,
        preview=first_line[:140],
        eyebrow=spec["eyebrow"],
        heading=subject,
        intro=theme,
        blocks=blocks,
        button_label=spec["button"],
        button_path=spec["path"],
        note="Written for you from your birth chart and the sky this "
             + ("week." if period == "weekly" else "month."),
    )


def write_outlook(kundli, period: str, as_of: datetime) -> str | None:
    """The agent's plain-words reading, or None when it could not write a
    clean one (the next run tries again)."""
    from ..agents.period_agent import PeriodAgent

    content, crossed = PeriodAgent(_chart(kundli)).generate_reading(period, now=as_of, style=OUTLOOK_STYLE)
    if crossed or not content.strip() or content.strip() == "Unable to generate a response.":
        log.warning("outlook %s for kundli %s not sent (crossed=%s)", period, kundli.id, crossed)
        return None
    return content


def _send_day(period: str, local_now: datetime) -> date | None:
    """The day this period's email goes out, if now is inside its writing
    window (the evening before through the late morning of the day)."""
    today = local_now.date()
    tomorrow = today + timedelta(days=1)
    if period == "weekly":
        is_send_day = lambda d: d.weekday() == 0  # noqa: E731
    else:
        is_send_day = lambda d: d.day == 1  # noqa: E731
    if is_send_day(today) and local_now.time() < OUTLOOK_GIVE_UP_AT:
        return today
    if is_send_day(tomorrow) and local_now.time() >= OUTLOOK_WRITE_FROM:
        return tomorrow
    return None


def schedule_outlook_emails(db: Session, now: datetime | None = None,
                            write: Callable[[object, str, datetime], str | None] = write_outlook,
                            max_per_run: int = MAX_OUTLOOKS_PER_RUN,
                            budget_seconds: float = OUTLOOK_BUDGET_SECONDS) -> dict:
    summary = {"weekly": 0, "monthly": 0, "deferred": 0, "failed": 0}
    started = _time.monotonic()
    written = 0
    for period, spec in _OUTLOOK.items():
        for recipient in cm.email_subscribers(db, spec["category"]):
            user_id = recipient.user_id
            zone, local_now = _local_now(db, recipient, now)
            day = _send_day(period, local_now)
            if day is None:
                continue
            start, end = outlook_window(period, day)
            dedupe_key = f"{spec['category']}:{user_id}:{start.isoformat()}"
            if _exists(db, dedupe_key):
                continue
            kundli = _primary_kundli(db, user_id)
            if kundli is None:
                continue
            if written >= max_per_run or _time.monotonic() - started > budget_seconds:
                summary["deferred"] += 1
                continue
            written += 1
            try:
                markdown = write(kundli, period, datetime.combine(day, time(9, 0), tzinfo=zone))
            except Exception:
                log.exception("%s outlook for %s failed", period, user_id)
                db.rollback()
                markdown = None
            if not markdown:
                summary["failed"] += 1
                continue
            when = _utc(datetime.combine(day, spec["send"], tzinfo=zone))
            _queue(db, user_id, spec["category"], when, outlook_content(period, markdown, start, end),
                   dedupe_key, kundli_id=kundli.id, timezone=zone.key)
            summary[period] += 1
    return summary


# ── Learn your chart ──────────────────────────────────────────────────────────

SIGN_PLAIN = {
    "Aries": "direct, quick to start, happiest with something to fight for",
    "Taurus": "steady, loyal and fond of comfort, slow to change course",
    "Gemini": "curious, talkative and quick, always connecting ideas and people",
    "Cancer": "caring and protective, guided by feeling and close to family",
    "Leo": "warm, generous and proud, at ease when leading",
    "Virgo": "careful, useful and precise, quietly improving things",
    "Libra": "fair, sociable and drawn to balance and beauty",
    "Scorpio": "intense, private and determined, slow to trust and loyal once it does",
    "Sagittarius": "hopeful, frank and restless for meaning and new horizons",
    "Capricorn": "patient, practical and ambitious over the long run",
    "Aquarius": "independent and idealistic, thinking about the group and the future",
    "Pisces": "gentle, imaginative and sensitive to what others feel",
}

PLANET_PLAIN = {
    "Sun": "your sense of self, confidence and purpose",
    "Moon": "your mind, moods and what makes you feel safe",
    "Mars": "your energy, courage and drive",
    "Mercury": "how you think, speak, learn and trade",
    "Jupiter": "growth, wisdom, teachers and good fortune",
    "Venus": "love, beauty, pleasure and what you value",
    "Saturn": "patience, work, duty and lessons that take time",
    "Rahu": "hunger for the new and unfamiliar, and restless ambition",
    "Ketu": "letting go, inner life and what you already know deeply",
}

HOUSE_PLAIN = (
    ("1", "You: body, temperament, how you meet the world"),
    ("2", "Money you keep, family, food and speech"),
    ("3", "Effort, courage, siblings, short trips"),
    ("4", "Home, mother, inner peace, property"),
    ("5", "Children, creativity, study, romance"),
    ("6", "Daily work, health habits, rivals and debts"),
    ("7", "Partner, marriage, close one-to-one bonds"),
    ("8", "Change, shared money, what is hidden"),
    ("9", "Luck, teachers, faith, father, long journeys"),
    ("10", "Career, reputation, what you are known for"),
    ("11", "Gains, friends, hopes and networks"),
    ("12", "Rest, spending, letting go, faraway places"),
)

LESSON_COUNT = 8


def chart_facts(kundli) -> dict:
    chart = _chart(kundli)
    lagna = chart.lagna_details()
    planets = chart.planet_details()
    current = chart.dashas().get("current") or {}

    def period(level):
        row = current.get(level) or {}
        return {"lord": row.get("lord"), "end": (row.get("end") or "")[:10]} if row.get("lord") else None

    return {
        "lagna": lagna["sign"],
        "sun": planets["Sun"]["sign"],
        "moon": planets["Moon"]["sign"],
        "nakshatra": planets["Moon"]["nakshatra"],
        "nakshatra_lord": planets["Moon"].get("nakshatra_lord"),
        "mahadasha": period("mahadasha"),
        "antardasha": period("antardasha"),
        "time_exact": (kundli.birth_time_accuracy or "exact") == "exact",
    }


def _month_year(iso: str) -> str:
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d:%B %Y}"


def lesson_content(n: int, facts: dict) -> EmailContent:
    """Lesson `n` (1 to 8), filled in from the reader's own chart."""
    def sign_line(sign):
        return f"{sign}: {SIGN_PLAIN.get(sign, '')}".rstrip(": ")

    blocks: list[dict] = []
    path, button = "/m/chart", "Open your chart"
    if n == 1:
        title = "What a birth chart is"
        intro = ("A birth chart is a map of the sky at the moment and place you were born: where the "
                 "Sun, the Moon and the planets stood, and which part of the sky was rising in the east.")
        blocks += [
            {"type": "text", "heading": "Why yours may look different",
             "body": ("Siddha follows Vedic astrology, which measures the signs against the fixed stars. "
                      "Most magazine horoscopes measure them against the seasons instead. The two have "
                      "drifted about 24 degrees apart over the centuries, so many people find their Vedic "
                      "Sun sign is one sign earlier than the one they grew up with.")},
            {"type": "callout", "heading": "In your chart",
             "body": f"Your Sun is in {facts['sun']} in the Vedic system."},
            {"type": "text", "heading": "Over the next few weeks",
             "body": ("Seven more short lessons follow, one every few days: your rising sign, your Moon, "
                      "your birth star, the twelve parts of life, the nine planets, the periods of your "
                      "life, and what yogas and doshas really mean.")},
        ]
    elif n == 2:
        title = "Your rising sign"
        intro = ("The rising sign (lagna in Sanskrit) is the sign that was coming up over the eastern "
                 "horizon when you were born. Vedic astrology treats it as the starting point of the whole "
                 "chart: it describes your body, your temperament and how you meet the world.")
        blocks.append({"type": "callout", "heading": "Yours", "body": sign_line(facts["lagna"]) + "."})
        if not facts["time_exact"]:
            blocks.append({"type": "text", "heading": "A note on your birth time",
                           "body": ("The rising sign changes about every two hours, and your birth time is "
                                    "marked as not exact, so treat this one lightly. If you find your exact "
                                    "time, add it in the app and your chart will update.")})
        blocks.append({"type": "text", "heading": "How it is used",
                       "body": ("Every part of life in your chart is counted from this sign, so it shapes "
                                "which planets matter most for you. That is why two people with the same "
                                "Sun sign can have very different charts.")})
    elif n == 3:
        title = "Your Moon sign"
        intro = ("In Vedic astrology the Moon matters as much as the Sun, often more. It stands for the mind: "
                 "your moods, your instincts and what helps you feel settled.")
        blocks.append({"type": "callout", "heading": "Yours", "body": sign_line(facts["moon"]) + "."})
        blocks.append({"type": "text", "heading": "Why it matters day to day",
                       "body": ("The Moon moves through a sign in about two and a half days, much faster "
                                "than anything else. Your daily reading looks at where it is each day "
                                "compared with where it was when you were born. That is a large part of why "
                                "some days feel easy and others take more care.")})
        path, button = "/m/today", "Open today"
    elif n == 4:
        title = "Your birth star"
        intro = ("The sky is also divided into 27 smaller star groups called nakshatras. The one the Moon "
                 "was in when you were born is your birth star. Many families still use it to choose a "
                 "name's first sound and to pick good days.")
        lord = facts.get("nakshatra_lord")
        body = f"{facts['nakshatra']}."
        if lord and lord in PLANET_PLAIN:
            body += f" It is linked with {lord}, which stands for {PLANET_PLAIN[lord]}."
        blocks.append({"type": "callout", "heading": "Yours", "body": body})
        blocks.append({"type": "text", "heading": "Where you will see it",
                       "body": ("Your birth star decides the order of the life periods in lesson seven, and "
                                "it is one of the things compared when two charts are matched.")})
    elif n == 5:
        title = "The twelve parts of life"
        intro = ("A chart is split into twelve houses, each standing for one part of life. Counting starts "
                 f"from your rising sign, {facts['lagna']}, which is your first house.")
        blocks.append({"type": "rows", "heading": "The houses", "rows": [list(r) for r in HOUSE_PLAIN]})
        blocks.append({"type": "text", "heading": "Reading them",
                       "body": ("A planet sitting in a house brings its nature into that part of life. "
                                "An empty house is not a problem; it simply means that part of life is "
                                "read through the planet that rules its sign.")})
    elif n == 6:
        title = "The nine planets"
        intro = ("Vedic astrology works with nine: the Sun, the Moon, five planets you can see, and two "
                 "points where the Moon's path crosses the Sun's, called Rahu and Ketu. Each one stands "
                 "for a kind of energy in your life.")
        blocks.append({"type": "rows", "heading": "What each stands for",
                       "rows": [[p, d[0].upper() + d[1:]] for p, d in PLANET_PLAIN.items()]})
        blocks.append({"type": "text", "heading": "Good and hard are not fixed",
                       "body": ("No planet is simply good or bad. Saturn brings delays and also lasting "
                                "results; Jupiter brings growth and sometimes too much of a good thing.")})
    elif n == 7:
        title = "The chapters of your life"
        intro = ("Vedic astrology divides life into long periods, each led by one planet. This system is "
                 "called the dasha. While a planet's period runs, the parts of life it stands for come "
                 "forward.")
        maha, antar = facts.get("mahadasha"), facts.get("antardasha")
        if maha:
            body = (f"You are in a {maha['lord']} period until {_month_year(maha['end'])}. "
                    f"{maha['lord']} stands for {PLANET_PLAIN.get(maha['lord'], 'its own themes')}.")
            if antar:
                body += (f" Inside it, a shorter {antar['lord']} chapter runs until "
                         f"{_month_year(antar['end'])}, bringing {PLANET_PLAIN.get(antar['lord'], 'its themes')} "
                         "into focus.")
            blocks.append({"type": "callout", "heading": "Where you are now", "body": body})
        blocks.append({"type": "text", "heading": "How to use it",
                       "body": ("A period is a season, not a sentence. It tells you what is likely to ask for "
                                "your attention, so you can plan around it.")})
        path, button = "/m/chart/periods", "See your life periods"
    else:
        title = "Yogas and doshas"
        intro = ("A yoga is a pattern of planets that points to a strength. A dosha is a pattern that "
                 "points to something to be careful with. You will see both in the app.")
        blocks += [
            {"type": "callout", "heading": "A flag, not a verdict",
             "body": ("A dosha never means something bad will happen. Many charts have one, and the "
                      "tradition itself lists the conditions that soften or cancel each of them. Treat it "
                      "as a note to pay attention, and be wary of anyone who uses one to frighten you.")},
            {"type": "text", "heading": "About remedies",
             "body": ("Traditional remedies are simple practices: a prayer, a fast, an act of giving, a "
                      "habit. They are never something you have to pay someone to remove.")},
            {"type": "text", "heading": "That's the series",
             "body": ("Thanks for reading along. Your daily reading and the Ask tab will keep using what "
                      "you have learned here.")},
        ]
        path, button = "/m/chart/yogas", "See your yogas and doshas"
    subject = f"Learn your chart, {n} of {LESSON_COUNT}: {title}"
    return EmailContent(
        subject=subject,
        preview=intro[:140],
        eyebrow=f"Learn your chart · {n} of {LESSON_COUNT}",
        heading=title,
        intro=intro,
        blocks=blocks,
        button_label=button,
        button_path=path,
    )


def _turned_on_at(db: Session, user_id: str, category: str) -> datetime | None:
    row = (db.query(NotificationPreference.updated_at)
           .filter(NotificationPreference.user_id == user_id, NotificationPreference.category == category)
           .first())
    return row[0] if row else None


def _next_at(day: date, at: time, zone, local_now: datetime) -> datetime:
    """`at` today if it has not passed, else tomorrow, as naive UTC."""
    when = datetime.combine(day, at, tzinfo=zone)
    if when <= local_now:
        when += timedelta(days=1)
    return _utc(when)


def schedule_lesson_emails(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    jobs: list[NotificationJob] = []
    now_utc = _utc(now) if now else datetime.utcnow()
    for recipient in cm.email_subscribers(db, "lessons_email"):
        user_id = recipient.user_id
        sent = (db.query(NotificationJob)
                .filter(NotificationJob.user_id == user_id, NotificationJob.category == "lessons_email")
                .order_by(NotificationJob.scheduled_for.desc())
                .all())
        n = len(sent) + 1
        if n > LESSON_COUNT:
            continue
        if sent and sent[0].scheduled_for > now_utc - timedelta(days=LESSON_GAP_DAYS):
            continue
        if not sent:
            # A day after turning lessons on, so the first one does not land
            # beside the welcome email.
            since = _turned_on_at(db, user_id, "lessons_email")
            if since and since > now_utc - timedelta(days=1):
                continue
        dedupe_key = f"lessons_email:{user_id}:{n}"
        if _exists(db, dedupe_key):
            continue
        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        try:
            content = lesson_content(n, chart_facts(kundli))
        except Exception:
            log.exception("lesson %s for %s failed", n, user_id)
            db.rollback()
            continue
        zone, local_now = _local_now(db, recipient, now)
        when = _next_at(local_now.date(), LESSON_SEND_TIME, zone, local_now)
        jobs.append(_queue(db, user_id, "lessons_email", when, content, dedupe_key,
                           kundli_id=kundli.id, timezone=zone.key))
    return jobs


# ── Tips: back after a while, and compatibility ───────────────────────────────

def last_seen(db: Session, user_id: str) -> datetime | None:
    """When the reader last opened the app, from their devices and push tokens."""
    seen = [
        db.query(func.max(PushToken.last_seen_at)).filter(PushToken.user_id == user_id).scalar(),
        db.query(func.max(UserDevice.last_seen_at)).filter(UserDevice.user_id == user_id).scalar(),
    ]
    seen = [s for s in seen if s]
    return max(seen) if seen else None


def away_content(upcoming: list[list[str]], city: str) -> EmailContent:
    blocks: list[dict] = []
    if upcoming:
        blocks.append({"type": "rows", "heading": f"Coming up in {city}", "rows": upcoming})
    blocks.append({"type": "text", "heading": "Waiting in the app",
                   "body": ("Your daily reading is written fresh each morning, and the calendar shows the "
                            "good times in each day for your plans. Ask is there for any question about "
                            "your chart.")})
    return EmailContent(
        subject="What's ahead in the next two weeks",
        preview="The moon days and festivals coming up where you are.",
        eyebrow="Coming up",
        heading="The next two weeks",
        intro="Here are the days worth knowing about before they arrive, dated for where you are.",
        blocks=blocks,
        button_label="Open your calendar",
        button_path="/m/calendar",
        note="Your family or temple calendar may mark a day apart; follow theirs.",
    )


def compat_content() -> EmailContent:
    return EmailContent(
        subject="See how your chart meets someone else's",
        preview="Add a partner, friend or family member and compare your charts.",
        eyebrow="Something to try",
        heading="Compare two charts",
        intro=("Siddha can set your chart beside someone else's: a partner, a friend, a parent, a "
               "colleague. You only need their date, time and place of birth."),
        blocks=[
            {"type": "items", "heading": "What it shows", "items": [
                ["Where you naturally agree", "The temperament, habits and values you share."],
                ["Where you will need patience", "The places your rhythms differ, and how to meet them."],
                ["A score, with its reasons", "The traditional matching points, each one explained."],
            ]},
            {"type": "callout", "heading": "A score is not a verdict",
             "body": ("A low score is a list of things to talk about, not a reason to walk away. Many "
                      "happy couples have one.")},
        ],
        button_label="Try compatibility",
        button_path="/m/compat",
    )


def schedule_tip_emails(db: Session, now: datetime | None = None) -> list[NotificationJob]:
    from ..api.timing_place import resolve_timing_place
    from .email_jobs import coming_up

    jobs: list[NotificationJob] = []
    now_utc = _utc(now) if now else datetime.utcnow()
    for recipient in cm.email_subscribers(db, "tips_email"):
        user_id = recipient.user_id
        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        zone, local_now = _local_now(db, recipient, now)

        seen = last_seen(db, user_id)
        if seen and seen < now_utc - timedelta(days=AWAY_DAYS):
            recent = (db.query(NotificationJob.id)
                      .filter(NotificationJob.user_id == user_id,
                              NotificationJob.dedupe_key.like(f"away_email:{user_id}:%"),
                              NotificationJob.scheduled_for > now_utc - timedelta(days=AWAY_REPEAT_DAYS))
                      .first())
            dedupe_key = f"away_email:{user_id}:{seen.date().isoformat()}"
            if not recent and not _exists(db, dedupe_key):
                try:
                    place = resolve_timing_place(kundli, zone.key)
                    content = away_content(coming_up(local_now.date(), place.city, place.nation), place.city)
                except Exception:
                    log.exception("away email for %s failed", user_id)
                    db.rollback()
                    content = None
                if content:
                    when = _next_at(local_now.date(), TIPS_SEND_TIME, zone, local_now)
                    jobs.append(_queue(db, user_id, "tips_email", when, content, dedupe_key,
                                       timezone=zone.key))
                    continue  # one tip at a time

        dedupe_key = f"compat_invite_email:{user_id}"
        if _exists(db, dedupe_key):
            continue
        if len(crud.list_kundlis(db, user_id)) > 1:
            continue  # they have already added someone
        if kundli.created_at and kundli.created_at > now_utc - timedelta(days=COMPAT_AFTER_DAYS):
            continue
        when = _next_at(local_now.date(), TIPS_SEND_TIME, zone, local_now)
        jobs.append(_queue(db, user_id, "tips_email", when, compat_content(), dedupe_key,
                           timezone=zone.key))
    return jobs
