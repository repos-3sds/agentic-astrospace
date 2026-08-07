import json
import os
import anthropic
from typing import Any, Iterator


class BaseAstroAgent:
    model = "claude-opus-5"
    system_prompt = ""
    tools = []

    def __init__(self, api_key: str = None):
        from dotenv import load_dotenv
        load_dotenv()
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if key.startswith("sk-ant-si"):
            self.client = anthropic.Anthropic(auth_token=key)
        else:
            self.client = anthropic.Anthropic(api_key=key or None)

    def run(self, user_input: str) -> str:
        text, _tools = self.run_messages([{"role": "user", "content": user_input}])
        return text

    def run_messages(self, messages: list) -> tuple[str, list]:
        """Agent loop over an existing conversation. Returns (text, tools_used)."""
        messages = list(messages)
        tools_used = []

        while True:
            response = self.client.messages.create(
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

    def run_messages_stream(self, messages: list) -> Iterator[str]:
        """Streaming counterpart to `run_messages`. Yields text deltas as they
        arrive instead of returning the final string, so a caller can forward
        them to a client incrementally (e.g. as SSE frames).

        Runs the same tool loop `run_messages` does. Any text is streamed as
        it arrives regardless of which turn produces it — a turn that ends in
        `tool_use` is still executed and fed back afterward. In practice a
        tool-use turn rarely emits user-facing text before the tool call, and
        no current domain agent uses tools, so this is not yet a real gap;
        revisit if a future tool-using domain agent narrates before calling.
        """
        messages = list(messages)

        while True:
            with self.client.messages.stream(
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
