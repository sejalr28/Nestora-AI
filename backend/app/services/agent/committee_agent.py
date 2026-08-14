"""
Committee Assistant: a second agent role (Phase 11), with broader
read/aggregate tools than the Resident Assistant -- society-wide vendor and
service-request visibility, resident search, and dashboard statistics.
Every tool wraps the exact same services/core/ functions Phase 10's MCP
server calls -- no new business logic, same as resident_agent.py wrapping
services/agent/tools.py.
"""

from app.services.agent.base_agent import BaseAgent, build_system_prompt
from app.services.agent.committee_tools import COMMITTEE_TOOL_REGISTRY, COMMITTEE_TOOL_SPECS
from app.services.llm.base import LLMProvider

COMMITTEE_SYSTEM_PROMPT = build_system_prompt(
    role_description=(
        "You are the Committee Assistant for a co-op housing society, helping committee "
        "members (not individual residents) get a society-wide view: vendor coverage, "
        "open/assigned/done service requests, resident lookups, and overall occupancy "
        "statistics. Always use the available tools to check real data before answering -- "
        "never guess. Keep replies concise and factual, suitable for a committee member "
        "reviewing the dashboard. If a tool returns an error, relay it plainly rather than "
        "making something up. You do not log service requests on a resident's behalf -- "
        "direct committee members to the Service Requests page in the dashboard for that."
    ),
    tool_specs=COMMITTEE_TOOL_SPECS,
)

# Explicit, auditable tool list for this role -- deliberately excludes
# log_service_request and every other resident-write tool. The committee
# role only ever gets read/aggregate tools (see committee_tools.py); there
# is no mechanism here for a committee chat message to create or modify a
# resident's service request.
COMMITTEE_TOOLS = COMMITTEE_TOOL_SPECS


class CommitteeAgent(BaseAgent):
    def __init__(self, provider: LLMProvider, max_iterations: int = 4):
        super().__init__(
            provider=provider,
            tool_specs=COMMITTEE_TOOL_SPECS,
            tool_registry=COMMITTEE_TOOL_REGISTRY,
            system_prompt=COMMITTEE_SYSTEM_PROMPT,
            max_iterations=max_iterations,
        )