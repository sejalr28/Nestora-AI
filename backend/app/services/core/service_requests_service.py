"""
Service requests service layer. Framework-free: takes a Session, returns
plain dicts (via the existing ServiceRequestRead schema) so REST routes and
MCP tools call the exact same code path.
"""

from sqlalchemy.orm import Session, joinedload

from app.models.building import Building
from app.models.flat import Flat
from app.models.service_request import RequestStatus, ServiceRequest
from app.schemas.service_request import ServiceRequestRead

SERVICE_REQUEST_LOAD_OPTIONS = [
    joinedload(ServiceRequest.flat),
    joinedload(ServiceRequest.requested_by),
    joinedload(ServiceRequest.vendor),
]


def list_service_requests(db: Session, status: RequestStatus | str | None = None) -> list[dict]:
    if isinstance(status, str):
        status = RequestStatus(status)

    query = db.query(ServiceRequest).options(*SERVICE_REQUEST_LOAD_OPTIONS)
    if status:
        query = query.filter(ServiceRequest.status == status)
    requests = query.order_by(ServiceRequest.created_at.desc()).all()
    return [ServiceRequestRead.model_validate(r).model_dump() for r in requests]


def create_service_request(
    db: Session,
    flat_id: int,
    category: str,
    description: str | None = None,
    requested_by_id: int | None = None,
) -> dict:
    """For requests logged directly (dashboard or MCP). Requests from
    WhatsApp are created by the agent's log_service_request tool instead
    (see services/agent/tools.py) -- that path stays independent since it
    also enforces "always the current resident's own flat", which doesn't
    apply to a dashboard- or MCP-originated request."""
    request = ServiceRequest(
        flat_id=flat_id,
        category=category,
        description=description,
        requested_by_id=requested_by_id,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    loaded = db.get(ServiceRequest, request.id, options=SERVICE_REQUEST_LOAD_OPTIONS)
    return ServiceRequestRead.model_validate(loaded).model_dump()


def update_service_request(
    db: Session,
    request_id: int,
    status: RequestStatus | str | None = None,
    vendor_id: int | None = None,
    assigned_slot: str | None = None,
) -> dict | None:
    """Used for both: assigning a vendor+slot, and marking a request done --
    mirrors the assign()/complete() actions in the original SocietyBoard
    prototype's RequestsPanel. Returns None if the request doesn't exist
    (framework-free -- the caller, REST route or agent tool, decides how to
    report that: an HTTPException for REST, a plain {"error": ...} dict for
    an agent tool). Only fields explicitly passed (non-None) are updated --
    None here means "leave unchanged," not "clear the field.\""""
    request = db.get(ServiceRequest, request_id)
    if not request:
        return None

    if isinstance(status, str):
        status = RequestStatus(status)

    if status is not None:
        request.status = status
    if vendor_id is not None:
        request.vendor_id = vendor_id
    if assigned_slot is not None:
        request.assigned_slot = assigned_slot

    db.commit()
    db.refresh(request)
    loaded = db.get(ServiceRequest, request_id, options=SERVICE_REQUEST_LOAD_OPTIONS)
    return ServiceRequestRead.model_validate(loaded).model_dump()


def count_active_requests_for_vendor(db: Session, vendor_id: int) -> int:
    """How many currently-assigned (in-progress) requests a vendor has --
    used by find_available_vendor to rank vendors by current capacity."""
    return (
        db.query(ServiceRequest)
        .filter(ServiceRequest.vendor_id == vendor_id, ServiceRequest.status == RequestStatus.assigned)
        .count()
    )


def resolve_flat_by_name(db: Session, building_name: str, flat_number: int) -> Flat | None:
    """Looks up a Flat from a human-friendly building name + flat number --
    used by MCP's create_service_request tool, since MCP callers shouldn't
    need to know internal database IDs the way a dashboard form (which has
    dropdowns populated from /buildings and /flats) already does."""
    building = db.query(Building).filter(Building.name.ilike(building_name)).first()
    if not building:
        return None
    return (
        db.query(Flat)
        .filter(Flat.building_id == building.id, Flat.flat_number == flat_number)
        .first()
    )