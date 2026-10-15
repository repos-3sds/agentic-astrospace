"""Terms of Service and Privacy Policy, served by the API.

The app stores require a public privacy-policy URL and the sign-in screen
promises Terms; both live here rather than in the SPA so the same URL works in
a store listing, in a browser and inside the native app (which opens them in
the system browser via @capacitor/browser).

The documents are HTML fragments under astrospace/legal/, written to match
what the software actually does. Operator identity and the contact address
come from the environment so the text never has to be edited per deployment:

    LEGAL_OPERATOR_NAME   e.g. "Example Pvt Ltd"   (default: "the Siddha team")
    LEGAL_CONTACT_EMAIL   e.g. "privacy@example.com" (default: unset — the
                          contact sentence then points at the store listing)
"""
from __future__ import annotations

import html
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["legal"])

LEGAL_DIR = Path(__file__).resolve().parent.parent / "legal"
LAST_UPDATED = "15 October 2026"
DOCUMENTS = {
    "terms": ("terms.html", "Terms of Service"),
    "privacy": ("privacy.html", "Privacy Policy"),
}

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Siddha</title>
<style>
  :root {{ color-scheme: light dark; --bg: #faf7f0; --fg: #1e1710; --muted: #6f6256; --accent: #b13f2e; --rule: #e6ddd0; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #15110d; --fg: #f3ebdf; --muted: #a89d8e; --accent: #e9866f; --rule: #332a22; }} }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6 -apple-system, "Inter", system-ui, sans-serif; }}
  main {{ max-width: 42rem; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 1.75rem; line-height: 1.2; margin: 0 0 4px; }}
  h2 {{ font-size: 1.05rem; margin: 28px 0 8px; }}
  p, li {{ margin: 0 0 12px; }}
  .meta {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 24px; }}
  a {{ color: var(--accent); }}
  nav {{ display: flex; gap: 16px; padding-bottom: 16px; margin-bottom: 24px; border-bottom: 1px solid var(--rule); font-size: 0.9rem; }}
</style>
</head>
<body>
<main>
<nav><a href="/legal/terms">Terms of Service</a><a href="/legal/privacy">Privacy Policy</a></nav>
{body}
</main>
</body>
</html>
"""


def _substitutions() -> dict[str, str]:
    operator = html.escape(os.getenv("LEGAL_OPERATOR_NAME", "").strip() or "the Siddha team")
    email = html.escape(os.getenv("LEGAL_CONTACT_EMAIL", "").strip())
    if email:
        contact_line = f'Questions go to <a href="mailto:{email}">{email}</a>.'
        contact_rights = f'write to <a href="mailto:{email}">{email}</a>'
    else:
        contact_line = "Contact details are listed with the app in the App Store and Google Play."
        contact_rights = "contact us through the app store listing"
    return {
        "{{OPERATOR}}": operator,
        "{{UPDATED}}": LAST_UPDATED,
        "{{CONTACT_LINE}}": contact_line,
        "{{CONTACT_RIGHTS}}": contact_rights,
    }


def render_legal_document(name: str) -> str:
    """The full HTML page for one document, placeholders filled in."""
    if name not in DOCUMENTS:
        raise KeyError(name)
    filename, title = DOCUMENTS[name]
    body = (LEGAL_DIR / filename).read_text(encoding="utf-8")
    for token, value in _substitutions().items():
        body = body.replace(token, value)
    return _PAGE.format(title=title, body=body)


@router.get("/legal/{name}", response_class=HTMLResponse, include_in_schema=False)
def legal_document(name: str) -> HTMLResponse:
    try:
        return HTMLResponse(render_legal_document(name))
    except KeyError:
        raise HTTPException(status_code=404, detail="No such document")
