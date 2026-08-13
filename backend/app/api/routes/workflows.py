from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.agent.workflow_agent import WorkflowAgent
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMProvider

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowRequest(BaseModel):
    goal: str


class WorkflowStepResult(BaseModel):
    step: int | None
    tool: str | None
    arguments: dict
    reason: str
    status: str
    result: dict


class WorkflowResponse(BaseModel):
    goal: str
    plan: list[dict]
    results: list[WorkflowStepResult]
    summary: str


@router.post("/run", response_model=WorkflowResponse)
def run_workflow(
    payload: WorkflowRequest,
    db: Session = Depends(get_db),
    provider: LLMProvider = Depends(get_llm_provider),
):
    """
    Runs an autonomous multi-step workflow toward a stated goal (Phase 12):
    plans an ordered sequence of tool calls, executes each one against the
    real database, and returns a plain-language summary alongside the
    step-by-step trace. Synchronous -- the whole plan executes within this
    one request/response, capped at WorkflowAgent's max_steps so it can't
    run indefinitely. No persistence: each run is stateless, nothing is
    saved beyond what this response returns.
    """
    agent = WorkflowAgent(provider)
    return agent.run(db, goal=payload.goal)