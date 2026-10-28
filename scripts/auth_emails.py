"""Sign-in emails (Supabase Auth) in the Siddha look, sent through Resend.

Supabase Auth sends its own emails: confirm your email, the sign-in link,
reset password, change email, invite and the re-check code. Out of the box
they come from Supabase's shared sender in plain grey text. This script
keeps them in the repo, in the same layout as the reader emails
(astrospace/notifications/email.py), and applies them to the live project.

    python scripts/auth_emails.py build   # writes supabase/templates/*.html
    python scripts/auth_emails.py apply   # sets SMTP + templates on the live project
    python scripts/auth_emails.py urls    # points sign-in links at asksiddha.app/open

`urls` asks only for the access token, shows the Site URL and redirect
allow-list before and after, and changes nothing until you type y. It only
ever adds to the allow-list.

`apply` asks for two secrets and never prints them: a Supabase personal
access token (supabase.com/dashboard/account/tokens) and the Resend API key.
It uses only the Python standard library, so it runs on a bare Mac.

The {{ .ConfirmationURL }}-style placeholders are Supabase's own template
variables, filled in by Supabase when it sends.
"""
from __future__ import annotations

import getpass
import json
import sys
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

PROJECT_REF = "wcaqjhqckipgkvhbiwjt"
TEMPLATES = Path(__file__).resolve().parent.parent / "supabase" / "templates"
LOGO = "https://asksiddha.app/email/siddha-logo.png"
SITE = "https://asksiddha.app"
SENDER_EMAIL = "asksiddha@3senses.design"
SENDER_NAME = "Siddha"
ADDRESS = "Siddha, 3 Senses Design Studio, India 533005"

# Same palette as astrospace/notifications/email.py.
BG, CARD, INK, MUTED = "#FAF7F0", "#FFFFFF", "#201A14", "#756B5E"
ACCENT, ACCENT_STRONG, RULE, SOFT = "#B13F2E", "#8F2F22", "#E6DCCD", "#FFFCF6"
SERIF = "Georgia,'Times New Roman',serif"
SANS = "-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

LINK = "{{ .ConfirmationURL }}"

# (key, subject, heading, body paragraphs, button label or None, closing line)
EMAILS = [
    ("confirmation", "Confirm your email for Siddha", "Confirm your email",
     ["Welcome to Siddha. Tap the button below to confirm this is your email, and you're in."],
     "Confirm my email",
     "If you didn't create a Siddha account, you can ignore this email. Nothing will happen."),
    ("magic_link", "Your Siddha sign-in link", "Here's your sign-in link",
     ["Tap the button below to sign in to Siddha. It works once, and only for the next hour.",
      "Open it on the phone where you asked for it."],
     "Sign in to Siddha",
     "If you didn't ask to sign in, you can ignore this email. Your account is safe."),
    ("recovery", "Reset your Siddha password", "Reset your password",
     ["Someone, hopefully you, asked to reset the password for your Siddha account. "
      "Tap the button below to choose a new one. The link works for the next hour."],
     "Choose a new password",
     "If you didn't ask for this, you can ignore this email. Your password stays the same."),
    ("email_change", "Confirm your new email for Siddha", "Confirm your new email",
     ["You asked to change the email on your Siddha account from {{ .Email }} to {{ .NewEmail }}. "
      "Tap the button below to confirm."],
     "Confirm the new email",
     "If you didn't ask for this, don't tap the button, and reply to this email so we can help."),
    ("invite", "You're invited to Siddha", "You're invited to Siddha",
     ["Siddha is a daily guide built from your own birth chart: what each day is good for, "
      "the good times in it, and answers to your questions. Tap the button below to accept "
      "and set up your account."],
     "Accept the invite",
     "If you weren't expecting this, you can ignore this email."),
    ("reauthentication", "Your Siddha confirmation code", "Your confirmation code",
     ["Enter this code in Siddha to confirm it's you. It works for the next hour."],
     None,
     "If you didn't ask for a code, you can ignore this email. Your account is safe."),
]


