import json

from app.main import app
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMResponse
from tests.fakes import FakeProvider


def _plan(*steps):
    return json.dumps({"steps": list(steps)})


def test_run_workflow_end_to_end(client, seeded):
    fake = FakeProvider([
        LLMResponse(content=_plan(
            {"step": 1, "tool": "dashboard_summary", "arguments": {}, "reason": "check occupancy"},
        )),
        LLMResponse(content="Occupancy is currently 100%."),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake

    resp = client.post("/api/v1/workflows/run", json={"goal": "what's our occupancy?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["goal"] == "what's our occupancy?"
    assert len(body["results"]) == 1
    assert body["results"][0]["status"] == "done"
    assert body["summary"] == "Occupancy is currently 100%."


def test_run_workflow_requires_goal_field(client):
    resp = client.post("/api/v1/workflows/run", json={})
    assert resp.status_code == 422


def test_run_workflow_reports_step_errors_in_response(client, seeded):
    fake = FakeProvider([
        LLMResponse(content=_plan(
            {"step": 1, "tool": "assign_vendor_to_request", "arguments": {"request_id": 99999, "vendor_id": 1, "assigned_slot": "9 AM"}, "reason": "bad id"},
        )),
        LLMResponse(content="That request doesn't exist."),
    ])
    app.dependency_overrides[get_llm_provider] = lambda: fake

    resp = client.post("/api/v1/workflows/run", json={"goal": "assign something invalid"})

    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "error"