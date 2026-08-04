from pydantic import BaseModel, ConfigDict

from app.models.service_request import RequestStatus
from app.schemas.flat import FlatRead
from app.schemas.resident import ResidentRead
from app.schemas.vendor import VendorRead


class ServiceRequestCreate(BaseModel):
    """For requests logged directly via the dashboard (not through WhatsApp,
    which creates these through the agent's log_service_request tool instead)."""
    flat_id: int
    requested_by_id: int | None = None
    category: str
    description: str | None = None


class ServiceRequestUpdate(BaseModel):
    status: RequestStatus | None = None
    vendor_id: int | None = None
    assigned_slot: str | None = None


class ServiceRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    flat: FlatRead
    requested_by: ResidentRead | None
    category: str
    description: str | None
    status: RequestStatus
    vendor: VendorRead | None
    assigned_slot: str | None