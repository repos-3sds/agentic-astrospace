"""Queue an alert shortly before each named timing window of the day.

Every window the Today screen lists gets one: Rahu Kalam, Yamaganda, Gulika
Kalam, Durmuhurta, Varjyam, Bhadra, and the auspicious ones (Brahma Muhurta,
Abhijit, Amrit Kalam, Godhuli). Choghadiya and hora blocks are not included;
they tile the whole day and would mean a push every hour.

The copy says a window is coming and when it runs, never what will go wrong
in it (settings/notifications.component.html: "never fear-based").
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from ..core.cities import lookup_city
from ..db import crud, crud_mobile as cm
from ..db.models import NotificationJob, PushToken
from .morning_brief import _primary_kundli, _zone

CATEGORY = "window_alert"
DEFAULT_LEAD_MINUTES = 45
# The worker sends what is due once every 15 minutes, so a job lands up to
# 15 minutes after its time: a "45 minutes before" alert arrived 32 minutes
# before (regression 2026-10-17, N-d). Queuing half a run early centres
# arrival on the lead time; the copy names the clock time, so early is safe.
HALF_WORKER_CADENCE = timedelta(minutes=7, seconds=30)


def windows_for(kundli, day: date, tz_name: str, city: str | None = None,
                nation: str | None = None) -> list[dict]:
    """The day's named windows at the reader's timing place, as Today shows them."""
    from ..context.timing_place import resolve_timing_place
    from ..core.vedic.panchanga_day import daily_panchanga

    place = resolve_timing_place(kundli, tz_name, city, nation)
    payload = daily_panchanga(
        day.year, day.month, day.day, city=place.city, nation=place.nation,
        lat=place.lat, lng=place.lng, tz_str=place.tz_str,
        display_tz_str=place.viewer_tz or place.tz_str,
    )
    windows = payload["windows"]
    return windows.get("inauspicious", []) + windows.get("auspicious", [])


def _in_quiet_hours(local: datetime, start, end) -> bool:
    if start is None or end is None:
        return False
    t = local.time()
    return start <= t < end if start <= end else (t >= start or t < end)


def _copy(window: dict) -> tuple[str, str]:
    name = window["name"]
    title = f"{name} at {window['start']}"
    body = f"{name} runs {window['start']}–{window['end']}."
    if window.get("note"):
        body += f" {window['note']}."
    return title, body


def schedule_window_alerts(db: Session, now: datetime | None = None,
                           windows: Callable[..., list[dict]] = windows_for,
                           days_ahead: int = 1) -> list[NotificationJob]:
    """Idempotent per window: re-running returns the existing jobs.

    Covers today and tomorrow in each reader's zone, so a window just after
    midnight (Brahma Muhurta, night Durmuhurta) is queued before it arrives.
    Windows that have already begun are skipped; one whose lead time has
    passed but has not started is sent now. `windows` is injectable so tests
    do not need the ephemeris.
    """
    now_utc = (now or datetime.utcnow()).replace(tzinfo=ZoneInfo("UTC"))
    user_ids = {
        row.user_id for row in db.query(PushToken.user_id).filter(PushToken.revoked_at.is_(None))
    }
    jobs: list[NotificationJob] = []
    for user_id in sorted(user_ids):
        prefs = cm.get_notification_preferences(db, user_id).get(CATEGORY, {})
        if not prefs.get("enabled", True):
            continue
        kundli = _primary_kundli(db, user_id)
        if kundli is None:
            continue
        tokens = cm.list_active_push_tokens(db, user_id)
        tz_name = prefs.get("timezone") or next((t.timezone for t in tokens if t.timezone), None)
        # A city chosen in Settings is the place Today shows; alerts follow it.
        place = _chosen_place(db, user_id)
        place_kwargs = {"city": place[0], "nation": place[1]} if place else {}
        zone = _zone(place[2] if place else tz_name)
        wanted: set[str] = set()
        complete = True
        lead = timedelta(minutes=prefs.get("lead_time_minutes") or DEFAULT_LEAD_MINUTES)
        today = now_utc.astimezone(zone).date()

        for offset in range(days_ahead + 1):
            day = today + timedelta(days=offset)
            try:
                day_windows = windows(kundli, day, zone.key, **place_kwargs)
            except Exception:  # an unknown city must not stall everyone else
                complete = False
                continue
            for window in day_windows:
                start = datetime.fromisoformat(window["start_iso"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=zone)
                if start <= now_utc:
                    continue
                send_at = max(start - lead - HALF_WORKER_CADENCE, now_utc)
                if _in_quiet_hours(send_at.astimezone(zone),
                                   prefs.get("quiet_hours_start"), prefs.get("quiet_hours_end")):
                    continue
                title, body = _copy(window)
                dedupe_key = f"{CATEGORY}:{user_id}:{window['name']}:{window['start_iso']}"
                wanted.add(dedupe_key)
                jobs.append(cm.schedule_notification(
                    db, user_id, CATEGORY,
                    send_at.astimezone(ZoneInfo("UTC")).replace(tzinfo=None), title,
                    dedupe_key=dedupe_key,
                    kundli_id=kundli.id, timezone=zone.key, body=body, deep_link="/m/today",
                    payload={"window": window["name"], "kind": window.get("kind"),
                             "start": window["start_iso"], "end": window["end_iso"]},
                ))
        if complete:  # a day that failed to compute proves nothing stale
            _drop_superseded(db, user_id, wanted)
    return jobs


def _chosen_place(db: Session, user_id: str) -> tuple[str, str, str] | None:
    """(city, nation, timezone) when the reader picked a panchanga place."""
    settings = crud.get_user_settings(db, user_id)
    place = settings.panchanga_place if settings and settings.timezone_mode == "panchanga_place" else None
    if not place or not place.get("city"):
        return None
    geo = lookup_city(place["city"], place.get("nation") or "IN")
    return (place["city"], place.get("nation") or "IN", geo[2]) if geo else None


def _drop_superseded(db: Session, user_id: str, wanted: set[str]) -> None:
    """Cancel queued window alerts this run no longer produces.

    After a city or timezone change the old place's windows were still queued
    and went out on the old clock beside the new ones (retest of build 487).
    A pending job for a window that has already begun is dropped too: it
    would arrive late."""
    stale = (
        db.query(NotificationJob)
        .filter(NotificationJob.user_id == user_id, NotificationJob.category == CATEGORY,
                NotificationJob.status == "pending")
        .all()
    )
    for job in stale:
        if job.dedupe_key not in wanted:
            cm.cancel_notification(db, job.id, "place changed")
