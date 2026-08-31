from fastapi.testclient import TestClient


def test_search_finds_matter_by_name(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    client.post("/matters", json={"name": "Very Distinctive Matter Name"}, headers=headers)

    response = client.get("/search", params={"q": "Distinctive"}, headers=headers)

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["type"] == "matter"
    assert results[0]["title"] == "Very Distinctive Matter Name"


def test_search_without_query_returns_empty(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    client.post("/matters", json={"name": "Some Matter"}, headers=headers)

    response = client.get("/search", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_search_requires_authentication(client: TestClient) -> None:
    response = client.get("/search", params={"q": "anything"})

    assert response.status_code == 401


def test_search_visible_to_support_staff(client: TestClient, auth_headers) -> None:
    attorney_headers = auth_headers("attorney")
    client.post("/matters", json={"name": "Readable Matter"}, headers=attorney_headers)

    response = client.get("/search", params={"q": "Readable"}, headers=auth_headers("support_staff"))

    assert response.status_code == 200
    assert len(response.json()) == 1
