from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.llm.base import LLMMessage, ToolSpec
from app.services.llm.claude_provider import ClaudeProvider


def _fake_anthropic_response(content_blocks):
    return SimpleNamespace(content=content_blocks)


def test_claude_provider_parses_plain_text_reply():
    provider = ClaudeProvider(api_key="fake-key-not-used")
    provider.client = MagicMock()
    provider.client.messages.create.return_value = _fake_anthropic_response(
        [SimpleNamespace(type="text", text="Bore water is off tonight.")]
    )

    response = provider.chat([LLMMessage(role="user", content="is bore water on tonight?")])

    assert response.content == "Bore water is off tonight."
    assert response.tool_calls == []


def test_claude_provider_parses_tool_use_block():
    provider = ClaudeProvider(api_key="fake-key-not-used")
    provider.client = MagicMock()
    provider.client.messages.create.return_value = _fake_anthropic_response(
        [SimpleNamespace(type="tool_use", id="toolu_1", name="get_water_schedule", input={"source": "bore"})]
    )

    response = provider.chat(
        [LLMMessage(role="user", content="when's bore water?")],
        tools=[ToolSpec(name="get_water_schedule", description="...", parameters={"type": "object", "properties": {}})],
    )

    assert response.content is None
    assert response.tool_calls[0].name == "get_water_schedule"
    assert response.tool_calls[0].arguments == {"source": "bore"}


def test_claude_provider_pulls_system_message_out_of_messages_list():
    provider = ClaudeProvider(api_key="fake-key-not-used")
    provider.client = MagicMock()
    provider.client.messages.create.return_value = _fake_anthropic_response(
        [SimpleNamespace(type="text", text="ok")]
    )

    provider.chat([
        LLMMessage(role="system", content="You are the Society Assistant."),
        LLMMessage(role="user", content="hi"),
    ])

    _, kwargs = provider.client.messages.create.call_args
    assert kwargs["system"] == "You are the Society Assistant."
    assert all(m["role"] != "system" for m in kwargs["messages"])