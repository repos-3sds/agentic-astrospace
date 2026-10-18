import base64
import hashlib

from astrospace.api.security_headers import content_security_policy, security_headers


def test_csp_is_report_only_and_allows_the_inline_theme_script_by_hash():
    script = "\n    (function () { document.documentElement.classList.add('x'); })();\n  "
    html = f"<html><head><script>{script}</script></head></html>"
    headers = dict(security_headers(False, html))
    assert b"content-security-policy" not in headers
    policy = headers[b"content-security-policy-report-only"].decode()
    digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert f"'sha256-{digest}'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "'unsafe-inline'" not in policy.split("script-src", 1)[1].split(";", 1)[0]


def test_csp_without_a_build_still_has_a_policy():
    assert content_security_policy(None).startswith("default-src 'self'")


def test_angular_stylesheet_onload_handler_is_allowed_by_hash():
    html = '<link rel="stylesheet" href="s.css" media="print" onload="this.media=\'all\'">'
    policy = content_security_policy(html)
    digest = base64.b64encode(hashlib.sha256("this.media='all'".encode()).digest()).decode()
    assert "'unsafe-hashes'" in policy and f"'sha256-{digest}'" in policy
