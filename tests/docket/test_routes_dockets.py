import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from legalintel.storage import init_db
from tests.conftest import TEST_JWT_SECRET

ENTRY_1 = {"id": 1, "entry_number": 1, "description": "Complaint filed", "date_filed": "2026-01-01"}
ENTRY_2 = {"id": 2, "entry_number": 2, "description": "Answer filed", "date_filed": "2026-01-05"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, db_path: str) -> TestClient:
    monkeypatch.setattr(settings, "db_path", db_path)
    monkeypatch.setattr(settings, "jwt_secret_key", TEST_JWT_SECRET)
    monkeypatch.setattr(settings, "courtlistener_api_token", "fake-token")
    init_db(db_path)
    return TestClient(app)


def test_track_docket_returns_201_and_appears_in_list(
    client: TestClient, auth_headers, entries_transport_factory, patch_courtlistener_client
) -> None:
    headers = auth_headers("attorney")
    patch_courtlistener_client(entries_transport_factory([]))

    response = client.post(
        "/dockets/track", json={"courtlistener_docket_id": 69510553}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["courtlistener_docket_id"] == 69510553

    listed = client.get("/dockets", headers=headers).json()
    assert [d["courtlistener_docket_id"] for d in listed] == [69510553]


def test_track_docket_without_token_returns_401(client: TestClient) -> None:
    response = client.post("/dockets/track", json={"courtlistener_docket_id": 69510553})

    assert response.status_code == 401


def test_track_docket_without_courtlistener_token_returns_503(
    client: TestClient, auth_headers, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "courtlistener_api_token", None)

    response = client.post(
        "/dockets/track", json={"courtlistener_docket_id": 69510553}, headers=auth_headers("attorney")
    )

    assert response.status_code == 503


def test_track_duplicate_docket_returns_409(
    client: TestClient, auth_headers, entries_transport_factory, patch_courtlistener_client
) -> None:
    headers = auth_headers("attorney")
    patch_courtlistener_client(entries_transport_factory([]))
    client.post("/dockets/track", json={"courtlistener_docket_id": 69510553}, headers=headers)

    response = client.post(
        "/dockets/track", json={"courtlistener_docket_id": 69510553}, headers=headers
    )

    assert response.status_code == 409


def test_check_twice_then_list_alerts(
    client: TestClient, auth_headers, entries_transport_factory, patch_courtlistener_client
) -> None:
    headers = auth_headers("attorney")
    patch_courtlistener_client(entries_transport_factory([ENTRY_1, ENTRY_2]))
    tracked = client.post(
        "/dockets/track", json={"courtlistener_docket_id": 69510553}, headers=headers
    ).json()

    first_check = client.post(f"/dockets/{tracked['id']}/check", headers=headers)
    assert first_check.status_code == 200
    assert first_check.json()["alert_created"] is True
    assert len(first_check.json()["new_entries"]) == 2

    second_check = client.post(f"/dockets/{tracked['id']}/check", headers=headers)
    assert second_check.status_code == 200
    assert second_check.json()["alert_created"] is False
    assert second_check.json()["new_entries"] == []

    alerts = client.get(f"/dockets/{tracked['id']}/alerts", headers=headers)
    assert alerts.status_code == 200
    assert len(alerts.json()) == 1
    assert alerts.json()[0]["new_entry_count"] == 2

    entries = client.get(f"/dockets/{tracked['id']}/entries", headers=headers)
    assert entries.status_code == 200
    assert {e["courtlistener_entry_id"] for e in entries.json()} == {1, 2}
    assert {e["description"] for e in entries.json()} == {"Complaint filed", "Answer filed"}


def test_check_unknown_docket_returns_404(client: TestClient, auth_headers) -> None:
    response = client.post("/dockets/9999/check", headers=auth_headers("attorney"))

    assert response.status_code == 404


def test_track_docket_with_unknown_matter_id_returns_404(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/dockets/track",
        json={"courtlistener_docket_id": 69510553, "matter_id": 9999},
        headers=auth_headers("attorney"),
    )

    assert response.status_code == 404


def test_track_docket_with_real_matter_id_links_it(
    client: TestClient, auth_headers, entries_transport_factory, patch_courtlistener_client
) -> None:
    headers = auth_headers("attorney")
    matter = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()
    patch_courtlistener_client(entries_transport_factory([]))

    response = client.post(
        "/dockets/track",
        json={"courtlistener_docket_id": 69510553, "matter_id": matter["id"]},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["matter_id"] == matter["id"]
