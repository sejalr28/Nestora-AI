"""
Agent factory (Phase 11): a single place that knows how to construct the
right agent for a role. Callers (assistant.py, whatsapp.py) ask for an
agent by role name -- they never import ResidentAgent/CommitteeAgent
directly, and never duplicate provider-wiring logic.

ROLE_TOOL_NAMES exists purely for auditability: a reviewer (or a test) can
read this one dict to see exactly which tools each role can reach, without
tracing through BaseAgent construction in two different files.
"""

from app.services.agent.base_agent import BaseAgent
from app.services.agent.committee_agent import COMMITTEE_TOOLS, CommitteeAgent
from app.services.agent.resident_agent import RESIDENT_TOOLS, ResidentAgent
from app.services.llm.base import LLMProvider

RESIDENT_ROLE = "resident"
COMMITTEE_ROLE = "committee"

_AGENT_CLASSES: dict[str, type[BaseAgent]] = {
    RESIDENT_ROLE: ResidentAgent,
    COMMITTEE_ROLE: CommitteeAgent,
}

# Explicit, auditable role -> tool-name mapping.
ROLE_TOOL_NAMES: dict[str, list[str]] = {
    RESIDENT_ROLE: [t.name for t in RESIDENT_TOOLS],
    COMMITTEE_ROLE: [t.name for t in COMMITTEE_TOOLS],
}


def get_agent(role: str, provider: LLMProvider, max_iterations: int = 4) -> BaseAgent:
    """Returns the correct agent instance for a role. An unrecognized role
    falls back to the resident agent -- the more restrictive of the two --
    so a typo or unexpected value can never silently grant *more* access
    than the default."""
    agent_class = _AGENT_CLASSES.get(role, ResidentAgent)
    return agent_class(provider, max_iterations=max_iterations)


def available_roles() -> list[str]:
    return list(_AGENT_CLASSES.keys())