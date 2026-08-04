from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.errors import not_found
from app.database import get_db
from app.models.service_request import RequestStatus, ServiceRequest
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead, ServiceRequestUpdate

router = APIRouter(prefix="/service-requests", tags=["service-requests"])

_LOAD_OPTIONS = [
    joinedload(ServiceRequest.flat),
    joinedload(ServiceRequest.requested_by),
    joinedload(ServiceRequest.vendor),
]


@router.get("", response_model=list[ServiceRequestRead])
def list_service_requests(status: RequestStatus | None = None, db: Session = Depends(get_db)):
    query = db.query(ServiceRequest).options(*_LOAD_OPTIONS)
    if status:
        query = query.filter(ServiceRequest.status == status)
    return query.order_by(ServiceRequest.created_at.desc()).all()


@router.post("", response_model=ServiceRequestRead, status_code=201)
def create_service_request(payload: ServiceRequestCreate, db: Session = Depends(get_db)):
    """For requests the committee logs directly via the dashboard. Requests
    from WhatsApp are created by the agent's log_service_request tool instead
    (see services/agent/tools.py) -- this route exists so the dashboard can
    log on a resident's behalf too, e.g. a phone-in complaint."""
    request = ServiceRequest(**payload.model_dump())
    db.add(request)
    db.commit()
    db.refresh(request)
    return db.get(ServiceRequest, request.id, options=_LOAD_OPTIONS)


@router.patch("/{request_id}", response_model=ServiceRequestRead)
def update_service_request(request_id: int, payload: ServiceRequestUpdate, db: Session = Depends(get_db)):
    """Used for both: the committee assigning a vendor+slot, and marking a
    request done -- mirrors the assign()/complete() actions in the original
    SocietyBoard prototype's RequestsPanel."""
    request = db.get(ServiceRequest, request_id)
    if not request:
        raise not_found("Service request", request_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(request, field, value)

    db.commit()
    db.refresh(request)
    return db.get(ServiceRequest, request_id, options=_LOAD_OPTIONS)