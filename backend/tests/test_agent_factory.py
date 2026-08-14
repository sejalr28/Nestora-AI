from app.services.agent.committee_agent import CommitteeAgent
from app.services.agent.factory import (
    COMMITTEE_ROLE,
    RESIDENT_ROLE,
    ROLE_TOOL_NAMES,
    available_roles,
    get_agent,
)
from app.services.agent.resident_agent import ResidentAgent
from tests.fakes import FakeProvider


def test_get_agent_resident_role_returns_resident_agent():
    agent = get_agent(RESIDENT_ROLE, provider=FakeProvider([]))
    assert isinstance(agent, ResidentAgent)


def test_get_agent_committee_role_returns_committee_agent():
    agent = get_agent(COMMITTEE_ROLE, provider=FakeProvider([]))
    assert isinstance(agent, CommitteeAgent)


def test_get_agent_unknown_role_falls_back_to_resident():
    """An unrecognized role must never silently grant *more* access than
    the default -- falling back to the more restrictive resident role is
    the safe direction for an unexpected value."""
    agent = get_agent("not-a-real-role", provider=FakeProvider([]))
    assert isinstance(agent, ResidentAgent)


def test_get_agent_passes_through_max_iterations():
    agent = get_agent(RESIDENT_ROLE, provider=FakeProvider([]), max_iterations=7)
    assert agent.max_iterations == 7


def test_available_roles_lists_both_roles():
    assert set(available_roles()) == {RESIDENT_ROLE, COMMITTEE_ROLE}


def test_role_tool_names_mapping_is_explicit_and_disjoint():
    resident_tools = set(ROLE_TOOL_NAMES[RESIDENT_ROLE])
    committee_tools = set(ROLE_TOOL_NAMES[COMMITTEE_ROLE])

    assert resident_tools == {"get_water_schedule", "get_flat_status", "log_service_request"}
    assert committee_tools == {
        "list_buildings",
        "list_vendors",
        "list_service_requests",
        "search_residents",
        "dashboard_summary",
    }
    # the write-capable resident tool must never appear in the committee's list
    assert "log_service_request" not in committee_tools
    assert resident_tools.isdisjoint(committee_tools)


def test_agents_constructed_by_the_factory_actually_carry_the_mapped_tools():
    """Confirms ROLE_TOOL_NAMES isn't just a description that could drift
    from reality -- the agent the factory actually builds carries exactly
    that tool set."""
    resident_agent = get_agent(RESIDENT_ROLE, provider=FakeProvider([]))
    committee_agent = get_agent(COMMITTEE_ROLE, provider=FakeProvider([]))

    assert set(resident_agent.tool_registry.keys()) == set(ROLE_TOOL_NAMES[RESIDENT_ROLE])
    assert set(committee_agent.tool_registry.keys()) == set(ROLE_TOOL_NAMES[COMMITTEE_ROLE])