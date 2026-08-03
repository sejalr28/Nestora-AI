"""
Ollama provider. Talks to a locally-running `ollama serve` over HTTP --
no API key, no per-token cost. Requires the model to be pulled first:
    ollama pull llama3.1

Wire format notes (Ollama's /api/chat, as of the tool-calling support added
in 0.3+): tool_calls in the response don't carry an `id` the way OpenAI's
do, so we generate our own synthetic ids purely for our own bookkeeping in
the agent loop (matching a tool result back to the call that requested it).
When sending a tool result back, Ollama just wants role="tool" + content --
it doesn't require the id round-tripped. If you're on a very new/old Ollama
version and this drifts, that mismatch is the first place to check.
"""

import uuid
from typing import Any

import httpx

from app.services.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolCall, ToolSpec


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[LLMMessage], tools: list[ToolSpec] | None = None) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._to_ollama_message(m) for m in messages],
            "stream": False,
        }
        if tools:
            payload["tools"] = [self._to_ollama_tool(t) for t in tools]

        response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return self._parse_response(response.json())

    @staticmethod
    def _to_ollama_message(message: LLMMessage) -> dict[str, Any]:
        out: dict[str, Any] = {"role": message.role, "content": message.content or ""}
        if message.role == "tool" and message.name:
            out["name"] = message.name  # some Ollama models use this to disambiguate multiple calls
        return out

    @staticmethod
    def _to_ollama_tool(tool: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> LLMResponse:
        message = data.get("message", {})
        raw_tool_calls = message.get("tool_calls") or []

        tool_calls = [
            ToolCall(
                id=str(uuid.uuid4()),  # synthetic -- Ollama doesn't send one
                name=tc["function"]["name"],
                arguments=tc["function"].get("arguments") or {},
            )
            for tc in raw_tool_calls
        ]

        return LLMResponse(
            content=message.get("content") or None,
            tool_calls=tool_calls,
            raw=data,
        )