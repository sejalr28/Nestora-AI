from pydantic import BaseModel, ConfigDict

from app.models.flat import FlatStatus
from app.schemas.building import BuildingRead


class FlatCreate(BaseModel):
    building_id: int
    flat_number: int
    status: FlatStatus = FlatStatus.unknown


class FlatUpdate(BaseModel):
    # All optional: PATCH-style partial update (e.g. just changing status).
    status: FlatStatus | None = None


class FlatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    flat_number: int
    status: FlatStatus
    building: BuildingRead
