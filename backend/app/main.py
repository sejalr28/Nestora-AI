"""
App entrypoint. `uvicorn app.main:app --reload` runs this.

Why this file stays thin: it only wires things together (middleware,
routers). Business logic lives in services/, DB access in models/ + routes,
so this file never grows past ~50 lines even as the app scales.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes import assistant, buildings, flats, residents, service_requests, vendors, water_schedule, whatsapp
from app.config import settings
from app.database import engine

app = FastAPI(
    title="SocietyBoard AI",
    description="AI-powered co-op housing society platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """
    Confirms the API is up AND can reach Postgres — useful for docker-compose
    healthchecks and for sanity-checking local setup before building on top.
    """
    db_status = "unknown"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # noqa: BLE001 — intentionally broad for a health probe
        db_status = f"unreachable: {exc}"

    return {
        "status": "ok",
        "environment": settings.environment,
        "database": db_status,
        "llm_provider": settings.llm_provider,
    }


app.include_router(assistant.router, prefix=settings.api_v1_prefix)
app.include_router(buildings.router, prefix=settings.api_v1_prefix)
app.include_router(flats.router, prefix=settings.api_v1_prefix)
app.include_router(residents.router, prefix=settings.api_v1_prefix)
app.include_router(water_schedule.router, prefix=settings.api_v1_prefix)
app.include_router(vendors.router, prefix=settings.api_v1_prefix)
app.include_router(service_requests.router, prefix=settings.api_v1_prefix)
app.include_router(whatsapp.router, prefix=settings.api_v1_prefix)