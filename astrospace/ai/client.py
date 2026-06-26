import os
import anthropic
from typing import Optional


class AstroClient:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        # Session ingress tokens (sk-ant-si-*) use Bearer auth, not API key auth
        if key.startswith("sk-ant-si"):
            self.client = anthropic.Anthropic(auth_token=key)
        else:
            self.client = anthropic.Anthropic(api_key=key or None)
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
