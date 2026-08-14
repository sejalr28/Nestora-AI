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


def test_chat_defaults_to_resident_role(client, seeded):
    """No agent_role in the payload -> ResidentAgent, same as before Phase 11."""
    fake = FakeProvider([
        LLMResponse(content=_tool_call_json("log_service_request", {"category": "Plumber", "description": "leak"})),
        LLMResponse(content=_final_answer_json("done")),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post("/api/v1/assistant/chat", json={"message": "log a leak"})
    assert resp.status_code == 200
    # log_service_request only exists for ResidentAgent -- if this ran
    # under CommitteeAgent it would come back as "Unknown tool" instead.
    tool_result = fake.calls[1][-1].content
    assert "Unknown tool" not in tool_result


def test_chat_committee_role_uses_committee_tools(client, seeded):
    fake = FakeProvider([
        LLMResponse(content=_tool_call_json("dashboard_summary")),
        LLMResponse(content=_final_answer_json("Occupancy is 100%.")),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post(
        "/api/v1/assistant/chat", json={"message": "what's our occupancy?", "agent_role": "committee"}
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Occupancy is 100%."


def test_chat_committee_role_cannot_log_service_requests(client, seeded):
    """log_service_request isn't in CommitteeAgent's tool set -- confirms
    role separation is real, not just a different system prompt."""
    fake = FakeProvider([
        LLMResponse(content=_tool_call_json("log_service_request", {"category": "Plumber", "description": "leak"})),
        LLMResponse(content=_final_answer_json("can't do that here")),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post(
        "/api/v1/assistant/chat", json={"message": "log a leak", "agent_role": "committee"}
    )
    assert resp.status_code == 200
    tool_result = fake.calls[1][-1].content
    assert "Unknown tool" in tool_result


def test_chat_unknown_agent_role_falls_back_to_resident(client, seeded):
    fake = FakeProvider([LLMResponse(content="hi")])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post(
        "/api/v1/assistant/chat", json={"message": "hello", "agent_role": "not-a-real-role"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"reply": "hi"}


def test_chat_role_field_resident(client, seeded):
    """Matches this phase's exact spec example:
    {"message": "When is bore water?", "role": "resident"}"""
    fake = FakeProvider([
        LLMResponse(content=_tool_call_json("get_water_schedule", {"source": "bore"})),
        LLMResponse(content=_final_answer_json("Bore water: 9 PM - 1 AM.")),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post(
        "/api/v1/assistant/chat", json={"message": "When is bore water?", "role": "resident"}
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Bore water: 9 PM - 1 AM."


def test_chat_role_field_committee(client, seeded):
    """Matches this phase's exact spec example:
    {"message": "How many open service requests do we have?", "role": "committee"}"""
    fake = FakeProvider([
        LLMResponse(content=_tool_call_json("list_service_requests", {"status": "open"})),
        LLMResponse(content=_final_answer_json("There are 0 open requests.")),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "How many open service requests do we have?", "role": "committee"},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "There are 0 open requests."


def test_chat_role_field_takes_precedence_over_legacy_agent_role_field(client, seeded):
    fake = FakeProvider([
        LLMResponse(content=_tool_call_json("dashboard_summary")),
        LLMResponse(content=_final_answer_json("Occupancy is 100%.")),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake
    resp = client.post(
        "/api/v1/assistant/chat",
        json={"message": "occupancy?", "role": "committee", "agent_role": "resident"},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "Occupancy is 100%."