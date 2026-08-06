import json

from app.main import app
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMResponse
from tests.fakes import FakeProvider


def _tool_call_json(tool, arguments=None):
    return json.dumps({"tool": tool, "arguments": arguments or {}})


def _final_answer_json(text):
    return json.dumps({"tool": None, "final_answer": text})


def test_chat_returns_agent_reply(client):
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [LLMResponse(content="Corporation water: 8-10 AM.")]
    )
    resp = client.post("/api/v1/assistant/chat", json={"message": "when's water today?"})
    assert resp.status_code == 200
    assert resp.json() == {"reply": "Corporation water: 8-10 AM."}


def test_chat_executes_tool_call(client, seeded):
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider([
        LLMResponse(content=_tool_call_json("get_water_schedule")),
        LLMResponse(content=_final_answer_json("Both sources checked.")),
    ])
    resp = client.post("/api/v1/assistant/chat", json={"message": "water?"})
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Both sources checked."


def test_chat_passes_history_to_agent(client):
    fake = FakeProvider([LLMResponse(content="ok")])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post("/api/v1/assistant/chat", json={
        "message": "and bore water?",
        "history": [
            {"role": "user", "content": "when's corp water?"},
            {"role": "assistant", "content": "8-10 AM"},
        ],
    })
    assert resp.status_code == 200
    roles = [m.role for m in fake.calls[0]]
    assert roles == ["system", "user", "assistant", "user"]


def test_chat_without_resident_cannot_log_request(client, seeded):
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider([
        LLMResponse(content=_tool_call_json("log_service_request", {"category": "Plumber", "description": "leak"})),
        LLMResponse(content=_final_answer_json("I can't log that without a resident.")),
    ])
    resp = client.post("/api/v1/assistant/chat", json={"message": "log a leak"})
    assert resp.status_code == 200
    assert "can't log" in resp.json()["reply"].lower()


def test_chat_requires_message_field(client):
    resp = client.post("/api/v1/assistant/chat", json={})
    assert resp.status_code == 422