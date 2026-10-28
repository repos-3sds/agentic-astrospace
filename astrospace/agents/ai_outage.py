"""Notice when the AI provider refuses for lack of credit, so the team hears
before the testers do.

AI Studio's prepaid credit ran out on 2026-10-17 and again on 2026-10-28
(11:01 UTC): every Ask and daily brief failed with "402 RESOURCE_EXHAUSTED
... Your prepayment credits are depleted" for five hours before anyone
noticed. Agent code calls `note_failure(exc)` where it already logs a failed
model call; the API route and the notifications worker then call
`take_credit_outage()` and queue one team email per day
(`owner_alerts.queue_ai_credit_alert`).
"""
from __future__ import annotations

import threading
from datetime import datetime

_lock = threading.Lock()
_seen_at: datetime | None = None


def is_credit_exhausted(exc: BaseException | None) -> bool:
    """True for a provider refusal over money, never for a rate limit (429
    is also RESOURCE_EXHAUSTED, and passes on its own)."""
    seen = 0
    while exc is not None and seen < 8:
        text = str(exc).lower()
        if "402" in text or "credits are depleted" in text or "prepayment credit" in text:
            return True
        if getattr(exc, "code", None) == 402 or getattr(exc, "status_code", None) == 402:
            return True
        exc = exc.__cause__ or exc.__context__
        seen += 1
    return False


def note_failure(exc: BaseException | None) -> None:
    global _seen_at
    if is_credit_exhausted(exc):
        with _lock:
            _seen_at = _seen_at or datetime.utcnow()


def take_credit_outage() -> datetime | None:
    """When this process first saw the credit refusal since the last take,
    or None. Clears it."""
    global _seen_at
    with _lock:
        seen, _seen_at = _seen_at, None
    return seen
