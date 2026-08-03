"""
Building: one of the 15 buildings in the society. Kept as its own table
(rather than a free-text string on Flat) so it can carry its own attributes
later (e.g. which buildings have a bore-water pump installed) without a
migration touching every flat row.
"""

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g. "Building 7"
    has_bore_water = Column(Boolean, default=False, nullable=False)  # not all buildings have it installed

    flats = relationship("Flat", back_populates="building", cascade="all, delete-orphan")
