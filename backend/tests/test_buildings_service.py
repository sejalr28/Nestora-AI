from app.services.core.buildings_service import list_buildings


def test_list_buildings_empty(db):
    assert list_buildings(db) == []


def test_list_buildings_returns_dicts_sorted_by_name(db, seeded):
    result = list_buildings(db)
    assert result == [{"id": seeded["building"].id, "name": "Building 7", "has_bore_water": True}]