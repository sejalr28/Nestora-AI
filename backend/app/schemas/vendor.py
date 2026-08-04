from pydantic import BaseModel, ConfigDict


class VendorCreate(BaseModel):
    name: str
    category: str
    phone_number: str
    is_active: bool = True


class VendorUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    phone_number: str
    is_active: bool