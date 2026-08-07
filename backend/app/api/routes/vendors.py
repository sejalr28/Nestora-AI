from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.database import get_db
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorRead, VendorUpdate
from app.services.core.vendors_service import list_vendors as _list_vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorRead])
def list_vendors(category: str | None = None, active_only: bool = True, db: Session = Depends(get_db)):
    return _list_vendors(db, category=category, active_only=active_only)


@router.post("", response_model=VendorRead, status_code=201)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.patch("/{vendor_id}", response_model=VendorRead)
def update_vendor(vendor_id: int, payload: VendorUpdate, db: Session = Depends(get_db)):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise not_found("Vendor", vendor_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)

    db.commit()
    db.refresh(vendor)
    return vendor