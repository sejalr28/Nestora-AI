"""
Tool definitions for the Society Assistant agent.

Each tool is a plain Python function that takes a ToolContext (DB session +
who's asking) plus whatever arguments the LLM supplied, and returns a small
JSON-serializable dict. The LLM never touches the DB directly -- it can
only call these, with these exact signatures, which is what keeps the
agent's capabilities auditable and bounded.

Security note: `resident` on ToolContext comes from the caller (resolved
from the WhatsApp phone number before the agent ever runs), never from
LLM-supplied arguments. That's deliberate -- log_service_request always
files against ctx.resident's own flat, so the model can't be prompted into
filing a complaint "for" someone else's flat.
"""

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.flat import Flat
from app.models.resident import Resident
from app.models.service_request import ServiceRequest
from app.models.water_schedule import WaterSchedule
from app.services.llm.base import ToolSpec


@dataclass
class ToolContext:
    db: Session
    resident: Resident | None = None


def get_water_schedule(ctx: ToolContext, source: str | None = None) -> dict[str, Any]:
    """source: 'corporation', 'bore', or None for both."""
    query = ctx.db.query(WaterSchedule)
    if source:
        query = query.filter(WaterSchedule.source == source)
    rows = query.all()

    if not rows:
        return {"error": "No water schedule has been set yet."}

    return {
        "schedules": [
            {
                "source": row.source.value,
                "start_time": row.start_time.strftime("%H:%M"),
                "end_time": row.end_time.strftime("%H:%M"),
                "note": row.note,
            }
            for row in rows
        ]
    }


def get_flat_status(ctx: ToolContext, building_name: str, flat_number: int) -> dict[str, Any]:
    building = ctx.db.query(Building).filter(Building.name.ilike(building_name)).first()
    if not building:
        return {"error": f"No building found matching '{building_name}'."}

    flat = (
        ctx.db.query(Flat)
        .filter(Flat.building_id == building.id, Flat.flat_number == flat_number)
        .first()
    )
    if not flat:
        return {"error": f"No record for flat {flat_number} in {building.name}."}

    return {
        "building": building.name,
        "flat_number": flat.flat_number,
        "status": flat.status.value,
    }


def log_service_request(ctx: ToolContext, category: str, description: str) -> dict[str, Any]:
    if ctx.resident is None:
        return {"error": "Can't log a request until you're onboarded with your building and flat."}

    request = ServiceRequest(
        flat_id=ctx.resident.flat_id,
        requested_by_id=ctx.resident.id,
        category=category,
        description=description,
    )
    ctx.db.add(request)
    ctx.db.commit()
    ctx.db.refresh(request)

    return {
        "request_id": request.id,
        "category": request.category,
        "status": request.status.value,
        "message": "Request logged. The committee will assign a vendor and follow up.",
    }


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="get_water_schedule",
        description="Get today's water timing for corporation water and/or bore water.",
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["corporation", "bore"],
                    "description": "Which source to look up. Omit to get both.",
                }
            },
            "required": [],
        },
    ),
    ToolSpec(
        name="get_flat_status",
        description="Look up whether a specific flat is vacant, owner-occupied, rented, or unset.",
        parameters={
            "type": "object",
            "properties": {
                "building_name": {"type": "string", "description": "e.g. 'Building 7'"},
                "flat_number": {"type": "integer", "description": "e.g. 302"},
            },
            "required": ["building_name", "flat_number"],
        },
    ),
    ToolSpec(
        name="log_service_request",
        description=(
            "File a maintenance/service request for the current resident's own flat "
            "(e.g. plumbing, electrical issue). Always for the person currently chatting."
        ),
        parameters={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["Plumber", "Electrician", "Carpenter", "Pest Control"],
                },
                "description": {"type": "string", "description": "What's wrong, in the resident's words."},
            },
            "required": ["category", "description"],
        },
    ),
]

TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "get_water_schedule": get_water_schedule,
    "get_flat_status": get_flat_status,
    "log_service_request": log_service_request,
}