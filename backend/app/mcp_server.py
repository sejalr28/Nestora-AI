"""
SocietyBoard AI MCP server.

This is a fourth entry point into the same application, alongside the REST
API (api/routes/), the WhatsApp webhook, and the AI Assistant chat endpoint
(both of which go through SocietyAgent). None of those three changed to
make this possible -- every tool below is a few lines that open a DB
session via session_scope() and call a function from services/core/ (or,
for water schedule/flat status, the existing services/agent/tools.py
functions directly, completely unmodified). No tool function here contains
a db.query(...) itself.

Uses app/mcp_protocol.py -- a from-scratch, standard-library-only MCP
implementation -- instead of the official `mcp` SDK, whose pinned
dependencies conflict with this project's FastAPI/Pydantic versions.

Run (stdio transport -- what MCP Inspector and Claude Desktop/Code use):
    python -m app.mcp_server
"""

from app.database import session_scope
from app.mcp_protocol import MCPServer
from app.services.agent import tools as agent_tools
from app.services.agent.tools import ToolContext
from app.services.core.buildings_service import list_buildings as _list_buildings
from app.services.core.dashboard_service import get_dashboard_summary as _get_dashboard_summary
from app.services.core.residents_service import search_residents as _search_residents
from app.services.core.service_requests_service import (
    create_service_request as _create_service_request,
    list_service_requests as _list_service_requests,
    resolve_flat_by_name,
)
from app.services.core.vendors_service import list_vendors as _list_vendors

mcp = MCPServer("societyboard-ai")


@mcp.tool()
def get_water_schedule(source: str | None = None) -> dict:
    """Get today's water timing for corporation water and/or bore water.
    source: 'corporation', 'bore', or omit for both."""
    with session_scope() as db:
        return agent_tools.get_water_schedule(ToolContext(db=db), source=source)


@mcp.tool()
def get_flat_status(building_name: str, flat_number: int) -> dict:
    """Look up whether a specific flat is vacant, owner-occupied, rented, or unset."""
    with session_scope() as db:
        return agent_tools.get_flat_status(
            ToolContext(db=db), building_name=building_name, flat_number=flat_number
        )


@mcp.tool()
def search_residents(query: str) -> dict:
    """Search residents by name or phone number (case-insensitive substring match)."""
    with session_scope() as db:
        results = _search_residents(db, query)
        return {"results": results, "count": len(results)}


@mcp.tool()
def list_buildings() -> dict:
    """List every building in the society, including bore-water availability."""
    with session_scope() as db:
        return {"buildings": _list_buildings(db)}


@mcp.tool()
def list_vendors(category: str | None = None, active_only: bool = True) -> dict:
    """List vendors, optionally filtered by category
    (Plumber, Electrician, Carpenter, Pest Control)."""
    with session_scope() as db:
        return {"vendors": _list_vendors(db, category=category, active_only=active_only)}


@mcp.tool()
def list_service_requests(status: str | None = None) -> dict:
    """List service requests, optionally filtered by status (open, assigned, done)."""
    with session_scope() as db:
        return {"service_requests": _list_service_requests(db, status=status)}


@mcp.tool()
def create_service_request(
    building_name: str,
    flat_number: int,
    category: str,
    description: str | None = None,
) -> dict:
    """File a new maintenance/service request for a specific flat, identified
    by building name and flat number (e.g. 'Building 7', 302)."""
    with session_scope() as db:
        flat = resolve_flat_by_name(db, building_name, flat_number)
        if flat is None:
            return {"error": f"No record for flat {flat_number} in a building matching '{building_name}'."}
        return _create_service_request(db, flat_id=flat.id, category=category, description=description)


@mcp.tool()
def dashboard_summary() -> dict:
    """Aggregate summary of the society: occupancy, vendor coverage by
    category, and service request status counts."""
    with session_scope() as db:
        return _get_dashboard_summary(db)


def main():
    mcp.run()


if __name__ == "__main__":
    main()