"""
Provider-agnostic LLM interface.

Why this file exists: the agent (services/agent/agent.py) talks only to
this interface, never to Ollama's or Anthropic's SDK directly. Swapping
LLM_PROVIDER in .env from "ollama" to "claude" means writing zero new
agent code -- only a new class here implementing `chat()`.

Design notes:
- Tools are described with ToolSpec (name/description/JSON-schema params),
  a format every major provider can be mapped to or from. Each provider
  translates ToolSpec -> its own wire format internally.
- LLMMessage covers all four roles: system, user, assistant, and tool
  (tool = the result we send back after executing a tool call).
- LLMResponse always exposes both `content` and `tool_calls` because a
  model can return either, or both (e.g. "Let me check that." + a call).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSpec:
    """Describes one callable tool to the LLM. `parameters` is a JSON Schema
    object (the "properties"/"required"/etc. dict), not a full schema envelope --
    each provider wraps it in whatever envelope it expects."""
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class ToolCall:
    """One tool invocation requested by the model."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMMessage:
    """One turn in the conversation. For role='tool', `tool_call_id` and
    `name` link the result back to the ToolCall that requested it."""
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # provider's raw response payload, kept for debugging/logging


class LLMProvider(ABC):
    """Implement this once per provider. The agent only ever calls `chat()`."""

    @abstractmethod
    def chat(self, messages: list[LLMMessage], tools: list[ToolSpec] | None = None) -> LLMResponse:
        """Send the conversation so far (+ optional available tools) and get
        back either a text reply, one or more tool calls, or both."""
        raise NotImplementedError