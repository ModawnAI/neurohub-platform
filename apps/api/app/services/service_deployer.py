"""Service Deployer — manages deploying containerized services to Fly.io.

Handles:
- Creating Fly apps for services
- Deploying service container images
- Scaling machines
- Undeploying services
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("neurohub.service_deployer")


class DeploymentStatus(str, Enum):
    PENDING = "PENDING"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    UNDEPLOYED = "UNDEPLOYED"


@dataclass
class DeploymentRecord:
    app_name: str
    image: str
    status: DeploymentStatus
    machine_ids: list[str] | None = None
    error: str | None = None


class ServiceDeployer:
    """Manages Fly.io app lifecycle for NeuroHub services."""

    def __init__(
        self,
        fly_api_token: str,
        fly_org: str = "neurohub",
        registry_host: str = "registry.fly.io",
        api_base_url: str = "https://api.machines.dev",
    ):
        self.fly_api_token = fly_api_token
        self.fly_org = fly_org
        self.registry_host = registry_host
        self.api_base_url = api_base_url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.fly_api_token}",
            "Content-Type": "application/json",
        }

    def _sanitize_name(self, name: str) -> str:
        sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
        return re.sub(r"-+", "-", sanitized)

    def _app_name(self, service_name: str) -> str:
        return f"neurohub-svc-{self._sanitize_name(service_name)}"

    def image_tag(self, service_name: str, version: str) -> str:
        sanitized = self._sanitize_name(service_name)
        return f"{self.registry_host}/neurohub-svc-{sanitized}:{version}"

    async def create_app(self, service_def: dict) -> str:
        """Create a Fly app for the service. Idempotent."""
        import httpx

        app_name = self._app_name(service_def["name"])
        url = f"{self.api_base_url}/v1/apps"
        payload = {
            "app_name": app_name,
            "org_slug": self.fly_org,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            if resp.status_code in (200, 201):
                logger.info("Created Fly app: %s", app_name)
            elif resp.status_code == 422:
                logger.info("Fly app %s already exists", app_name)
            else:
                resp.raise_for_status()

        return app_name

    async def deploy(self, service_def: dict) -> DeploymentRecord:
        """Deploy a service container image to Fly.io."""
        import httpx

        app_name = self._app_name(service_def["name"])
        image = service_def.get("container_image", "")

        if not image:
            version = service_def.get("version_label", "latest")
            image = self.image_tag(service_def["name"], version)

        resources = service_def.get("resource_requirements", {})
        memory_gb = resources.get("memory_gb", 1)
        cpus = resources.get("cpus", 1)

        payload = {
            "region": "nrt",
            "config": {
                "image": image,
                "guest": {
                    "memory_mb": int(memory_gb * 1024),
                    "cpus": cpus,
                    "cpu_kind": "shared",
                },
                "env": {
                    "NEUROHUB_SERVICE_NAME": service_def["name"],
                    "NEUROHUB_SERVICE_VERSION": service_def.get("version_label", "1.0.0"),
                },
                "auto_destroy": False,
                "restart": {"policy": "always"},
                "services": [
                    {
                        "ports": [{"port": 443, "handlers": ["tls", "http"]}],
                        "protocol": "tcp",
                        "internal_port": 8080,
                    },
                ],
            },
        }

        url = f"{self.api_base_url}/v1/apps/{app_name}/machines"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        logger.info("Deployed machine %s for app %s", data["id"], app_name)
        return DeploymentRecord(
            app_name=app_name,
            image=image,
            status=DeploymentStatus.DEPLOYED,
            machine_ids=[data["id"]],
        )

    async def list_machines(self, app_name: str) -> list[dict]:
        """List all machines for a Fly app."""
        import httpx

        url = f"{self.api_base_url}/v1/apps/{app_name}/machines"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def scale(self, app_name: str, target_count: int) -> int:
        """Scale the number of machines for an app."""
        import httpx

        machines = await self.list_machines(app_name)
        current = len(machines)

        if current >= target_count:
            return current

        # Create additional machines cloned from the first
        if not machines:
            raise ValueError(f"No machines found for {app_name}. Deploy first.")

        template = machines[0]
        url = f"{self.api_base_url}/v1/apps/{app_name}/machines"

        async with httpx.AsyncClient(timeout=30) as client:
            for _ in range(target_count - current):
                payload = {
                    "region": "nrt",
                    "config": template.get("config", {}),
                }
                await client.post(url, json=payload, headers=self._headers())

        return target_count

    async def undeploy(self, app_name: str) -> None:
        """Stop and destroy all machines for an app."""
        import httpx

        machines = await self.list_machines(app_name)

        async with httpx.AsyncClient(timeout=10) as client:
            for m in machines:
                mid = m["id"]
                url = f"{self.api_base_url}/v1/apps/{app_name}/machines/{mid}"
                await client.delete(url, headers=self._headers())
                logger.info("Destroyed machine %s", mid)
