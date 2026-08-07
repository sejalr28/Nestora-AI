"""
Buildings service layer. Framework-free: takes a Session, returns plain
dicts (via the existing BuildingRead schema, not hand-rolled serialization)
so the same function works identically whether the caller is a FastAPI
route or an MCP tool.
"""

from sqlalchemy.orm import Session

from app.models.building import Building
from app.schemas.building import BuildingRead


def list_buildings(db: Session) -> list[dict]:
    buildings = db.query(Building).order_by(Building.name).all()
    return [BuildingRead.model_validate(b).model_dump() for b in buildings]