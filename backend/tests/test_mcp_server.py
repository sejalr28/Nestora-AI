from contextlib import contextmanager

import pytest

from app import mcp_server


@pytest.fixture(autouse=True)
def patch_session_scope(monkeypatch, db):
    """mcp_server's tools call session_scope() (bound to the real Postgres
    engine) internally -- patch it to yield the test's sqlite fixture
    instead, the same way FastAPI route tests override get_db."""

    @contextmanager
    def fake_session_scope():
        yield db

    monkeypatch.setattr(mcp_server, "session_scope", fake_session_scope)


def test_get_water_schedule(seeded):
    result = mcp_server.get_water_schedule(source="bore")
    assert result["schedules"][0]["source"] == "bore"


def test_get_flat_status(seeded):
    result = mcp_server.get_flat_status(building_name="Building 7", flat_number=302)
    assert result == {"building": "Building 7", "flat_number": 302, "status": "rented"}


def test_search_residents(seeded):
    result = mcp_server.search_residents(query="Sejal")
    assert result["count"] == 1
    assert result["results"][0]["name"] == "Sejal"


def test_list_buildings(seeded):
    result = mcp_server.list_buildings()
    assert result["buildings"] == [{"id": seeded["building"].id, "name": "Building 7", "has_bore_water": True}]


def test_list_vendors(db, seeded):
    from app.models.vendor import Vendor

    db.add(Vendor(name="Ganesh Pipe Works", category="Plumber", phone_number="9000000000"))
    db.commit()

    result = mcp_server.list_vendors(category="Plumber")
    assert [v["name"] for v in result["vendors"]] == ["Ganesh Pipe Works"]


def test_list_service_requests(db, seeded):
    mcp_server.create_service_request(building_name="Building 7", flat_number=302, category="Plumber")

    result = mcp_server.list_service_requests(status="open")
    assert len(result["service_requests"]) == 1


def test_create_service_request_resolves_flat_by_name(seeded):
    result = mcp_server.create_service_request(
        building_name="Building 7", flat_number=302, category="Plumber", description="leak"
    )
    assert result["flat"]["flat_number"] == 302
    assert result["status"] == "open"


def test_create_service_request_unknown_flat_returns_error(seeded):
    result = mcp_server.create_service_request(building_name="Building 99", flat_number=101, category="Plumber")
    assert "error" in result


def test_dashboard_summary(seeded):
    result = mcp_server.dashboard_summary()
    assert result["buildings"] == 1
    assert result["residents"] == 1


def test_exactly_the_required_eight_tools_are_registered():
    assert set(mcp_server.mcp._tools.keys()) == {
        "get_water_schedule",
        "get_flat_status",
        "search_residents",
        "list_buildings",
        "list_vendors",
        "list_service_requests",
        "create_service_request",
        "dashboard_summary",
    }