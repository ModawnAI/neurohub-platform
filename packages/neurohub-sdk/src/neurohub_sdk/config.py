"""Service configuration."""

from dataclasses import dataclass, field
import re


@dataclass
class ServiceConfig:
    name: str
    version: str
    display_name: str
    description: str = ""
    department: str | None = None
    category: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def image_tag(self) -> str:
        sanitized = re.sub(r"[^a-z0-9-]", "-", self.name.lower()).strip("-")
        return f"neurohub-{sanitized}:{self.version}"

    @property
    def app_name(self) -> str:
        sanitized = re.sub(r"[^a-z0-9-]", "-", self.name.lower()).strip("-")
        return f"neurohub-svc-{sanitized}"
