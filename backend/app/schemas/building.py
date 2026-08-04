"""
Pydantic schemas for Building.
"""

from pydantic import BaseModel, ConfigDict


class BuildingCreate(BaseModel):
    name: str
    has_bore_water: bool = False


class BuildingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    has_bore_water: bool