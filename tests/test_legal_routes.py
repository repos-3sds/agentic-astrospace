"""Terms and Privacy Policy are served by the API, with no template tokens left in."""
from __future__ import annotations

import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from astrospace.api.legal_routes import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize("name, heading", [("terms", "Terms of Service"), ("privacy", "Privacy Policy")])
def test_documents_render_as_html(client, name, heading, monkeypatch):
    monkeypatch.delenv("LEGAL_OPERATOR_NAME", raising=False)
    monkeypatch.delenv("LEGAL_CONTACT_EMAIL", raising=False)
    response = client.get(f"/legal/{name}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert f"<h1>{heading}</h1>" in response.text
    assert "{{" not in response.text
    assert "the Siddha team" in response.text


def test_operator_and_contact_come_from_the_environment(client, monkeypatch):
    monkeypatch.setenv("LEGAL_OPERATOR_NAME", "Example <Pvt> Ltd")
    monkeypatch.setenv("LEGAL_CONTACT_EMAIL", "privacy@example.com")
    text = client.get("/legal/privacy").text
    assert "Example &lt;Pvt&gt; Ltd" in text
    assert 'href="mailto:privacy@example.com"' in text


def test_terms_keep_the_product_constraints(client):
    text = client.get("/legal/terms").text
    flat = re.sub(r"\s+", " ", text)
    assert "not predict death" in flat
    assert "not</strong> medical, legal, financial" in flat
    assert "traditional practices" in flat


def test_unknown_document_is_404(client):
    assert client.get("/legal/cookies").status_code == 404
