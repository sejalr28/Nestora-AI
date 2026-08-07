"""
Dashboard/statistics service layer. New capability -- today this exact
aggregation only exists client-side in DashboardHomePage.jsx, computed by
combining five separate API calls in the browser. This gives MCP (and any
future caller) a single efficient server-side version. Reuses
vendors_service.list_vendors for the vendor breakdown rather than
re-querying Vendor directly.
"""

from sqlalchemy.orm import Session

from app.models.building import Building
from app.models.flat import Flat, FlatStatus
from app.models.resident import Resident
from app.models.service_request import RequestStatus, ServiceRequest
from app.services.core.vendors_service import list_vendors


def get_dashboard_summary(db: Session) -> dict:
    buildings_count = db.query(Building).count()

    flats = db.query(Flat).all()
    flats_count = len(flats)
    occupied = sum(1 for f in flats if f.status in (FlatStatus.owner, FlatStatus.rented))
    vacant = sum(1 for f in flats if f.status == FlatStatus.vacant)
    unset = flats_count - occupied - vacant
    occupancy_rate = round((occupied / flats_count) * 100) if flats_count else 0

    residents_count = db.query(Resident).count()

    active_vendors = list_vendors(db, active_only=True)
    vendors_by_category: dict[str, int] = {}
    for vendor in active_vendors:
        vendors_by_category[vendor["category"]] = vendors_by_category.get(vendor["category"], 0) + 1

    requests_by_status = {status.value: 0 for status in RequestStatus}
    for status in RequestStatus:
        requests_by_status[status.value] = (
            db.query(ServiceRequest).filter(ServiceRequest.status == status).count()
        )

    return {
        "buildings": buildings_count,
        "flats": flats_count,
        "residents": residents_count,
        "active_vendors": len(active_vendors),
        "occupancy": {
            "occupied": occupied,
            "vacant": vacant,
            "unset": unset,
            "occupancy_rate_percent": occupancy_rate,
        },
        "vendors_by_category": vendors_by_category,
        "service_requests_by_status": requests_by_status,
    }