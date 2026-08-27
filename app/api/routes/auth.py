from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.security import get_current_user, require_role
from legalintel.auth import db as auth_db
from legalintel.auth.security import create_access_token, hash_password, verify_password
from legalintel.models.user import AuditLogEntry, LoginRequest, TokenResponse, User, UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    record = auth_db.get_user_by_email(settings.db_path, payload.email)
    if record is None or not record.is_active or not verify_password(payload.password, record.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not settings.jwt_secret_key:
        raise HTTPException(status_code=503, detail="JWT_SECRET_KEY is not set - cannot issue tokens.")
    token = create_access_token(user_id=record.id, secret_key=settings.jwt_secret_key)
    auth_db.log_action(settings.db_path, user_id=record.id, action="login")

    user = User(**record.model_dump(exclude={"password_hash"}))
    return TokenResponse(access_token=token, user=user)


@router.post("/logout", status_code=204)
def logout(user: User = Depends(get_current_user)) -> None:
    # Stateless JWT - nothing to invalidate server-side. This endpoint exists purely
    # so a "logout" audit event has somewhere to be recorded.
    auth_db.log_action(settings.db_path, user_id=user.id, action="logout")


@router.get("/me", response_model=User)
def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/users", response_model=User, status_code=201)
def create_user(payload: UserCreate, _: User = Depends(require_role("attorney"))) -> User:
    if auth_db.get_user_by_email(settings.db_path, payload.email) is not None:
        raise HTTPException(status_code=409, detail=f"A user with email {payload.email} already exists.")
    record = auth_db.create_user(
        settings.db_path,
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    return User(**record.model_dump(exclude={"password_hash"}))


@router.get("/audit-log", response_model=list[AuditLogEntry])
def get_audit_log(_: User = Depends(require_role("attorney"))) -> list[AuditLogEntry]:
    return auth_db.list_audit_log(settings.db_path)
