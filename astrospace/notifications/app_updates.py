"""Ask readers on an old build of the app to update (docs/app_updates.md).

Three parts, all driven by one row per platform in app_releases:

- `version_status` answers the app's check on every launch: is this build
  current, is an update waiting (a sheet the reader can put off for a day),
  or is it too old to open (a full-screen "please update" and nothing else)?
- `schedule_update_reminders` queues a push to each phone still on an older
  build: the first a few hours after the build is released (so the store has
  it), then after 2 days, 4 more, and weekly, at most five per build. A build
  that must be updated is reminded every two days, at most eight times.
- The worker sends each reminder only to the phones still behind
  (`token_ids` and `below_build` in the job's payload), so a reader who
  updated one phone is not told again on it.

Nothing blocks a build unless Hawk has set `required_build` or
`block_after_days` for its platform; until then everything here is a gentle
reminder. The copy never says what is new, so a build can be announced in
its own time (group readings wait for Diwali) without the reminder giving
it away.

APP_UPDATE_REMINDERS=off stops the pushes everywhere; the in-app check
still answers.
"""
from __future__ import annotations

import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..db import crud_mobile as cm
from ..db.models import AppRelease, NotificationJob, PushToken
from .email_jobs import _utc
from .morning_brief import _zone

CATEGORY = "app_update"
PLATFORMS = ("android", "ios")
PROVIDER = {"android": "fcm", "ios": "apns"}

# Builds up to this one never send their build number with the push token,
# so a token without one is on this build or older. Builds are numbered by
# commit count on main; this was main's count before update reminders.
LAST_SILENT_BUILD = 633

# Where "Update" goes when app_releases has no update_url. Play's listing
# shows "Update" to closed testers; TestFlight is where every iPhone tester
# has the app until it is on the App Store.
DEFAULT_UPDATE_URL = {
    "android": "https://play.google.com/store/apps/details?id=app.asksiddha.mobile",
    "ios": "itms-beta://beta.itunes.apple.com/v1/app/6827191709",
}

# Play reviews a closed-testing release before testers can get it, which
# usually takes minutes and sometimes hours.
FIRST_REMINDER_AFTER = timedelta(hours=6)
# Days between reminders, the first counted from FIRST_REMINDER_AFTER.
GAPS_DAYS = (0, 2, 4, 7, 7)
REQUIRED_GAP_DAYS = 2
REQUIRED_MAX = 8
# A phone not opened in this long has probably gone (a reinstall, a new
# phone); it is not nagged.
ACTIVE_WITHIN = timedelta(days=60)
# Pushes go out in the reader's day, never at night.
DAY_START = time(10, 0)
DAY_END = time(20, 0)
DEEP_LINK = "/m/today"
# Same reading as clock_change: with every switch off the reader has said
# "no notifications", and this is a notification.
PUSH_SWITCHES = ("morning_brief", "window_alert", "festival_reminder",
                 "remedy_reminder", "daily_subhashita")

UTC = ZoneInfo("UTC")


def enabled(environ=None) -> bool:
    env = os.environ if environ is None else environ
    return (env.get("APP_UPDATE_REMINDERS") or "on").strip().lower() not in ("0", "off", "false", "no")


# ── The release rows ──────────────────────────────────────────────────────────

def get_release(db: Session, platform: str) -> AppRelease | None:
    return db.get(AppRelease, platform)


_UNSET = object()


def set_release(db: Session, platform: str, *, latest_build=_UNSET, required_build=_UNSET,
                block_after_days=_UNSET, update_url=_UNSET, by: str | None = None,
                now: datetime | None = None) -> AppRelease:
    """Change only the fields given; None clears one. Moving latest_build
    restarts the reminder count, since the reminders are per build."""
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform {platform!r}")
    now = now or datetime.utcnow()
    row = db.get(AppRelease, platform) or AppRelease(platform=platform)
    if latest_build is not _UNSET and latest_build != row.latest_build:
        row.latest_build = latest_build
        row.latest_set_at = now if latest_build is not None else None
    if required_build is not _UNSET:
        row.required_build = required_build
    if block_after_days is not _UNSET:
        row.block_after_days = block_after_days
    if update_url is not _UNSET:
        row.update_url = update_url
    row.updated_by = by
    row.updated_at = now
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def release_dict(row: AppRelease | None, platform: str) -> dict:
    return {
        "platform": platform,
        "latest_build": row.latest_build if row else None,
        "latest_set_at": row.latest_set_at.isoformat() if row and row.latest_set_at else None,
        "required_build": row.required_build if row else None,
        "block_after_days": row.block_after_days if row else None,
        "update_url": update_url(row, platform),
    }


