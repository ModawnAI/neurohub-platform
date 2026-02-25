"""Pydantic schemas for Service Definition — dynamic service system."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Input Schema sub-models
# ---------------------------------------------------------------------------


class InputFieldCondition(BaseModel):
    """Show this field only when another field matches a value."""

    field: str
    value: Any


class InputField(BaseModel):
    """A single demographics / input field in a service definition."""

    key: str = Field(..., description="Unique field key, e.g. 'patient_age'")
    type: Literal["text", "number", "select", "date", "radio", "checkbox", "textarea"] = "text"
    label: str = Field(..., description="Display label (Korean)")
    label_en: str | None = None
    placeholder: str | None = None
    required: bool = False
    default: Any = None
    options: list[dict[str, str]] | None = Field(
        None, description='For select/radio: [{"value":"M","label":"남성"},...]'
    )
    validation: dict[str, Any] | None = Field(
        None,
        description="Validation rules: min, max, min_length, max_length, pattern",
    )
    condition: InputFieldCondition | None = Field(None, description="Conditional display rule")
    help_text: str | None = None
    group: str | None = Field(None, description="Fieldset/group name for layout")


class InputSchema(BaseModel):
    """Top-level input schema for a service definition."""

    fields: list[InputField] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Upload Slots
# ---------------------------------------------------------------------------


class UploadSlot(BaseModel):
    """Definition of a file upload slot."""

    key: str = Field(..., description="Slot key, e.g. 'mri_t1'")
    label: str
    label_en: str | None = None
    required: bool = True
    accepted_types: list[str] = Field(
        default_factory=lambda: ["DICOM"],
        description="DICOM, NIfTI, EEG, EDF, SET, CSV, etc.",
    )
    accepted_extensions: list[str] | None = Field(
        None, description="e.g. ['.dcm', '.nii', '.nii.gz']"
    )
    min_files: int = 1
    max_files: int = 500
    description: str | None = None
    help_text: str | None = None


# ---------------------------------------------------------------------------
# Options Schema
# ---------------------------------------------------------------------------


class OptionField(BaseModel):
    """A configurable analysis option."""

    key: str
    type: Literal["select", "number", "checkbox", "text", "radio"] = "select"
    label: str
    label_en: str | None = None
    required: bool = False
    default: Any = None
    options: list[dict[str, str]] | None = None
    validation: dict[str, Any] | None = None
    help_text: str | None = None


class OptionsSchema(BaseModel):
    fields: list[OptionField] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


class VolumeDiscount(BaseModel):
    min_cases: int
    discount_percent: float


class PricingSchema(BaseModel):
    base_price: int = Field(0, description="Base price per request (KRW)")
    per_case_price: int = Field(0, description="Price per case (KRW)")
    currency: str = "KRW"
    volume_discounts: list[VolumeDiscount] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Output Schema
# ---------------------------------------------------------------------------


class OutputField(BaseModel):
    key: str
    type: Literal["image", "pdf", "csv", "json", "html", "table", "chart"] = "json"
    label: str
    label_en: str | None = None
    description: str | None = None


class OutputSchema(BaseModel):
    fields: list[OutputField] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Full Service Definition Schema (for registration)
# ---------------------------------------------------------------------------


class ServiceDefinitionPayload(BaseModel):
    """Full JSON payload for creating/registering a service."""

    input_schema: InputSchema | None = None
    upload_slots: list[UploadSlot] | None = None
    options_schema: OptionsSchema | None = None
    pricing: PricingSchema | None = None
    output_schema: OutputSchema | None = None


# ---------------------------------------------------------------------------
# API Request/Response schemas
# ---------------------------------------------------------------------------


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    department: str | None = None
    category: str | None = None
    service_type: str = Field("AUTOMATIC", pattern="^(AUTOMATIC|HUMAN_IN_LOOP)$")
    requires_evaluator: bool = False
    definition: ServiceDefinitionPayload | None = None


class ServiceUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    department: str | None = None
    category: str | None = None
    service_type: str | None = Field(None, pattern="^(AUTOMATIC|HUMAN_IN_LOOP)$")
    requires_evaluator: bool | None = None
    input_schema: dict | None = None
    upload_slots: list | None = None
    options_schema: dict | None = None
    pricing: dict | None = None
    output_schema: dict | None = None


class ServiceRead(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    display_name: str
    description: str | None = None
    version: int
    version_label: str
    status: str
    department: str | None = None
    category: str | None = None
    service_type: str = "AUTOMATIC"
    requires_evaluator: bool = False
    input_schema: dict | None = None
    upload_slots: list | None = None
    options_schema: dict | None = None
    pricing: dict | None = None
    output_schema: dict | None = None
    created_at: datetime


class ServiceListResponse(BaseModel):
    items: list[ServiceRead]


class PipelineRead(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID
    name: str
    version: str
    is_default: bool
    created_at: datetime


class PipelineListResponse(BaseModel):
    items: list[PipelineRead]
