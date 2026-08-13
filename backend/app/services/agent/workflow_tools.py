"""
Tools for WorkflowAgent (Phase 12) -- the broadest read+write tool surface
in the app, since this is explicitly an admin/automation capability, not a
resident-facing one. Every function wraps a services/core/ function (the
same ones REST routes, MCP tools, and committee_tools.py use). No new
business logic -- assign_vendor_to_request and mark_request_done are thin
compositions of the existing update_service_request.
"""

from typing import Any, Callable

from app.services.agent.tools import ToolContext
from app.services.core.buildings_service import list_buildings as _list_buildings
from app.services.core.dashboard_service import get_dashboard_summary as _get_dashboard_summary
from app.services.core.residents_service import search_residents as _search_residents
from app.services.core.service_requests_service import (
    create_service_request as _create_service_request,
    list_service_requests as _list_service_requests,
    resolve_flat_by_name,
    update_service_request as _update_service_request,
)
from app.services.core.vendors_service import (
    find_available_vendor as _find_available_vendor,
    list_vendors as _list_vendors,
)
from app.services.llm.base import ToolSpec

_CATEGORY_ENUM = ["Plumber", "Electrician", "Carpenter", "Pest Control"]


def list_buildings(ctx: ToolContext) -> dict:
    return {"buildings": _list_buildings(ctx.db)}


def list_vendors(ctx: ToolContext, category: str | None = None, active_only: bool = True) -> dict:
    return {"vendors": _list_vendors(ctx.db, category=category, active_only=active_only)}


def find_available_vendor(ctx: ToolContext, category: str) -> dict:
    vendor = _find_available_vendor(ctx.db, category)
    if vendor is None:
        return {"error": f"No active vendor found for category '{category}'."}
    return {"vendor": vendor}


def list_service_requests(ctx: ToolContext, status: str | None = None) -> dict:
    return {"service_requests": _list_service_requests(ctx.db, status=status)}


def create_service_request(
    ctx: ToolContext,
    building_name: str,
    flat_number: int,
    category: str,
    description: str | None = None,
) -> dict:
    flat = resolve_flat_by_name(ctx.db, building_name, flat_number)
    if flat is None:
        return {"error": f"No record for flat {flat_number} in a building matching '{building_name}'."}
    return _create_service_request(ctx.db, flat_id=flat.id, category=category, description=description)


def assign_vendor_to_request(ctx: ToolContext, request_id: int, vendor_id: int, assigned_slot: str) -> dict:
    result = _update_service_request(
        ctx.db, request_id=request_id, status="assigned", vendor_id=vendor_id, assigned_slot=assigned_slot
    )
    if result is None:
        return {"error": f"No service request with id {request_id}."}
    return result


def mark_request_done(ctx: ToolContext, request_id: int) -> dict:
    result = _update_service_request(ctx.db, request_id=request_id, status="done")
    if result is None:
        return {"error": f"No service request with id {request_id}."}
    return result


def search_residents(ctx: ToolContext, query: str) -> dict:
    results = _search_residents(ctx.db, query)
    return {"results": results, "count": len(results)}


def dashboard_summary(ctx: ToolContext) -> dict:
    return _get_dashboard_summary(ctx.db)


WORKFLOW_TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="list_buildings",
        description="List every building in the society.",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
    ToolSpec(
        name="list_vendors",
        description="List vendors, optionally filtered by category and active status.",
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": _CATEGORY_ENUM},
                "active_only": {"type": "boolean"},
            },
            "required": [],
        },
    ),
    ToolSpec(
        name="find_available_vendor",
        description=(
            "Find the active vendor in a category with the most current capacity "
            "(fewest currently-assigned requests)."
        ),
        parameters={
            "type": "object",
            "properties": {"category": {"type": "string", "enum": _CATEGORY_ENUM}},
            "required": ["category"],
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
        name="create_service_request",
        description="File a new service request for a flat identified by building name and flat number.",
        parameters={
            "type": "object",
            "properties": {
                "building_name": {"type": "string"},
                "flat_number": {"type": "integer"},
                "category": {"type": "string", "enum": _CATEGORY_ENUM},
                "description": {"type": "string"},
            },
            "required": ["building_name", "flat_number", "category"],
        },
    ),
    ToolSpec(
        name="assign_vendor_to_request",
        description="Assign a vendor and time slot to an existing service request (sets its status to assigned).",
        parameters={
            "type": "object",
            "properties": {
                "request_id": {"type": "integer"},
                "vendor_id": {"type": "integer"},
                "assigned_slot": {"type": "string"},
            },
            "required": ["request_id", "vendor_id", "assigned_slot"],
        },
    ),
    ToolSpec(
        name="mark_request_done",
        description="Mark a service request as done.",
        parameters={"type": "object", "properties": {"request_id": {"type": "integer"}}, "required": ["request_id"]},
    ),
    ToolSpec(
        name="search_residents",
        description="Search residents by name or phone number.",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
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

WORKFLOW_TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "list_buildings": list_buildings,
    "list_vendors": list_vendors,
    "find_available_vendor": find_available_vendor,
    "list_service_requests": list_service_requests,
    "create_service_request": create_service_request,
    "assign_vendor_to_request": assign_vendor_to_request,
    "mark_request_done": mark_request_done,
    "search_residents": search_residents,
    "dashboard_summary": dashboard_summary,
}