"""Tests for the HTTP server that wraps a BaseService.

The server exposes /predict, /health, /schema endpoints following
the NeuroHub container contract.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from neurohub_sdk import BaseService, InputContext, OutputContext, ServiceConfig
from neurohub_sdk.schema import InputField, OutputField, UploadSlot, SchemaDefinition
from neurohub_sdk.server import create_app


class SampleService(BaseService):
    config = ServiceConfig(
        name="sample-service",
        version="1.0.0",
        display_name="Sample Service",
    )

    schema = SchemaDefinition(
        inputs=[
            InputField(key="text", type="text", label="텍스트", required=True),
        ],
        uploads=[
            UploadSlot(
                key="image",
                label="이미지",
                required=False,
                accepted_extensions=[".jpg", ".png"],
                max_files=1,
            ),
        ],
        outputs=[
            OutputField(key="length", type="number", label="길이"),
        ],
    )

    async def predict(self, ctx: InputContext) -> OutputContext:
        text = ctx.get_input("text")
        output = ctx.create_output()
        output.set("length", len(text))
        return output


class FailingService(BaseService):
    config = ServiceConfig(name="fail-service", version="1.0.0", display_name="Fail")

    schema = SchemaDefinition(
        inputs=[InputField(key="x", type="text", label="X", required=True)],
        outputs=[],
    )

    async def predict(self, ctx: InputContext) -> OutputContext:
        raise ValueError("Intentional failure")


@pytest.fixture
def app():
    return create_app(SampleService())


@pytest.fixture
def failing_app():
    return create_app(FailingService())


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def failing_client(failing_app):
    transport = ASGITransport(app=failing_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sample-service"
        assert data["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_ready(self, client):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200


class TestSchemaEndpoint:
    @pytest.mark.asyncio
    async def test_schema_returns_full_definition(self, client):
        resp = await client.get("/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "sample-service"
        assert data["version"] == "1.0.0"
        assert len(data["schema"]["inputs"]) == 1
        assert len(data["schema"]["uploads"]) == 1
        assert len(data["schema"]["outputs"]) == 1

    @pytest.mark.asyncio
    async def test_schema_input_details(self, client):
        resp = await client.get("/schema")
        data = resp.json()
        inp = data["schema"]["inputs"][0]
        assert inp["key"] == "text"
        assert inp["type"] == "text"
        assert inp["label"] == "텍스트"
        assert inp["required"] is True


class TestPredictEndpoint:
    @pytest.mark.asyncio
    async def test_predict_with_job_spec(self, client):
        """Predict endpoint accepts a full JobSpec and returns structured output."""
        job_spec = {
            "run_id": "run-001",
            "request_id": "req-001",
            "case_id": "case-001",
            "user_inputs": {"text": "hello world"},
            "case_demographics": {},
            "user_options": {},
            "input_artifacts": {},
            "storage": {},
        }
        resp = await client.post("/predict", json=job_spec)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCEEDED"
        assert data["results"]["length"] == 11

    @pytest.mark.asyncio
    async def test_predict_returns_metrics(self, client):
        job_spec = {
            "run_id": "run-002",
            "request_id": "req-002",
            "case_id": "case-002",
            "user_inputs": {"text": "test"},
            "case_demographics": {},
            "user_options": {},
            "input_artifacts": {},
            "storage": {},
        }
        resp = await client.post("/predict", json=job_spec)
        data = resp.json()
        # Server should add timing metrics automatically
        assert "metrics" in data
        assert "processing_time_ms" in data["metrics"]

    @pytest.mark.asyncio
    async def test_predict_missing_input(self, client):
        """Missing required input should return error."""
        job_spec = {
            "run_id": "run-003",
            "request_id": "req-003",
            "case_id": "case-003",
            "user_inputs": {},  # Missing 'text'
            "case_demographics": {},
            "user_options": {},
            "input_artifacts": {},
            "storage": {},
        }
        resp = await client.post("/predict", json=job_spec)
        data = resp.json()
        # Should still return 200 with FAILED status (not HTTP error)
        assert resp.status_code == 200
        assert data["status"] == "FAILED"
        assert "error" in data

    @pytest.mark.asyncio
    async def test_predict_service_exception(self, failing_client):
        """Service exception should be caught and returned as structured error."""
        job_spec = {
            "run_id": "run-fail",
            "request_id": "req-fail",
            "case_id": "case-fail",
            "user_inputs": {"x": "anything"},
            "case_demographics": {},
            "user_options": {},
            "input_artifacts": {},
            "storage": {},
        }
        resp = await failing_client.post("/predict", json=job_spec)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "FAILED"
        assert "Intentional failure" in data["error"]["message"]

    @pytest.mark.asyncio
    async def test_predict_invalid_json(self, client):
        resp = await client.post("/predict", content=b"not json", headers={"content-type": "application/json"})
        assert resp.status_code == 422


class TestDockerfileGeneration:
    def test_generates_dockerfile(self):
        from neurohub_sdk.packaging import generate_dockerfile

        svc = SampleService()
        dockerfile = generate_dockerfile(svc)
        assert "FROM python:" in dockerfile
        assert "neurohub-sdk" in dockerfile
        assert "EXPOSE 8080" in dockerfile
        assert "HEALTHCHECK" in dockerfile

    def test_generates_fly_toml(self):
        from neurohub_sdk.packaging import generate_fly_toml

        svc = SampleService()
        toml = generate_fly_toml(svc, app_name="neurohub-svc-sample-service")
        assert "neurohub-svc-sample-service" in toml
        assert "8080" in toml
        assert "nrt" in toml  # Default region
