import httpx
import respx

from app.services.llm.base import LLMMessage, ToolSpec
from app.services.llm.ollama_provider import OllamaProvider


@respx.mock
def test_ollama_provider_parses_plain_text_reply():
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={
            "model": "llama3.1",
            "message": {"role": "assistant", "content": "Bore water is off tonight."},
        })
    )

    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1")
    response = provider.chat([LLMMessage(role="user", content="is bore water on tonight?")])

    assert response.content == "Bore water is off tonight."
    assert response.tool_calls == []


@respx.mock
def test_ollama_provider_parses_tool_call():
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={
            "model": "llama3.1",
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "get_water_schedule", "arguments": {"source": "bore"}}}
                ],
            },
        })
    )

    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1")
    response = provider.chat(
        [LLMMessage(role="user", content="when's bore water?")],
        tools=[ToolSpec(name="get_water_schedule", description="...", parameters={"type": "object", "properties": {}})],
    )

    assert response.content is None
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "get_water_schedule"
    assert response.tool_calls[0].arguments == {"source": "bore"}
    # id is synthetic (Ollama doesn't send one) but must exist for our own bookkeeping
    assert response.tool_calls[0].id


@respx.mock
def test_ollama_provider_sends_tools_in_expected_wire_format():
    route = respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={"message": {"role": "assistant", "content": "ok"}})
    )

    provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.1")
    provider.chat(
        [LLMMessage(role="user", content="hi")],
        tools=[ToolSpec(name="ping", description="pings", parameters={"type": "object", "properties": {}})],
    )

    sent_body = route.calls[0].request.content
    import json
    payload = json.loads(sent_body)
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "ping"