import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OnboardingRequest(BaseModel):
    user_type: str = Field(..., pattern="^(SERVICE_USER|EXPERT|ADMIN)$")
    display_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    specialization: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
    organization_name: str | None = Field(default=None, max_length=200)
    organization_code: str | None = Field(default=None, max_length=50)
    organization_type: str | None = Field(default=None, pattern="^(individual|hospital|clinic)$")


class MeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    username: str
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    user_type: str | None = None
    institution_id: uuid.UUID | None = None
    institution_name: str | None = None
    roles: list[str] = []
    expert_status: str | None = None
    specialization: str | None = None
    bio: str | None = None
    onboarding_completed: bool = False
    created_at: datetime | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    specialization: str | None = Field(default=None, max_length=200)
    bio: str | None = Field(default=None, max_length=2000)
