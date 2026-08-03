from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.errors import not_found
from app.database import get_db
from app.models.flat import Flat
from app.schemas.flat import FlatCreate, FlatRead, FlatUpdate

router = APIRouter(prefix="/flats", tags=["flats"])


@router.get("", response_model=list[FlatRead])
def list_flats(building_id: int | None = None, db: Session = Depends(get_db)):
    """List flats, optionally filtered to one building (used by the directory tab)."""
    query = db.query(Flat).options(joinedload(Flat.building))
    if building_id is not None:
        query = query.filter(Flat.building_id == building_id)
    return query.order_by(Flat.building_id, Flat.flat_number).all()


@router.get("/{flat_id}", response_model=FlatRead)
def get_flat(flat_id: int, db: Session = Depends(get_db)):
    flat = db.get(Flat, flat_id, options=[joinedload(Flat.building)])
    if not flat:
        raise not_found("Flat", flat_id)
    return flat


@router.post("", response_model=FlatRead, status_code=201)
def create_flat(payload: FlatCreate, db: Session = Depends(get_db)):
    flat = Flat(**payload.model_dump())
    db.add(flat)
    db.commit()
    db.refresh(flat)
    return flat


@router.patch("/{flat_id}", response_model=FlatRead)
def update_flat(flat_id: int, payload: FlatUpdate, db: Session = Depends(get_db)):
    """Partial update — mainly used to change occupancy status from the dashboard."""
    flat = db.get(Flat, flat_id)
    if not flat:
        raise not_found("Flat", flat_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(flat, field, value)

    db.commit()
    db.refresh(flat)
    return flat
