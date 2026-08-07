"""
Residents service layer. search_residents is a new capability -- today's
REST API only supports exact lookup (by id, or by phone for the WhatsApp
webhook), not a general search. Framework-free: takes a Session, returns
plain dicts via the existing ResidentRead schema.
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.resident import Resident
from app.schemas.resident import ResidentRead


def search_residents(db: Session, query: str) -> list[dict]:
    """Case-insensitive substring match against name or phone number."""
    pattern = f"%{query}%"
    residents = (
        db.query(Resident)
        .filter(or_(Resident.name.ilike(pattern), Resident.phone_number.ilike(pattern)))
        .order_by(Resident.id)
        .all()
    )
    return [ResidentRead.model_validate(r).model_dump() for r in residents]