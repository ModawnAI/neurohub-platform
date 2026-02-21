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
