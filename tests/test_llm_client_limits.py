"""Provider call limits (production audit 2026-10-15, P1 "Timeouts").

The SDK defaults were a 600 s timeout with 2 retries (Anthropic), no timeout
(Gemini) and an uncapped Anthropic tool loop, while Cloud Run cuts the request
at 300 s. These pin the bounded, shared clients that replaced them.
"""
from types import SimpleNamespace

from astrospace.agents import base as base_module
from astrospace.agents.base import MAX_TOOL_ROUNDS, BaseAstroAgent


class _ToolAgent(BaseAstroAgent):
    system_prompt = "Use the tool."
    tools = [{
        "name": "get_number",
        "description": "Returns a test number",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }]

    def _tool_get_number(self):
        return {"number": 7}


def test_anthropic_client_is_shared_and_bounded(monkeypatch):
    monkeypatch.setattr(base_module, "_clients", {})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    first = base_module.anthropic_client()
    assert base_module.anthropic_client() is first
    assert first.max_retries == 1
    assert float(first.timeout) == 60.0


def test_agents_reuse_the_module_client(monkeypatch):
    monkeypatch.setattr(base_module, "_clients", {})
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    assert BaseAstroAgent()._anthropic_client() is BaseAstroAgent()._anthropic_client()


def test_an_injected_client_still_wins(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    agent = BaseAstroAgent()
    fake = object()
    agent.client = fake
    assert agent._anthropic_client() is fake


def test_gemini_client_has_an_explicit_timeout(monkeypatch):
    monkeypatch.setattr(base_module, "_clients", {})
    captured = {}

    class FakeGenaiClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    import google.genai as genai
    monkeypatch.setattr(genai, "Client", FakeGenaiClient)
    base_module.gemini_client("test-key")
    assert captured["http_options"].timeout == 60_000


def test_gemini_can_run_on_vertex_ai_without_a_key(monkeypatch):
    monkeypatch.setattr(base_module, "_clients", {})
    monkeypatch.setenv("GEMINI_BACKEND", "vertex")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    captured = {}

    class FakeGenaiClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    import google.genai as genai
    monkeypatch.setattr(genai, "Client", FakeGenaiClient)
    base_module.gemini_client()
    assert captured["vertexai"] is True
    assert captured["project"] == "test-project"
    assert captured["location"] == "global"
    assert "api_key" not in captured
    assert captured["http_options"].timeout == 60_000


def test_ai_studio_stays_the_default_backend(monkeypatch):
    monkeypatch.delenv("GEMINI_BACKEND", raising=False)
    assert base_module.gemini_backend() == "ai_studio"
    monkeypatch.setenv("GEMINI_BACKEND", "Vertex")
    assert base_module.gemini_backend() == "vertex"


def test_anthropic_tool_loop_is_capped(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            stop_reason="tool_use",
            content=[SimpleNamespace(type="tool_use", name="get_number", input={},
                                     id=f"t{len(calls)}")],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )

    agent = _ToolAgent()
    agent.client = SimpleNamespace(messages=SimpleNamespace(create=create))
    text, tools_used = agent.run_messages([{"role": "user", "content": "loop forever"}])
    assert len(calls) == MAX_TOOL_ROUNDS
    assert tools_used == ["get_number"] * MAX_TOOL_ROUNDS
    assert text == "Unable to generate a response."
