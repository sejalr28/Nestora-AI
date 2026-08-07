from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.database import get_db
from app.models.service_request import RequestStatus, ServiceRequest
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead, ServiceRequestUpdate
from app.services.core.service_requests_service import (
    SERVICE_REQUEST_LOAD_OPTIONS,
    create_service_request as _create_service_request,
    list_service_requests as _list_service_requests,
)

router = APIRouter(prefix="/service-requests", tags=["service-requests"])


@router.get("", response_model=list[ServiceRequestRead])
def list_service_requests(status: RequestStatus | None = None, db: Session = Depends(get_db)):
    return _list_service_requests(db, status=status)


@router.post("", response_model=ServiceRequestRead, status_code=201)
def create_service_request(payload: ServiceRequestCreate, db: Session = Depends(get_db)):
    """For requests the committee logs directly via the dashboard. Requests
    from WhatsApp are created by the agent's log_service_request tool instead
    (see services/agent/tools.py) -- this route exists so the dashboard can
    log on a resident's behalf too, e.g. a phone-in complaint."""
    return _create_service_request(
        db,
        flat_id=payload.flat_id,
        category=payload.category,
        description=payload.description,
        requested_by_id=payload.requested_by_id,
    )


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
    return db.get(ServiceRequest, request_id, options=SERVICE_REQUEST_LOAD_OPTIONS)