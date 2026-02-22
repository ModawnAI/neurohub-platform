import uuid
from datetime import datetime

from pydantic import BaseModel


class ServiceRead(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    display_name: str
    version: str
    status: str
    department: str | None = None
    created_at: datetime


class PipelineRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    name: str
    version: str
    is_default: bool
    created_at: datetime


class ServiceListResponse(BaseModel):
    items: list[ServiceRead]


class PipelineListResponse(BaseModel):
    items: list[PipelineRead]


class ServiceCreate(BaseModel):
    name: str
    display_name: str
    version: str = "1.0"
    department: str | None = None
    description: str | None = None


class ServiceUpdate(BaseModel):
    display_name: str | None = None
    version: str | None = None
    department: str | None = None
    description: str | None = None
    status: str | None = None
