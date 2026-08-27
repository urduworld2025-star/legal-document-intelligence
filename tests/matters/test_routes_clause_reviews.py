from fastapi.testclient import TestClient

from legalintel.matters import db as matters_db


def _create_reviewable_document(db_path: str, headers: dict[str, str], client: TestClient) -> tuple[int, int]:
    matter_id = client.post("/matters", json={"name": "Acme v. Beta"}, headers=headers).json()["id"]
    document = matters_db.add_matter_document(
        db_path,
        matter_id=matter_id,
        source_filename="contract.pdf",
        analysis_type="extract_clauses",
        result={"clauses": [{"category": "Governing Law"}, {"category": "Non-Compete"}]},
    )
    return matter_id, document.id


def test_mark_clause_reviewed_as_paralegal_returns_reviewer_name(
    client: TestClient, auth_headers, db_path: str
) -> None:
    headers = auth_headers("paralegal", email="paralegal@example.com")
    matter_id, document_id = _create_reviewable_document(db_path, headers, client)

    response = client.post(f"/matters/{matter_id}/documents/{document_id}/review/0", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["clause_index"] == 0
    assert body["reviewed_by_name"] != ""

    listed = client.get(f"/matters/{matter_id}/documents/{document_id}/review", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_mark_clause_reviewed_as_support_staff_returns_403(
    client: TestClient, auth_headers, db_path: str
) -> None:
    attorney_headers = auth_headers("attorney")
    matter_id, document_id = _create_reviewable_document(db_path, attorney_headers, client)

    response = client.post(
        f"/matters/{matter_id}/documents/{document_id}/review/0",
        headers=auth_headers("support_staff"),
    )

    assert response.status_code == 403


def test_unmark_clause_reviewed_removes_it(client: TestClient, auth_headers, db_path: str) -> None:
    headers = auth_headers("attorney")
    matter_id, document_id = _create_reviewable_document(db_path, headers, client)
    client.post(f"/matters/{matter_id}/documents/{document_id}/review/0", headers=headers)

    response = client.delete(f"/matters/{matter_id}/documents/{document_id}/review/0", headers=headers)
    listed = client.get(f"/matters/{matter_id}/documents/{document_id}/review", headers=headers)

    assert response.status_code == 204
    assert listed.json() == []


def test_mark_clause_reviewed_invalid_index_returns_400(
    client: TestClient, auth_headers, db_path: str
) -> None:
    headers = auth_headers("attorney")
    matter_id, document_id = _create_reviewable_document(db_path, headers, client)

    response = client.post(f"/matters/{matter_id}/documents/{document_id}/review/99", headers=headers)

    assert response.status_code == 400
