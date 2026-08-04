from app.services.agent.agent import SocietyAgent
from app.services.llm.base import LLMResponse, ToolCall
from tests.fakes import FakeProvider


def test_agent_answers_directly_when_no_tool_call_needed(db, seeded):
    provider = FakeProvider([LLMResponse(content="Hi! How can I help?")])
    agent = SocietyAgent(provider)

    reply = agent.run(db, seeded["resident"], "hello")

    assert reply == "Hi! How can I help?"
    assert len(provider.calls) == 1


def test_agent_executes_tool_call_and_returns_final_reply(db, seeded):
    provider = FakeProvider([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="call_1", name="get_water_schedule", arguments={"source": "bore"})],
        ),
        LLMResponse(content="Bore water comes 9 PM - 1 AM tonight."),
    ])
    agent = SocietyAgent(provider)

    reply = agent.run(db, seeded["resident"], "when's bore water today?")

    assert reply == "Bore water comes 9 PM - 1 AM tonight."
    assert len(provider.calls) == 2
    # second call to the provider must include the tool's result as a "tool" message
    second_call_roles = [m.role for m in provider.calls[1]]
    assert "tool" in second_call_roles


def test_agent_gives_up_gracefully_after_max_iterations(db, seeded):
    # Provider that ALWAYS asks for another tool call -- simulates a
    # confused/looping model. The agent must not hang forever.
    looping_response = LLMResponse(
        content=None,
        tool_calls=[ToolCall(id="call_x", name="get_water_schedule", arguments={})],
    )
    provider = FakeProvider([looping_response] * 10)
    agent = SocietyAgent(provider, max_iterations=3)

    reply = agent.run(db, seeded["resident"], "when's water?")

    assert "wasn't able to finish" in reply
    assert len(provider.calls) == 3


def test_agent_reports_unidentified_resident_cleanly(db, seeded):
    provider = FakeProvider([
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(
                id="call_1", name="log_service_request",
                arguments={"category": "Plumber", "description": "leak"},
            )],
        ),
        LLMResponse(content="I can't log that until you're onboarded."),
    ])
    agent = SocietyAgent(provider)

    reply = agent.run(db, resident=None, user_message="my tap is leaking")

    assert "onboarded" in reply.lower()