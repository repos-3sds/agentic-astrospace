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

from ..db import crud_mobile as cm
from ..db.models import NotificationJob, PushToken
from .morning_brief import _primary_kundli, _zone

CATEGORY = "window_alert"
DEFAULT_LEAD_MINUTES = 45


def windows_for(kundli, day: date, tz_name: str) -> list[dict]:
    """The day's named windows at the reader's timing place, as Today shows them."""
    from ..api.timing_place import resolve_timing_place
    from ..core.vedic.panchanga_day import daily_panchanga

    place = resolve_timing_place(kundli, tz_name)
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
        zone = _zone(tz_name)
        lead = timedelta(minutes=prefs.get("lead_time_minutes") or DEFAULT_LEAD_MINUTES)
        today = now_utc.astimezone(zone).date()

        for offset in range(days_ahead + 1):
            day = today + timedelta(days=offset)
            try:
                day_windows = windows(kundli, day, zone.key)
            except Exception:  # an unknown city must not stall everyone else
                continue
            for window in day_windows:
                start = datetime.fromisoformat(window["start_iso"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=zone)
                if start <= now_utc:
                    continue
                send_at = max(start - lead, now_utc)
                if _in_quiet_hours(send_at.astimezone(zone),
                                   prefs.get("quiet_hours_start"), prefs.get("quiet_hours_end")):
                    continue
                title, body = _copy(window)
                jobs.append(cm.schedule_notification(
                    db, user_id, CATEGORY,
                    send_at.astimezone(ZoneInfo("UTC")).replace(tzinfo=None), title,
                    dedupe_key=f"{CATEGORY}:{user_id}:{window['name']}:{window['start_iso']}",
                    kundli_id=kundli.id, timezone=zone.key, body=body, deep_link="/m/today",
                    payload={"window": window["name"], "kind": window.get("kind"),
                             "start": window["start_iso"], "end": window["end_iso"]},
                ))
    return jobs
