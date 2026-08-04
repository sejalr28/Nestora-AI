from app.main import app
from app.models.resident import Resident
from app.services.llm import get_llm_provider
from app.services.llm.base import LLMResponse
from tests.fakes import FakeProvider


def test_webhook_prompts_onboarding_for_unknown_number(client):
    resp = client.post(
        "/api/v1/whatsapp/webhook",
        data={"From": "whatsapp:+911111111111", "Body": "hi"},
    )
    assert resp.status_code == 200
    assert "Reply with your name" in resp.text


def test_webhook_onboards_new_resident_and_persists_them(client, db, seeded):
    resp = client.post(
        "/api/v1/whatsapp/webhook",
        data={"From": "whatsapp:+912222222222", "Body": "Priya, Building 7, 405"},
    )
    assert resp.status_code == 200
    assert "Priya" in resp.text
    assert "Building 7" in resp.text

    resident = db.query(Resident).filter(Resident.phone_number == "+912222222222").first()
    assert resident is not None
    assert resident.name == "Priya"
    assert resident.flat.flat_number == 405


def test_webhook_onboarding_rejects_unknown_building(client, seeded):
    resp = client.post(
        "/api/v1/whatsapp/webhook",
        data={"From": "whatsapp:+913333333333", "Body": "Raj, Building 99, 101"},
    )
    assert "couldn't find" in resp.text.lower()


def test_webhook_routes_known_resident_through_the_agent(client, seeded):
    app.dependency_overrides[get_llm_provider] = lambda: FakeProvider(
        [LLMResponse(content="Corporation water: 8-10 AM.")]
    )

    resp = client.post(
        "/api/v1/whatsapp/webhook",
        data={"From": "whatsapp:+919876543210", "Body": "when's water today?"},  # matches seeded resident
    )

    assert resp.status_code == 200
    assert "Corporation water: 8-10 AM." in resp.text