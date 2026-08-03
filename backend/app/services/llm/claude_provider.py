"""
Anthropic Claude provider. Same LLMProvider interface as OllamaProvider --
the agent code doesn't know or care which one it's talking to. Switch to
this by setting LLM_PROVIDER=claude and ANTHROPIC_API_KEY in .env; nothing
else in the app changes.

Not wired into the default dev setup (Ollama is) since the whole point of
V1 is zero API cost -- this exists so the "modular, swap later" promise is
real code, not just a comment.
"""

from typing import Any

import anthropic

from app.services.llm.base import LLMMessage, LLMProvider, LLMResponse, ToolCall, ToolSpec


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def chat(self, messages: list[LLMMessage], tools: list[ToolSpec] | None = None) -> LLMResponse:
        system_text, anthropic_messages = self._split_system(messages)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": anthropic_messages,
        }
        if system_text:
            kwargs["system"] = system_text
        if tools:
            kwargs["tools"] = [self._to_anthropic_tool(t) for t in tools]

        response = self.client.messages.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _split_system(messages: list[LLMMessage]) -> tuple[str | None, list[dict[str, Any]]]:
        """Anthropic takes the system prompt as a separate top-level param,
        not as a message in the list -- pull it out."""
        system_text = None
        out: list[dict[str, Any]] = []

        for m in messages:
            if m.role == "system":
                system_text = m.content
                continue
            if m.role == "tool":
                # Anthropic represents a tool result as a user message containing
                # a tool_result content block, not its own "tool" role.
                out.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id,
                        "content": m.content or "",
                    }],
                })
            elif m.role == "assistant" and m.tool_calls:
                out.append({
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                        for tc in m.tool_calls
                    ],
                })
            else:
                out.append({"role": m.role, "content": m.content or ""})

        return system_text, out

    @staticmethod
    def _to_anthropic_tool(tool: ToolSpec) -> dict[str, Any]:
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }

    @staticmethod
    def _parse_response(response: Any) -> LLMResponse:
        content_text = None
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_text = (content_text or "") + block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        return LLMResponse(content=content_text, tool_calls=tool_calls, raw=response)