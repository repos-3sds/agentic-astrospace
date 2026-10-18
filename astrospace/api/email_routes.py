"""Email: the reader's own settings, the unsubscribe links, and the provider's
delivery webhook.

/api/v1/me/email            signed-in: which emails are on, and the address
/api/v1/email/unsubscribe   public, signed link from every email (GET shows a
                            confirm button; POST is the one-click unsubscribe
                            mail apps send, RFC 8058, and the button's submit)
/api/v1/email/webhooks/resend
                            public, Svix-signed: hard bounces and spam
                            complaints stop all email to that address

GET never unsubscribes: corporate link scanners open every link in an email,
and a GET that acted would unsubscribe people who never clicked.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import logging
import os
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import crud_mobile as cm, get_db
from ..db.models import EmailRecipient
from ..notifications.email import ALL_CATEGORIES, read_unsubscribe_token
from .auth import CurrentUser

router = APIRouter(tags=["email"])
log = logging.getLogger(__name__)

# How far a webhook's timestamp may drift before it is refused as a replay.
WEBHOOK_TOLERANCE_SECONDS = 300


# ── The reader's settings ─────────────────────────────────────────────────────

class EmailSettingUpdate(BaseModel):
    enabled: bool
    # The app's current IANA timezone, so emails land at the reader's morning.
    timezone: str | None = Field(None, max_length=64)


def _email_state(db: Session, user_id: str, address: str | None) -> dict:
    prefs = cm.get_notification_preferences(db, user_id)
    recipient = cm.get_email_recipient(db, user_id)
    return {
        "address": address or (recipient.email if recipient else None),
        "deliverable": bool(address) and not (recipient and recipient.suppressed_at),
        "suppressed_reason": recipient.suppressed_reason if recipient else None,
        "categories": {c: bool(prefs.get(c, {}).get("enabled")) for c in cm.EMAIL_CATEGORIES},
    }


@router.get("/api/v1/me/email")
def get_email_settings(user: CurrentUser, db: Session = Depends(get_db)):
    if user.email:
        cm.upsert_email_recipient(db, user.id, user.email)
    return _email_state(db, user.id, user.email)


@router.put("/api/v1/me/email/{category}")
def set_email_setting(category: str, payload: EmailSettingUpdate, user: CurrentUser,
                      db: Session = Depends(get_db)):
    if category not in cm.EMAIL_CATEGORIES:
        raise HTTPException(status_code=404, detail=f"Unknown email category {category!r}")
    if payload.enabled and not user.email:
        raise HTTPException(status_code=400, detail="Your account has no email address")
    if user.email:
        cm.upsert_email_recipient(db, user.id, user.email, timezone=payload.timezone)
    cm.set_notification_preference(db, user.id, category, enabled=payload.enabled,
                                   channels=["email"])
    return _email_state(db, user.id, user.email)


# ── Unsubscribe ───────────────────────────────────────────────────────────────

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} · Siddha</title>
<style>
  body {{ margin:0; background:#F6EFE4; color:#2B2118; font-family:Georgia,'Times New Roman',serif; }}
  main {{ max-width:480px; margin:48px auto; padding:0 16px; }}
  .card {{ background:#FFFDF9; border:1px solid #E6DACB; border-radius:16px; padding:28px 24px; }}
  h1 {{ font-weight:normal; font-size:26px; margin:0 0 12px; }}
  p {{ font-size:17px; line-height:1.55; margin:0 0 16px; }}
  button {{ background:#7A4E2D; color:#fff; border:0; border-radius:999px; padding:12px 24px;
           font:15px Arial,Helvetica,sans-serif; cursor:pointer; }}
  .brand {{ letter-spacing:.12em; text-transform:uppercase; color:#7A4E2D; font-size:15px; margin:0 0 16px; }}
</style></head>
<body><main><p class="brand">Siddha</p><div class="card">{body}</div></main></body></html>"""

_LABELS = {
    "daily_email": "your daily reading emails",
    "festival_email": "moon and festival day emails",
    ALL_CATEGORIES: "all emails from Siddha",
}


def _page(title: str, body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(title=html.escape(title), body=body), status_code=status)


