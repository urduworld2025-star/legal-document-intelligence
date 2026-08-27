from datetime import timedelta

import pytest

from legalintel.auth.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET_KEY = "test-secret-key-that-is-at-least-32-bytes-long"


def test_hash_password_round_trips_with_verify() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert verify_password("correct-horse-battery-staple", password_hash) is True


def test_verify_password_rejects_wrong_password() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert verify_password("wrong-password", password_hash) is False


def test_create_and_decode_access_token_round_trips() -> None:
    token = create_access_token(user_id=42, secret_key=SECRET_KEY)

    assert decode_access_token(token, secret_key=SECRET_KEY) == 42


def test_decode_access_token_rejects_expired_token() -> None:
    token = create_access_token(user_id=42, secret_key=SECRET_KEY, expires_delta=timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, secret_key=SECRET_KEY)


def test_decode_access_token_rejects_tampered_signature() -> None:
    token = create_access_token(user_id=42, secret_key=SECRET_KEY)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, secret_key="a-different-secret-key-also-32-bytes-plus")
