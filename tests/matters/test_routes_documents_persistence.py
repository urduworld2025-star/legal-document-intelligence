from pathlib import Path

from fastapi.testclient import TestClient


def _create_matter(client: TestClient, headers: dict[str, str]) -> int:
    return client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()["id"]


def test_parse_with_matter_id_persists_document(
    client: TestClient, auth_headers, sample_pdf_path: Path
) -> None:
    headers = auth_headers("attorney")
    matter_id = _create_matter(client, headers)

    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/documents/parse",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"matter_id": matter_id},
            headers=headers,
        )
    assert response.status_code == 200

    detail = client.get(f"/matters/{matter_id}", headers=headers).json()
    assert len(detail["documents"]) == 1
    assert detail["documents"][0]["analysis_type"] == "parse"
    assert detail["documents"][0]["source_filename"] == "sample.pdf"


def test_parse_without_matter_id_persists_nothing(
    client: TestClient, auth_headers, sample_pdf_path: Path
) -> None:
    headers = auth_headers("attorney")
    matter_id = _create_matter(client, headers)

    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/documents/parse", files={"file": ("sample.pdf", f, "application/pdf")}, headers=headers
        )
    assert response.status_code == 200

    detail = client.get(f"/matters/{matter_id}", headers=headers).json()
    assert detail["documents"] == []


def test_parse_as_support_staff_returns_403(
    client: TestClient, auth_headers, sample_pdf_path: Path
) -> None:
    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/documents/parse",
            files={"file": ("sample.pdf", f, "application/pdf")},
            headers=auth_headers("support_staff"),
        )

    assert response.status_code == 403


def test_parse_with_unknown_matter_id_returns_404(
    client: TestClient, auth_headers, sample_pdf_path: Path
) -> None:
    headers = auth_headers("attorney")
    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/documents/parse",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"matter_id": 9999},
            headers=headers,
        )

    assert response.status_code == 404
