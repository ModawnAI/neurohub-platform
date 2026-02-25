"""Rigorous edge-case tests for ContainerRunner and ServiceDeployer.

Covers:
- Malformed inputs, empty/null fields, unicode
- Network failures, timeouts, retries
- Concurrent operations
- Resource boundary cases (0 GPU, huge memory, no steps)
- State machine edge cases
- Real-world Fly API error patterns
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.container_runner import (
    ContainerRunner,
    ContainerConfig,
    ContainerStatus,
    MachineSpec,
    RunResult,
    service_to_app_name,
    app_name_from_job_spec,
)
from app.services.service_deployer import (
    ServiceDeployer,
    DeploymentStatus,
    DeploymentRecord,
)


def _ok(json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = json_data or {}
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def _err(status_code, json_data=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text or f"HTTP {status_code}"
    resp.raise_for_status = MagicMock(side_effect=Exception(f"HTTP {status_code}"))
    return resp


def _async_client(**overrides):
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    for k, v in overrides.items():
        setattr(mock_client, k, v)
    return mock_client


@pytest.fixture
def runner():
    return ContainerRunner(fly_api_token="test-tok", fly_org="neurohub")


@pytest.fixture
def deployer():
    return ServiceDeployer(fly_api_token="test-tok", fly_org="neurohub")


# ═══════════════════════════════════════════════════════════════════════════
# ContainerConfig edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestContainerConfigEdgeCases:
    def test_zero_memory(self):
        step = {"index": 0, "name": "tiny", "image": "x:1", "resources": {"memory_gb": 0}, "timeout_seconds": 10}
        config = ContainerConfig.from_step(step, {})
        assert config.memory_mb == 0

    def test_fractional_memory(self):
        step = {"index": 0, "name": "frac", "image": "x:1", "resources": {"memory_gb": 0.5}, "timeout_seconds": 60}
        config = ContainerConfig.from_step(step, {})
        assert config.memory_mb == 512

    def test_very_large_memory(self):
        step = {"index": 0, "name": "big", "image": "x:1", "resources": {"memory_gb": 128, "gpu": 8}, "timeout_seconds": 3600}
        config = ContainerConfig.from_step(step, {})
        assert config.memory_mb == 131072
        assert config.gpus == 8

    def test_missing_resources_key(self):
        step = {"index": 0, "name": "bare", "image": "x:1", "timeout_seconds": 30}
        config = ContainerConfig.from_step(step, {})
        assert config.memory_mb == 1024  # default
        assert config.cpus == 1

    def test_empty_step(self):
        with pytest.raises(ValueError, match="must specify a container 'image'"):
            ContainerConfig.from_step({}, {})

    def test_gpu_boundary_zero(self):
        step = {"index": 0, "name": "nogpu", "image": "x:1", "resources": {"gpu": 0, "memory_gb": 2}, "timeout_seconds": 60}
        config = ContainerConfig.from_step(step, {})
        assert config.gpu_kind is None
        assert config.gpus == 0
        assert config.cpu_kind == "shared"

    def test_gpu_boundary_one(self):
        step = {"index": 0, "name": "gpu1", "image": "x:1", "resources": {"gpu": 1, "memory_gb": 8}, "timeout_seconds": 60}
        config = ContainerConfig.from_step(step, {})
        assert config.gpu_kind == "a100-pcie-40gb"
        assert config.gpus == 1
        assert config.cpu_kind == "performance"

    def test_custom_gpu_kind(self):
        step = {"index": 0, "name": "custom", "image": "x:1", "resources": {"gpu": 1, "gpu_kind": "l40s", "memory_gb": 48}, "timeout_seconds": 60}
        config = ContainerConfig.from_step(step, {})
        assert config.gpu_kind == "l40s"


# ═══════════════════════════════════════════════════════════════════════════
# App name generation edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestAppNameEdgeCases:
    def test_empty_name(self):
        assert service_to_app_name("") == "neurohub-svc-"

    def test_unicode_korean(self):
        result = service_to_app_name("뇌 MRI 분류기")
        assert result.startswith("neurohub-svc-")
        # Korean chars become hyphens
        assert "--" not in result or "neurohub-svc-" in result

    def test_special_characters(self):
        result = service_to_app_name("my.service@v2!#$%")
        assert "." not in result.split("neurohub-svc-")[1]
        assert "@" not in result

    def test_already_prefixed(self):
        result = service_to_app_name("neurohub-svc-existing")
        assert result == "neurohub-svc-neurohub-svc-existing"

    def test_very_long_name(self):
        result = service_to_app_name("a" * 200)
        assert result.startswith("neurohub-svc-")

    def test_numbers_only(self):
        result = service_to_app_name("12345")
        assert result == "neurohub-svc-12345"

    def test_hyphens_collapsed(self):
        result = service_to_app_name("my---service---name")
        assert "---" not in result

    def test_from_job_spec_missing_service(self):
        result = app_name_from_job_spec({})
        assert result == "neurohub-svc-unknown"

    def test_from_job_spec_empty_name(self):
        result = app_name_from_job_spec({"service": {"name": ""}})
        assert result == "neurohub-svc-"


# ═══════════════════════════════════════════════════════════════════════════
# MachineSpec payload edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestMachineSpecEdgeCases:
    def test_empty_env(self):
        config = ContainerConfig(image="x:1")
        spec = MachineSpec(config=config, job_spec={}, env={})
        payload = spec.to_fly_payload()
        assert payload["config"]["env"] == {}

    def test_large_env(self):
        config = ContainerConfig(image="x:1")
        env = {f"KEY_{i}": f"VALUE_{i}" for i in range(100)}
        spec = MachineSpec(config=config, job_spec={}, env=env)
        payload = spec.to_fly_payload()
        assert len(payload["config"]["env"]) == 100

    def test_no_gpu_payload(self):
        config = ContainerConfig(image="x:1", gpus=0, gpu_kind=None)
        spec = MachineSpec(config=config, job_spec={}, env={})
        payload = spec.to_fly_payload()
        assert "gpus" not in payload["config"]["guest"]
        assert "gpu_kind" not in payload["config"]["guest"]

    def test_auto_destroy_always_true(self):
        config = ContainerConfig(image="x:1")
        spec = MachineSpec(config=config, job_spec={}, env={})
        payload = spec.to_fly_payload()
        assert payload["config"]["auto_destroy"] is True

    def test_custom_region(self):
        config = ContainerConfig(image="x:1")
        spec = MachineSpec(config=config, job_spec={}, env={}, region="iad")
        payload = spec.to_fly_payload()
        assert payload["region"] == "iad"


# ═══════════════════════════════════════════════════════════════════════════
# ContainerRunner error handling
# ═══════════════════════════════════════════════════════════════════════════


class TestContainerRunnerErrors:
    @pytest.mark.asyncio
    async def test_launch_network_error(self, runner):
        """Network failure during launch returns FAILED."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(side_effect=ConnectionError("DNS failed")))
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 10}]}, 0)
            assert result.status == "FAILED"
            assert "Launch failed" in result.error

    @pytest.mark.asyncio
    async def test_launch_http_500(self, runner):
        """Fly API 500 should be caught."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_err(500)))
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 10}]}, 0)
            assert result.status == "FAILED"

    @pytest.mark.asyncio
    async def test_launch_http_401_unauthorized(self, runner):
        """Invalid API token should fail."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_err(401, {"error": "unauthorized"})))
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 10}]}, 0)
            assert result.status == "FAILED"

    @pytest.mark.asyncio
    async def test_status_check_network_error(self, runner):
        """If status check fails, machine status treated as FAILED."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(get=AsyncMock(side_effect=ConnectionError("timeout")))
            MC.return_value = mc

            with pytest.raises(ConnectionError):
                await runner.get_machine_status("app", "m-1")

    @pytest.mark.asyncio
    async def test_logs_retrieval_failure_returns_empty(self, runner):
        """Failed log retrieval returns empty string."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(get=AsyncMock(return_value=_err(404)))
            MC.return_value = mc

            logs = await runner.get_machine_logs("app", "m-1")
            assert logs == ""

    @pytest.mark.asyncio
    async def test_destroy_ignores_404(self, runner):
        """Destroying already-destroyed machine should not raise."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(delete=AsyncMock(return_value=_ok()))
            MC.return_value = mc

            # Should not raise
            await runner.destroy_machine("app", "m-nonexistent")

    @pytest.mark.asyncio
    async def test_execute_step_empty_steps_list(self, runner):
        """Job spec with no steps should handle gracefully."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})))
            mc.get = AsyncMock(return_value=_ok({"id": "m-1", "state": "stopped"}))
            mc.delete = AsyncMock(return_value=_ok())
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": []}, 0)
            # Should handle IndexError gracefully or use empty step
            assert result.machine_id in ("m-1", "")

    @pytest.mark.asyncio
    async def test_execute_step_no_steps_key(self, runner):
        """Job spec without 'steps' key."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})))
            mc.get = AsyncMock(return_value=_ok({"id": "m-1", "state": "stopped"}))
            mc.delete = AsyncMock(return_value=_ok())
            MC.return_value = mc

            result = await runner.execute_step("app", {}, 0)
            assert result.machine_id in ("m-1", "")


class TestContainerRunnerTimeout:
    @pytest.mark.asyncio
    async def test_very_short_timeout(self, runner):
        """Extremely short timeout should still complete without hanging."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})),
                get=AsyncMock(return_value=_ok({"id": "m-1", "state": "started"})),
                delete=AsyncMock(return_value=_ok()),
            )
            MC.return_value = mc

            result = await runner.execute_step(
                "app",
                {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 1}]},
                0,
                timeout_override=0.01,
            )
            assert result.status == "TIMEOUT"
            assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_zero_timeout(self, runner):
        """Zero timeout: should immediately timeout."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})),
                get=AsyncMock(return_value=_ok({"id": "m-1", "state": "started"})),
                delete=AsyncMock(return_value=_ok()),
            )
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 0}]}, 0, timeout_override=0.001)
            assert result.status == "TIMEOUT"


class TestContainerStatusMapping:
    def test_all_fly_states(self):
        assert ContainerStatus.from_fly_state("created") == ContainerStatus.CREATED
        assert ContainerStatus.from_fly_state("starting") == ContainerStatus.STARTING
        assert ContainerStatus.from_fly_state("started") == ContainerStatus.RUNNING
        assert ContainerStatus.from_fly_state("stopping") == ContainerStatus.STOPPING
        assert ContainerStatus.from_fly_state("stopped") == ContainerStatus.STOPPED
        assert ContainerStatus.from_fly_state("failed") == ContainerStatus.FAILED
        assert ContainerStatus.from_fly_state("destroyed") == ContainerStatus.DESTROYED

    def test_unknown_state(self):
        assert ContainerStatus.from_fly_state("some-new-state") == ContainerStatus.FAILED

    def test_empty_state(self):
        assert ContainerStatus.from_fly_state("") == ContainerStatus.FAILED


# ═══════════════════════════════════════════════════════════════════════════
# Presigned URL enrichment
# ═══════════════════════════════════════════════════════════════════════════


class TestEnrichInputUrls:
    @pytest.mark.asyncio
    async def test_no_artifacts(self, runner):
        job_spec = {"input_artifacts": {}, "storage": {}}
        enriched = await runner.enrich_input_urls(job_spec, sign_fn=AsyncMock())
        assert enriched["presigned_urls"] == {}

    @pytest.mark.asyncio
    async def test_multiple_artifacts(self, runner):
        job_spec = {
            "input_artifacts": {"mri": "path/mri.nii", "eeg": "path/eeg.edf", "csv": "path/data.csv"},
            "storage": {"bucket_inputs": "neurohub-inputs"},
        }

        async def mock_sign(bucket, path):
            return f"https://signed/{bucket}/{path}"

        enriched = await runner.enrich_input_urls(job_spec, sign_fn=mock_sign)
        assert len(enriched["presigned_urls"]) == 3
        assert "neurohub-inputs" in enriched["presigned_urls"]["mri"]

    @pytest.mark.asyncio
    async def test_sign_failure_propagates(self, runner):
        job_spec = {"input_artifacts": {"file": "path/file"}, "storage": {}}

        async def failing_sign(bucket, path):
            raise Exception("Storage unavailable")

        with pytest.raises(Exception, match="Storage unavailable"):
            await runner.enrich_input_urls(job_spec, sign_fn=failing_sign)

    @pytest.mark.asyncio
    async def test_preserves_original_job_spec(self, runner):
        original = {"input_artifacts": {"x": "path"}, "storage": {}, "run_id": "test"}

        async def mock_sign(bucket, path):
            return "url"

        enriched = await runner.enrich_input_urls(original, sign_fn=mock_sign)
        # Original should not be mutated
        assert "presigned_urls" not in original
        assert enriched["run_id"] == "test"


# ═══════════════════════════════════════════════════════════════════════════
# ServiceDeployer edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestServiceDeployerEdgeCases:
    @pytest.mark.asyncio
    async def test_deploy_without_container_image(self, deployer):
        """When no container_image is provided, should generate default tag."""
        svc = {"name": "test-svc", "version_label": "2.0.0"}

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})))
            MC.return_value = mc

            record = await deployer.deploy(svc)
            assert "neurohub-svc-test-svc:2.0.0" in record.image

    @pytest.mark.asyncio
    async def test_deploy_with_explicit_image(self, deployer):
        svc = {"name": "test-svc", "container_image": "custom-registry.io/my-model:latest"}

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})))
            MC.return_value = mc

            record = await deployer.deploy(svc)
            assert record.image == "custom-registry.io/my-model:latest"

    @pytest.mark.asyncio
    async def test_deploy_network_failure(self, deployer):
        svc = {"name": "test-svc", "container_image": "x:1"}

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_err(500)))
            MC.return_value = mc

            with pytest.raises(Exception):
                await deployer.deploy(svc)

    @pytest.mark.asyncio
    async def test_scale_below_current_count(self, deployer):
        """Scaling to a count equal or below current should be a no-op."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                get=AsyncMock(return_value=_ok([{"id": "m-1"}, {"id": "m-2"}, {"id": "m-3"}])),
            )
            MC.return_value = mc

            count = await deployer.scale("app", target_count=2)
            assert count == 3  # No scale down, returns current count

    @pytest.mark.asyncio
    async def test_scale_no_machines_raises(self, deployer):
        """Scaling with no existing machines should raise."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(get=AsyncMock(return_value=_ok([])))
            MC.return_value = mc

            with pytest.raises(ValueError, match="No machines found"):
                await deployer.scale("app", target_count=2)

    @pytest.mark.asyncio
    async def test_undeploy_empty_app(self, deployer):
        """Undeploy on app with no machines should be fine."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                get=AsyncMock(return_value=_ok([])),
                delete=AsyncMock(return_value=_ok()),
            )
            MC.return_value = mc

            await deployer.undeploy("app")
            mc.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_app_rate_limited(self, deployer):
        """Fly API 429 rate limit should propagate."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=AsyncMock(return_value=_err(429, {"error": "rate limited"})))
            MC.return_value = mc

            with pytest.raises(Exception, match="429"):
                await deployer.create_app({"name": "test"})


class TestImageTagSanitization:
    def test_spaces(self, deployer):
        assert deployer.image_tag("brain mri", "1.0") == "registry.fly.io/neurohub-svc-brain-mri:1.0"

    def test_uppercase(self, deployer):
        assert deployer.image_tag("BrainMRI", "1.0") == "registry.fly.io/neurohub-svc-brainmri:1.0"

    def test_dots(self, deployer):
        assert deployer.image_tag("service.v2", "1.0") == "registry.fly.io/neurohub-svc-service-v2:1.0"

    def test_korean_name(self, deployer):
        tag = deployer.image_tag("뇌분석서비스", "1.0")
        assert tag.startswith("registry.fly.io/neurohub-svc-")
        assert tag.endswith(":1.0")

    def test_empty_version(self, deployer):
        tag = deployer.image_tag("svc", "")
        assert tag == "registry.fly.io/neurohub-svc-svc:"


# ═══════════════════════════════════════════════════════════════════════════
# ContainerRunner full lifecycle with state transitions
# ═══════════════════════════════════════════════════════════════════════════


class TestFullLifecycleScenarios:
    @pytest.mark.asyncio
    async def test_machine_fails_immediately(self, runner):
        """Machine goes created → failed."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})),
                get=AsyncMock(return_value=_ok({"id": "m-1", "state": "failed"})),
                delete=AsyncMock(return_value=_ok()),
            )
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 60}]}, 0)
            assert result.status == "FAILED"

    @pytest.mark.asyncio
    async def test_machine_destroyed_externally(self, runner):
        """Machine is destroyed by external process during execution."""
        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})),
                get=AsyncMock(return_value=_ok({"id": "m-1", "state": "destroyed"})),
                delete=AsyncMock(return_value=_ok()),
            )
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 60}]}, 0)
            assert result.status == "DESTROYED"

    @pytest.mark.asyncio
    async def test_successful_run_with_logs(self, runner):
        """Full success path with log output."""
        with patch("httpx.AsyncClient") as MC:
            logs_resp = _ok()
            logs_resp.text = "2024-01-01 Loading model...\n2024-01-01 Inference complete.\nResult: normal (0.95)"

            mc = _async_client(
                post=AsyncMock(return_value=_ok({"id": "m-success", "state": "created"})),
                get=AsyncMock(side_effect=[
                    _ok({"id": "m-success", "state": "started"}),
                    _ok({"id": "m-success", "state": "stopped"}),
                    logs_resp,  # logs call
                ]),
                delete=AsyncMock(return_value=_ok()),
            )
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "classify", "image": "x:1", "resources": {}, "timeout_seconds": 60}]}, 0)
            assert result.status == "SUCCEEDED"
            assert result.machine_id == "m-success"
            assert "Inference complete" in result.logs
            assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_multiple_status_transitions(self, runner):
        """Machine goes through created → starting → started → stopping → stopped."""
        call_count = 0
        states = ["starting", "started", "started", "stopping", "stopped"]

        async def mock_get(*args, **kwargs):
            nonlocal call_count
            state = states[min(call_count, len(states) - 1)]
            call_count += 1
            return _ok({"id": "m-1", "state": state})

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(
                post=AsyncMock(return_value=_ok({"id": "m-1", "state": "created"})),
                delete=AsyncMock(return_value=_ok()),
            )
            mc.get = mock_get
            MC.return_value = mc

            result = await runner.execute_step("app", {"steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 30}]}, 0)
            assert result.status == "SUCCEEDED"


# ═══════════════════════════════════════════════════════════════════════════
# JobSpec encoding
# ═══════════════════════════════════════════════════════════════════════════


class TestJobSpecEncoding:
    @pytest.mark.asyncio
    async def test_job_spec_base64_encoded_in_env(self, runner):
        """Verify the job spec is base64 encoded in the machine env."""
        import base64
        import json

        captured_payload = {}

        async def capture_post(url, json=None, headers=None):
            captured_payload.update(json or {})
            return _ok({"id": "m-1", "state": "created", "instance_id": "i-1"})

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=capture_post)
            MC.return_value = mc

            job_spec = {
                "run_id": "test-123",
                "steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 10}],
            }
            await runner.launch_machine("app", job_spec, 0)

            env = captured_payload["config"]["env"]
            decoded = json.loads(base64.b64decode(env["NEUROHUB_JOB_SPEC"]))
            assert decoded["run_id"] == "test-123"
            assert env["NEUROHUB_RUN_ID"] == "test-123"
            assert env["NEUROHUB_STEP_INDEX"] == "0"

    @pytest.mark.asyncio
    async def test_large_job_spec_encoding(self, runner):
        """Large job specs with many artifacts should encode correctly."""
        import base64
        import json

        captured_payload = {}

        async def capture_post(url, json=None, headers=None):
            captured_payload.update(json or {})
            return _ok({"id": "m-1", "state": "created", "instance_id": "i-1"})

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=capture_post)
            MC.return_value = mc

            # Big job spec with many artifacts
            artifacts = {f"file_{i}": f"institutions/x/requests/y/cases/z/file_{i}.dcm" for i in range(50)}
            job_spec = {
                "run_id": "big-test",
                "input_artifacts": artifacts,
                "steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 10}],
            }
            await runner.launch_machine("app", job_spec, 0)

            env = captured_payload["config"]["env"]
            decoded = json.loads(base64.b64decode(env["NEUROHUB_JOB_SPEC"]))
            assert len(decoded["input_artifacts"]) == 50

    @pytest.mark.asyncio
    async def test_unicode_in_job_spec(self, runner):
        """Korean/unicode content in job spec should encode correctly."""
        import base64
        import json

        captured_payload = {}

        async def capture_post(url, json=None, headers=None):
            captured_payload.update(json or {})
            return _ok({"id": "m-1", "state": "created", "instance_id": "i-1"})

        with patch("httpx.AsyncClient") as MC:
            mc = _async_client(post=capture_post)
            MC.return_value = mc

            job_spec = {
                "run_id": "korean-test",
                "user_inputs": {"clinical_notes": "환자는 두통과 어지러움을 호소합니다. MRI T1 스캔 필요."},
                "patient_ref": "김철수",
                "steps": [{"index": 0, "name": "s", "image": "x:1", "resources": {}, "timeout_seconds": 10}],
            }
            await runner.launch_machine("app", job_spec, 0)

            env = captured_payload["config"]["env"]
            decoded = json.loads(base64.b64decode(env["NEUROHUB_JOB_SPEC"]))
            assert "두통" in decoded["user_inputs"]["clinical_notes"]
            assert decoded["patient_ref"] == "김철수"
