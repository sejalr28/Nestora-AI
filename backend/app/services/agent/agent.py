"""
SocietyAgent: a provider-agnostic JSON-action loop.
"""

import json
import re

from sqlalchemy.orm import Session

from app.models.resident import Resident
from app.services.agent.tools import TOOL_REGISTRY, TOOL_SPECS, ToolContext
from app.services.llm.base import LLMMessage, LLMProvider

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _build_tool_catalog() -> str:
    lines = []
    for spec in TOOL_SPECS:
        lines.append(f"- {spec.name}: {spec.description}")
        lines.append(
            f"  Parameters (JSON schema): {json.dumps(spec.parameters)}"
        )
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are the Society Assistant for a co-op housing society.\n\n"
    "Available tools:\n"
    f"{_build_tool_catalog()}\n\n"
    "Always reply ONLY with valid JSON.\n\n"
    'Tool call:\n{"tool":"tool_name","arguments":{...}}\n\n'
    'Final answer:\n{"tool":null,"final_answer":"your reply"}'
)


def _parse_action(content: str | None):
    if not content:
        return None

    text = content.strip()

    match = _CODE_FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()

    try:
        parsed = json.loads(text)
    except Exception:
        return None

    return parsed if isinstance(parsed, dict) else None


class SocietyAgent:

    def __init__(self, provider: LLMProvider, max_iterations: int = 4):
        self.provider = provider
        self.max_iterations = max_iterations

    def run(
        self,
        db: Session,
        resident: Resident | None,
        user_message: str,
        history: list[LLMMessage] | None = None,
    ) -> str:

        ctx = ToolContext(db=db, resident=resident)

        messages = [
            LLMMessage(role="system", content=SYSTEM_PROMPT)
        ]

        messages.extend(history or [])
        messages.append(
            LLMMessage(role="user", content=user_message)
        )

        for iteration in range(self.max_iterations):

            response = self.provider.chat(messages)

            print("=" * 70)
            print("Iteration", iteration + 1)
            print(response.content)
            print("=" * 70)

            action = _parse_action(response.content)

            if action is None:
                return response.content or "No response."

            tool = action.get("tool")

            if tool is None:
                return (
                    action.get("final_answer")
                    or response.content
                    or "No response."
                )

            print("Executing:", tool)
            print("Arguments:", action.get("arguments"))

            result = self._execute_tool(
                ctx,
                tool,
                action.get("arguments") or {},
            )

            print("Tool Result:", result)

            if "error" in result:
                return result["error"]

            messages.append(
                LLMMessage(
                    role="assistant",
                    content=response.content,
                )
            )

            messages.append(
                LLMMessage(
                    role="user",
                    content=(
                        f"Tool returned:\n{json.dumps(result)}\n\n"
                        "Do NOT call the same tool again.\n"
                        "If you have enough information, reply ONLY as:\n"
                        '{"tool":null,"final_answer":"..."}'
                    ),
                )
            )

        return (
            "I wasn't able to finish looking that up -- "
            "please try rephrasing or contact the committee directly."
        )

    @staticmethod
    def _execute_tool(
        ctx: ToolContext,
        name: str,
        arguments: dict,
    ) -> dict:

        fn = TOOL_REGISTRY.get(name)

        if not fn:
            return {"error": f"Unknown tool '{name}'."}

        try:
            return fn(ctx, **arguments)

        except Exception as exc:
            return {"error": str(exc)}