"""
Tools for the Committee Assistant agent. Every function here wraps a
services/core/ function -- the exact same code path Phase 10's MCP server
uses and the REST routes use. No query logic lives in this file.
"""

from typing import Any, Callable

from app.services.agent.tools import ToolContext
from app.services.core.buildings_service import list_buildings as _list_buildings
from app.services.core.dashboard_service import get_dashboard_summary as _get_dashboard_summary
from app.services.core.residents_service import search_residents as _search_residents
from app.services.core.service_requests_service import list_service_requests as _list_service_requests
from app.services.core.vendors_service import list_vendors as _list_vendors
from app.services.llm.base import ToolSpec


def list_buildings(ctx: ToolContext) -> dict:
    return {"buildings": _list_buildings(ctx.db)}


def list_vendors(ctx: ToolContext, category: str | None = None, active_only: bool = True) -> dict:
    return {"vendors": _list_vendors(ctx.db, category=category, active_only=active_only)}


def list_service_requests(ctx: ToolContext, status: str | None = None) -> dict:
    return {"service_requests": _list_service_requests(ctx.db, status=status)}


def search_residents(ctx: ToolContext, query: str) -> dict:
    results = _search_residents(ctx.db, query)
    return {"results": results, "count": len(results)}


def dashboard_summary(ctx: ToolContext) -> dict:
    return _get_dashboard_summary(ctx.db)


COMMITTEE_TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="list_buildings",
        description="List every building in the society, including bore-water availability.",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        name="list_vendors",
        description="List vendors, optionally filtered by category and active status.",
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["Plumber", "Electrician", "Carpenter", "Pest Control"],
                },
                "active_only": {"type": "boolean"},
            },
            "required": [],
        },
    ),
    ToolSpec(
        name="list_service_requests",
        description="List service requests, optionally filtered by status.",
        parameters={
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["open", "assigned", "done"]}},
            "required": [],
        },
    ),
    ToolSpec(
        name="search_residents",
        description="Search residents by name or phone number (partial match).",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
    ToolSpec(
        name="dashboard_summary",
        description=(
            "Aggregate summary of the society: occupancy, vendor coverage by category, "
            "and service request status counts."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
    ),
]

COMMITTEE_TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "list_buildings": list_buildings,
    "list_vendors": list_vendors,
    "list_service_requests": list_service_requests,
    "search_residents": search_residents,
    "dashboard_summary": dashboard_summary,
}