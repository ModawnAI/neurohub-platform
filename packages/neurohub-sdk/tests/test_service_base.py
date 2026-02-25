"""Tests for BaseService — the core abstraction service authors use.

TDD: These tests define the expected behavior before implementation.
"""

import pytest
from neurohub_sdk import BaseService, InputContext, OutputContext, ServiceConfig
from neurohub_sdk.schema import InputField, OutputField, UploadSlot, SchemaDefinition


# ── Minimal service implementation for testing ──


class EchoService(BaseService):
    """Simplest possible service: echoes input back."""

    config = ServiceConfig(
        name="echo-service",
        version="1.0.0",
        display_name="Echo Service",
        description="Echoes input back for testing",
    )

    schema = SchemaDefinition(
        inputs=[
            InputField(key="message", type="text", label="메시지", required=True),
        ],
        outputs=[
            OutputField(key="echo", type="text", label="에코 결과"),
        ],
    )

    async def predict(self, ctx: InputContext) -> OutputContext:
        message = ctx.get_input("message")
        output = ctx.create_output()
        output.set("echo", message)
        return output


class ImageClassifier(BaseService):
    """Multi-modal service: takes image + text, returns classification."""

    config = ServiceConfig(
        name="brain-classifier",
        version="2.1.0",
        display_name="뇌 MRI 분류기",
        description="Brain MRI classification service",
        department="neurology",
    )

    schema = SchemaDefinition(
        inputs=[
            InputField(key="patient_age", type="number", label="나이", required=True),
            InputField(
                key="scan_type",
                type="select",
                label="스캔 유형",
                required=True,
                options=[
                    {"value": "t1", "label": "T1"},
                    {"value": "t2", "label": "T2"},
                    {"value": "flair", "label": "FLAIR"},
                ],
            ),
        ],
        uploads=[
            UploadSlot(
                key="mri_scan",
                label="MRI 스캔",
                required=True,
                accepted_extensions=[".nii", ".nii.gz", ".dcm"],
                max_files=1,
            ),
            UploadSlot(
                key="reference",
                label="참고 이미지",
                required=False,
                accepted_extensions=[".jpg", ".png"],
                max_files=5,
            ),
        ],
        outputs=[
            OutputField(key="classification", type="text", label="분류 결과"),
            OutputField(key="confidence", type="number", label="신뢰도"),
            OutputField(key="heatmap_path", type="file", label="히트맵"),
        ],
    )

    async def predict(self, ctx: InputContext) -> OutputContext:
        age = ctx.get_input("patient_age")
        scan_type = ctx.get_input("scan_type")
        mri_bytes = await ctx.get_file("mri_scan")

        output = ctx.create_output()
        output.set("classification", "normal")
        output.set("confidence", 0.95)
        output.set_file("heatmap_path", b"fake-heatmap-png", "heatmap.png", "image/png")
        return output


# ── Tests ──


class TestServiceConfig:
    def test_basic_config(self):
        svc = EchoService()
        assert svc.config.name == "echo-service"
        assert svc.config.version == "1.0.0"
        assert svc.config.display_name == "Echo Service"

    def test_config_with_department(self):
        svc = ImageClassifier()
        assert svc.config.department == "neurology"

    def test_config_generates_image_tag(self):
        svc = EchoService()
        tag = svc.config.image_tag
        assert tag == "neurohub-echo-service:1.0.0"


class TestSchemaDefinition:
    def test_inputs_defined(self):
        svc = EchoService()
        assert len(svc.schema.inputs) == 1
        assert svc.schema.inputs[0].key == "message"
        assert svc.schema.inputs[0].type == "text"
        assert svc.schema.inputs[0].required is True

    def test_multi_modal_uploads(self):
        svc = ImageClassifier()
        assert len(svc.schema.uploads) == 2
        mri_slot = svc.schema.uploads[0]
        assert mri_slot.key == "mri_scan"
        assert ".dcm" in mri_slot.accepted_extensions
        assert mri_slot.max_files == 1

    def test_outputs_defined(self):
        svc = ImageClassifier()
        assert len(svc.schema.outputs) == 3
        assert svc.schema.outputs[0].key == "classification"

    def test_schema_to_dict_roundtrip(self):
        svc = ImageClassifier()
        d = svc.schema.to_dict()
        assert "inputs" in d
        assert "uploads" in d
        assert "outputs" in d
        restored = SchemaDefinition.from_dict(d)
        assert len(restored.inputs) == len(svc.schema.inputs)
        assert len(restored.uploads) == len(svc.schema.uploads)
        assert len(restored.outputs) == len(svc.schema.outputs)


