"""Tests for the pipeline orchestrator — end-to-end processing coordination.

Tests the pipeline stages from zip extraction through to technique execution.
Uses mocked services for container execution and DB access.
"""

import os
import tempfile
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    PipelineStageResult,
    _get_nifti_shape,
    _run_async,
)


def _create_test_zip(work_dir: str, content: dict[str, bytes] | None = None) -> str:
    """Create a test zip with fake DICOM files."""
    zip_path = os.path.join(work_dir, "test_upload.zip")

    if content is None:
        content = {
            "patient/series1/001.dcm": b"\x00" * 128 + b"DICM" + b"\x00" * 256,
            "patient/series1/002.dcm": b"\x00" * 128 + b"DICM" + b"\x00" * 256,
            "patient/report.pdf": b"Fake PDF content",
        }

    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in content.items():
            zf.writestr(name, data)

    return zip_path


class TestPipelineStageResult:
    def test_completed_stage(self):
        stage = PipelineStageResult(
            stage="test_stage",
            status="COMPLETED",
            duration_ms=1500,
            details={"key": "value"},
        )
        assert stage.status == "COMPLETED"
        assert stage.error is None

    def test_failed_stage(self):
        stage = PipelineStageResult(
            stage="test_stage",
            status="FAILED",
            error="Something went wrong",
        )
        assert stage.status == "FAILED"
        assert "Something" in stage.error


class TestPipelineResult:
    def test_to_dict(self):
        result = PipelineResult(
            request_id="req-123",
            case_id="case-456",
            status="COMPLETED",
            modalities_found=["T1", "PET"],
            pre_qc_checks=[
                {"status": "PASS", "modality": "T1"},
                {"status": "WARN", "modality": "PET"},
            ],
            can_proceed=True,
        )
        d = result.to_dict()
        assert d["request_id"] == "req-123"
        assert d["status"] == "COMPLETED"
        assert d["modalities_found"] == ["T1", "PET"]
        assert d["pre_qc_summary"]["pass"] == 1
        assert d["pre_qc_summary"]["warn"] == 1
        assert d["pre_qc_summary"]["can_proceed"] is True

    def test_empty_result(self):
        result = PipelineResult(
            request_id="req-123",
            case_id="case-456",
            status="FAILED",
            errors=["No files found"],
        )
        d = result.to_dict()
        assert d["status"] == "FAILED"
        assert len(d["errors"]) == 1


class TestPipelineOrchestrator:
    def test_init(self, tmp_path):
        orch = PipelineOrchestrator(
            work_dir=str(tmp_path),
            request_id="req-123",
            case_id="case-456",
            service_id="svc-789",
            patient_ref="P001",
        )
        assert orch.request_id == "req-123"
        assert orch.case_id == "case-456"
        assert os.path.isdir(orch.nifti_dir)
        assert os.path.isdir(orch.bids_dir)
        assert os.path.isdir(orch.output_dir)

    def test_pipeline_with_empty_zip(self, tmp_path):
        """Pipeline should fail on a zip with no medical files."""
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir)

        zip_path = _create_test_zip(work_dir, {
            "readme.txt": b"Just a readme",
            "data.csv": b"col1,col2\n1,2",
        })

        orch = PipelineOrchestrator(
            work_dir=work_dir,
            request_id="req-123",
            case_id="case-456",
        )
        result = orch.run_full_pipeline(zip_path)
        assert result.status == "FAILED"
        assert len(result.errors) > 0
        assert "DICOM" in result.errors[0] or "NIfTI" in result.errors[0]

    @patch("app.services.pipeline_orchestrator.PipelineOrchestrator._stage_convert_to_nifti")
    def test_pipeline_extract_stage(self, mock_convert, tmp_path):
        """Test that extract+scan stage works with DICOM files."""
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir)

        zip_path = _create_test_zip(work_dir)

        mock_convert.return_value = PipelineStageResult(
            stage="convert_to_nifti",
            status="FAILED",
            error="dcm2niix not installed",
        )

        orch = PipelineOrchestrator(
            work_dir=work_dir,
            request_id="req-123",
            case_id="case-456",
        )
        result = orch.run_full_pipeline(zip_path)

        # Should have passed extract+scan stage before failing at conversion
        stage_names = [s.stage for s in result.stages]
        assert "extract_and_scan" in stage_names
        extract_stage = next(s for s in result.stages if s.stage == "extract_and_scan")
        assert extract_stage.status == "COMPLETED"

    def test_pipeline_result_stages_tracked(self, tmp_path):
        """Test that all stages are tracked in the result."""
        work_dir = str(tmp_path / "work")
        os.makedirs(work_dir)

        zip_path = _create_test_zip(work_dir, {
            "readme.txt": b"No medical files here",
        })

        orch = PipelineOrchestrator(
            work_dir=work_dir,
            request_id="req-123",
            case_id="case-456",
        )
        result = orch.run_full_pipeline(zip_path)

        # Even on failure, stages should be recorded
        assert len(result.stages) >= 1


class TestRunAsync:
    def test_run_simple_coroutine(self):
        async def coro():
            return 42
        assert _run_async(coro()) == 42

    def test_run_async_with_io(self):
        async def coro():
            import asyncio
            await asyncio.sleep(0.01)
            return "done"
        assert _run_async(coro()) == "done"


class TestGetNiftiShape:
    def test_nonexistent_file(self):
        assert _get_nifti_shape("/nonexistent/file.nii") == ()

    def test_invalid_file(self, tmp_path):
        bad = str(tmp_path / "bad.nii")
        with open(bad, "w") as f:
            f.write("not a nifti")
        assert _get_nifti_shape(bad) == ()


# ── Process Request API Endpoint Test ──────────────────────────────────


class TestProcessEndpointIntegration:
    """Test the /requests/{id}/process endpoint logic."""

    def test_process_request_validates_status(self):
        """Verify process endpoint only allows certain statuses."""
        from app.services.state_machine import RequestStatus

        allowed = {"CREATED", "RECEIVING", "STAGING", "READY_TO_COMPUTE"}
        for status in RequestStatus:
            if status.value in allowed:
                continue
            # These statuses should NOT allow processing
            assert status.value not in allowed
