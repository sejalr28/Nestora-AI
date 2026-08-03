"""
SocietyAgent: the tool-calling loop. Provider-agnostic -- works identically
whether `provider` is OllamaProvider or ClaudeProvider, because both speak
the same LLMProvider interface.

Loop shape: send messages -> if the model asks for tool calls, execute each
against the real DB and feed the results back as tool messages -> repeat,
capped at max_iterations so a confused model can't loop forever -> return
the first plain-text reply.
"""

import json

from sqlalchemy.orm import Session

from app.models.resident import Resident
from app.services.agent.tools import TOOL_REGISTRY, TOOL_SPECS, ToolContext
from app.services.llm.base import LLMMessage, LLMProvider

SYSTEM_PROMPT = (
    "You are the Society Assistant for a co-op housing society. You help residents "
    "with water timings, flat occupancy lookups, and logging service requests. "
    "Always use the available tools to check real data before answering -- never guess "
    "water timings, flat status, or request details. Keep replies short and direct, "
    "suitable for a WhatsApp message. If a tool returns an error, relay it plainly "
    "rather than making something up."
)


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
        messages: list[LLMMessage] = [LLMMessage(role="system", content=SYSTEM_PROMPT)]
        messages.extend(history or [])
        messages.append(LLMMessage(role="user", content=user_message))

        for _ in range(self.max_iterations):
            response = self.provider.chat(messages, tools=TOOL_SPECS)

            if not response.tool_calls:
                return response.content or "Sorry, I didn't get a response for that."

            # Record the assistant's tool-call turn, then execute each call
            # and append its result before looping back to the model.
            messages.append(
                LLMMessage(role="assistant", content=response.content, tool_calls=response.tool_calls)
            )

            for call in response.tool_calls:
                result = self._execute_tool(ctx, call.name, call.arguments)
                messages.append(
                    LLMMessage(
                        role="tool",
                        content=json.dumps(result),
                        tool_call_id=call.id,
                        name=call.name,
                    )
                )

        return "I wasn't able to finish looking that up -- please try rephrasing or contact the committee directly."

    @staticmethod
    def _execute_tool(ctx: ToolContext, name: str, arguments: dict) -> dict:
        fn = TOOL_REGISTRY.get(name)
        if not fn:
            return {"error": f"Unknown tool '{name}'."}
        try:
            return fn(ctx, **arguments)
        except Exception as exc:  # noqa: BLE001 -- a tool failing shouldn't crash the agent loop
            return {"error": f"Tool '{name}' failed: {exc}"}