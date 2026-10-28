"""Tell testers what is new when a build reaches them.

Two moments, both started by GitHub Actions (docs/release_announcements.md):

- Draft, on every upload to Play internal testing (ship.yml). The merged
  pull requests since the build testers have now are turned into a few plain
  lines, and the team gets a preview email: the reader email exactly as it
  would go out, the Play "What's new" text, and the WhatsApp channel post and
  broadcast message ready to paste. Nothing goes to readers.
- Announce, when a build is released to closed testing (release.yml, only on
  Hawk's word). The previewed lines are emailed to every reader who has
  "tips and reminders" email on, under that category, so consent, the
  unsubscribe link and the send-time consent check are the ones they already
  agreed to. The team gets the WhatsApp texts again to post.

WhatsApp is text for a person to paste: Channels and Business-app broadcast
lists have no API. Sending from code needs the WhatsApp Business Platform
through a provider, which waits for public launch.

Copy rules: plain English for Indian readers, no prices, no website or /buy
link, never the internal test link. Model output is checked against those
rules and replaced by tidied pull-request titles when it breaks one.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import NotificationJob
from .email import EmailContent
from .email_jobs import _content_dict, _tz_for, _utc
from .morning_brief import _zone
from .owner_alerts import CATEGORY as TEAM_CATEGORY, CHANNEL as TEAM_CHANNEL

log = logging.getLogger("astrospace.notifications")

# "What's new" rides on the tips category: readers turned it on for "a
# feature worth trying", and this is that.
CATEGORY = "tips_email"
STORE_URL = "https://play.google.com/store/apps/details?id=app.asksiddha.mobile"
REPLY_TO = "asksiddha@3senses.design"
MAX_NOTES = 5
MAX_NOTE_CHARS = 120
PLAY_NOTES_LIMIT = 500
# Readers' local hours in which a release email may go out at once; outside
# them it waits for 10:00.
SEND_FROM, SEND_UNTIL, SEND_LATER_AT = time(9, 0), time(20, 0), time(10, 0)
# Job owner for team emails that are about no reader.
TEAM_USER = "team"

# Files that change what a tester sees in the app. A pull request that only
# touched CI, scripts, docs, tests, migrations or the website is left out.
_USER_FACING = re.compile(r"^(ui/src/|ui/android/app/src/|astrospace/|main\.py$)")
_NOT_USER_FACING = re.compile(r"\.spec\.ts$|^ui/src/environments/|^astrospace/admin/")

_PR_NUMBER = re.compile(r"\s*\(#\d+\)\s*$")
_PREFIX = re.compile(r"^(feat|fix|chore|refactor|perf|style|build|ci|docs|test)(\([^)]*\))?!?:\s*", re.I)

# Anything a note must never say. Prices and the website are Play billing
# rules; links and test-track words keep the internal link out of public posts.
_FORBIDDEN = re.compile(
    r"https?://|www\.|asksiddha\.app|/buy|₹|\$|\brs\.?\s?\d|\brupees?\b|\bprice|\bpay\b|\bpaid\b|"
    r"\bdiscount|\bsubscri|internal test|\bAAB\b|\bAPI\b|\bCI\b|pull request|\bPR\b|#\d+",
    re.I,
)


def is_user_facing(files: list[str]) -> bool:
    return any(_USER_FACING.search(f) and not _NOT_USER_FACING.search(f) for f in files)


def tidy_title(title: str) -> str:
    title = _PREFIX.sub("", _PR_NUMBER.sub("", title.strip()))
    return (title[:1].upper() + title[1:]).rstrip(".") if title else ""


def _acceptable(note: str) -> bool:
    return 0 < len(note) <= MAX_NOTE_CHARS and not _FORBIDDEN.search(note)


def fallback_notes(titles: list[str]) -> list[str]:
    notes = [t for t in (tidy_title(t) for t in titles) if _acceptable(t)]
    return notes[:MAX_NOTES]


WRITER_PROMPT = """You write the "What's new" lines for Siddha, a Vedic astrology app, when a new
version reaches testers. Below are the titles of the changes, as the developers wrote them.

