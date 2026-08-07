from app.models.service_request import RequestStatus
from app.services.core.service_requests_service import create_service_request
from app.services.core.vendors_service import find_available_vendor, list_vendors


def _make_vendor(db, name, category="Plumber", is_active=True):
    from app.models.vendor import Vendor

    vendor = Vendor(name=name, category=category, phone_number="9000000000", is_active=is_active)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def test_list_vendors_filters_by_category_and_active(db):
    _make_vendor(db, "Ganesh Pipe Works", category="Plumber", is_active=True)
    _make_vendor(db, "Old Electrician", category="Electrician", is_active=False)

    plumbers = list_vendors(db, category="Plumber", active_only=True)
    assert [v["name"] for v in plumbers] == ["Ganesh Pipe Works"]

    all_vendors = list_vendors(db, active_only=False)
    assert len(all_vendors) == 2


def test_find_available_vendor_returns_none_when_no_active_vendor(db):
    assert find_available_vendor(db, "Plumber") is None


def test_find_available_vendor_picks_least_busy(db, seeded):
    busy = _make_vendor(db, "Busy Plumbing", category="Plumber")
    free = _make_vendor(db, "Free Plumbing", category="Plumber")

    flat_id = seeded["flat"].id
    for _ in range(2):
        request = create_service_request(db, flat_id=flat_id, category="Plumber", description="leak")
        from app.models.service_request import ServiceRequest

        db.query(ServiceRequest).filter(ServiceRequest.id == request["id"]).update(
            {"status": RequestStatus.assigned, "vendor_id": busy.id}
        )
        db.commit()

    result = find_available_vendor(db, "Plumber")
    assert result["name"] == "Free Plumbing"