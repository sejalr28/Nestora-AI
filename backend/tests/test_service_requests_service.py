from app.models.service_request import RequestStatus
from app.services.core.service_requests_service import (
    count_active_requests_for_vendor,
    create_service_request,
    list_service_requests,
    resolve_flat_by_name,
    update_service_request,
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


def test_update_service_request_assigns_vendor_and_slot(db, seeded):
    from app.models.vendor import Vendor

    vendor = Vendor(name="Ganesh Pipe Works", category="Plumber", phone_number="9000000000")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    request = create_service_request(db, flat_id=seeded["flat"].id, category="Plumber")
    updated = update_service_request(
        db, request_id=request["id"], status="assigned", vendor_id=vendor.id, assigned_slot="Tomorrow 9-10 AM"
    )

    assert updated["status"] == "assigned"
    assert updated["vendor"]["name"] == "Ganesh Pipe Works"
    assert updated["assigned_slot"] == "Tomorrow 9-10 AM"


def test_update_service_request_accepts_status_as_enum_or_string(db, seeded):
    request = create_service_request(db, flat_id=seeded["flat"].id, category="Plumber")

    updated = update_service_request(db, request_id=request["id"], status=RequestStatus.done)
    assert updated["status"] == "done"

    updated = update_service_request(db, request_id=request["id"], status="open")
    assert updated["status"] == "open"


def test_update_service_request_leaves_unspecified_fields_unchanged(db, seeded):
    from app.models.vendor import Vendor

    vendor = Vendor(name="Ganesh Pipe Works", category="Plumber", phone_number="9000000000")
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    request = create_service_request(db, flat_id=seeded["flat"].id, category="Plumber")
    update_service_request(db, request_id=request["id"], status="assigned", vendor_id=vendor.id, assigned_slot="9 AM")

    # Only marking done -- vendor/slot set earlier must survive untouched.
    updated = update_service_request(db, request_id=request["id"], status="done")
    assert updated["status"] == "done"
    assert updated["vendor"]["name"] == "Ganesh Pipe Works"
    assert updated["assigned_slot"] == "9 AM"


def test_update_service_request_returns_none_for_unknown_id(db, seeded):
    assert update_service_request(db, request_id=999999, status="done") is None