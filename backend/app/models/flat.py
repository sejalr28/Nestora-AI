"""
Flat: one unit inside a Building. `status` drives the occupancy-directory
feature (vacant/owner/rented/unknown) and is what the WhatsApp bot and admin
dashboard both read and write.
"""

import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class FlatStatus(str, enum.Enum):
    unknown = "unknown"
    owner = "owner"
    rented = "rented"
    vacant = "vacant"


class Flat(Base):
    __tablename__ = "flats"

    id = Column(Integer, primary_key=True)
    building_id = Column(Integer, ForeignKey("buildings.id"), nullable=False)
    flat_number = Column(Integer, nullable=False)  # e.g. 302 (floor 3, unit 02)
    status = Column(Enum(FlatStatus), default=FlatStatus.unknown, nullable=False)

    building = relationship("Building", back_populates="flats")
    residents = relationship("Resident", back_populates="flat", cascade="all, delete-orphan")
    service_requests = relationship("ServiceRequest", back_populates="flat")

    __table_args__ = (
        UniqueConstraint("building_id", "flat_number", name="uq_flat_building_number"),
    )
