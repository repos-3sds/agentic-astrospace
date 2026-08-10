from fastapi.testclient import TestClient

from astrospace.admin.security import current_admin
from astrospace.agents.domain_agent import _BASE_SYSTEM
from astrospace.agents.registry import AGENT_REGISTRY
from astrospace.api.auth import AuthUser
from astrospace.context.taxonomy import taxonomy
from main import app


def _admin(role: str) -> AuthUser:
    return AuthUser(
        id=f"test-{role}",
        email=f"{role}@example.test",
        role=role,
        auth_enabled=True,
    )


def test_agent_prompt_registry_is_sourced_from_live_definitions():
    app.dependency_overrides[current_admin] = lambda: _admin("admin")
    try:
        response = TestClient(app).get("/api/v1/admin/agent-prompts")
    finally:
        app.dependency_overrides.pop(current_admin, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "agent_prompt_registry_v1"
    assert payload["base"]["prompt"] == _BASE_SYSTEM.strip()
    assert payload["editable"] is False
    assert payload["coverage"]["configured"] == len(AGENT_REGISTRY)
    assert payload["coverage"]["taxonomy_total"] == len(taxonomy())
    assert {row["id"] for row in payload["domains"]} == set(AGENT_REGISTRY)
    assert {
        row["id"]: row["addendum"] for row in payload["domains"]
    } == {
        domain_id: config.domain_addendum.strip()
        for domain_id, config in AGENT_REGISTRY.items()
    }


def test_agent_prompt_registry_rejects_reviewer_access():
    app.dependency_overrides[current_admin] = lambda: _admin("reviewer")
    try:
        response = TestClient(app).get("/api/v1/admin/agent-prompts")
    finally:
        app.dependency_overrides.pop(current_admin, None)

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator permission required"
