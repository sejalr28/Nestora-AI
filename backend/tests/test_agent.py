import json

from app.services.agent.agent import SocietyAgent
from app.services.llm.base import LLMResponse
from tests.fakes import FakeProvider


def _tool_call_json(tool, arguments=None):
    return json.dumps({"tool": tool, "arguments": arguments or {}})


def _final_answer_json(text):
    return json.dumps({"tool": None, "final_answer": text})


def test_agent_answers_directly_when_no_tool_call_needed(db, seeded):
    provider = FakeProvider([LLMResponse(content=_final_answer_json("Hi! How can I help?"))])
    agent = SocietyAgent(provider)

    reply = agent.run(db, seeded["resident"], "hello")

    assert reply == "Hi! How can I help?"
    assert len(provider.calls) == 1
    # tools are no longer sent via any provider-native mechanism -- the
    # agent drives tool use entirely through the JSON protocol in the
    # system prompt, so provider.chat() is called with no `tools` arg.
    assert provider.tools_received == [None]


def test_agent_executes_tool_call_and_returns_final_reply(db, seeded):
    provider = FakeProvider([
        LLMResponse(content=_tool_call_json("get_water_schedule", {"source": "bore"})),
        LLMResponse(content=_final_answer_json("Bore water comes 9 PM - 1 AM tonight.")),
    ])
    agent = SocietyAgent(provider)

    reply = agent.run(db, seeded["resident"], "when's bore water today?")

    assert reply == "Bore water comes 9 PM - 1 AM tonight."
    assert len(provider.calls) == 2
    # the tool result is fed back as an ordinary user-role message -- no
    # special "tool" role or tool_call_id needed anymore
    second_call_roles = [m.role for m in provider.calls[1]]
    assert second_call_roles[-1] == "user"
    assert "Tool returned:" in provider.calls[1][-1].content
    assert '"schedules"' in provider.calls[1][-1].content


def test_agent_handles_model_wrapping_json_in_a_code_fence(db, seeded):
    # Some local models add markdown fences despite being told not to --
    # the agent should still parse the action correctly.
    fenced = "```json\n" + _tool_call_json("get_water_schedule", {"source": "corporation"}) + "\n```"
    provider = FakeProvider([
        LLMResponse(content=fenced),
        LLMResponse(content=_final_answer_json("Corporation water: 8-10 AM.")),
    ])
    agent = SocietyAgent(provider)

    reply = agent.run(db, seeded["resident"], "when's corp water?")

    assert reply == "Corporation water: 8-10 AM."


def test_agent_falls_back_to_raw_text_when_model_ignores_json_protocol(db, seeded):
    # If the model replies with plain (non-JSON) text, the agent shouldn't
    # crash -- it relays the raw text as the answer.
    provider = FakeProvider([LLMResponse(content="Sorry, I'm not sure how to help with that.")])
    agent = SocietyAgent(provider)

    reply = agent.run(db, seeded["resident"], "asdkjasd")

    assert reply == "Sorry, I'm not sure how to help with that."


def test_agent_gives_up_gracefully_after_max_iterations(db, seeded):
    # Provider that ALWAYS asks for another tool call -- simulates a
    # confused/looping model. The agent must not hang forever.
    looping_response = LLMResponse(content=_tool_call_json("get_water_schedule"))
    provider = FakeProvider([looping_response] * 10)
    agent = SocietyAgent(provider, max_iterations=3)

    reply = agent.run(db, seeded["resident"], "when's water?")

    assert "wasn't able to finish" in reply
    assert len(provider.calls) == 3


def test_agent_reports_unidentified_resident_cleanly(db, seeded):
    provider = FakeProvider([
        LLMResponse(content=_tool_call_json("log_service_request", {"category": "Plumber", "description": "leak"})),
        LLMResponse(content=_final_answer_json("I can't log that until you're onboarded.")),
    ])
    agent = SocietyAgent(provider)

    reply = agent.run(db, resident=None, user_message="my tap is leaking")

    assert "onboarded" in reply.lower()