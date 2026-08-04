def test_list_and_create_buildings(client):
    resp = client.post("/api/v1/buildings", json={"name": "Building 3", "has_bore_water": False})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Building 3"

    resp = client.get("/api/v1/buildings")
    assert resp.status_code == 200
    assert any(b["name"] == "Building 3" for b in resp.json())


def test_create_building_rejects_duplicate_name(client):
    client.post("/api/v1/buildings", json={"name": "Building 9"})
    resp = client.post("/api/v1/buildings", json={"name": "Building 9"})
    assert resp.status_code == 409


def test_water_schedule_upsert_creates_then_updates(client):
    resp = client.put(
        "/api/v1/water-schedule/corporation",
        json={"start_time": "08:00:00", "end_time": "10:00:00", "note": "fill early"},
    )
    assert resp.status_code == 200
    assert resp.json()["start_time"] == "08:00:00"

    resp = client.put("/api/v1/water-schedule/corporation", json={"note": "updated note"})
    assert resp.status_code == 200
    assert resp.json()["note"] == "updated note"
    assert resp.json()["start_time"] == "08:00:00"  # untouched by the partial update

    resp = client.get("/api/v1/water-schedule")
    assert len(resp.json()) == 1


def test_water_schedule_requires_times_on_first_create(client):
    resp = client.put("/api/v1/water-schedule/bore", json={"note": "no times given"})
    assert resp.status_code == 422


def test_vendor_crud_and_filtering(client):
    resp = client.post(
        "/api/v1/vendors",
        json={"name": "Ganesh Pipe Works", "category": "Plumber", "phone_number": "9822104455"},
    )
    assert resp.status_code == 201
    vendor_id = resp.json()["id"]

    resp = client.get("/api/v1/vendors?category=Plumber")
    assert len(resp.json()) == 1

    resp = client.patch(f"/api/v1/vendors/{vendor_id}", json={"is_active": False})
    assert resp.status_code == 200

    # active_only defaults to True, so the now-inactive vendor drops out
    resp = client.get("/api/v1/vendors")
    assert all(v["id"] != vendor_id for v in resp.json())


def test_service_request_create_list_and_assign(client, seeded):
    flat_id = seeded["flat"].id
    resident_id = seeded["resident"].id

    resp = client.post(
        "/api/v1/service-requests",
        json={"flat_id": flat_id, "requested_by_id": resident_id, "category": "Plumber", "description": "leak"},
    )
    assert resp.status_code == 201
    request_id = resp.json()["id"]
    assert resp.json()["flat"]["flat_number"] == 302
    assert resp.json()["status"] == "open"

    vendor_resp = client.post(
        "/api/v1/vendors", json={"name": "Shinde Plumbing", "category": "Plumber", "phone_number": "9765832210"}
    )
    vendor_id = vendor_resp.json()["id"]

    resp = client.patch(
        f"/api/v1/service-requests/{request_id}",
        json={"status": "assigned", "vendor_id": vendor_id, "assigned_slot": "Tomorrow 9-10 AM"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "assigned"
    assert resp.json()["vendor"]["name"] == "Shinde Plumbing"

    resp = client.get("/api/v1/service-requests?status=assigned")
    assert len(resp.json()) == 1