"""
Manual, interactive verification of the real Ollama + agent stack against
your real dev DB. Not part of the automated test suite (those use fakes/
mocks and run anywhere) -- this is for you to sanity-check the actual local
setup once Ollama is installed on your machine.

Prerequisites:
    1. docker-compose up postgres -d      (or the full stack)
    2. alembic upgrade head
    3. ollama pull llama3.1
    4. ollama serve                       (usually already running as a service)

Run:
    cd backend
    python scripts/verify_ollama_agent.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.building import Building
from app.models.flat import Flat, FlatStatus
from app.models.resident import Resident
from app.models.water_schedule import WaterSchedule, WaterSource
from app.services.agent.agent import SocietyAgent
from app.services.llm import get_llm_provider


def ensure_seed_data(db):
    """Creates minimal demo data if the DB is empty, so this script works
    on a completely fresh clone without manual setup."""
    if db.query(Building).count() > 0:
        return

    print("No data found -- seeding a demo building/flat/resident/water schedule...")
    building = Building(name="Building 7", has_bore_water=True)
    db.add(building)
    db.flush()

    flat = Flat(building_id=building.id, flat_number=302, status=FlatStatus.rented)
    db.add(flat)
    db.flush()

    resident = Resident(flat_id=flat.id, phone_number="+919876543210", name="Demo Resident", role="tenant")
    db.add(resident)

    db.add(WaterSchedule(source=WaterSource.corporation, start_time="08:00", end_time="10:00",
                          note="Municipal line -- fill early."))
    db.add(WaterSchedule(source=WaterSource.bore, start_time="21:00", end_time="01:00",
                          note="Alternate nights only."))
    db.commit()
    print(f"Seeded: {building.name}, Flat {flat.flat_number}, resident {resident.phone_number}\n")


def main():
    db = SessionLocal()
    ensure_seed_data(db)
    resident = db.query(Resident).first()

    provider = get_llm_provider()
    agent = SocietyAgent(provider)

    print(f"Chatting as {resident.name} ({resident.phone_number}). Ctrl+C to quit.\n")
    print("Try: 'when's bore water today?' / 'is flat 302 in building 7 vacant?' / 'my tap is leaking'\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            reply = agent.run(db, resident, user_input)
            print(f"Assistant: {reply}\n")
    except KeyboardInterrupt:
        print("\nBye.")
    finally:
        db.close()


if __name__ == "__main__":
    main()