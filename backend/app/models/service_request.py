"""
ServiceRequest: a resident's complaint/maintenance request. Created via
WhatsApp ("kitchen tap leaking") or the admin dashboard, then triaged
(category, vendor assignment) either by the AI agent (Step 3) or manually
by the committee via the dashboard (Step 5).
"""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class RequestStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    done = "done"


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(Integer, primary_key=True)
    flat_id = Column(Integer, ForeignKey("flats.id"), nullable=False)
    requested_by_id = Column(Integer, ForeignKey("residents.id"), nullable=True)  # nullable: dashboard-created requests may not have a resident
    category = Column(String(50), nullable=False)  # "Plumber", "Electrician", ...
    description = Column(Text, nullable=True)
    status = Column(Enum(RequestStatus), default=RequestStatus.open, nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    assigned_slot = Column(String(50), nullable=True)  # e.g. "Tomorrow 9-10 AM"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    flat = relationship("Flat", back_populates="service_requests")
    requested_by = relationship("Resident", back_populates="service_requests")
    vendor = relationship("Vendor")
