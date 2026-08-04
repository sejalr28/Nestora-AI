import datetime

from pydantic import BaseModel, ConfigDict

from app.models.water_schedule import WaterSource


class WaterScheduleUpdate(BaseModel):
    # All optional: the dashboard edits one source (corp or bore) at a time.
    start_time: datetime.time | None = None
    end_time: datetime.time | None = None
    note: str | None = None
    updated_by: str | None = None


class WaterScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: WaterSource
    start_time: datetime.time
    end_time: datetime.time
    note: str | None
    updated_by: str | None