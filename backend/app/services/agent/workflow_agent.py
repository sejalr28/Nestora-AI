"""
WorkflowAgent: plan -> execute -> report, autonomous multi-step execution
over a goal (Phase 12).

This is deliberately a different shape from BaseAgent (Phase 9-11), which
is reactive: one message in, one tool decision at a time. WorkflowAgent is
given a goal once, produces an explicit ordered plan up front (a list of
tool calls with reasons), executes every step in that plan against the
real database, and then asks the model for a plain-language summary of
what happened. It reuses BaseAgent's JSON-parsing (_parse_action tolerates
a model wrapping its JSON in a markdown fence) and tool-execution
(execute_tool) helpers rather than reimplementing either.

Bounded like every agent in this app: max_steps caps how long a plan can
be (a runaway plan gets truncated, not executed indefinitely) -- the same
"bounded autonomy" principle as BaseAgent.max_iterations.
"""

import json

from sqlalchemy.orm import Session

from app.services.agent.base_agent import _build_tool_catalog, _parse_action, execute_tool
from app.services.agent.tools import ToolContext
from app.services.agent.workflow_tools import WORKFLOW_TOOL_REGISTRY, WORKFLOW_TOOL_SPECS
from app.services.llm.base import LLMMessage, LLMProvider, ToolSpec

DEFAULT_MAX_STEPS = 8


def build_plan_prompt(tool_specs: list[ToolSpec], max_steps: int) -> str:
    return (
        "You are a planning assistant for a co-op housing society's automation system. "
        "Given a goal, produce an ordered plan of tool calls to accomplish it. "
        f"Use at most {max_steps} steps -- prefer fewer steps over more. Only use the tools "
        "listed below; do not invent tools or arguments they don't accept.\n\n"
        "Available tools:\n"
        f"{_build_tool_catalog(tool_specs)}\n\n"
        "Respond with ONLY a single JSON object -- no other text, no markdown code fences -- "
        "in exactly this form:\n"
        '{"steps": [{"step": 1, "tool": "<tool_name>", "arguments": {...}, "reason": "<why this step>"}, ...]}\n\n'
        "If the goal doesn't require any tool calls (or can't be done with the tools available), "
        'respond with an empty steps list: {"steps": []}'
    )


def build_summary_prompt() -> str:
    return (
        "You are summarizing the results of an automated workflow for a housing society "
        "committee member. Given the original goal and what each planned step actually did, "
        "write a short, plain-language summary of what was accomplished. Explicitly mention "
        "anything that failed or was skipped -- do not gloss over errors. Respond in plain "
        "text, not JSON."
    )


class WorkflowAgent:
    def __init__(
        self,
        provider: LLMProvider,
        tool_specs: list[ToolSpec] | None = None,
        tool_registry: dict | None = None,
        max_steps: int = DEFAULT_MAX_STEPS,
    ):
        self.provider = provider
        self.tool_specs = tool_specs if tool_specs is not None else WORKFLOW_TOOL_SPECS
        self.tool_registry = tool_registry if tool_registry is not None else WORKFLOW_TOOL_REGISTRY
        self.max_steps = max_steps

    def run(self, db: Session, goal: str) -> dict:
        ctx = ToolContext(db=db, resident=None)

        plan = self._make_plan(goal)
        if plan is None or not isinstance(plan.get("steps"), list):
            return {
                "goal": goal,
                "plan": [],
                "results": [],
                "summary": "I couldn't come up with a plan for that -- try rephrasing the goal.",
            }

        raw_steps = plan["steps"]
        truncated = len(raw_steps) > self.max_steps
        steps = raw_steps[: self.max_steps]

        results = []
        for step in steps:
            tool_name = step.get("tool") if isinstance(step, dict) else None
            arguments = (step.get("arguments") or {}) if isinstance(step, dict) else {}
            result = execute_tool(self.tool_registry, ctx, tool_name, arguments)
            results.append(
                {
                    "step": step.get("step") if isinstance(step, dict) else None,
                    "tool": tool_name,
                    "arguments": arguments,
                    "reason": step.get("reason", "") if isinstance(step, dict) else "",
                    "status": "error" if isinstance(result, dict) and "error" in result else "done",
                    "result": result,
                }
            )

        summary = self._summarize(goal, results, truncated)
        return {"goal": goal, "plan": steps, "results": results, "summary": summary}

    def _make_plan(self, goal: str) -> dict | None:
        system_prompt = build_plan_prompt(self.tool_specs, self.max_steps)
        response = self.provider.chat(
            [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=goal),
            ]
        )
        return _parse_action(response.content)

    def _summarize(self, goal: str, results: list[dict], truncated: bool) -> str:
        note = (
            " (Note: the plan the model produced was longer than the step limit and was truncated.)"
            if truncated
            else ""
        )
        response = self.provider.chat(
            [
                LLMMessage(role="system", content=build_summary_prompt()),
                LLMMessage(
                    role="user",
                    content=f"Goal: {goal}{note}\n\nStep results: {json.dumps(results)}",
                ),
            ]
        )
        return response.content or "Workflow completed, but I couldn't generate a summary."