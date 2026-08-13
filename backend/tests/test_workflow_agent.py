import json

from app.services.agent.workflow_agent import WorkflowAgent
from app.services.llm.base import LLMResponse
from tests.fakes import FakeProvider


def _plan(*steps):
    return json.dumps({"steps": list(steps)})


def test_workflow_executes_single_step_plan_and_summarizes(db, seeded):
    from app.models.vendor import Vendor

    db.add(Vendor(name="Ganesh Pipe Works", category="Plumber", phone_number="9000000000"))
    db.commit()

    provider = FakeProvider([
        LLMResponse(content=_plan(
            {"step": 1, "tool": "find_available_vendor", "arguments": {"category": "Plumber"}, "reason": "check capacity"},
        )),
        LLMResponse(content="Found Ganesh Pipe Works, who has capacity."),
    ])
    agent = WorkflowAgent(provider)

    outcome = agent.run(db, goal="find an available plumber")

    assert len(outcome["results"]) == 1
    assert outcome["results"][0]["status"] == "done"
    assert outcome["results"][0]["result"]["vendor"]["name"] == "Ganesh Pipe Works"
    assert outcome["summary"] == "Found Ganesh Pipe Works, who has capacity."
    assert len(provider.calls) == 2  # one for the plan, one for the summary


def test_workflow_executes_multi_step_plan_in_order(db, seeded):
    from app.models.vendor import Vendor
    from app.services.core.service_requests_service import create_service_request

    vendor = Vendor(name="Ganesh Pipe Works", category="Plumber", phone_number="9000000000")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    request = create_service_request(db, flat_id=seeded["flat"].id, category="Plumber", description="leak")

    provider = FakeProvider([
        LLMResponse(content=_plan(
            {"step": 1, "tool": "list_service_requests", "arguments": {"status": "open"}, "reason": "find open requests"},
            {
                "step": 2, "tool": "assign_vendor_to_request",
                "arguments": {"request_id": request["id"], "vendor_id": vendor.id, "assigned_slot": "Tomorrow 9-10 AM"},
                "reason": "assign the plumber",
            },
        )),
        LLMResponse(content="Assigned Ganesh Pipe Works to the open plumbing request."),
    ])
    agent = WorkflowAgent(provider)

    outcome = agent.run(db, goal="assign a plumber to all open plumbing requests")

    assert [r["status"] for r in outcome["results"]] == ["done", "done"]
    assert outcome["results"][1]["result"]["status"] == "assigned"


def test_workflow_records_a_failed_step_without_stopping_the_rest(db, seeded):
    provider = FakeProvider([
        LLMResponse(content=_plan(
            {"step": 1, "tool": "assign_vendor_to_request", "arguments": {"request_id": 999999, "vendor_id": 1, "assigned_slot": "9 AM"}, "reason": "bad id on purpose"},
            {"step": 2, "tool": "dashboard_summary", "arguments": {}, "reason": "sanity check afterward"},
        )),
        LLMResponse(content="Step 1 failed (unknown request); step 2 succeeded."),
    ])
    agent = WorkflowAgent(provider)

    outcome = agent.run(db, goal="assign something invalid, then check the dashboard")

    assert outcome["results"][0]["status"] == "error"
    assert outcome["results"][1]["status"] == "done"


def test_workflow_truncates_plans_longer_than_max_steps(db, seeded):
    steps = [
        {"step": i, "tool": "dashboard_summary", "arguments": {}, "reason": "padding"}
        for i in range(1, 11)  # 10 steps, exceeds the default cap of 8
    ]
    provider = FakeProvider([
        LLMResponse(content=_plan(*steps)),
        LLMResponse(content="Ran the (truncated) plan."),
    ])
    agent = WorkflowAgent(provider)

    outcome = agent.run(db, goal="do something with a huge plan")

    assert len(outcome["results"]) == 8
    # the truncation note must have reached the summarization call
    summary_call_content = provider.calls[1][-1].content
    assert "truncated" in summary_call_content.lower()


def test_workflow_handles_unparseable_plan_gracefully(db, seeded):
    provider = FakeProvider([LLMResponse(content="not json at all")])
    agent = WorkflowAgent(provider)

    outcome = agent.run(db, goal="do something vague")

    assert outcome["results"] == []
    assert outcome["plan"] == []
    assert "couldn't come up with a plan" in outcome["summary"].lower()
    assert len(provider.calls) == 1  # never reaches the summarization call


def test_workflow_handles_empty_steps_plan(db, seeded):
    provider = FakeProvider([
        LLMResponse(content=_plan()),
        LLMResponse(content="Nothing needed to be done."),
    ])
    agent = WorkflowAgent(provider)

    outcome = agent.run(db, goal="a goal needing no tool calls")

    assert outcome["results"] == []
    assert outcome["summary"] == "Nothing needed to be done."