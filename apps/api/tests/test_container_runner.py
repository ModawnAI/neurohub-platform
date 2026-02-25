"""Tests for the Container Runner — Fly Machine API orchestrator.

TDD: Tests define expected behavior for launching, monitoring,
and collecting results from containerized service executions.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.container_runner import (
    ContainerRunner,
    ContainerConfig,
    ContainerStatus,
    MachineSpec,
    RunResult,
)


def _make_response(status_code=200, json_data=None, text=""):
    """Create a mock httpx response that behaves correctly."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status = MagicMock()  # Sync method, not async
    if status_code >= 400:
        from httpx import HTTPStatusError, Request, Response

        resp.raise_for_status.side_effect = HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=resp
        )
    return resp


@pytest.fixture
def runner():
    return ContainerRunner(
        fly_api_token="test-token",
        fly_org="neurohub",
        api_base_url="https://api.machines.dev",
    )


@pytest.fixture
def sample_job_spec():
    return {
        "run_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "case_id": str(uuid.uuid4()),
        "institution_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "service": {
            "name": "brain-classifier",
            "display_name": "뇌 MRI 분류기",
            "version": 1,
        },
        "pipeline": {"name": "classify-pipeline", "version": "1.0.0"},
        "priority": 5,
        "user_inputs": {"patient_age": 65, "scan_type": "t1"},
        "user_options": {},
        "case_demographics": {"age": 65, "sex": "M"},
        "patient_ref": "PAT-001",
        "input_artifacts": {
            "mri_scan": "institutions/inst-1/requests/req-1/cases/case-1/mri.nii.gz",
        },
        "steps": [
            {
                "index": 0,
                "name": "classify",
                "image": "registry.fly.io/neurohub-svc-brain-classifier:1.0.0",
                "command": None,
                "resources": {"gpu": 0, "memory_gb": 4},
                "timeout_seconds": 300,
            },
        ],
        "storage": {
            "bucket_inputs": "neurohub-inputs",
            "bucket_outputs": "neurohub-outputs",
            "output_base": "institutions/inst-1/requests/req-1/cases/case-1/outputs",
        },
        "callback_url": "/internal/runs/run-1/result",
        "heartbeat_url": "/internal/runs/run-1/heartbeat",
    }


class TestContainerConfig:
    def test_from_job_spec_step(self, sample_job_spec):
        step = sample_job_spec["steps"][0]
        config = ContainerConfig.from_step(step, sample_job_spec)
        assert config.image == "registry.fly.io/neurohub-svc-brain-classifier:1.0.0"
        assert config.memory_mb == 4096
        assert config.cpu_kind == "shared"
        assert config.timeout_seconds == 300

    def test_gpu_step_uses_performance_cpu(self):
        step = {
            "index": 0,
            "name": "gpu-step",
            "image": "registry.fly.io/neurohub-svc-gpu:1.0.0",
            "resources": {"gpu": 1, "memory_gb": 16},
            "timeout_seconds": 600,
        }
        config = ContainerConfig.from_step(step, {"run_id": "test"})
        assert config.gpu_kind == "a100-pcie-40gb"
        assert config.cpus == 4
        assert config.memory_mb == 16384

    def test_default_resources(self):
        step = {
            "index": 0,
            "name": "default",
            "image": "test:latest",
            "resources": {},
            "timeout_seconds": 300,
        }
        config = ContainerConfig.from_step(step, {"run_id": "test"})
        assert config.memory_mb == 1024
        assert config.cpus == 1


class TestMachineSpec:
    def test_to_fly_api_payload(self, sample_job_spec):
        step = sample_job_spec["steps"][0]
        config = ContainerConfig.from_step(step, sample_job_spec)
        spec = MachineSpec(
            config=config,
            job_spec=sample_job_spec,
            env={
                "NEUROHUB_JOB_SPEC": "base64-encoded-job-spec",
                "NEUROHUB_API_URL": "https://neurohub-api.fly.dev",
                "NEUROHUB_INTERNAL_KEY": "secret",
            },
        )
        payload = spec.to_fly_payload()
        assert payload["config"]["image"] == config.image
        assert payload["config"]["guest"]["memory_mb"] == 4096
        assert "NEUROHUB_JOB_SPEC" in payload["config"]["env"]
        assert payload["config"]["auto_destroy"] is True
        assert payload["region"] == "nrt"

    def test_gpu_payload_includes_gpu(self):
        config = ContainerConfig(
            image="test:latest",
            memory_mb=16384,
            cpus=4,
            cpu_kind="performance",
            gpu_kind="a100-pcie-40gb",
            gpus=1,
            timeout_seconds=600,
        )
        spec = MachineSpec(config=config, job_spec={}, env={})
        payload = spec.to_fly_payload()
        assert payload["config"]["guest"]["gpus"] == 1
        assert payload["config"]["guest"]["gpu_kind"] == "a100-pcie-40gb"


