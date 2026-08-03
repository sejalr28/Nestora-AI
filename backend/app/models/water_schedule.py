"""
WaterSchedule: one row per water source (corporation / bore). Kept as a
small standalone table rather than a singleton config blob because it needs
an audit trail (who last updated it, when) and because bore-water timing
genuinely varies by building in some societies — this shape supports adding
a building_id override later without a redesign.
"""

import enum

from sqlalchemy import Column, DateTime, Enum, Integer, String, Time, func

from app.database import Base


class WaterSource(str, enum.Enum):
    corporation = "corporation"
    bore = "bore"


class WaterSchedule(Base):
    __tablename__ = "water_schedules"

    id = Column(Integer, primary_key=True)
    source = Column(Enum(WaterSource), unique=True, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    note = Column(String(255), nullable=True)
    updated_by = Column(String(120), nullable=True)  # committee member name
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
