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
DEFAULT_POSTAL_ADDRESS = "Siddha, 3 Senses Design Studio, India 533005"
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

# The app's light palette (ui/src/styles-mobile.scss), written out literally:
# email clients ignore CSS custom properties and most dark-mode hints.
_BG = "#FAF7F0"
_CARD = "#FFFFFF"
_INK = "#201A14"
_MUTED = "#756B5E"
_ACCENT = "#B13F2E"
_ACCENT_STRONG = "#8F2F22"
_GOLD = "#7A5218"
_RULE = "#E6DCCD"
_SOFT = "#FFFCF6"
_GOOD_TINT = "#F3F7EE"
_CARE_TINT = "#FBF1EC"
_SERIF = "Georgia,'Times New Roman',serif"
_SANS = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

# Served from the SPA's public folder (ui/public/email/), so it is the same
# URL the app is on. Email clients block or mangle SVG, so it is a PNG.
LOGO_PATH = "/email/siddha-logo.png"

CATEGORY_LABELS = {
    "daily_email": "your daily reading",
    "festival_email": "moon and festival days",
    "system": "account emails",
}


@dataclass(frozen=True)
class EmailContent:
    """What one email says, as plain data (it is stored in the job payload).

    `blocks` is a list of dicts, rendered in order:
      {"type": "text", "heading": str|None, "body": str}       a paragraph
      {"type": "items", "heading": str, "tone": "good"|"care"|None,
       "items": [[title, detail], ...]}                        titled points
      {"type": "rows", "heading": str, "rows": [[label, value], ...]}
      {"type": "callout", "heading": str|None, "body": str}    a tinted box
    """

    subject: str
    preview: str
    heading: str
    intro: str
    eyebrow: str | None = None
    date_line: str | None = None
    chips: list[str] = field(default_factory=list)
    blocks: list[dict] = field(default_factory=list)
    button_label: str = "Open Siddha"
    button_path: str = "/m/today"
    note: str | None = None


def _label(text: str) -> str:
    return (f'<p style="margin:28px 0 10px;font-family:{_SANS};font-size:12px;letter-spacing:.1em;'
            f'text-transform:uppercase;color:{_ACCENT_STRONG};font-weight:700">{html.escape(text)}</p>')


def _block_html(block: dict) -> str:
    e = html.escape
    kind = block.get("type")
    heading = block.get("heading")
    out = _label(heading) if heading else ""
    if kind == "text":
        for para in str(block.get("body") or "").split("\n\n"):
            if para.strip():
                out += f'<p style="margin:0 0 14px;font-size:17px;line-height:1.65;color:{_INK}">{e(para.strip())}</p>'
    elif kind == "items":
        tint = {"good": _GOOD_TINT, "care": _CARE_TINT}.get(block.get("tone"), _SOFT)
        for title, detail in block.get("items") or []:
            out += (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                    f'style="margin:0 0 10px;background:{tint};border:1px solid {_RULE};border-radius:12px">'
                    f'<tr><td style="padding:14px 16px">'
                    f'<p style="margin:0 0 4px;font-family:{_SANS};font-size:16px;font-weight:700;color:{_INK}">{e(title)}</p>')
            if detail:
                out += f'<p style="margin:0;font-size:15px;line-height:1.55;color:{_MUTED}">{e(detail)}</p>'
            out += '</td></tr></table>'
    elif kind == "rows":
        rows = "".join(
            f'<tr><td style="padding:12px 0;border-top:1px solid {_RULE};width:96px;vertical-align:top;'
            f'font-family:{_SANS};font-size:13px;font-weight:700;letter-spacing:.04em;color:{_GOLD}">{e(label)}</td>'
            f'<td style="padding:12px 0 12px 12px;border-top:1px solid {_RULE};font-size:16px;line-height:1.6;color:{_INK}">{e(value)}</td></tr>'
            for label, value in block.get("rows") or []
        )
        out += f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>'
    elif kind == "callout":
        out += (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                f'style="margin:4px 0 0;background:{_SOFT};border-left:4px solid {_ACCENT};border-radius:8px">'
                f'<tr><td style="padding:14px 16px;font-size:16px;line-height:1.6;color:{_INK}">{e(block.get("body") or "")}</td></tr></table>')
    return out


def _block_text(block: dict) -> list[str]:
    lines = [block["heading"].upper()] if block.get("heading") else []
    kind = block.get("type")
    if kind in ("text", "callout"):
        lines.append(str(block.get("body") or ""))
    elif kind == "items":
        for title, detail in block.get("items") or []:
            lines.append(f"- {title}" + (f": {detail}" if detail else ""))
    elif kind == "rows":
        lines += [f"{label}: {value}" for label, value in block.get("rows") or []]
    return lines + [""]


