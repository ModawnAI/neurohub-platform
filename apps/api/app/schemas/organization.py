import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrgCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    institution_type: str = Field(default="HOSPITAL", pattern="^(HOSPITAL|CLINIC|INDIVIDUAL)$")
    contact_email: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=30)


class OrgRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    code: str
    name: str
    status: str
    institution_type: str = "HOSPITAL"
    contact_email: str | None = None
    contact_phone: str | None = None
    member_count: int = 0
    created_at: datetime | None = None


class OrgListResponse(BaseModel):
    items: list[OrgRead]
    total: int


class OrgUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=30)


class InviteCreate(BaseModel):
    email: str = Field(..., max_length=200)
    role_scope: str | None = Field(default=None, max_length=50)


class InviteRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    role_scope: str | None = None
    status: str
    invite_token: str
    expires_at: datetime | None = None
    created_at: datetime | None = None


class MemberRead(BaseModel):
    model_config = {"from_attributes": True}

    user_id: uuid.UUID
    username: str | None = None
    display_name: str | None = None
    email: str | None = None
    role_scope: str | None = None
    user_type: str | None = None
    created_at: datetime | None = None


class JoinRequest(BaseModel):
    invite_token: str = Field(..., max_length=100)
