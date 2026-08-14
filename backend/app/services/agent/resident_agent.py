"""
Resident Assistant: the agent role WhatsApp and the AI Assistant's default
("resident") mode use. Same tools and system prompt the original
SocietyAgent (Phase 3-9) always had -- this file just configures BaseAgent
with them instead of hardcoding them into the loop itself.
"""

from app.services.agent.base_agent import BaseAgent, build_system_prompt
from app.services.agent.tools import TOOL_REGISTRY, TOOL_SPECS
from app.services.llm.base import LLMProvider

RESIDENT_SYSTEM_PROMPT = build_system_prompt(
    role_description=(
        "You are the Society Assistant for a co-op housing society. You help residents "
        "with water timings, flat occupancy lookups, and logging service requests. "
        "Always use the available tools to check real data before answering -- never guess "
        "water timings, flat status, or request details. Keep replies short and direct, "
        "suitable for a WhatsApp message. If a tool returns an error, relay it plainly "
        "rather than making something up."
    ),
    tool_specs=TOOL_SPECS,
)

# Explicit, auditable tool list for this role -- anyone reviewing security
# boundaries can read this without tracing through BaseAgent construction.
# log_service_request's own signature (ctx, category, description) never
# accepts a resident_id or flat_id from the model -- it always writes
# against ctx.resident (the caller-supplied resident, resolved from the
# WhatsApp phone number or the authenticated session, never from LLM
# output), so the model cannot impersonate a different resident.
RESIDENT_TOOLS = TOOL_SPECS


class ResidentAgent(BaseAgent):
    def __init__(self, provider: LLMProvider, max_iterations: int = 4):
        super().__init__(
            provider=provider,
            tool_specs=TOOL_SPECS,
            tool_registry=TOOL_REGISTRY,
            system_prompt=RESIDENT_SYSTEM_PROMPT,
            max_iterations=max_iterations,
        )