def update_url(row: AppRelease | None, platform: str) -> str:
    return (row.update_url if row and row.update_url else None) or DEFAULT_UPDATE_URL[platform]


# ── What the app is told on launch ────────────────────────────────────────────

def is_blocked(row: AppRelease | None, build: int | None, now: datetime | None = None) -> bool:
    """Too old to open: below required_build, or below latest_build once it
    has been out block_after_days."""
    if row is None or build is None:
        return False
    if row.required_build and build < row.required_build:
        return True
    if (row.block_after_days is not None and row.latest_build and row.latest_set_at
            and build < row.latest_build):
        return (now or datetime.utcnow()) >= row.latest_set_at + timedelta(days=row.block_after_days)
    return False


def is_behind(row: AppRelease | None, build: int | None) -> bool:
    """Older than the build readers can install. A token with no build is
    from before this feature, so behind any build after LAST_SILENT_BUILD."""
    if row is None or not row.latest_build:
        return False
    if build is None:
        return row.latest_build > LAST_SILENT_BUILD
    return build < row.latest_build


def version_status(row: AppRelease | None, platform: str, build: int,
                   now: datetime | None = None) -> dict:
    if is_blocked(row, build, now):
        status = "update_required"
    elif is_behind(row, build):
        status = "update_available"
    else:
        status = "current"
    return {
        "platform": platform,
        "build": build,
        "status": status,
        "latest_build": row.latest_build if row else None,
        "required_build": row.required_build if row else None,
        "update_url": update_url(row, platform),
    }


# ── Reminder pushes ───────────────────────────────────────────────────────────

def copy_for(platform: str, required: bool) -> tuple[str, str]:
    """(title, body): what to do and where, never what is new."""
    store = "Google Play" if platform == "android" else "TestFlight"
    if required:
        return ("Please update Siddha",
                f"This version of Siddha has stopped working. Update it from {store} "
                "to carry on. Your profiles and notes stay as they are.")
    return ("A new version of Siddha is ready",
            f"Update from {store} when you have a minute. Your profiles and notes stay as they are.")


def _wants_push(prefs: dict) -> bool:
    if not prefs.get(CATEGORY, {}).get("enabled", True):
        return False
    return any(prefs.get(cat, {}).get("enabled") for cat in PUSH_SWITCHES)


def _in_the_day(when: datetime, zone: ZoneInfo) -> datetime:
    """`when`, moved to the next 10:00 local if it falls outside 10:00-20:00."""
    local = when.astimezone(zone)
    if DAY_START <= local.time() < DAY_END:
        return when
    day = local.date() if local.time() < DAY_START else local.date() + timedelta(days=1)
    return datetime.combine(day, DAY_START, tzinfo=zone).astimezone(UTC)


def _key_prefix(user_id: str, platform: str, build: int) -> str:
    return f"{CATEGORY}:{user_id}:{platform}:{build}:"


def _behind_tokens(tokens: list[PushToken], row: AppRelease) -> list[PushToken]:
    """This reader's phones still behind. A token with no build is skipped
    when a phone of theirs on this platform already reported a current
    build more recently: that is an old registration of the same phone."""
    current = [t for t in tokens if t.app_build is not None and not is_behind(row, t.app_build)]
    newest_current = max((t.last_seen_at or datetime.min for t in current), default=None)
    behind = []
    for token in tokens:
        if not is_behind(row, token.app_build):
            continue
        if token.app_build is None and newest_current and (token.last_seen_at or datetime.min) <= newest_current:
            continue
        behind.append(token)
    return behind


