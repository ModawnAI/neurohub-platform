"""Schema definitions for service inputs, outputs, and upload slots."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InputField:
    key: str
    type: str  # text, number, select, date, radio, checkbox, textarea
    label: str
    label_en: str | None = None
    required: bool = False
    options: list[dict[str, str]] | None = None  # For select/radio: [{"value": "x", "label": "X"}]
    validation: dict[str, Any] | None = None  # min, max, min_length, pattern
    condition: dict[str, Any] | None = None  # Conditional display rules
    group: str | None = None  # For fieldset grouping

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "key": self.key,
            "type": self.type,
            "label": self.label,
            "required": self.required,
        }
        if self.label_en:
            d["label_en"] = self.label_en
        if self.options:
            d["options"] = self.options
        if self.validation:
            d["validation"] = self.validation
        if self.condition:
            d["condition"] = self.condition
        if self.group:
            d["group"] = self.group
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "InputField":
        return cls(
            key=d["key"],
            type=d["type"],
            label=d["label"],
            label_en=d.get("label_en"),
            required=d.get("required", False),
            options=d.get("options"),
            validation=d.get("validation"),
            condition=d.get("condition"),
            group=d.get("group"),
        )


@dataclass
class UploadSlot:
    key: str
    label: str
    label_en: str | None = None
    required: bool = False
    accepted_extensions: list[str] = field(default_factory=list)
    accepted_types: list[str] = field(default_factory=list)  # DICOM, NIfTI, EEG, CSV, etc.
    min_files: int = 0
    max_files: int = 10

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "label_en": self.label_en,
            "required": self.required,
            "accepted_extensions": self.accepted_extensions,
            "accepted_types": self.accepted_types,
            "min_files": self.min_files,
            "max_files": self.max_files,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UploadSlot":
        return cls(
            key=d["key"],
            label=d["label"],
            label_en=d.get("label_en"),
            required=d.get("required", False),
            accepted_extensions=d.get("accepted_extensions", []),
            accepted_types=d.get("accepted_types", []),
            min_files=d.get("min_files", 0),
            max_files=d.get("max_files", 10),
        )


@dataclass
class OutputField:
    key: str
    type: str  # text, number, file, json
    label: str
    label_en: str | None = None
    description: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "key": self.key,
            "type": self.type,
            "label": self.label,
        }
        if self.label_en:
            d["label_en"] = self.label_en
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "OutputField":
        return cls(
            key=d["key"],
            type=d["type"],
            label=d["label"],
            label_en=d.get("label_en"),
            description=d.get("description"),
        )


@dataclass
class SchemaDefinition:
    inputs: list[InputField] = field(default_factory=list)
    uploads: list[UploadSlot] = field(default_factory=list)
    outputs: list[OutputField] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "inputs": [i.to_dict() for i in self.inputs],
            "uploads": [u.to_dict() for u in self.uploads],
            "outputs": [o.to_dict() for o in self.outputs],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SchemaDefinition":
        return cls(
            inputs=[InputField.from_dict(i) for i in d.get("inputs", [])],
            uploads=[UploadSlot.from_dict(u) for u in d.get("uploads", [])],
            outputs=[OutputField.from_dict(o) for o in d.get("outputs", [])],
        )
