import json
import logging
import os
import threading
from typing import Any, Iterator, TypeVar

from pydantic import BaseModel

_SchemaT = TypeVar("_SchemaT", bound=BaseModel)


def extract_usage(response: Any) -> dict:
    """Token counts from an Anthropic (`usage.input_tokens/output_tokens`)
    or Gemini (`usage_metadata.prompt_token_count/candidates_token_count`)
    response, as {"input_tokens", "output_tokens", "cached_tokens"}; zeros
    when absent. `cached_tokens` is the part of the input the provider
    billed at its cache rate (about a tenth), so the logs show how much of
    the spend caching is already saving."""
    usage = getattr(response, "usage", None)
    if usage is not None:
        return {
            "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            "cached_tokens": _int(getattr(usage, "cache_read_input_tokens", 0)),
        }
    meta = getattr(response, "usage_metadata", None)
    if meta is not None:
        return {
            "input_tokens": int(getattr(meta, "prompt_token_count", 0) or 0),
            "output_tokens": int(getattr(meta, "candidates_token_count", 0) or 0),
            "cached_tokens": _int(getattr(meta, "cached_content_token_count", 0)),
        }
    return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}


def compact_json(value: Any) -> str:
    """JSON for a prompt: no indentation and no \\u escapes. The model reads
    exactly the same data as from `indent=2`, and the chart bundle in every
    Ask prompt comes out about a third fewer characters."""
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)


def _int(value: Any) -> int:
    """A token count from an SDK field that may be None or a mock."""
    return value if isinstance(value, int) else 0


DEFAULT_ANTHROPIC_MODEL = "claude-opus-5"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

log = logging.getLogger(__name__)
# One JSON line per model call, from every feature (Ask, the daily brief,
# Telugu translation, ...), so spend can be read per feature off the logs.
usage_log = logging.getLogger("astrospace.ai.usage")

# Provider call limits. The SDK defaults were a 600 s timeout with 2 retries
# (Anthropic) and no timeout at all (Gemini), while Cloud Run cuts the request
# at 300 s — so a stuck call kept a worker thread and the spend running long
# after the reader had been shown an error. One structured answer at
# max_tokens=8192 finishes well inside 60 s; a call that doesn't is better
# failed (and repaired or reported) than waited on.
LLM_TIMEOUT_SECONDS = 60.0
LLM_MAX_RETRIES = 1
# Hard cap on model round-trips in one tool loop. Each round is a full,
# billed model call; nothing in the prompts needs more than a handful.
MAX_TOOL_ROUNDS = 6

# Module-level clients, reused across agents and requests: one connection
# pool (and one TLS handshake) per credential per process instead of one per
# Ask turn. Keyed by credential so an explicit `api_key=` still gets its own.
# Both SDK clients are safe to share between threads.
_clients: dict[tuple, Any] = {}
_clients_lock = threading.Lock()


def _shared_client(key: tuple, factory) -> Any:
    client = _clients.get(key)
    if client is None:
        with _clients_lock:
            client = _clients.get(key)
            if client is None:
                client = factory()
                _clients[key] = client
    return client


def anthropic_client(api_key: str | None = None):
    """The shared Anthropic client for this credential: 60 s timeout, 1 retry."""
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def build():
        import anthropic

        limits = {"timeout": LLM_TIMEOUT_SECONDS, "max_retries": LLM_MAX_RETRIES}
        if key.startswith("sk-ant-si"):
            return anthropic.Anthropic(auth_token=key, **limits)
        return anthropic.Anthropic(api_key=key or None, **limits)

    return _shared_client(("anthropic", key), build)


def gemini_backend() -> str:
    """"vertex" when GEMINI_BACKEND says so, else "ai_studio" (the default).

    Vertex AI serves the same Gemini models, billed to the Google Cloud
    project instead of AI Studio's prepaid credit (which ran out on
    2026-10-17 and stopped every AI feature at once). It signs in as the
    Cloud Run service account, so there is no API key to set or rotate."""
    value = os.getenv("GEMINI_BACKEND", "").strip().lower()
    return "vertex" if value in {"vertex", "vertexai", "vertex_ai"} else "ai_studio"