class TestInputContext:
    def test_get_input_value(self):
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={"message": "hello"},
            demographics={},
            options={},
            files={},
            storage_config={},
        )
        assert ctx.get_input("message") == "hello"

    def test_get_input_missing_raises(self):
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={},
            demographics={},
            options={},
            files={},
            storage_config={},
        )
        with pytest.raises(KeyError):
            ctx.get_input("nonexistent")

    def test_get_input_with_default(self):
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={},
            demographics={},
            options={},
            files={},
            storage_config={},
        )
        assert ctx.get_input("nonexistent", default="fallback") == "fallback"

    def test_get_demographics(self):
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={},
            demographics={"age": 65, "sex": "M"},
            options={},
            files={},
            storage_config={},
        )
        assert ctx.demographics["age"] == 65

    def test_get_option(self):
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={},
            demographics={},
            options={"threshold": 0.5},
            files={},
            storage_config={},
        )
        assert ctx.get_option("threshold") == 0.5

    def test_files_registry(self):
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={},
            demographics={},
            options={},
            files={
                "mri_scan": {"storage_path": "institutions/x/scan.nii.gz", "presigned_url": "https://example.com/scan.nii.gz"},
            },
            storage_config={"bucket_inputs": "neurohub-inputs"},
        )
        assert ctx.has_file("mri_scan")
        assert not ctx.has_file("reference")

    def test_has_file_with_presigned_url(self):
        """Test that file registry tracks presigned URLs."""
        ctx = InputContext(
            run_id="test-run-1",
            request_id="test-req-1",
            case_id="test-case-1",
            inputs={},
            demographics={},
            options={},
            files={
                "mri_scan": {
                    "storage_path": "path/scan.nii.gz",
                    "presigned_url": "https://storage.example.com/scan.nii.gz",
                },
            },
            storage_config={},
        )
        assert ctx.has_file("mri_scan")
        file_info = ctx.files["mri_scan"]
        assert file_info["presigned_url"] == "https://storage.example.com/scan.nii.gz"

    def test_from_job_spec(self):
        """InputContext can be built from a standard JobSpec dict."""
        job_spec = {
            "run_id": "abc-123",
            "request_id": "req-456",
            "case_id": "case-789",
            "user_inputs": {"message": "hello"},
            "case_demographics": {"age": 30},
            "user_options": {"debug": True},
            "input_artifacts": {
                "mri_scan": "institutions/inst-1/scan.nii.gz",
            },
            "storage": {
                "bucket_inputs": "neurohub-inputs",
                "bucket_outputs": "neurohub-outputs",
            },
        }
        ctx = InputContext.from_job_spec(job_spec)
        assert ctx.run_id == "abc-123"
        assert ctx.get_input("message") == "hello"
        assert ctx.demographics["age"] == 30
        assert ctx.has_file("mri_scan")


class TestOutputContext:
    def test_set_and_get(self):
        output = OutputContext(run_id="test-run-1")
        output.set("classification", "normal")
        output.set("confidence", 0.95)
        result = output.to_dict()
        assert result["results"]["classification"] == "normal"
        assert result["results"]["confidence"] == 0.95

    def test_set_file(self):
        output = OutputContext(run_id="test-run-1")
        output.set_file("heatmap", b"png-bytes", "heatmap.png", "image/png")
        result = output.to_dict()
        assert "heatmap" in result["files"]
        assert result["files"]["heatmap"]["filename"] == "heatmap.png"
        assert result["files"]["heatmap"]["content_type"] == "image/png"
        assert result["files"]["heatmap"]["size"] == 9

    def test_set_metrics(self):
        output = OutputContext(run_id="test-run-1")
        output.set_metric("processing_time_ms", 1234)
        output.set_metric("memory_peak_mb", 512)
        result = output.to_dict()
        assert result["metrics"]["processing_time_ms"] == 1234

    def test_set_error(self):
        output = OutputContext(run_id="test-run-1")
        output.set_error("Model failed to load", code="MODEL_LOAD_ERROR")
        result = output.to_dict()
        assert result["status"] == "FAILED"
        assert result["error"]["message"] == "Model failed to load"
        assert result["error"]["code"] == "MODEL_LOAD_ERROR"

    def test_success_status(self):
        output = OutputContext(run_id="test-run-1")
        output.set("result", "ok")
        result = output.to_dict()
        assert result["status"] == "SUCCEEDED"

    def test_to_result_manifest(self):
        """OutputContext produces a result_manifest compatible with Run model."""
        output = OutputContext(run_id="test-run-1")
        output.set("classification", "tumor")
        output.set("confidence", 0.87)
        output.set_metric("inference_ms", 456)
        manifest = output.to_result_manifest()
        assert manifest["status"] == "completed"
        assert manifest["results"]["classification"] == "tumor"
        assert "metrics" in manifest


class TestPredict:
    @pytest.mark.asyncio
    async def test_echo_predict(self):
        svc = EchoService()
        ctx = InputContext(
            run_id="r1",
            request_id="req1",
            case_id="c1",
            inputs={"message": "hello world"},
            demographics={},
            options={},
            files={},
            storage_config={},
        )
        output = await svc.predict(ctx)
        result = output.to_dict()
        assert result["results"]["echo"] == "hello world"
        assert result["status"] == "SUCCEEDED"

    @pytest.mark.asyncio
    async def test_classifier_predict_without_files(self):
        """Classifier should work with mock data even without real file downloads."""
        svc = ImageClassifier()
        ctx = InputContext(
            run_id="r2",
            request_id="req2",
            case_id="c2",
            inputs={"patient_age": 65, "scan_type": "t1"},
            demographics={"age": 65},
            options={},
            files={"mri_scan": {"storage_path": "fake/path.nii.gz", "presigned_url": None}},
            storage_config={},
        )
        # Override get_file to return fake bytes for testing
        ctx._file_cache["mri_scan"] = b"fake-mri-data"
        output = await svc.predict(ctx)
        result = output.to_dict()
        assert result["results"]["classification"] == "normal"
        assert result["results"]["confidence"] == 0.95
        assert result["status"] == "SUCCEEDED"
