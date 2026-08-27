from fastapi.testclient import TestClient


def test_create_matter_returns_201(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/matters",
        json={"name": "Acme v. Beta", "description": "Contract dispute"},
        headers=auth_headers("attorney"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme v. Beta"
    assert body["description"] == "Contract dispute"


def test_create_matter_as_paralegal_returns_201(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/matters", json={"name": "Acme v. Beta"}, headers=auth_headers("paralegal")
    )
    assert response.status_code == 201


def test_create_matter_as_support_staff_returns_403(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/matters", json={"name": "Acme v. Beta"}, headers=auth_headers("support_staff")
    )
    assert response.status_code == 403


def test_create_matter_without_token_returns_401(client: TestClient) -> None:
    response = client.post("/matters", json={"name": "Acme v. Beta"})
    assert response.status_code == 401


def test_list_matters_shows_created_matter(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers)
    response = client.get("/matters", headers=headers)
    assert response.status_code == 200
    assert [m["name"] for m in response.json()] == ["Acme v. Beta"]


def test_get_matter_detail_returns_matter_with_empty_lists(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    created = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()
    response = client.get(f"/matters/{created['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["matter"]["id"] == created["id"]
    assert body["documents"] == []
    assert body["tracked_dockets"] == []


def test_get_unknown_matter_returns_404(client: TestClient, auth_headers) -> None:
    response = client.get("/matters/9999", headers=auth_headers("attorney"))
    assert response.status_code == 404


def test_delete_matter_as_paralegal_returns_403(client: TestClient, auth_headers) -> None:
    attorney_headers = auth_headers("attorney")
    created = client.post("/matters", json={"name": "Acme v. Beta"}, headers=attorney_headers).json()

    response = client.delete(f"/matters/{created['id']}", headers=auth_headers("paralegal"))

    assert response.status_code == 403


def test_delete_matter_as_attorney_then_404(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    created = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()

    delete_response = client.delete(f"/matters/{created['id']}", headers=headers)
    get_response = client.get(f"/matters/{created['id']}", headers=headers)

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_unknown_matter_returns_404(client: TestClient, auth_headers) -> None:
    response = client.delete("/matters/9999", headers=auth_headers("attorney"))
    assert response.status_code == 404
