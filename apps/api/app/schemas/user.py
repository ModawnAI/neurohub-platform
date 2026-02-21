import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    user_type: str | None = None
    is_active: bool = True
    institution_id: uuid.UUID | None = None
    institution_name: str | None = None
    role_scope: str | None = None
    expert_status: str | None = None
    specialization: str | None = None
    onboarding_completed: bool = False
    created_at: datetime | None = None
    last_login_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int


class UserUpdate(BaseModel):
    is_active: bool | None = None
    display_name: str | None = Field(default=None, max_length=100)


class ExpertApproval(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
