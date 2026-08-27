from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Role = Literal["attorney", "paralegal", "support_staff"]


class User(BaseModel):
    id: int
    email: str
    name: str
    role: Role
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: Role


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: User


class AuditLogEntry(BaseModel):
    id: int
    user_id: int | None
    action: str
    detail: str | None
    created_at: datetime


class ClauseReview(BaseModel):
    matter_document_id: int
    clause_index: int
    reviewed_by: int
    reviewed_by_name: str
    reviewed_at: datetime
