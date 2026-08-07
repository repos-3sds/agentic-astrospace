import json
import os
from typing import Any, Iterator


DEFAULT_ANTHROPIC_MODEL = "claude-opus-5"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


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
        if self.provider == "gemini":
            self.model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        else:
            self.provider = "anthropic"
            self.model = os.getenv("ANTHROPIC_MODEL", self.model)

    def run(self, user_input: str) -> str:
        text, _tools = self.run_messages([{"role": "user", "content": user_input}])
        return text

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

    # Anthropic provider --------------------------------------------------

    def _anthropic_client(self):
        if self.client is not None:
            return self.client

        import anthropic

        key = self.api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if key.startswith("sk-ant-si"):
            self.client = anthropic.Anthropic(auth_token=key)
        else:
            self.client = anthropic.Anthropic(api_key=key or None)
        return self.client

    def _run_messages_anthropic(self, messages: list) -> tuple[str, list]:
        messages = list(messages)
        tools_used = []

        while True:
            response = self._anthropic_client().messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

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

        return "Unable to generate a response.", tools_used

    def _run_messages_stream_anthropic(self, messages: list) -> Iterator[str]:
        messages = list(messages)

        while True:
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

    # Gemini provider -----------------------------------------------------

    def _gemini_client(self):
        if self.client is not None:
            return self.client

        from google import genai

        key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=key)
        return self.client

    def _gemini_types(self):
        from google.genai import types
        return types

    def _gemini_config(self, include_tools: bool = True):
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

        for _ in range(8):
            response = self._gemini_client().models.generate_content(
                model=self.model,
                contents=contents,
                config=self._gemini_config(include_tools=True),
            )

            function_calls = getattr(response, "function_calls", None) or []
            if not function_calls:
                return self._response_text(response), tools_used

            if not getattr(response, "candidates", None):
                return "Unable to generate a response.", tools_used

            contents.append(response.candidates[0].content)
            for function_call in function_calls:
                name = function_call.name
                args = dict(function_call.args or {})
                tools_used.append(name)
                result = self._dispatch_tool(name, args)
                contents.append(types.Content(
                    role="tool",
                    parts=[types.Part.from_function_response(
                        name=name,
                        response={"result": result},
                    )],
                ))

        return "Unable to generate a response.", tools_used

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
            import traceback
            traceback.print_exc()
            return {"error": f"Tool {name} failed: {type(e).__name__}: {e}"}
