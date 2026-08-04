from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.database import get_db
from app.models.water_schedule import WaterSchedule, WaterSource
from app.schemas.water_schedule import WaterScheduleRead, WaterScheduleUpdate

router = APIRouter(prefix="/water-schedule", tags=["water-schedule"])


@router.get("", response_model=list[WaterScheduleRead])
def list_water_schedule(db: Session = Depends(get_db)):
    return db.query(WaterSchedule).order_by(WaterSchedule.source).all()


@router.put("/{source}", response_model=WaterScheduleRead)
def upsert_water_schedule(source: WaterSource, payload: WaterScheduleUpdate, db: Session = Depends(get_db)):
    """
    PUT, not PATCH: the dashboard's water-timing editor always submits a full
    start/end/note for one source (see the original SocietyBoard prototype's
    water-edit form), and this creates the row if it doesn't exist yet --
    convenient for a fresh deployment with no seed data.
    """
    schedule = db.query(WaterSchedule).filter(WaterSchedule.source == source).first()
    if schedule is None:
        if payload.start_time is None or payload.end_time is None:
            raise HTTPException(
                status_code=422,
                detail="start_time and end_time are required when creating a schedule for the first time",
            )
        schedule = WaterSchedule(source=source, start_time=payload.start_time, end_time=payload.end_time)
        db.add(schedule)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)

    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/{source}", response_model=WaterScheduleRead)
def get_water_schedule(source: WaterSource, db: Session = Depends(get_db)):
    schedule = db.query(WaterSchedule).filter(WaterSchedule.source == source).first()
    if not schedule:
        raise not_found("Water schedule for source", source.value)
    return schedule