"""Tests for the Service Deployment system."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.service_deployer import (
    ServiceDeployer,
    DeploymentStatus,
    DeploymentRecord,
)


def _make_response(status_code=200, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def deployer():
    return ServiceDeployer(
        fly_api_token="test-token",
        fly_org="neurohub",
        registry_host="registry.fly.io",
    )


@pytest.fixture
def sample_service_def():
    return {
        "id": str(uuid.uuid4()),
        "name": "brain-classifier",
        "display_name": "뇌 MRI 분류기",
        "version": 1,
        "version_label": "1.0.0",
        "institution_id": str(uuid.uuid4()),
        "container_image": "registry.fly.io/neurohub-svc-brain-classifier:1.0.0",
        "resource_requirements": {
            "memory_gb": 4,
            "cpus": 2,
            "gpu": 0,
        },
    }


class TestServiceDeployer:
    @pytest.mark.asyncio
    async def test_create_fly_app(self, deployer, sample_service_def):
        mock_resp = _make_response(201, {"id": "app-abc", "name": "neurohub-svc-brain-classifier"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            app_name = await deployer.create_app(sample_service_def)
            assert app_name == "neurohub-svc-brain-classifier"

    @pytest.mark.asyncio
    async def test_create_app_already_exists(self, deployer, sample_service_def):
        mock_resp = _make_response(422, {"error": "app already exists"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            app_name = await deployer.create_app(sample_service_def)
            assert app_name == "neurohub-svc-brain-classifier"

    @pytest.mark.asyncio
    async def test_deploy_image(self, deployer, sample_service_def):
        mock_resp = _make_response(200, {"id": "machine-deploy-1", "state": "created"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            record = await deployer.deploy(sample_service_def)
            assert isinstance(record, DeploymentRecord)
            assert record.status == DeploymentStatus.DEPLOYED
            assert record.app_name == "neurohub-svc-brain-classifier"
            assert record.image == sample_service_def["container_image"]

    @pytest.mark.asyncio
    async def test_scale_service(self, deployer):
        list_resp = _make_response(200, [{"id": "m-1", "state": "started", "config": {}}])
        create_resp = _make_response(200, {"id": "m-2", "state": "created"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=list_resp)
            mock_client.post = AsyncMock(return_value=create_resp)
            MockClient.return_value = mock_client

            count = await deployer.scale("neurohub-svc-brain-classifier", target_count=2)
            assert count == 2

    @pytest.mark.asyncio
    async def test_list_deployments(self, deployer):
        mock_resp = _make_response(200, [
            {"id": "m-1", "state": "started", "config": {"image": "test:1.0.0"}},
            {"id": "m-2", "state": "stopped", "config": {"image": "test:1.0.0"}},
        ])

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            machines = await deployer.list_machines("neurohub-svc-brain-classifier")
            assert len(machines) == 2

    @pytest.mark.asyncio
    async def test_undeploy_stops_all_machines(self, deployer):
        list_resp = _make_response(200, [
            {"id": "m-1", "state": "started"},
            {"id": "m-2", "state": "started"},
        ])
        delete_resp = _make_response(200)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=list_resp)
            mock_client.delete = AsyncMock(return_value=delete_resp)
            MockClient.return_value = mock_client

            await deployer.undeploy("neurohub-svc-brain-classifier")
            assert mock_client.delete.call_count == 2


class TestImageTagGeneration:
    def test_generates_correct_tag(self, deployer):
        tag = deployer.image_tag("brain-classifier", "2.1.0")
        assert tag == "registry.fly.io/neurohub-svc-brain-classifier:2.1.0"

    def test_sanitizes_name(self, deployer):
        tag = deployer.image_tag("My Cool Service!", "1.0.0")
        assert tag == "registry.fly.io/neurohub-svc-my-cool-service:1.0.0"
