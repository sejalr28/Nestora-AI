"""
BaseAgent: the provider-agnostic JSON-action loop (unchanged from Phase 9),
now parametrized by tool set + system prompt instead of hardcoding
resident-only tools. This is what makes Phase 11's multiple agent roles
possible without duplicating the loop mechanics -- ResidentAgent and
CommitteeAgent each just configure BaseAgent with their own tools and
prompt; neither reimplements the loop.

Why this exists instead of relying on each provider's native tool-calling:
native tool-calling support (and its wire format) varies by provider and,
for Ollama in particular, by model and version -- it's a fragile thing to
depend on for a project meant to run reliably against a local model. So
instead, the agent never asks a provider for native tool calls at all (it
calls provider.chat(messages) with no `tools` argument). The available
tools are described as plain text in the system prompt, and the model is
instructed to always reply with a single JSON object describing either a
tool call or its final answer. The agent parses that JSON itself, executes
the matching tool from its tool_registry, feeds the result back as a
normal user-role message, and loops until it gets a final answer.

Loop shape: send messages -> parse the model's JSON action -> if it's a
tool call, execute it against the real DB and feed the result back as
plain conversation -> repeat, capped at max_iterations so a confused model
can't loop forever -> return the final_answer text.
"""

import json
import re

from sqlalchemy.orm import Session

from app.models.resident import Resident
from app.services.agent.tools import ToolContext
from app.services.llm.base import LLMMessage, LLMProvider, ToolSpec

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _build_tool_catalog(tool_specs: list[ToolSpec]) -> str:
    """Renders a list of ToolSpecs as plain text for a system prompt -- what
    tells the model what tools exist and what arguments each takes, since
    we're not sending them via any provider's native tools param."""
    lines = []
    for spec in tool_specs:
        lines.append(f"- {spec.name}: {spec.description}")
        lines.append(f"  Parameters (JSON schema): {json.dumps(spec.parameters)}")
    return "\n".join(lines)


def build_system_prompt(role_description: str, tool_specs: list[ToolSpec]) -> str:
    """Builds a full system prompt from a role-specific description plus
    the shared JSON-action protocol instructions every agent role needs
    (identical across roles -- only role_description and tool_specs vary)."""
    return (
        f"{role_description}\n\n"
        "Available tools:\n"
        f"{_build_tool_catalog(tool_specs)}\n\n"
        "You MUST respond with ONLY a single JSON object -- no other text, no markdown code "
        "fences -- in exactly one of these two forms:\n"
        '1. To call a tool: {"tool": "<tool_name>", "arguments": {<arguments matching that '
        "tool's parameters>}}\n"
        '2. To give your final answer, once you have enough information: '
        '{"tool": null, "final_answer": "<your reply>"}\n\n'
        "Call a tool whenever you need real data before answering. Only use final_answer once "
        "you have everything you need (or a tool has told you something can't be done)."
    )


def _parse_action(content: str | None) -> dict | None:
    """Parses the model's reply as a JSON action object. Tolerates the model
    wrapping its JSON in a markdown code fence, which some local models do
    despite being told not to. Returns None if the content isn't valid JSON
    or isn't an object -- the caller falls back to treating the raw text as
    a final answer rather than failing outright on an occasional protocol slip."""
    if not content:
        return None

    text = content.strip()
    fence_match = _CODE_FENCE_RE.match(text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    return parsed if isinstance(parsed, dict) else None


def execute_tool(tool_registry: dict, ctx: ToolContext, name: str, arguments: dict) -> dict:
    """Executes one tool call against a given registry. Shared by BaseAgent
    (single-step, reactive) and WorkflowAgent (Phase 12, multi-step planned)
    so neither reimplements this error handling."""
    fn = tool_registry.get(name)
    if not fn:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return fn(ctx, **arguments)
    except Exception as exc:  # noqa: BLE001 -- a tool failing shouldn't crash the caller
        return {"error": f"Tool '{name}' failed: {exc}"}


class BaseAgent:
    """Configure with a tool set + system prompt to get a specific agent
    role (see resident_agent.py, committee_agent.py). Never instantiated
    directly by application code -- subclasses (or direct instantiation
    with explicit tools/prompt, as tests do) are the intended use."""

    def __init__(
        self,
        provider: LLMProvider,
        tool_specs: list[ToolSpec],
        tool_registry: dict,
        system_prompt: str,
        max_iterations: int = 4,
    ):
        self.provider = provider
        self.tool_specs = tool_specs
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def run(
        self,
        db: Session,
        resident: Resident | None,
        user_message: str,
        history: list[LLMMessage] | None = None,
    ) -> str:
        ctx = ToolContext(db=db, resident=resident)
        messages: list[LLMMessage] = [LLMMessage(role="system", content=self.system_prompt)]
        messages.extend(history or [])
        messages.append(LLMMessage(role="user", content=user_message))

        for _ in range(self.max_iterations):
            # No `tools` argument -- tool use is driven entirely by the JSON
            # protocol in the system prompt, not any provider's native tool-calling.
            response = self.provider.chat(messages)
            action = _parse_action(response.content)

            if action is None:
                # Model didn't follow the JSON protocol -- relay its raw text
                # rather than failing outright on an occasional slip.
                return response.content or "Sorry, I didn't get a response for that."

            tool_name = action.get("tool")

            if not tool_name:
                return action.get("final_answer") or response.content or "Sorry, I didn't get a response for that."

            result = self._execute_tool(ctx, tool_name, action.get("arguments") or {})

            # Record the assistant's JSON action turn, then feed the tool
            # result back as an ordinary user-role message -- no special
            # "tool" role or tool_call_id needed, since this is just plain
            # conversation from every provider's point of view.
            messages.append(LLMMessage(role="assistant", content=response.content))
            messages.append(
                LLMMessage(
                    role="user",
                    content=(
                        f"Tool result for `{tool_name}`: {json.dumps(result)}\n\n"
                        "Using this result, respond again with the JSON action format -- "
                        "another tool call if you need more information, or a final_answer."
                    ),
                )
            )

        return "I wasn't able to finish looking that up -- please try rephrasing or contact the committee directly."

    def _execute_tool(self, ctx: ToolContext, name: str, arguments: dict) -> dict:
        return execute_tool(self.tool_registry, ctx, name, arguments)