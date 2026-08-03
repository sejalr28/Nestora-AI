from app.services.agent.tools import ToolContext, get_flat_status, get_water_schedule, log_service_request


def test_get_water_schedule_returns_both_sources(db, seeded):
    result = get_water_schedule(ToolContext(db=db))
    assert len(result["schedules"]) == 2
    sources = {s["source"] for s in result["schedules"]}
    assert sources == {"corporation", "bore"}


def test_get_water_schedule_filters_by_source(db, seeded):
    result = get_water_schedule(ToolContext(db=db), source="bore")
    assert len(result["schedules"]) == 1
    assert result["schedules"][0]["source"] == "bore"
    assert result["schedules"][0]["start_time"] == "21:00"


def test_get_flat_status_known_flat(db, seeded):
    result = get_flat_status(ToolContext(db=db), building_name="Building 7", flat_number=302)
    assert result == {"building": "Building 7", "flat_number": 302, "status": "rented"}


def test_get_flat_status_unknown_building(db, seeded):
    result = get_flat_status(ToolContext(db=db), building_name="Building 99", flat_number=101)
    assert "error" in result


def test_log_service_request_requires_identified_resident(db, seeded):
    result = log_service_request(ToolContext(db=db, resident=None), category="Plumber", description="leak")
    assert "error" in result


def test_log_service_request_files_against_residents_own_flat(db, seeded):
    resident = seeded["resident"]
    result = log_service_request(
        ToolContext(db=db, resident=resident), category="Plumber", description="kitchen tap leaking"
    )
    assert result["status"] == "open"
    assert "request_id" in result