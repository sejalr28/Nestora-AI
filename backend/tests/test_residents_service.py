from app.services.core.residents_service import search_residents


def test_search_residents_matches_name(db, seeded):
    results = search_residents(db, "Sejal")
    assert len(results) == 1
    assert results[0]["name"] == "Sejal"


def test_search_residents_matches_phone_number(db, seeded):
    results = search_residents(db, "9876543210")
    assert len(results) == 1


def test_search_residents_is_case_insensitive(db, seeded):
    results = search_residents(db, "sejal")
    assert len(results) == 1


def test_search_residents_no_match_returns_empty(db, seeded):
    assert search_residents(db, "nonexistent") == []