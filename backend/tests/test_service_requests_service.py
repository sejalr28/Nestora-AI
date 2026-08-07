from app.models.service_request import RequestStatus
from app.services.core.service_requests_service import (
    count_active_requests_for_vendor,
    create_service_request,
    list_service_requests,
    resolve_flat_by_name,
)


def test_create_service_request_returns_nested_flat_and_building(db, seeded):
    result = create_service_request(db, flat_id=seeded["flat"].id, category="Plumber", description="leak")
    assert result["status"] == "open"
    assert result["flat"]["flat_number"] == 302
    assert result["flat"]["building"]["name"] == "Building 7"


def test_list_service_requests_filters_by_status_string_or_enum(db, seeded):
    create_service_request(db, flat_id=seeded["flat"].id, category="Plumber")

    by_string = list_service_requests(db, status="open")
    by_enum = list_service_requests(db, status=RequestStatus.open)
    assert len(by_string) == 1
    assert len(by_enum) == 1

    assert list_service_requests(db, status="done") == []


def test_resolve_flat_by_name_matches_case_insensitively(db, seeded):
    flat = resolve_flat_by_name(db, "building 7", 302)
    assert flat is not None
    assert flat.id == seeded["flat"].id


def test_resolve_flat_by_name_returns_none_for_unknown_building(db, seeded):
    assert resolve_flat_by_name(db, "Building 99", 101) is None


def test_count_active_requests_for_vendor(db, seeded):
    from app.models.service_request import ServiceRequest
    from app.models.vendor import Vendor

    vendor = Vendor(name="Ganesh Pipe Works", category="Plumber", phone_number="9000000000")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    assert count_active_requests_for_vendor(db, vendor.id) == 0

    request = create_service_request(db, flat_id=seeded["flat"].id, category="Plumber")
    db.query(ServiceRequest).filter(ServiceRequest.id == request["id"]).update(
        {"status": RequestStatus.assigned, "vendor_id": vendor.id}
    )
    db.commit()

    assert count_active_requests_for_vendor(db, vendor.id) == 1