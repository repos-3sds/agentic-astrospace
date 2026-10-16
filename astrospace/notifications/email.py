"""Email delivery: the transport, the signed links in every email, and the one
branded layout every email uses.

Only Resend is implemented (HTTP API, no SDK). The transport is one small
class behind the same shape as the push transports, so moving to Amazon SES
at volume is a new class and an env switch, not a rewrite.

Configuration is environment-only, never read from the repo:

    RESEND_API_KEY          from Secret Manager (resend-api-key); unset = not configured
    EMAIL_FROM              default "Siddha <asksiddha@3senses.design>"
    EMAIL_REPLY_TO          default asksiddha@3senses.design
    EMAIL_LINK_SECRET       signs unsubscribe links; required to send
    EMAIL_POSTAL_ADDRESS    footer sender line, default "Siddha, 3 Senses Design Studio, India"
    PUBLIC_BASE_URL         where links point, default the Cloud Run URL

Every marketing email carries List-Unsubscribe and List-Unsubscribe-Post
(RFC 8058), which Gmail and Yahoo require of bulk senders: one tap in the
mail app turns that one category off, with no sign-in.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
from dataclasses import dataclass, field
from typing import Protocol

DEFAULT_FROM = "Siddha <asksiddha@3senses.design>"
DEFAULT_REPLY_TO = "asksiddha@3senses.design"
DEFAULT_POSTAL_ADDRESS = "Siddha, 3 Senses Design Studio, India"
DEFAULT_BASE_URL = "https://agentic-astrospace-cwuqybpnzq-el.a.run.app"
RESEND_ENDPOINT = "https://api.resend.com/emails"

# Unsubscribe scope for "stop every email", alongside the per-category ones.
ALL_CATEGORIES = "all"


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str
    headers: dict = field(default_factory=dict)
    tags: dict = field(default_factory=dict)


@dataclass(frozen=True)
class EmailResult:
    ok: bool
    provider_message_id: str | None = None
    error: str | None = None
    # True when the address itself was refused; the worker suppresses it.
    address_dead: bool = False
    receipt: dict | None = None


class EmailTransport(Protocol):
    provider: str

    def send(self, message: EmailMessage) -> EmailResult: ...


class NotConfiguredEmail:
    """No key yet: every send fails with a stable reason and the job stays
    retryable, so adding the key later drains what is queued."""

    provider = "email"

    def __init__(self, reason: str):
        self.reason = reason

    def send(self, message: EmailMessage) -> EmailResult:
        return EmailResult(ok=False, error=self.reason)


class ResendTransport:
    provider = "resend"

    def __init__(self, api_key: str, sender: str = DEFAULT_FROM,
                 reply_to: str | None = DEFAULT_REPLY_TO, http=None):
        self.api_key = api_key
        self.sender = sender
        self.reply_to = reply_to
        self._http = http

    def _client(self):
        if self._http is None:
            import requests

            self._http = requests.Session()
        return self._http

    def send(self, message: EmailMessage) -> EmailResult:
        payload = {
            "from": self.sender,
            "to": [message.to],
            "subject": message.subject,
            "html": message.html,
            "text": message.text,
            "headers": message.headers,
            "tags": [{"name": k, "value": str(v)} for k, v in message.tags.items()],
        }
        if self.reply_to:
            payload["reply_to"] = self.reply_to
        try:
            response = self._client().post(
                RESEND_ENDPOINT, json=payload, timeout=15,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        except Exception as exc:  # network
            return EmailResult(ok=False, error=f"resend: {exc}")
        try:
            body = response.json()
        except ValueError:
            body = {"raw": (response.text or "")[:500]}
        if response.status_code in (200, 201):
            return EmailResult(ok=True, provider_message_id=body.get("id"), receipt=body)
        message_text = body.get("message") if isinstance(body, dict) else None
        name = body.get("name") if isinstance(body, dict) else None
        # 422 validation_error on the `to` field: the address cannot be sent to.
        dead = response.status_code == 422 and "to" in (message_text or "").lower()
        return EmailResult(
            ok=False, error=f"resend {response.status_code} {name or ''}: {message_text or ''}".strip(),
            address_dead=dead, receipt=body if isinstance(body, dict) else None,
        )


def email_transport_from_env(environ: dict | None = None) -> EmailTransport:
    env = os.environ if environ is None else environ
    key = (env.get("RESEND_API_KEY") or "").strip()
    if not key:
        return NotConfiguredEmail("email transport not configured (set RESEND_API_KEY)")
    if not (env.get("EMAIL_LINK_SECRET") or "").strip():
        # Without it no unsubscribe link can be signed, and an email without
        # a working unsubscribe must not go out.
        return NotConfiguredEmail("email transport not configured (set EMAIL_LINK_SECRET)")
    return ResendTransport(
        key,
        sender=(env.get("EMAIL_FROM") or DEFAULT_FROM).strip(),
        reply_to=(env.get("EMAIL_REPLY_TO") or DEFAULT_REPLY_TO).strip() or None,
    )


# ── Signed unsubscribe links ──────────────────────────────────────────────────

def _secret() -> bytes:
    secret = (os.getenv("EMAIL_LINK_SECRET") or "").strip()
    if not secret:
        raise RuntimeError("EMAIL_LINK_SECRET is not set")
    return secret.encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def unsubscribe_token(user_id: str, category: str) -> str:
    """`<user>.<category>.<mac>`, all base64url. No expiry: an unsubscribe
    link in a two-year-old email must still work."""
    body = f"{_b64(user_id.encode())}.{_b64(category.encode())}"
    mac = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()[:16]
    return f"{body}.{_b64(mac)}"


def read_unsubscribe_token(token: str) -> tuple[str, str] | None:
    """(user_id, category), or None for anything not signed by us."""
    try:
        user_part, category_part, mac_part = token.split(".")
        body = f"{user_part}.{category_part}"
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(expected, _unb64(mac_part)):
            return None
        return _unb64(user_part).decode(), _unb64(category_part).decode()
    except (ValueError, UnicodeDecodeError, RuntimeError):
        return None


def base_url() -> str:
    return (os.getenv("PUBLIC_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")


def unsubscribe_url(user_id: str, category: str) -> str:
    return f"{base_url()}/api/v1/email/unsubscribe?t={unsubscribe_token(user_id, category)}"


def unsubscribe_headers(user_id: str, category: str) -> dict:
    return {
        "List-Unsubscribe": f"<{unsubscribe_url(user_id, category)}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }


# ── The layout ────────────────────────────────────────────────────────────────

# Fixed light palette, the app's cream and brown. Email clients ignore CSS
# custom properties and most dark-mode hints, so the colours are literal and
# chosen to stay readable when a client inverts them.
_CREAM = "#F6EFE4"
_CARD = "#FFFDF9"
_INK = "#2B2118"
_MUTED = "#6E5F50"
_BROWN = "#7A4E2D"
_RULE = "#E6DACB"

CATEGORY_LABELS = {
    "daily_email": "your daily reading",
    "festival_email": "moon and festival days",
    "system": "account emails",
}


@dataclass(frozen=True)
class EmailContent:
    """What one email says. `sections` are (heading or None, paragraph) pairs;
    `lists` are (heading, short lines) pairs, shown after the sections."""

    subject: str
    preview: str
    heading: str
    intro: str
    sections: list[tuple[str | None, str]] = field(default_factory=list)
    lists: list[tuple[str, list[str]]] = field(default_factory=list)
    button_label: str = "Open Siddha"
    button_path: str = "/m/today"
    note: str | None = None


def render(content: EmailContent, *, user_id: str, category: str) -> tuple[str, str]:
    """(html, text) for one email. Every value is escaped here, once: agent
    copy is model output and is never trusted as markup."""
    e = html.escape
    link = f"{base_url()}{content.button_path}"
    address = os.getenv("EMAIL_POSTAL_ADDRESS") or DEFAULT_POSTAL_ADDRESS
    label = CATEGORY_LABELS.get(category, "these emails")
    marketing = category != "system"
    unsub_one = unsubscribe_url(user_id, category) if marketing else None
    unsub_all = unsubscribe_url(user_id, ALL_CATEGORIES) if marketing else None

    blocks: list[str] = []
    for heading, para in content.sections:
        if heading:
            blocks.append(
                f'<p style="margin:20px 0 4px;font-size:13px;letter-spacing:.06em;'
                f'text-transform:uppercase;color:{_BROWN};font-weight:600">{e(heading)}</p>'
            )
        blocks.append(f'<p style="margin:0 0 12px;font-size:16px;line-height:1.55">{e(para)}</p>')
    for heading, items in content.lists:
        if not items:
            continue
        blocks.append(
            f'<p style="margin:20px 0 4px;font-size:13px;letter-spacing:.06em;'
            f'text-transform:uppercase;color:{_BROWN};font-weight:600">{e(heading)}</p>'
        )
        lis = "".join(f'<li style="margin:0 0 6px">{e(i)}</li>' for i in items)
        blocks.append(f'<ul style="margin:0 0 12px;padding-left:20px;font-size:16px;line-height:1.5">{lis}</ul>')
    if content.note:
        blocks.append(f'<p style="margin:16px 0 0;font-size:13px;line-height:1.5;color:{_MUTED}">{e(content.note)}</p>')

    footer_links = ""
    if marketing:
        footer_links = (
            f'You get this because you turned on {e(label)} in Siddha. '
            f'<a href="{e(unsub_one)}" style="color:{_MUTED}">Stop these emails</a> · '
            f'<a href="{e(unsub_all)}" style="color:{_MUTED}">Stop all emails</a><br>'
        )

    html_body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{e(content.subject)}</title></head>
<body style="margin:0;padding:0;background:{_CREAM};color:{_INK};font-family:Georgia,'Times New Roman',serif">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(content.preview)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_CREAM}">
<tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px">
<tr><td style="padding:0 8px 16px;font-size:15px;letter-spacing:.12em;text-transform:uppercase;color:{_BROWN}">Siddha</td></tr>
<tr><td style="background:{_CARD};border:1px solid {_RULE};border-radius:16px;padding:28px 24px">
<h1 style="margin:0 0 12px;font-size:26px;line-height:1.25;font-weight:normal;color:{_INK}">{e(content.heading)}</h1>
<p style="margin:0 0 12px;font-size:17px;line-height:1.55;color:{_INK}">{e(content.intro)}</p>
{''.join(blocks)}
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0 4px"><tr>
<td style="background:{_BROWN};border-radius:999px">
<a href="{e(link)}" style="display:inline-block;padding:12px 24px;font-family:Arial,Helvetica,sans-serif;font-size:15px;color:#FFFFFF;text-decoration:none">{e(content.button_label)}</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:20px 8px 0;font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.6;color:{_MUTED}">
{footer_links}Siddha offers traditional guidance for reflection, not medical, legal or financial advice.<br>
{e(address)}
</td></tr>
</table></td></tr></table>
</body></html>"""

    text_lines = [content.heading, "", content.intro, ""]
    for heading, para in content.sections:
        if heading:
            text_lines.append(heading.upper())
        text_lines += [para, ""]
    for heading, items in content.lists:
        if items:
            text_lines.append(heading.upper())
            text_lines += [f"- {i}" for i in items] + [""]
    if content.note:
        text_lines += [content.note, ""]
    text_lines += [f"{content.button_label}: {link}", "", "--"]
    if marketing:
        text_lines += [f"Stop these emails: {unsub_one}", f"Stop all emails: {unsub_all}"]
    text_lines += [
        "Siddha offers traditional guidance for reflection, not medical, legal or financial advice.",
        address,
    ]
    return html_body, "\n".join(text_lines)


def build_message(to: str, content: EmailContent, *, user_id: str, category: str) -> EmailMessage:
    html_body, text = render(content, user_id=user_id, category=category)
    headers = unsubscribe_headers(user_id, category) if category != "system" else {}
    return EmailMessage(to=to, subject=content.subject, html=html_body, text=text,
                        headers=headers, tags={"category": category})