def schedule_update_reminders(db: Session, now: datetime | None = None,
                              environ=None) -> list[NotificationJob]:
    """Idempotent: each reminder has its own dedupe key, and the next is
    only queued once its gap after the last has passed."""
    if not enabled(environ):
        return []
    now = now or datetime.utcnow()
    now_utc = now.replace(tzinfo=UTC)
    jobs: list[NotificationJob] = []
    for platform in PLATFORMS:
        row = get_release(db, platform)
        if row is None or not row.latest_build or not row.latest_set_at:
            continue
        first_at = row.latest_set_at + FIRST_REMINDER_AFTER
        if now < first_at:
            continue
        tokens = (
            db.query(PushToken)
            .filter(PushToken.provider == PROVIDER[platform],
                    PushToken.revoked_at.is_(None),
                    PushToken.last_seen_at >= now - ACTIVE_WITHIN)
            .all()
        )
        by_user: dict[str, list[PushToken]] = {}
        for token in tokens:
            by_user.setdefault(token.user_id, []).append(token)
        for user_id in sorted(by_user):
            behind = _behind_tokens(by_user[user_id], row)
            if not behind:
                continue
            job = _next_reminder(db, user_id, platform, row, behind, now, now_utc, first_at)
            if job is not None:
                jobs.append(job)
    return jobs


def _next_reminder(db: Session, user_id: str, platform: str, row: AppRelease,
                   behind: list[PushToken], now: datetime, now_utc: datetime,
                   first_at: datetime) -> NotificationJob | None:
    prefix = _key_prefix(user_id, platform, row.latest_build)
    earlier = (
        db.query(NotificationJob)
        .filter(NotificationJob.user_id == user_id, NotificationJob.category == CATEGORY)
        .all()
    )
    # A newer build replaces the reminders for the one before it.
    for job in earlier:
        if job.status == "pending" and not (job.dedupe_key or "").startswith(prefix) \
                and (job.payload or {}).get("platform") == platform:
            cm.cancel_notification(db, job.id, reason="a newer build was released")
    mine = sorted((j for j in earlier if (j.dedupe_key or "").startswith(prefix)),
                  key=lambda j: j.scheduled_for)
    if any(j.status in ("pending", "processing") for j in mine):
        return None
    required = any(is_blocked(row, _build_of(t), now) for t in behind)
    count = len(mine)
    if required:
        if count >= REQUIRED_MAX:
            return None
        due = first_at if count == 0 else mine[-1].scheduled_for + timedelta(days=REQUIRED_GAP_DAYS)
    else:
        if count >= len(GAPS_DAYS):
            return None
        due = first_at if count == 0 else mine[-1].scheduled_for + timedelta(days=GAPS_DAYS[count])
    if now < due:
        return None
    if not _wants_push(cm.get_notification_preferences(db, user_id)):
        return None
    zone = _zone(_phone_zone(behind))
    when = _in_the_day(now_utc, zone)
    title, body = copy_for(platform, required)
    return cm.schedule_notification(
        db, user_id, CATEGORY, _utc(when), title,
        dedupe_key=f"{prefix}{count + 1}",
        timezone=zone.key, body=body, deep_link=DEEP_LINK,
        payload={"platform": platform, "below_build": row.latest_build,
                 "token_ids": [t.id for t in behind], "required": required,
                 "update_url": update_url(row, platform)},
    )


def _build_of(token: PushToken) -> int:
    """A token with no build is at most LAST_SILENT_BUILD; read it as that,
    the kindest guess."""
    return token.app_build if token.app_build is not None else LAST_SILENT_BUILD


def _phone_zone(tokens: list[PushToken]) -> str | None:
    for token in sorted(tokens, key=lambda t: t.last_seen_at or datetime.min, reverse=True):
        if token.timezone:
            return token.timezone
    return None


def tokens_for_job(tokens: list[PushToken], payload: dict | None) -> list[PushToken]:
    """The worker's filter: only the phones a reminder was meant for, and
    only those still behind when it goes out (the reader may have updated
    since it was queued). Jobs without these keys reach every phone, as before."""
    payload = payload or {}
    ids = payload.get("token_ids")
    if ids is not None:
        wanted = set(ids)
        tokens = [t for t in tokens if t.id in wanted]
    below = payload.get("below_build")
    if below is not None:
        tokens = [t for t in tokens if _build_of(t) < below]
    return tokens
