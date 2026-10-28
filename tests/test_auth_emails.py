"""The sign-in email templates keep Supabase's placeholders intact and the
live-config body names every template the script owns."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("auth_emails", ROOT / "scripts" / "auth_emails.py")
auth_emails = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth_emails)


def test_templates_in_repo_match_the_script():
    for key, subject, heading, paragraphs, button, closing in auth_emails.EMAILS:
        built = auth_emails.render(subject, heading, paragraphs, button, closing)
        assert (ROOT / "supabase" / "templates" / f"{key}.html").read_text() == built, key


def test_placeholders_survive_and_copy_stays_calm():
    for key, subject, heading, paragraphs, button, closing in auth_emails.EMAILS:
        html = auth_emails.render(subject, heading, paragraphs, button, closing)
        needed = "{{ .Token }}" if button is None else "{{ .ConfirmationURL }}"
        assert needed in html, key
        assert "&#123;" not in html and "{ {" not in html
        assert auth_emails.ADDRESS in html
    change = dict((e[0], e) for e in auth_emails.EMAILS)["email_change"]
    html = auth_emails.render(*change[1:])
    assert "{{ .Email }}" in html and "{{ .NewEmail }}" in html


def test_config_body_sets_resend_smtp_and_every_template():
    emails = {k: (s, "<html/>") for k, s, *_ in auth_emails.EMAILS}
    body = auth_emails.auth_config(emails, "re_test")
    assert body["smtp_host"] == "smtp.resend.com" and body["smtp_user"] == "resend"
    assert body["smtp_admin_email"] == "asksiddha@3senses.design" and body["smtp_sender_name"] == "Siddha"
    for key in emails:
        assert body[f"mailer_subjects_{key}"] and body[f"mailer_templates_{key}_content"] == "<html/>"


def test_urls_send_links_to_the_open_page_and_only_ever_add():
    current = {"site_url": "https://agentic-astrospace-cwuqybpnzq-el.a.run.app",
               "uri_allow_list": "https://example.test/keep,app.asksiddha.mobile://auth/callback"}
    wanted = auth_emails.url_config(current)
    assert wanted["site_url"] == "https://asksiddha.app/open"
    allowed = wanted["uri_allow_list"].split(",")
    assert allowed[:2] == ["https://example.test/keep", "app.asksiddha.mobile://auth/callback"]
    assert "https://asksiddha.app/open" in allowed
    assert len(allowed) == len(set(allowed))
    assert auth_emails.url_config({})["uri_allow_list"].split(",") == auth_emails.REDIRECTS


def test_open_page_matches_the_app():
    """The app sends email links to this page; Hosting must serve it and /m/ links."""
    import json
    service = (ROOT / "ui/src/app/core/auth.service.ts").read_text()
    assert f"EMAIL_LINK_PAGE = '{auth_emails.OPEN_PAGE}'" in service
    assert (ROOT / "firebase-public/open.html").exists()
    rewrites = json.loads((ROOT / "firebase.json").read_text())["hosting"]["rewrites"]
    sources = [r["source"] for r in rewrites]
    assert {"source": "/m/**", "destination": "/open.html"} in rewrites
    assert sources.index("/m/**") < sources.index("**")
    # Never forward a token: the app redeems a one-time PKCE code instead.
    script = (ROOT / "firebase-public/js/open-app.js").read_text()
    assert "access_token" not in script and "refresh_token" not in script
