from fastapi.testclient import TestClient


def test_report_for_empty_matter_returns_pdf(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    created = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()

    response = client.get(f"/matters/{created['id']}/report", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_report_for_unknown_matter_returns_404(client: TestClient, auth_headers) -> None:
    response = client.get("/matters/9999/report", headers=auth_headers("attorney"))

    assert response.status_code == 404


def test_report_sets_content_disposition_with_matter_id(client: TestClient, auth_headers) -> None:
    headers = auth_headers("attorney")
    created = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()

    response = client.get(f"/matters/{created['id']}/report", headers=headers)

    assert f'filename="matter-{created["id"]}-report.pdf"' in response.headers["content-disposition"]
