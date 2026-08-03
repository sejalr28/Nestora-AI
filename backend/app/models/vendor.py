"""
Vendor: a service provider (plumber, electrician, carpenter, pest control).
Kept simple in V1 — no separate "slots" table yet, since the agent will
generate/offer availability conversationally. If slot-booking gets more
rigorous later (e.g. preventing double-booking), that's a natural V2 table.
"""

from sqlalchemy import Boolean, Column, Integer, String

from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # "Plumber", "Electrician", ...
    phone_number = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
