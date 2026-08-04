from pydantic import BaseModel, ConfigDict, field_validator

from app.core.phone import normalize_phone
from app.models.resident import ResidentRole


class ResidentCreate(BaseModel):
    flat_id: int
    phone_number: str
    name: str | None = None
    role: ResidentRole | None = None

    @field_validator("phone_number")
    @classmethod
    def normalize(cls, v: str) -> str:
        return normalize_phone(v)


class ResidentUpdate(BaseModel):
    name: str | None = None
    role: ResidentRole | None = None
    flat_id: int | None = None


class ResidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    flat_id: int
    name: str | None
    phone_number: str
    role: ResidentRole | None