Write at most {limit} lines a tester would care about, most noticeable first. Each line:
- one short sentence, under 15 words, saying what they can now do or what works better;
- everyday words, no developer words (API, server, worker, refactor, cache, CI, PR, bug ID);
- no prices, money, plans, payments, website addresses or links of any kind;
- no fear, no promises about results, no exclamation marks.
Merge related changes into one line. Leave out changes a tester would not notice.
If nothing would be noticed, return an empty list.

Return JSON only: {{"notes": ["...", "..."]}}

Changes:
{changes}
{style}"""


def write_notes(titles: list[str], *, generate=None) -> tuple[list[str], str]:
    """(notes, "model"|"titles"). `generate(prompt) -> str` is the model call;
    by default Gemini. Any failure, or any line that breaks a copy rule,
    falls back to the tidied titles, so a draft always comes out."""
    titles = [t for t in titles if t.strip()]
    if not titles:
        return [], "titles"
    from ..agents.style import PLAIN_INDIAN_ENGLISH

    prompt = WRITER_PROMPT.format(
        limit=MAX_NOTES, changes="\n".join(f"- {tidy_title(t)}" for t in titles),
        style=PLAIN_INDIAN_ENGLISH,
    )
    try:
        raw = (generate or _gemini)(prompt)
        start, end = raw.find("{"), raw.rfind("}")
        notes = json.loads(raw[start:end + 1])["notes"]
        notes = [str(n).strip().rstrip(".") for n in notes if str(n).strip()]
        if notes and len(notes) <= MAX_NOTES and all(_acceptable(n) for n in notes):
            return notes, "model"
        log.warning("release notes from the model broke a copy rule; using titles")
    except Exception:
        log.exception("release notes model call failed; using titles")
    return fallback_notes(titles), "titles"


def _gemini(prompt: str) -> str:
    from google.genai import types

    from ..agents.base import DEFAULT_GEMINI_MODEL, gemini_client

    response = gemini_client().models.generate_content(
        model=DEFAULT_GEMINI_MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3),
    )
    return response.text or ""


# ── What each channel says ────────────────────────────────────────────────────

def play_notes(notes: list[str]) -> str:
    text = "\n".join(f"• {n}." for n in notes) or "Small fixes and improvements."
    return text[:PLAY_NOTES_LIMIT]


def whatsapp_channel_post(notes: list[str]) -> str:
    lines = ["*New in Siddha*", ""]
    lines += [f"• {n}." for n in notes] or ["• Small fixes and improvements."]
    lines += [
        "",
        f"Update Siddha from the Play Store: {STORE_URL}",
        "",
        f"Something not right, or an idea? Write to {REPLY_TO}",
    ]
    return "\n".join(lines)


def whatsapp_broadcast(notes: list[str]) -> str:
    lines = ["Namaste 🙏 A new version of Siddha is ready for you.", ""]
    lines += [f"• {n}." for n in notes] or ["• Small fixes and improvements."]
    lines += [
        "",
        "Open the Play Store and tap Update on Siddha. If you don't see it yet, try again in an hour.",
        "",
        "Reply here if anything feels wrong. It really helps.",
    ]
    return "\n".join(lines)


def reader_email(notes: list[str]) -> EmailContent:
    items = [[n + ".", ""] for n in notes] or [["Small fixes and improvements.", ""]]
    return EmailContent(
        subject="New in Siddha: " + (notes[0] if notes else "small fixes and improvements"),
        preview="A new version of Siddha is ready. Here is what changed.",
        eyebrow="What's new",
        heading="A new version is ready",
        intro=("Thank you for testing Siddha. The new version is on its way to your phone "
               "through the Play Store. Here is what changed."),
        blocks=[
            {"type": "items", "heading": "In this version", "tone": "good", "items": items},
            {"type": "text", "heading": "Getting it",
             "body": ("Open the Play Store, find Siddha and tap Update. If it isn't there yet, "
                      "try again in an hour; Play sends new versions out a little at a time.")},
            {"type": "callout", "heading": "Tell us",
             "body": ("Something not working, or an idea? Reply to this email. "
                      "A person reads every reply.")},
        ],
        button_label="Open Siddha",
        button_path="/m/today",
    )


def announcement(version_code: int, notes: list[str]) -> dict:
    return {
        "version_code": version_code,
        "notes": notes,
        "play_notes": play_notes(notes),
        "whatsapp_channel": whatsapp_channel_post(notes),
        "whatsapp_broadcast": whatsapp_broadcast(notes),
        "email_subject": reader_email(notes).subject,
    }


# ── Queuing ───────────────────────────────────────────────────────────────────

def _send_time(local_now: datetime) -> datetime:
    if SEND_FROM <= local_now.time() < SEND_UNTIL:
        return local_now
    day = local_now.date() + (timedelta(days=1) if local_now.time() >= SEND_UNTIL else timedelta())
    return datetime.combine(day, SEND_LATER_AT, tzinfo=local_now.tzinfo)


def queue_reader_emails(db: Session, version_code: int, notes: list[str],
                        now: datetime | None = None) -> int:
    """One email per consenting reader per version, however often this runs."""
    content = reader_email(notes)
    queued = 0
    for recipient in cm.email_subscribers(db, CATEGORY):
        key = f"release_email:{recipient.user_id}:{version_code}"
        if db.query(NotificationJob.id).filter(NotificationJob.dedupe_key == key).first():
            continue
        zone = _zone(_tz_for(db, recipient))
        local_now = now.astimezone(zone) if now else datetime.now(zone)
        cm.schedule_notification(
            db, recipient.user_id, CATEGORY, _utc(_send_time(local_now)), content.subject,
            dedupe_key=key, body=content.preview, deep_link=content.button_path,
            payload={"channel": "email", "content": _content_dict(content), "kind": "release"},
            timezone=zone.key,
        )
        queued += 1
    return queued


def team_email(version_code: int, ann: dict, *, stage: str, readers: int | None = None) -> EmailContent:
    """The team's copy: what readers get, and the WhatsApp texts to paste."""
    if stage == "draft":
        subject = f"Build {version_code} is going to internal testing: what's new"
        intro = (f"Build {version_code} is on its way to internal testing. Nothing has gone to testers. "
                 f"Say \u201cbroadcast update\u201d and readers with tips emails on get the "
                 f"email below, and these WhatsApp texts go to the channel and broadcast list.")
    else:
        subject = f"Build {version_code} released to testers: post on WhatsApp"
        intro = (f"Build {version_code} is on closed testing. {readers or 0} reader emails are "
                 f"queued. Paste the texts below into the Siddha channel and the testers' "
                 f"broadcast list.")
    reader = reader_email(ann["notes"])
    return EmailContent(
        subject=subject,
        preview=intro[:120],
        eyebrow="For the team",
        heading=f"What's new in build {version_code}",
        intro=intro,
        blocks=[
            {"type": "items", "heading": f"Reader email: {reader.subject}", "tone": "good",
             "items": reader.blocks[0]["items"]},
            {"type": "callout", "heading": "WhatsApp channel post", "body": ann["whatsapp_channel"]},
            {"type": "callout", "heading": "WhatsApp broadcast to testers", "body": ann["whatsapp_broadcast"]},
            {"type": "callout", "heading": "Play Store “What's new”", "body": ann["play_notes"]},
        ],
        button_label="Open Admin",
        button_path="/admin",
    )


def queue_team_email(db: Session, version_code: int, ann: dict, *, stage: str,
                     readers: int | None = None, now: datetime | None = None) -> NotificationJob:
    """Delivered by the worker to OWNER_ALERT_EMAILS, like the team alerts."""
    content = team_email(version_code, ann, stage=stage, readers=readers)
    when = (now.astimezone(ZoneInfo("UTC")).replace(tzinfo=None) if now else datetime.utcnow())
    return cm.schedule_notification(
        db, TEAM_USER, TEAM_CATEGORY, when, content.subject,
        dedupe_key=f"release_{stage}:{version_code}", body=content.preview,
        payload={"channel": TEAM_CHANNEL, "to": [], "kind": f"release_{stage}",
                 "content": _content_dict(content)},
    )