def _invalid() -> HTMLResponse:
    return _page("Link not recognised",
                 "<h1>This link didn't work</h1><p>It may have been copied incompletely. You can "
                 "turn emails off in the app under Settings, Notifications.</p>", 400)


def _resolve(token: str | None) -> tuple[str, str] | None:
    parsed = read_unsubscribe_token(token or "")
    if not parsed:
        return None
    user_id, category = parsed
    if category != ALL_CATEGORIES and category not in cm.EMAIL_CATEGORIES:
        return None
    return user_id, category


@router.get("/api/v1/email/unsubscribe", response_class=HTMLResponse)
def unsubscribe_page(t: str | None = None):
    parsed = _resolve(t)
    if not parsed:
        return _invalid()
    label = _LABELS[parsed[1]]
    return _page(
        "Unsubscribe",
        f"<h1>Stop {html.escape(label)}?</h1>"
        f"<p>You can turn them back on any time in the app.</p>"
        f'<form method="post"><input type="hidden" name="t" value="{html.escape(t or "")}">'
        f'<button type="submit">Yes, stop them</button></form>',
    )


@router.post("/api/v1/email/unsubscribe", response_class=HTMLResponse)
async def unsubscribe(request: Request, t: str | None = None, db: Session = Depends(get_db)):
    token = t
    if not token:
        form = await request.form()
        token = form.get("t")
    parsed = _resolve(token)
    if not parsed:
        return _invalid()
    user_id, category = parsed
    # Every reader we email has a recipient row. Without one the account is
    # gone (deletion removes it), and writing preferences would bring rows
    # back for a deleted person; the page reads the same either way.
    if db.get(EmailRecipient, user_id) is not None:
        categories = cm.EMAIL_CATEGORIES if category == ALL_CATEGORIES else (category,)
        for c in categories:
            cm.set_notification_preference(db, user_id, c, enabled=False, channels=["email"])
    log.info(json.dumps({"event": "email.unsubscribed", "category": category}))
    return _page(
        "Unsubscribed",
        f"<h1>Done</h1><p>We've stopped {html.escape(_LABELS[category])}. "
        f"You can turn them back on in the app under Settings, Notifications.</p>",
    )


# ── Provider webhook ──────────────────────────────────────────────────────────

def verify_svix(secret: str, headers, body: bytes, now: float | None = None) -> bool:
    """Resend signs webhooks with Svix: HMAC-SHA256 over "id.timestamp.body",
    keyed by the base64 part of the `whsec_` secret."""
    msg_id = headers.get("svix-id")
    stamp = headers.get("svix-timestamp")
    signatures = headers.get("svix-signature") or ""
    if not (msg_id and stamp and signatures):
        return False
    try:
        if abs((now or time.time()) - int(stamp)) > WEBHOOK_TOLERANCE_SECONDS:
            return False
        key = base64.b64decode(secret.removeprefix("whsec_"))
    except (ValueError, TypeError):
        return False
    expected = base64.b64encode(
        hmac.new(key, f"{msg_id}.{stamp}.".encode() + body, hashlib.sha256).digest()
    ).decode()
    for part in signatures.split():
        version, _, sig = part.partition(",")
        if version == "v1" and hmac.compare_digest(sig, expected):
            return True
    return False


@router.post("/api/v1/email/webhooks/resend")
async def resend_webhook(request: Request, db: Session = Depends(get_db)):
    secret = (os.getenv("RESEND_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    body = await request.body()
    if not verify_svix(secret, request.headers, body):
        raise HTTPException(status_code=401, detail="Bad signature")
    try:
        event = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad JSON")
    kind = event.get("type")
    data = event.get("data") or {}
    reason = None
    if kind == "email.complained":
        reason = "spam complaint"
    elif kind == "email.bounced":
        bounce_type = ((data.get("bounce") or {}).get("type") or "").lower()
        # A transient bounce (mailbox full, server busy) is retried by the
        # provider; only a permanent one means the address is gone.
        if bounce_type in ("", "permanent", "hard"):
            reason = "hard bounce"
    suppressed = 0
    if reason:
        for address in data.get("to") or []:
            suppressed += cm.suppress_email(db, address, reason)
    log.info(json.dumps({"event": "email.webhook", "type": kind, "suppressed": suppressed}))
    return {"ok": True, "suppressed": suppressed}
