from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD


def test_login_success_returns_token_and_user(client: TestClient, make_user) -> None:
    make_user("attorney@example.com", role="attorney")

    response = client.post("/auth/login", json={"email": "attorney@example.com", "password": TEST_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "attorney@example.com"
    assert body["user"]["role"] == "attorney"
    assert "access_token" in body


def test_login_wrong_password_returns_401(client: TestClient, make_user) -> None:
    make_user("attorney@example.com", role="attorney")

    response = client.post("/auth/login", json={"email": "attorney@example.com", "password": "wrong"})

    assert response.status_code == 401


def test_login_unknown_email_returns_401_with_same_message(client: TestClient, make_user) -> None:
    make_user("attorney@example.com", role="attorney")

    known_wrong_password = client.post(
        "/auth/login", json={"email": "attorney@example.com", "password": "wrong"}
    )
    unknown_email = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong"})

    assert unknown_email.status_code == 401
    assert unknown_email.json()["detail"] == known_wrong_password.json()["detail"]


def test_get_me_requires_token(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_get_me_returns_current_user(client: TestClient, auth_headers) -> None:
    response = client.get("/auth/me", headers=auth_headers("attorney"))

    assert response.status_code == 200
    assert response.json()["role"] == "attorney"


def test_create_user_as_attorney_succeeds(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/auth/users",
        json={"email": "para@example.com", "name": "Paralegal Pat", "password": "password123", "role": "paralegal"},
        headers=auth_headers("attorney"),
    )

    assert response.status_code == 201
    assert response.json()["role"] == "paralegal"


def test_create_user_as_paralegal_returns_403(client: TestClient, auth_headers) -> None:
    response = client.post(
        "/auth/users",
        json={"email": "x@example.com", "name": "X", "password": "password123", "role": "support_staff"},
        headers=auth_headers("paralegal"),
    )

    assert response.status_code == 403


def test_create_user_duplicate_email_returns_409(client: TestClient, auth_headers, make_user) -> None:
    make_user("dup@example.com")

    response = client.post(
        "/auth/users",
        json={"email": "dup@example.com", "name": "Dup", "password": "password123", "role": "paralegal"},
        headers=auth_headers("attorney"),
    )

    assert response.status_code == 409


def test_audit_log_as_attorney_succeeds(client: TestClient, auth_headers) -> None:
    response = client.get("/auth/audit-log", headers=auth_headers("attorney"))

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_audit_log_as_support_staff_returns_403(client: TestClient, auth_headers) -> None:
    response = client.get("/auth/audit-log", headers=auth_headers("support_staff"))

    assert response.status_code == 403
