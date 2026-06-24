import os
import anthropic
from typing import Optional


class AstroClient:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-opus-4-8"

    def chat(self, messages: list, system: str = "", tools: Optional[list] = None,
             max_tokens: int = 4096):
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools
        return self.client.messages.create(**kwargs)