def render(content: EmailContent, *, user_id: str, category: str) -> tuple[str, str]:
    """(html, text) for one email. Every value is escaped here, once: agent
    copy is model output and is never trusted as markup."""
    e = html.escape
    link = f"{base_url()}{content.button_path}"
    logo = f"{base_url()}{LOGO_PATH}"
    address = os.getenv("EMAIL_POSTAL_ADDRESS") or DEFAULT_POSTAL_ADDRESS
    label = CATEGORY_LABELS.get(category, "these emails")
    marketing = category != "system"
    unsub_one = unsubscribe_url(user_id, category) if marketing else None
    unsub_all = unsubscribe_url(user_id, ALL_CATEGORIES) if marketing else None

    eyebrow = (f'<p style="margin:0 0 10px;font-family:{_SANS};font-size:12px;letter-spacing:.1em;'
               f'text-transform:uppercase;color:{_ACCENT_STRONG};font-weight:700">{e(content.eyebrow)}</p>'
               if content.eyebrow else "")
    chips = "".join(
        f'<span style="display:inline-block;margin:0 6px 6px 0;padding:5px 12px;border:1px solid {_RULE};'
        f'border-radius:999px;background:{_SOFT};font-family:{_SANS};font-size:13px;color:{_GOLD}">{e(c)}</span>'
        for c in content.chips
    )
    chips = f'<div style="margin:4px 0 6px">{chips}</div>' if chips else ""
    date_line = (f'<tr><td style="padding:0 8px 10px;font-family:{_SANS};font-size:13px;color:{_MUTED}">'
                 f'{e(content.date_line)}</td></tr>' if content.date_line else "")
    note = (f'<p style="margin:24px 0 0;font-size:14px;line-height:1.55;color:{_MUTED};font-style:italic">'
            f'{e(content.note)}</p>' if content.note else "")

    footer_links = ""
    if marketing:
        footer_links = (
            f'You get this because you turned on {e(label)} in Siddha.<br>'
            f'<a href="{e(unsub_one)}" style="color:{_MUTED}">Stop these emails</a> · '
            f'<a href="{e(unsub_all)}" style="color:{_MUTED}">Stop all emails</a><br><br>'
        )

    html_body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{e(content.subject)}</title></head>
<body style="margin:0;padding:0;background:{_BG};color:{_INK};font-family:{_SERIF}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(content.preview)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG}">
<tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px">
<tr><td align="center" style="padding:0 8px 22px">
<a href="{e(base_url())}/m/today" style="text-decoration:none"><img src="{e(logo)}" width="220" alt="Siddha" style="display:block;width:220px;max-width:70%;height:auto;border:0;font-family:{_SERIF};font-size:24px;color:{_ACCENT_STRONG}"></a>
</td></tr>
{date_line}
<tr><td style="background:{_CARD};border:1px solid {_RULE};border-radius:20px;padding:32px 26px">
{eyebrow}<h1 style="margin:0 0 14px;font-size:30px;line-height:1.2;font-weight:normal;color:{_INK}">{e(content.heading)}</h1>
<p style="margin:0 0 16px;font-size:19px;line-height:1.6;color:{_INK}">{e(content.intro)}</p>
{chips}{''.join(_block_html(b) for b in content.blocks)}{note}
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:30px 0 4px"><tr>
<td style="background:{_ACCENT};border-radius:999px">
<a href="{e(link)}" style="display:inline-block;padding:14px 28px;font-family:{_SANS};font-size:16px;font-weight:600;color:#FFFFFF;text-decoration:none">{e(content.button_label)}</a>
</td></tr></table>
</td></tr>
<tr><td align="center" style="padding:24px 16px 0;font-family:{_SANS};font-size:12px;line-height:1.7;color:{_MUTED}">
{footer_links}Siddha offers traditional guidance for reflection, not medical, legal or financial advice.<br>
{e(address)}
</td></tr>
</table></td></tr></table>
</body></html>"""

    text_lines = []
    if content.date_line:
        text_lines += [content.date_line, ""]
    if content.eyebrow:
        text_lines.append(content.eyebrow.upper())
    text_lines += [content.heading, "", content.intro, ""]
    if content.chips:
        text_lines += [" · ".join(content.chips), ""]
    for block in content.blocks:
        text_lines += _block_text(block)
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
