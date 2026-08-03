"""
Resident: a person tied to a Flat, identified by phone number. This is the
table the WhatsApp onboarding flow (Step 4) writes to: when someone messages
the bot for the first time, we create a Resident here linking their phone
number to a building + flat number they reply with.

phone_number is unique because it's how every future WhatsApp message gets
matched back to "who is this and which flat are they in."
"""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class ResidentRole(str, enum.Enum):
    owner = "owner"
    tenant = "tenant"


class Resident(Base):
    __tablename__ = "residents"

    id = Column(Integer, primary_key=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False)
    name = Column(String(120), nullable=True)  # filled in during/after onboarding
    phone_number = Column(String(20), unique=True, nullable=False, index=True)  # WhatsApp identity, e.g. +919812345678
    role = Column(Enum(ResidentRole), nullable=True)
    onboarded_at = Column(DateTime(timezone=True), server_default=func.now())

    flat = relationship("Flat", back_populates="residents")
    service_requests = relationship("ServiceRequest", back_populates="requested_by")
