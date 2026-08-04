from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.building import Building
from app.schemas.building import BuildingCreate, BuildingRead

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("", response_model=list[BuildingRead])
def list_buildings(db: Session = Depends(get_db)):
    return db.query(Building).order_by(Building.name).all()


@router.post("", response_model=BuildingRead, status_code=201)
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)):
    existing = db.query(Building).filter(Building.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Building '{payload.name}' already exists")

    building = Building(**payload.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building