import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.building import Building
from app.models.flat import Flat, FlatStatus
from app.models.resident import Resident
from app.models.water_schedule import WaterSchedule, WaterSource


@pytest.fixture()
def db():
    """Fresh in-memory SQLite DB per test -- fast, no dependency on the dev
    Postgres container being up. Good enough for testing our own query logic;
    Postgres-specific behavior (if any is added later) still needs the real
    thing via docker-compose."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def seeded(db):
    """A building with one rented flat and one onboarded resident, plus a
    water schedule -- the minimum data the agent tools need to be exercised."""
    building = Building(name="Building 7", has_bore_water=True)
    db.add(building)
    db.flush()

    flat = Flat(building_id=building.id, flat_number=302, status=FlatStatus.rented)
    db.add(flat)
    db.flush()

    resident = Resident(flat_id=flat.id, phone_number="+919876543210", name="Sejal", role="tenant")
    db.add(resident)

    db.add(WaterSchedule(
        source=WaterSource.corporation,
        start_time=datetime.time(8, 0),
        end_time=datetime.time(10, 0),
        note="Municipal line -- fill early.",
    ))
    db.add(WaterSchedule(
        source=WaterSource.bore,
        start_time=datetime.time(21, 0),
        end_time=datetime.time(1, 0),
        note="Alternate nights only.",
    ))
    db.commit()

    return {"building": building, "flat": flat, "resident": resident}