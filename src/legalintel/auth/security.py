from datetime import datetime, timedelta, timezone

import bcrypt
import jwt


class AuthConfigError(RuntimeError):
    pass


class InvalidTokenError(RuntimeError):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(*, user_id: int, secret_key: str, expires_delta: timedelta = timedelta(hours=8)) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, secret_key, algorithm="HS256")


def decode_access_token(token: str, *, secret_key: str) -> int:
    """Returns the user id encoded in the token's `sub` claim. Raises InvalidTokenError
    on any expiry/signature/format failure - callers don't need to know PyJWT's
    exception hierarchy."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise InvalidTokenError(str(exc)) from exc
