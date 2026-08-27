from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from legalintel.storage import init_db
from tests.conftest import TEST_JWT_SECRET


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, db_path: str, stub_model_dir: Path) -> TestClient:
    monkeypatch.setattr(settings, "db_path", db_path)
    monkeypatch.setattr(settings, "jwt_secret_key", TEST_JWT_SECRET)
    monkeypatch.setattr(settings, "clause_model_dir", str(stub_model_dir))
    init_db(db_path)
    return TestClient(app)


def test_extract_clauses_with_matter_id_persists_result(
    client: TestClient, auth_headers, sample_pdf_path: Path
) -> None:
    headers = auth_headers("attorney")
    matter_id = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()["id"]

    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/documents/extract-clauses",
            files={"file": ("sample.pdf", f, "application/pdf")},
            data={"matter_id": matter_id},
            headers=headers,
        )
    assert response.status_code == 200

    detail = client.get(f"/matters/{matter_id}", headers=headers).json()
    assert len(detail["documents"]) == 1
    doc = detail["documents"][0]
    assert doc["analysis_type"] == "extract_clauses"
    assert "clauses" in doc["result"]
    assert "risk_summary" in doc["result"]


def test_extract_clauses_as_support_staff_returns_403(
    client: TestClient, auth_headers, sample_pdf_path: Path
) -> None:
    with open(sample_pdf_path, "rb") as f:
        response = client.post(
            "/documents/extract-clauses",
            files={"file": ("sample.pdf", f, "application/pdf")},
            headers=auth_headers("support_staff"),
        )

    assert response.status_code == 403
