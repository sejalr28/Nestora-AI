"""
Pydantic schemas mirror the ORM models but serve a different purpose:
they define what goes over the API wire, decoupled from DB structure so
we can change one without breaking the other.
"""

from pydantic import BaseModel, ConfigDict


class BuildingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    has_bore_water: bool