class TestContainerRunner:
    @pytest.mark.asyncio
    async def test_launch_machine(self, runner, sample_job_spec):
        mock_resp = _make_response(200, {"id": "machine-123", "state": "created", "instance_id": "inst-abc"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            result = await runner.launch_machine(
                app_name="neurohub-svc-brain-classifier",
                job_spec=sample_job_spec,
                step_index=0,
            )

            assert result.machine_id == "machine-123"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_machine_status(self, runner):
        mock_resp = _make_response(200, {"id": "machine-123", "state": "started"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            status = await runner.get_machine_status("neurohub-svc-brain-classifier", "machine-123")
            assert status == ContainerStatus.RUNNING

    @pytest.mark.asyncio
    async def test_wait_for_completion(self, runner):
        responses = [
            _make_response(200, {"id": "m-1", "state": "started"}),
            _make_response(200, {"id": "m-1", "state": "started"}),
            _make_response(200, {"id": "m-1", "state": "stopped"}),
        ]
        call_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            r = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return r

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = mock_get
            MockClient.return_value = mock_client

            status = await runner.wait_for_machine(
                "neurohub-svc-brain-classifier",
                "m-1",
                poll_interval=0.01,
                timeout=5,
            )
            assert status == ContainerStatus.STOPPED
            assert call_count >= 3

    @pytest.mark.asyncio
    async def test_get_machine_logs(self, runner):
        mock_resp = _make_response(200, text="2024-01-01 INFO: Starting...\n2024-01-01 INFO: Done.\n")
        mock_resp.text = "2024-01-01 INFO: Starting...\n2024-01-01 INFO: Done.\n"

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            logs = await runner.get_machine_logs("neurohub-svc-brain-classifier", "m-1")
            assert "Starting" in logs

    @pytest.mark.asyncio
    async def test_destroy_machine(self, runner):
        mock_resp = _make_response(200)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.delete = AsyncMock(return_value=mock_resp)
            MockClient.return_value = mock_client

            await runner.destroy_machine("neurohub-svc-brain-classifier", "m-1")
            mock_client.delete.assert_called_once()


class TestContainerRunnerExecuteStep:
    @pytest.mark.asyncio
    async def test_execute_step_full_cycle(self, runner, sample_job_spec):
        launch_resp = _make_response(200, {"id": "m-exec", "state": "created"})
        status_resp = _make_response(200, {"id": "m-exec", "state": "stopped"})
        logs_resp = _make_response(200)
        logs_resp.text = "Processing complete"
        destroy_resp = _make_response(200)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=launch_resp)
            mock_client.get = AsyncMock(side_effect=[status_resp, logs_resp])
            mock_client.delete = AsyncMock(return_value=destroy_resp)
            MockClient.return_value = mock_client

            result = await runner.execute_step(
                app_name="neurohub-svc-brain-classifier",
                job_spec=sample_job_spec,
                step_index=0,
            )

            assert isinstance(result, RunResult)
            assert result.status == "SUCCEEDED"
            assert result.machine_id == "m-exec"
            assert "Processing complete" in result.logs

    @pytest.mark.asyncio
    async def test_execute_step_timeout(self, runner, sample_job_spec):
        launch_resp = _make_response(200, {"id": "m-timeout", "state": "created"})
        status_resp = _make_response(200, {"id": "m-timeout", "state": "started"})
        destroy_resp = _make_response(200)

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=launch_resp)
            mock_client.get = AsyncMock(return_value=status_resp)
            mock_client.delete = AsyncMock(return_value=destroy_resp)
            MockClient.return_value = mock_client

            result = await runner.execute_step(
                app_name="neurohub-svc-brain-classifier",
                job_spec=sample_job_spec,
                step_index=0,
                timeout_override=0.05,
            )

            assert result.status == "TIMEOUT"


class TestAppNameGeneration:
    def test_from_service_name(self):
        from app.services.container_runner import service_to_app_name

        assert service_to_app_name("brain-classifier") == "neurohub-svc-brain-classifier"
        assert service_to_app_name("my_cool_service") == "neurohub-svc-my-cool-service"
        assert service_to_app_name("MRI Analyzer") == "neurohub-svc-mri-analyzer"

    def test_from_job_spec(self, sample_job_spec):
        from app.services.container_runner import app_name_from_job_spec

        name = app_name_from_job_spec(sample_job_spec)
        assert name == "neurohub-svc-brain-classifier"


class TestPresignedUrlGeneration:
    @pytest.mark.asyncio
    async def test_enrich_job_spec_with_presigned_urls(self, runner, sample_job_spec):
        async def mock_sign(bucket, path):
            return f"https://supabase.example.com/storage/v1/object/sign/{bucket}/{path}?token=abc"

        enriched = await runner.enrich_input_urls(sample_job_spec, sign_fn=mock_sign)
        assert "presigned_urls" in enriched
        assert "mri_scan" in enriched["presigned_urls"]
        assert "token=abc" in enriched["presigned_urls"]["mri_scan"]
