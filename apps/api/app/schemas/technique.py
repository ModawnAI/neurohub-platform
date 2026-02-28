"""Pydantic schemas for TechniqueModule CRUD."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TechniqueModuleCreate(BaseModel):
    key: str = Field(..., max_length=50)
    title_ko: str = Field(..., max_length=200)
    title_en: str = Field(..., max_length=200)
    modality: str = Field(..., max_length=30)
    category: str = Field(..., max_length=50)
    description: str | None = None
    docker_image: str = Field(..., max_length=500)
    version: str = Field(default="1.0.0", max_length=30)
    qc_config: dict | None = None
    output_schema: dict | None = None
    resource_requirements: dict | None = None


class TechniqueModuleUpdate(BaseModel):
    title_ko: str | None = Field(default=None, max_length=200)
    title_en: str | None = Field(default=None, max_length=200)
    modality: str | None = Field(default=None, max_length=30)
    category: str | None = Field(default=None, max_length=50)
    description: str | None = None
    docker_image: str | None = Field(default=None, max_length=500)
    version: str | None = Field(default=None, max_length=30)
    qc_config: dict | None = None
    output_schema: dict | None = None
    resource_requirements: dict | None = None


class TechniqueModuleRead(BaseModel):
    id: uuid.UUID
    key: str
    title_ko: str
    title_en: str
    modality: str
    category: str
    description: str | None
    docker_image: str
    version: str
    status: str
    qc_config: dict | None
    output_schema: dict | None
    resource_requirements: dict | None
    created_at: datetime


class TechniqueModuleListResponse(BaseModel):
    items: list[TechniqueModuleRead]
    total: int
