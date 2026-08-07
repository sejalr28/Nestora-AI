"""
Vendors service layer. Framework-free: takes a Session, returns plain
dicts (via the existing VendorRead schema) so REST routes and MCP tools
call the exact same code path.
"""

from sqlalchemy.orm import Session

from app.models.vendor import Vendor
from app.schemas.vendor import VendorRead
from app.services.core.service_requests_service import count_active_requests_for_vendor


def list_vendors(db: Session, category: str | None = None, active_only: bool = True) -> list[dict]:
    query = db.query(Vendor)
    if category:
        query = query.filter(Vendor.category == category)
    if active_only:
        query = query.filter(Vendor.is_active.is_(True))
    vendors = query.order_by(Vendor.category, Vendor.name).all()
    return [VendorRead.model_validate(v).model_dump() for v in vendors]


def find_available_vendor(db: Session, category: str) -> dict | None:
    """Returns the active vendor in this category with the fewest currently
    assigned (in-progress) requests -- i.e. the one with the most capacity
    right now. Returns None if no active vendor exists for the category.
    Reuses list_vendors for the base query rather than re-querying Vendor
    directly."""
    vendors = list_vendors(db, category=category, active_only=True)
    if not vendors:
        return None
    ranked = sorted(vendors, key=lambda v: count_active_requests_for_vendor(db, v["id"]))
    return ranked[0]