"""Pydantic schemas for DICOM Gateway."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class DicomSeriesRead(BaseModel):
    id: uuid.UUID
    study_id: uuid.UUID
    series_instance_uid: str
    series_number: int | None
    series_description: str | None
    modality: str | None
    num_instances: int
    storage_prefix: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DicomStudyRead(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    study_instance_uid: str
    patient_id: str
    patient_name: str | None
    study_date: date | None
    study_description: str | None
    modality: str | None
    num_series: int
    num_instances: int
    storage_prefix: str | None
    status: str
    source_aet: str | None
    request_id: uuid.UUID | None
    created_at: datetime
    series: list[DicomSeriesRead] = []

    model_config = {"from_attributes": True}


class DicomStudyList(BaseModel):
    items: list[DicomStudyRead]
    total: int


class LinkStudyRequest(BaseModel):
    request_id: uuid.UUID


class CreateRequestFromStudyRequest(BaseModel):
    service_id: uuid.UUID


class StowRsResult(BaseModel):
    study_instance_uid: str
    series_instance_uid: str
    sop_instance_uid: str
    status: str  # "success" | "failure"
    reason: str | None = None


class StowRsResponse(BaseModel):
    results: list[StowRsResult]
    success_count: int
    failure_count: int
