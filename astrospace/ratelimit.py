"""Per-account ceilings on model-backed work, on whether or not plans are enforced.

Commercial limits (entitlements/) count everything and block only once
ASTROSPACE_QUOTAS_ENFORCED is on. Until then nothing stopped one account from
generating without end: Ask answers, on-open daily briefs (whose cache key is
built from query parameters) and forced reading refreshes each cost a model
call. These ceilings sit far above what a reader does by hand and stay on
regardless of the plan switch.

Counted in process memory, per Cloud Run instance: the effective ceiling is the
limit times the number of instances serving one account, which is still a hard
bound. A Postgres-backed counter is the follow-up (see the Deferred backlog).
Each limit can be tuned with ASTROSPACE_LIMIT_<KIND>_PER_DAY / _PER_MINUTE.
"""
from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException

DAY = 24 * 60 * 60.0
MINUTE = 60.0


@dataclass(frozen=True)
class Limit:
    per_day: int
    per_minute: int
    message: str


# A reader asking by hand manages a few questions a minute and a few dozen a
# day; profiles are capped at 6, and each has one brief per tone/mode a day.
LIMITS: dict[str, Limit] = {
    "ask": Limit(
        per_day=60, per_minute=6,
        message="You’ve asked a lot of questions in a short time. Please wait a little and try again.",
    ),
    "brief": Limit(
        per_day=24, per_minute=6,
        message="Today’s reading is being prepared. Please try again in a little while.",
    ),
    # Reports cost no model call; this only stops one account flooding the
    # team's inbox.
    "report": Limit(
        per_day=30, per_minute=5,
        message="Thank you. You’ve sent many reports in a short time. Please try again a little later.",
    ),
    # Deep Ask runs 3 to 8 explorer rounds plus the writer, about five times
    # Fast's model calls (sweep 2026-10-29 S-1). Past this a question gets
    # today's Ask instead of a refusal; see deep_slot().
    "ask_deep": Limit(
        per_day=20, per_minute=2,
        message="Deep answers are resting for a while.",
    ),
    # One Listen in Telugu translates one screen; the app caches each.
    "translate": Limit(
        per_day=30, per_minute=5,
        message="Telugu is resting for a while; reading in English.",
    ),
    "reading": Limit(
        per_day=30, per_minute=6,
        message="You’ve made many new readings today. Please try again tomorrow.",
    ),
}

_events: dict[tuple[str, str], deque[float]] = {}
_guard = threading.Lock()


def _configured(kind: str, window: str, default: int) -> int:
    raw = os.getenv(f"ASTROSPACE_LIMIT_{kind.upper()}_{window}")
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def take(user_id: str, kind: str, *, now: float | None = None) -> bool:
    """Record one unit of `kind` for this account; False (nothing recorded)
    when either window is already full."""
    limit = LIMITS[kind]
    per_day = _configured(kind, "PER_DAY", limit.per_day)
    per_minute = _configured(kind, "PER_MINUTE", limit.per_minute)
    now = time.monotonic() if now is None else now
    with _guard:
        events = _events.setdefault((kind, user_id), deque())
        while events and now - events[0] >= DAY:
            events.popleft()
        recent = sum(1 for t in events if now - t < MINUTE)
        if len(events) >= per_day or recent >= per_minute:
            return False
        events.append(now)
        return True


_deep_in_flight: dict[str, float] = {}
# A slot whose release never came (a stream that never started) frees itself
# after this; an exploration stops at 120 s plus one model call.
DEEP_HOLD_MAX_S = 10 * 60.0


def _deep_busy(user_id: str, now: float) -> bool:
    held = _deep_in_flight.get(user_id)
    return held is not None and now - held < DEEP_HOLD_MAX_S


def deep_slot(user_id: str, *, now: float | None = None) -> Callable[[], None] | None:
    """Room for one Deep exploration: a release function, or None when the
    account already has one running or has used its "ask_deep" allowance.
    The caller answers with today's Ask on None. Release once the
    exploring thread has really ended, not when the reader stopped waiting,
    so an abandoned run still holds the slot while it spends."""
    now = time.monotonic() if now is None else now
    with _guard:
        if _deep_busy(user_id, now):
            return None
    if not take(user_id, "ask_deep", now=now):
        return None
    with _guard:
        raced = _deep_busy(user_id, now)
        if not raced:
            _deep_in_flight[user_id] = now
    if raced:  # another request took the slot between the two checks
        refund(user_id, "ask_deep")
        return None
    released = threading.Event()

    def release() -> None:
        if released.is_set():
            return
        released.set()
        with _guard:
            if _deep_in_flight.get(user_id) == now:
                del _deep_in_flight[user_id]

    return release


def refund(user_id: str, kind: str) -> None:
    """Give back the newest unit, for work that turned out to need no model
    call (a stored brief found after all, a failed write)."""
    with _guard:
        events = _events.get((kind, user_id))
        if events:
            events.pop()


def require(user_id: str, kind: str) -> None:
    """take(), or a 429 the apps show as-is."""
    if not take(user_id, kind):
        raise HTTPException(status_code=429, detail=LIMITS[kind].message)


def reset() -> None:
    """Tests only."""
    with _guard:
        _events.clear()
        _deep_in_flight.clear()