def gemini_client(api_key: str | None = None):
    """The shared Gemini client for this credential, with an explicit timeout."""
    from google.genai import types

    # HttpOptions.timeout is in milliseconds.
    http_options = types.HttpOptions(timeout=int(LLM_TIMEOUT_SECONDS * 1000))
    if gemini_backend() == "vertex" and not api_key:
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

        def build_vertex():
            from google import genai

            return genai.Client(
                vertexai=True, project=project or None, location=location,
                http_options=http_options,
            )

        return _shared_client(("gemini-vertex", project, location), build_vertex)

    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def build():
        from google import genai

        return genai.Client(api_key=key, http_options=http_options)

    return _shared_client(("gemini", key), build)


class BaseAstroAgent:
    model = DEFAULT_ANTHROPIC_MODEL
    system_prompt = ""
    tools = []

    def __init__(self, api_key: str = None):
        from dotenv import load_dotenv
        load_dotenv()

        self.provider = os.getenv("AI_PROVIDER", "anthropic").strip().lower()
        self.api_key = api_key
        self.client = None
        # One entry per model call this agent instance has made, in order:
        # {"purpose", "provider", "model", "input_tokens", "output_tokens"}.
        # The Ask orchestrator reads it after a turn to persist the cost of
        # the answer including its repair pass. Agents are created per turn,
        # so the ledger is per answer by construction.
        self.usage_log: list[dict] = []
        if self.provider == "gemini":
            self.model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        else:
            self.provider = "anthropic"
            self.model = os.getenv("ANTHROPIC_MODEL", self.model)

    def run(self, user_input: str) -> str:
        text, _tools = self.run_messages([{"role": "user", "content": user_input}])
        return text

    # Usage accounting ------------------------------------------------------

    def _record_usage(self, response: Any, purpose: str) -> None:
        """Append the token counts of one provider response. Tolerant of
        shape: a response without usage (a stub, an older SDK) records zeros
        rather than raising, because accounting must never cost a reader
        their answer."""
        entry = {
            "purpose": purpose, "provider": self.provider, "model": self.model,
            **extract_usage(response),
        }
        self.usage_log.append(entry)
        usage_log.info(json.dumps({"feature": type(self).__name__, **entry}))

    def usage_totals(self) -> dict:
        """Sum of `usage_log`, plus the per-call breakdown."""
        return {
            "provider": self.provider,
            "model": self.model,
            "calls": len(self.usage_log),
            "input_tokens": sum(int(u.get("input_tokens") or 0) for u in self.usage_log),
            "output_tokens": sum(int(u.get("output_tokens") or 0) for u in self.usage_log),
            "cached_tokens": sum(int(u.get("cached_tokens") or 0) for u in self.usage_log),
            "breakdown": list(self.usage_log),
        }

    def run_messages(self, messages: list) -> tuple[str, list]:
        """Agent loop over an existing conversation. Returns (text, tools_used)."""
        if self.provider == "gemini":
            return self._run_messages_gemini(messages)
        return self._run_messages_anthropic(messages)

    def run_messages_stream(self, messages: list) -> Iterator[str]:
        """Streaming counterpart to `run_messages`.

        Domain specialists currently stream without tools. Tool-backed agents
        fall back to one complete Gemini answer because the tool loop needs a
        full function-call response before it can dispatch local chart tools.
        """
        if self.provider == "gemini":
            yield from self._run_messages_stream_gemini(messages)
            return
        yield from self._run_messages_stream_anthropic(messages)

    def run_structured(
        self, messages: list, schema: type[_SchemaT], tool_name: str = "deliver_result",
        input_schema: dict | None = None,
    ) -> _SchemaT:
        """Force the model to answer via a single tool call whose input_schema
        is `schema.model_json_schema()`, then validate the call's input back
        into `schema`. Schema validity is free from Pydantic; the caller
        (the Ask orchestrator's verifier) checks content correctness — this
        method only guarantees *shape*, never grounding.

        `input_schema` overrides what the TOOL advertises while `schema`
        still governs validation — the two are deliberately separable so a
        caller can narrow a field per request (see
        `schema.reading_tool_schema()`, which compiles this request's valid
        citation set into an enum) without needing a distinct Pydantic model
        per request. Validation stays on the general model, so a provider
        that ignores the narrowed schema still produces a parseable object
        and is caught downstream by the verifier rather than crashing here.
        """
        if self.provider == "gemini":
            return self._run_structured_gemini(messages, schema, tool_name, input_schema)
        return self._run_structured_anthropic(messages, schema, tool_name, input_schema)

    def _run_structured_anthropic(
        self, messages: list, schema: type[_SchemaT], tool_name: str,
        input_schema: dict | None = None,
    ) -> _SchemaT:
        tool = {
            "name": tool_name,
            "description": f"Deliver the answer as {schema.__name__}.",
            "input_schema": input_schema or schema.model_json_schema(),
        }
        response = self._anthropic_client().messages.create(
            model=self.model,
            # 8192, not the 4096 every other call site here uses: this is the
            # structured-reading path (DomainReadingAgent et al.), and the
            # tool-call JSON has to fit acknowledgment + technical_basis +
            # interpretation + summary_and_assurance + guidance (actions,
            # remedies, follow-ups) in one payload. 2026-08-10: the domain
            # agent's ~350-word soft cap was removed in favor of completeness
            # (product spec: explanation depth is common to every persona
            # mode, never truncated) — 4096 stayed just headroom for that
            # single JSON call before, it would now risk truncating the tool
            # call mid-JSON on a genuinely multi-factor answer, surfacing as
            # `generation_failed` for no real reason. See astrospace/agents/
            # domain_agent.py's _BASE_SYSTEM rule 7.
            max_tokens=8192,
            system=self.system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
            messages=messages,
        )
        self._record_usage(response, tool_name)
        for block in response.content:
            if block.type == "tool_use" and block.name == tool_name:
                return schema.model_validate(block.input)
        raise ValueError(
            f"Model did not call {tool_name!r}; stop_reason={response.stop_reason!r}"
        )

    def _run_structured_gemini(
        self, messages: list, schema: type[_SchemaT], tool_name: str,
        input_schema: dict | None = None,
    ) -> _SchemaT:
        types = self._gemini_types()
        contents = self._gemini_contents_from_messages(messages)
        declaration = types.FunctionDeclaration(
            name=tool_name,
            description=f"Deliver the answer as {schema.__name__}.",
            parameters_json_schema=input_schema or schema.model_json_schema(),
        )
        config = types.GenerateContentConfig(
            system_instruction=self.system_prompt or None,
            # 8192 for the same reason as _run_structured_anthropic's
            # matching bump — this is the structured-reading path, and the
            # word-cap removal on the domain agent's prompt needs the room.
            max_output_tokens=8192,
            temperature=0.35,
            tools=[types.Tool(function_declarations=[declaration])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY", allowed_function_names=[tool_name],
                ),
            ),
        )
        response = self._gemini_client().models.generate_content(
            model=self.model, contents=contents, config=config,
        )
        self._record_usage(response, tool_name)
        for call in getattr(response, "function_calls", None) or []:
            if call.name == tool_name:
                return schema.model_validate(dict(call.args or {}))
        raise ValueError(f"Model did not call {tool_name!r}")

    # Anthropic provider --------------------------------------------------

    def _anthropic_client(self):
        # `self.client` stays an override point (tests inject fakes there);
        # otherwise every agent shares the process-wide client.
        if self.client is not None:
            return self.client
        return anthropic_client(self.api_key)

    def _run_messages_anthropic(self, messages: list) -> tuple[str, list]:
        messages = list(messages)
        tools_used = []

        for _round in range(MAX_TOOL_ROUNDS):
            response = self._anthropic_client().messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )
            self._record_usage(response, "messages")

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text, tools_used
                return "", tools_used

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tools_used.append(block.name)
                        result = self._dispatch_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            break
        else:
            log.warning("anthropic tool loop hit the %d-round cap", MAX_TOOL_ROUNDS)

        return "Unable to generate a response.", tools_used

    def _run_messages_stream_anthropic(self, messages: list) -> Iterator[str]:
        messages = list(messages)

        for _round in range(MAX_TOOL_ROUNDS):
            with self._anthropic_client().messages.stream(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
                response = stream.get_final_message()
            self._record_usage(response, "messages_stream")

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._dispatch_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                messages.append({"role": "user", "content": tool_results})
                continue

            return
        log.warning("anthropic streamed tool loop hit the %d-round cap", MAX_TOOL_ROUNDS)

    # Gemini provider -----------------------------------------------------

    def _gemini_client(self):
        if self.client is not None:
            return self.client
        return gemini_client(self.api_key)

    def _gemini_types(self):
        from google.genai import types
        return types

    def _gemini_config(self, include_tools: bool = True, allow_calls: bool = True):
        types = self._gemini_types()
        kwargs = {
            "system_instruction": self.system_prompt or None,
            "max_output_tokens": 4096,
            "temperature": 0.35,
        }
        if include_tools and self.tools:
            declarations = [
                types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters_json_schema=tool.get("input_schema", {
                        "type": "object",
                        "properties": {},
                    }),
                )
                for tool in self.tools
            ]
            kwargs["tools"] = [types.Tool(function_declarations=declarations)]
            if not allow_calls:
                # Tools stay declared (the history holds calls to them) but
                # the model must answer in text.
                kwargs["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="NONE"),
                )
        return types.GenerateContentConfig(**kwargs)

    def _gemini_contents_from_messages(self, messages: list):
        types = self._gemini_types()
        contents = []
        for message in messages:
            role = "model" if message.get("role") == "assistant" else "user"
            content = message.get("content", "")
            if isinstance(content, str):
                text = content
            else:
                text = json.dumps(content, default=str)
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=text)],
            ))
        return contents

    def _response_text(self, response) -> str:
        text = getattr(response, "text", None)
        if text:
            return text
        parts = []
        for candidate in getattr(response, "candidates", []) or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                part_text = getattr(part, "text", None)
                if part_text:
                    parts.append(part_text)
        return "".join(parts)

    def _run_messages_gemini(self, messages: list) -> tuple[str, list]:
        types = self._gemini_types()
        contents = self._gemini_contents_from_messages(messages)
        tools_used = []

        for _ in range(MAX_TOOL_ROUNDS):
            response = self._gemini_client().models.generate_content(
                model=self.model,
                contents=contents,
                config=self._gemini_config(include_tools=True),
            )
            self._record_usage(response, "messages")

            function_calls = getattr(response, "function_calls", None) or []
            if not function_calls:
                return self._response_text(response), tools_used

            if not getattr(response, "candidates", None):
                return "Unable to generate a response.", tools_used

            contents.append(response.candidates[0].content)
            # Every response to one model turn goes back in ONE user turn.
            # Gemini rejects a request whose function-response parts don't
            # match the function-call parts of the turn before (400 "number
            # of function response parts is equal to the number of function
            # call parts"), which is what one Content per call produced as
            # soon as the model called two tools in parallel. The SDK's own
            # automatic function calling builds the turn the same way.
            response_parts = []
            for function_call in function_calls:
                name = function_call.name
                args = dict(function_call.args or {})
                tools_used.append(name)
                result = self._dispatch_tool(name, args)
                response_parts.append(types.Part.from_function_response(
                    name=name,
                    response={"result": result},
                ))
            contents.append(types.Content(role="user", parts=response_parts))

        # Out of tool rounds: ask once more with tools off so the model writes
        # its answer from what it already fetched, rather than handing the
        # caller a placeholder it might persist as if it were the answer.
        response = self._gemini_client().models.generate_content(
            model=self.model,
            contents=contents,
            config=self._gemini_config(include_tools=True, allow_calls=False),
        )
        self._record_usage(response, "messages")
        return self._response_text(response) or "Unable to generate a response.", tools_used

    def _run_messages_stream_gemini(self, messages: list) -> Iterator[str]:
        if self.tools:
            text, _tools_used = self._run_messages_gemini(messages)
            if text:
                yield text
            return

        contents = self._gemini_contents_from_messages(messages)
        for chunk in self._gemini_client().models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=self._gemini_config(include_tools=False),
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text

    # Local tool dispatch -------------------------------------------------

    def _dispatch_tool(self, name: str, inputs: dict) -> Any:
        method = getattr(self, f"_tool_{name}", None)
        if not method:
            return {"error": f"Unknown tool: {name}"}
        try:
            return method(**inputs)
        except Exception as e:
            # Surface the failure to the model so it can adapt or report,
            # instead of crashing the whole agent run.
            log.exception("tool %s failed", name)
            return {"error": f"Tool {name} failed: {type(e).__name__}: {e}"}
