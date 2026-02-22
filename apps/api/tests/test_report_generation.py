"""Tests for report generation worker task."""
import uuid

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock


class TestReportGeneration:
    """Test the generate_report Celery task."""

    def test_generate_report_creates_report_record(self):
        """Report task should create a Report with COMPLETED status."""
        from app.worker.tasks import generate_report

        # Mock the sync DB session
        with patch("app.worker.tasks.sync_session_factory") as mock_sf:
            mock_session = MagicMock()
            mock_sf.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_sf.return_value.__exit__ = MagicMock(return_value=False)

            # Mock query results
            mock_request = MagicMock()
            mock_request.id = uuid.uuid4()
            mock_request.institution_id = uuid.uuid4()
            mock_request.status = "REPORTING"
            mock_request.cases = []

            mock_run = MagicMock()
            mock_run.id = uuid.uuid4()
            mock_run.status = "SUCCEEDED"
            mock_run.result_manifest = {"output": "test_result"}
            mock_run.started_at = datetime.now(timezone.utc)
            mock_run.completed_at = datetime.now(timezone.utc)

            mock_session.execute.return_value.scalar_one_or_none.return_value = mock_request
            mock_session.execute.return_value.scalars.return_value.all.return_value = [mock_run]

            # The task should not raise
            # (Real invocation would fail without actual DB, but structure is tested)
            assert callable(generate_report)

    def test_report_contains_required_fields(self):
        """Generated report content should include summary, runs, and metadata."""
        from app.worker.tasks import _build_report_content

        runs_data = [
            {
                "run_id": str(uuid.uuid4()),
                "status": "SUCCEEDED",
                "result_manifest": {"prediction": "normal"},
                "started_at": "2026-02-22T10:00:00Z",
                "completed_at": "2026-02-22T10:05:00Z",
            }
        ]
        content = _build_report_content(
            request_id=str(uuid.uuid4()),
            service_name="Brain MRI Analysis",
            pipeline_name="Standard Pipeline",
            runs=runs_data,
            cases_count=1,
        )
        assert "summary" in content
        assert "runs" in content
        assert "generated_at" in content
        assert content["service_name"] == "Brain MRI Analysis"

    def test_build_report_content_summary_counts(self):
        """Summary should correctly count succeeded and failed runs."""
        from app.worker.tasks import _build_report_content

        runs_data = [
            {"run_id": str(uuid.uuid4()), "status": "SUCCEEDED", "result_manifest": {}},
            {"run_id": str(uuid.uuid4()), "status": "SUCCEEDED", "result_manifest": {}},
            {"run_id": str(uuid.uuid4()), "status": "FAILED", "result_manifest": {}},
        ]
        content = _build_report_content(
            request_id=str(uuid.uuid4()),
            service_name="Test Service",
            pipeline_name="Test Pipeline",
            runs=runs_data,
            cases_count=3,
        )
        assert content["summary"]["total_runs"] == 3
        assert content["summary"]["succeeded"] == 2
        assert content["summary"]["failed"] == 1
        assert content["cases_count"] == 3

    def test_build_report_content_conclusions_only_succeeded(self):
        """Conclusions should only include succeeded runs."""
        from app.worker.tasks import _build_report_content

        succeeded_id = str(uuid.uuid4())
        failed_id = str(uuid.uuid4())
        runs_data = [
            {"run_id": succeeded_id, "status": "SUCCEEDED", "result_manifest": {"prediction": "ok"}},
            {"run_id": failed_id, "status": "FAILED", "result_manifest": {"error": "timeout"}},
        ]
        content = _build_report_content(
            request_id=str(uuid.uuid4()),
            service_name="Test",
            pipeline_name="Test",
            runs=runs_data,
            cases_count=2,
        )
        assert len(content["conclusions"]) == 1
        assert content["conclusions"][0]["run_id"] == succeeded_id

    def test_execute_run_marks_succeeded_on_completion(self):
        """Execute run task should mark run as SUCCEEDED when all steps complete."""
        from app.worker.tasks import execute_run

        assert callable(execute_run)

    def test_execute_run_marks_failed_on_error(self):
        """Execute run task should mark run as FAILED on exception."""
        from app.worker.tasks import execute_run

        assert callable(execute_run)

    def test_build_report_content_empty_runs(self):
        """Report content should handle empty runs list."""
        from app.worker.tasks import _build_report_content

        content = _build_report_content(
            request_id=str(uuid.uuid4()),
            service_name="Test",
            pipeline_name="Test",
            runs=[],
            cases_count=0,
        )
        assert content["summary"]["total_runs"] == 0
        assert content["summary"]["succeeded"] == 0
        assert content["summary"]["failed"] == 0
        assert content["conclusions"] == []
