from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.database import get_db
from app.models.resident import Resident
from app.schemas.resident import ResidentCreate, ResidentRead, ResidentUpdate

router = APIRouter(prefix="/residents", tags=["residents"])


@router.get("", response_model=list[ResidentRead])
def list_residents(db: Session = Depends(get_db)):
    return db.query(Resident).order_by(Resident.id).all()


@router.get("/by-phone/{phone_number}", response_model=ResidentRead)
def get_resident_by_phone(phone_number: str, db: Session = Depends(get_db)):
    """
    Look up a resident by phone number. This is the endpoint the WhatsApp
    webhook (Step 4) will call on every incoming message to figure out
    "who is texting and which flat are they in" — a 404 here means the
    number hasn't been onboarded yet and the bot should start onboarding.
    """
    resident = db.query(Resident).filter(Resident.phone_number == phone_number).first()
    if not resident:
        raise not_found("Resident with phone number", phone_number)
    return resident


@router.get("/{resident_id}", response_model=ResidentRead)
def get_resident(resident_id: int, db: Session = Depends(get_db)):
    resident = db.get(Resident, resident_id)
    if not resident:
        raise not_found("Resident", resident_id)
    return resident


@router.post("", response_model=ResidentRead, status_code=201)
def create_resident(payload: ResidentCreate, db: Session = Depends(get_db)):
    """Creates a resident. This is also what WhatsApp onboarding calls once
    a new phone number replies with its building + flat number."""
    resident = Resident(**payload.model_dump())
    db.add(resident)
    db.commit()
    db.refresh(resident)
    return resident


@router.patch("/{resident_id}", response_model=ResidentRead)
def update_resident(resident_id: int, payload: ResidentUpdate, db: Session = Depends(get_db)):
    resident = db.get(Resident, resident_id)
    if not resident:
        raise not_found("Resident", resident_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(resident, field, value)

    db.commit()
    db.refresh(resident)
    return resident