def render(subject: str, heading: str, paragraphs: list[str], button: str | None, closing: str) -> str:
    """One email. Copy here is ours, not user input; it is escaped anyway,
    except the Supabase placeholders, which must reach Supabase intact."""
    def text(s: str) -> str:
        return escape(s, quote=False)

    paras = "".join(
        f'<p style="margin:0 0 16px;font-size:18px;line-height:1.6;color:{INK}">{text(p)}</p>'
        for p in paragraphs
    )
    if button:
        action = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:26px 0 22px"><tr>'
            f'<td style="background:{ACCENT};border-radius:999px">'
            f'<a href="{LINK}" style="display:inline-block;padding:14px 28px;font-family:{SANS};'
            f'font-size:16px;font-weight:600;color:#FFFFFF;text-decoration:none">{text(button)}</a>'
            f'</td></tr></table>'
            f'<p style="margin:0 0 6px;font-family:{SANS};font-size:13px;color:{MUTED}">'
            f'If the button doesn\'t work, copy this link into your browser:</p>'
            f'<p style="margin:0 0 20px;font-family:{SANS};font-size:13px;line-height:1.5;word-break:break-all">'
            f'<a href="{LINK}" style="color:{ACCENT_STRONG}">{LINK}</a></p>'
        )
    else:
        action = (
            f'<p style="margin:22px 0 22px;padding:16px 0;background:{SOFT};border:1px solid {RULE};'
            f'border-radius:12px;text-align:center;font-family:{SANS};font-size:32px;font-weight:700;'
            f'letter-spacing:.3em;color:{INK}">{{{{ .Token }}}}</p>'
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{text(subject)}</title></head>
<body style="margin:0;padding:0;background:{BG};color:{INK};font-family:{SERIF}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG}">
<tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px">
<tr><td align="center" style="padding:0 8px 22px">
<img src="{LOGO}" width="170" alt="Siddha" style="display:block;margin:0 auto;width:170px;max-width:60%;height:auto;border:0;font-family:{SERIF};font-size:24px;color:{ACCENT_STRONG}">
</td></tr>
<tr><td style="background:{CARD};border:1px solid {RULE};border-radius:20px;padding:32px 26px">
<h1 style="margin:0 0 14px;font-size:28px;line-height:1.2;font-weight:normal;color:{INK}">{text(heading)}</h1>
{paras}{action}
<p style="margin:0;font-family:{SANS};font-size:14px;line-height:1.6;color:{MUTED}">{text(closing)}</p>
</td></tr>
<tr><td align="center" style="padding:24px 16px 0;font-family:{SANS};font-size:12px;line-height:1.7;color:{MUTED}">
You get this because someone used this address with <a href="{SITE}" style="color:{MUTED}">Siddha</a>.<br>
{escape(ADDRESS)}
</td></tr>
</table></td></tr></table>
</body></html>
"""


def build() -> dict[str, tuple[str, str]]:
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    out = {}
    for key, subject, heading, paragraphs, button, closing in EMAILS:
        html = render(subject, heading, paragraphs, button, closing)
        (TEMPLATES / f"{key}.html").write_text(html)
        out[key] = (subject, html)
    return out


def auth_config(emails: dict[str, tuple[str, str]], resend_key: str) -> dict:
    """The Management API body: Resend SMTP, then each subject and template."""
    body = {
        "smtp_host": "smtp.resend.com",
        "smtp_port": "465",
        "smtp_user": "resend",
        "smtp_pass": resend_key,
        "smtp_admin_email": SENDER_EMAIL,
        "smtp_sender_name": SENDER_NAME,
        # Supabase's shared sender allows 2 an hour; with our own SMTP this
        # is ours to set. Generous enough for a launch day.
        "rate_limit_email_sent": 100,
    }
    for key, (subject, html) in emails.items():
        body[f"mailer_subjects_{key}"] = subject
        body[f"mailer_templates_{key}_content"] = html
    return body


# Where sign-in email links land (firebase-public/open.html). Also the Site
# URL, which Supabase falls back to when a link names no allowed redirect:
# until 2026-10-28 that was the Cloud Run web app, so a reader who confirmed
# their email from a phone was left on the owner's web tool.
OPEN_PAGE = f"{SITE}/open"
OWNER_WEB = "https://agentic-astrospace-cwuqybpnzq-el.a.run.app"
REDIRECTS = [
    OPEN_PAGE,
    # Google and Apple sign-in in the app's own browser sheet.
    "app.asksiddha.mobile://auth/callback",
    # The owner's own web sign-ins, which return to /app.
    f"{OWNER_WEB}/**",
]


def url_config(current: dict) -> dict:
    """Site URL to the open page; every redirect in REDIRECTS allowed, none removed."""
    existing = [u.strip() for u in (current.get("uri_allow_list") or "").split(",") if u.strip()]
    merged = existing + [u for u in REDIRECTS if u not in existing]
    return {"site_url": OPEN_PAGE, "uri_allow_list": ",".join(merged)}


def _api(token: str, method: str, body: dict | None = None) -> dict:
    request = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/config/auth",
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def urls() -> int:
    token = getpass.getpass("Supabase access token (input hidden): ").strip()
    if not token:
        print("Stopped: no token. Nothing changed.")
        return 1
    try:
        current = _api(token, "GET")
    except urllib.error.HTTPError as error:
        print(f"Supabase said no ({error.code}): {error.read().decode()[:400]}")
        return 1
    wanted = url_config(current)
    print(f"Site URL now:   {current.get('site_url')}")
    print(f"Site URL after: {wanted['site_url']}")
    print("Redirect URLs after (existing ones kept):")
    for url in wanted["uri_allow_list"].split(","):
        print(f"  {url}")
    if input("Apply these? [y/N] ").strip().lower() != "y":
        print("Nothing changed.")
        return 0
    try:
        result = _api(token, "PATCH", wanted)
    except urllib.error.HTTPError as error:
        print(f"Supabase said no ({error.code}): {error.read().decode()[:400]}")
        return 1
    print(f"Done. Site URL is {result.get('site_url')}.")
    return 0


def apply() -> int:
    emails = build()
    print(f"Templates written to {TEMPLATES}")
    token = getpass.getpass("Supabase access token (input hidden): ").strip()
    resend_key = getpass.getpass("Resend API key, starts with re_ (input hidden): ").strip()
    if not token or not resend_key.startswith("re_"):
        print("Stopped: the token is empty or the Resend key doesn't start with re_. Nothing changed.")
        return 1
    request = urllib.request.Request(
        f"https://api.supabase.com/v1/projects/{PROJECT_REF}/config/auth",
        data=json.dumps(auth_config(emails, resend_key)).encode(),
        method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        print(f"Supabase said no ({error.code}): {error.read().decode()[:400]}")
        return 1
    print("Done. Sign-in emails now go through Resend as "
          f"{result.get('smtp_sender_name')} <{result.get('smtp_admin_email')}>, "
          f"with {len(emails)} Siddha templates.")
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "build"
    if command == "build":
        build()
        print(f"Templates written to {TEMPLATES}")
    elif command == "apply":
        sys.exit(apply())
    elif command == "urls":
        sys.exit(urls())
    else:
        print(__doc__)
        sys.exit(2)
