from types import SimpleNamespace

from google.genai import types

from astrospace.agents.base import MAX_TOOL_ROUNDS, BaseAstroAgent


class GeminiStreamAgent(BaseAstroAgent):
    system_prompt = "Reply briefly."
    tools = []


class GeminiToolAgent(BaseAstroAgent):
    system_prompt = "Use the tool."
    tools = [{
        "name": "get_number",
        "description": "Returns a test number",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }]

    def _tool_get_number(self):
        return {"number": 7}


class FakeModels:
    def __init__(self, responses=None, stream_chunks=None):
        self.responses = list(responses or [])
        self.stream_chunks = list(stream_chunks or [])

    def generate_content(self, **_kwargs):
        return self.responses.pop(0)

    def generate_content_stream(self, **_kwargs):
        return iter(self.stream_chunks)


class FakeClient:
    def __init__(self, models):
        self.models = models


def test_gemini_streaming_uses_configured_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash")
    agent = GeminiStreamAgent()
    agent.client = FakeClient(FakeModels(
        stream_chunks=[SimpleNamespace(text="sid"), SimpleNamespace(text="dha")],
    ))

    text = "".join(agent.run_messages_stream([{"role": "user", "content": "hi"}]))

    assert agent.provider == "gemini"
    assert agent.model == "gemini-3.5-flash"
    assert text == "siddha"


def test_gemini_tool_loop_dispatches_local_tools(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    tool_call = SimpleNamespace(name="get_number", args={})
    function_call_content = types.Content(
        role="model",
        parts=[types.Part.from_function_call(name="get_number", args={})],
    )
    agent = GeminiToolAgent()
    agent.client = FakeClient(FakeModels(responses=[
        SimpleNamespace(
            function_calls=[tool_call],
            candidates=[SimpleNamespace(content=function_call_content)],
            text=None,
        ),
        SimpleNamespace(function_calls=[], candidates=[], text="tool ok 7"),
    ]))

    answer, tools_used = agent.run_messages([{"role": "user", "content": "call it"}])

    assert answer == "tool ok 7"
    assert tools_used == ["get_number"]


class GeminiTwoToolAgent(GeminiToolAgent):
    tools = GeminiToolAgent.tools + [{
        "name": "get_word",
        "description": "Returns a test word",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    }]

    def _tool_get_word(self):
        return {"word": "siddha"}


class RecordingModels(FakeModels):
    def __init__(self, responses):
        super().__init__(responses=responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return super().generate_content(**kwargs)


def _calls_turn(*names):
    return SimpleNamespace(
        function_calls=[SimpleNamespace(name=n, args={}) for n in names],
        candidates=[SimpleNamespace(content=types.Content(
            role="model",
            parts=[types.Part.from_function_call(name=n, args={}) for n in names],
        ))],
        text=None,
    )


def test_gemini_parallel_calls_answer_in_one_turn(monkeypatch):
    """Readings' first turn calls its chart tools in parallel. Gemini 400s
    unless every function response of that turn comes back in one Content."""
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    models = RecordingModels([
        _calls_turn("get_number", "get_word"),
        SimpleNamespace(function_calls=[], candidates=[], text="7 siddha"),
    ])
    agent = GeminiTwoToolAgent()
    agent.client = FakeClient(models)

    answer, tools_used = agent.run_messages([{"role": "user", "content": "call both"}])

    assert answer == "7 siddha"
    assert tools_used == ["get_number", "get_word"]
    reply = models.calls[1]["contents"][-1]
    assert reply.role == "user"
    assert [p.function_response.name for p in reply.parts] == ["get_number", "get_word"]


def test_gemini_out_of_tool_rounds_asks_for_text(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    models = RecordingModels([_calls_turn("get_number") for _ in range(MAX_TOOL_ROUNDS)] + [
        SimpleNamespace(function_calls=[], candidates=[], text="answer from what I have"),
    ])
    agent = GeminiToolAgent()
    agent.client = FakeClient(models)

    answer, _ = agent.run_messages([{"role": "user", "content": "loop"}])

    assert answer == "answer from what I have"
    final = models.calls[-1]["config"]
    assert final.tool_config.function_calling_config.mode == types.FunctionCallingConfigMode.NONE
