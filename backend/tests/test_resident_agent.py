import json

from app.services.agent.resident_agent import RESIDENT_TOOLS, ResidentAgent
from app.services.llm.base import LLMResponse
from tests.fakes import FakeProvider


def _tool_call_json(tool, arguments=None):
    return json.dumps({"tool": tool, "arguments": arguments or {}})


def _final_answer_json(text):
    return json.dumps({"tool": None, "final_answer": text})


def test_resident_agent_has_exactly_the_resident_tools():
    names = {t.name for t in RESIDENT_TOOLS}
    assert names == {"get_water_schedule", "get_flat_status", "log_service_request"}

    agent = ResidentAgent(provider=FakeProvider([]))
    assert set(agent.tool_registry.keys()) == names


def test_resident_agent_uses_the_shared_base_agent_loop():
    from app.services.agent.base_agent import BaseAgent

    assert isinstance(ResidentAgent(provider=FakeProvider([])), BaseAgent)


def test_log_service_request_tool_signature_accepts_no_resident_or_flat_id():
    """Security requirement: the LLM must never be able to supply a
    resident_id or flat_id to impersonate another resident. This asserts
    the tool function itself has no such parameter -- it structurally
    cannot accept one, regardless of what JSON arguments a model sends."""
    import inspect

    from app.services.agent.tools import log_service_request

    params = set(inspect.signature(log_service_request).parameters)
    assert "resident_id" not in params
    assert "flat_id" not in params
    assert params == {"ctx", "category", "description"}


def test_log_service_request_writes_against_the_callers_resident(db, seeded):
    """The normal path: the request always gets filed against ctx.resident
    (supplied by the caller -- WhatsApp's phone lookup), never anything
    the model provides."""
    provider = FakeProvider([
        LLMResponse(content=_tool_call_json("log_service_request", {"category": "Plumber", "description": "leak"})),
        LLMResponse(content=_final_answer_json("Logged against your flat.")),
    ])
    agent = ResidentAgent(provider)

    reply = agent.run(db, seeded["resident"], "log a leak")

    assert reply == "Logged against your flat."
    from app.models.service_request import ServiceRequest

    created = db.query(ServiceRequest).filter(ServiceRequest.flat_id == seeded["flat"].id).all()
    assert len(created) == 1
    assert created[0].requested_by_id == seeded["resident"].id


def test_log_service_request_rejects_an_attempted_resident_impersonation(db, seeded):
    """If a model tries to smuggle a resident_id/flat_id into the tool
    arguments to impersonate someone else, the attempt fails safely: the
    tool's real signature doesn't accept those keys, so it errors out
    (via the shared execute_tool error handling) instead of silently
    honoring them or crashing the whole request."""
    provider = FakeProvider([
        LLMResponse(content=_tool_call_json(
            "log_service_request",
            {"category": "Plumber", "description": "leak", "resident_id": 999, "flat_id": 999},
        )),
        LLMResponse(content=_final_answer_json("noted")),
    ])
    agent = ResidentAgent(provider)
    agent.run(db, seeded["resident"], "log a leak")

    tool_result_message = provider.calls[1][-1].content
    assert "Tool 'log_service_request' failed" in tool_result_message
    assert "unexpected keyword argument" in tool_result_message

    # and confirm nothing was actually created as a side effect of the attempt
    from app.models.service_request import ServiceRequest

    assert db.query(ServiceRequest).count() == 0


def test_resident_agent_answers_directly_without_tools(db, seeded):
    provider = FakeProvider([LLMResponse(content=_final_answer_json("Hi! How can I help?"))])
    agent = ResidentAgent(provider)

    reply = agent.run(db, seeded["resident"], "hello")

    assert reply == "Hi! How can I help?"