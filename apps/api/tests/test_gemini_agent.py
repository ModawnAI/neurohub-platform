"""Phase 12 — Gemini AI Agent tests.

Tests use GEMINI_ENABLED=false by default (no real API calls).
Agent logic is tested via mock/disabled mode.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agent import AIAgentRun
from app.models.request import Case, Request
from app.models.run import Run
from app.services.gemini_agent import AgentResponse, GeminiAgent, gemini_agent, track_agent_run
from tests.conftest import DEFAULT_INSTITUTION_ID, DEFAULT_PIPELINE_ID, DEFAULT_SERVICE_ID

pytestmark = pytest.mark.anyio


# --- Helpers ---


async def _create_run(db: AsyncSession) -> Run:
    req = Request(
        institution_id=DEFAULT_INSTITUTION_ID,
        service_id=DEFAULT_SERVICE_ID,
        pipeline_id=DEFAULT_PIPELINE_ID,
        status="COMPUTING",
    )
    db.add(req)
    await db.flush()

    case = Case(
        request_id=req.id,
        institution_id=DEFAULT_INSTITUTION_ID,
        patient_ref="PAT-GEMINI-001",
    )
    db.add(case)
    await db.flush()

    run = Run(
        institution_id=DEFAULT_INSTITUTION_ID,
        request_id=req.id,
        case_id=case.id,
        status="RUNNING",
    )
    db.add(run)
    await db.flush()
    return run


# --- Tests ---


async def test_gemini_agent_disabled_skips():
    """GEMINI_ENABLED=False → no API calls, returns skipped."""
    agent = GeminiAgent()
    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = False
        mock_settings.gemini_model = "gemini-3-flash-preview"
        result = await agent.review_pre_qc([{"status": "PASS"}], "MRI")

    assert result.success is True
    assert result.output.get("skipped") is True


async def test_gemini_agent_pre_qc_review():
    """Pre-QC review returns structured summary when enabled."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "QC 결과 양호합니다. 분석 진행을 권고합니다."
    mock_response.usage_metadata = MagicMock(total_token_count=150)
    mock_client.models.generate_content.return_value = mock_response
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        result = await agent.review_pre_qc([{"status": "PASS", "check_type": "VOXEL_SIZE"}], "MRI")

    assert result.success is True
    assert result.agent_type == "PRE_QC_REVIEW"
    assert "text" in result.output
    assert result.tokens_used == 150


async def test_gemini_agent_report_narrative_korean():
    """Report narrative output is Korean clinical text."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "검사 소견: 전두엽 영역에서 대사 저하가 관찰됩니다."
    mock_response.usage_metadata = MagicMock(total_token_count=200)
    mock_client.models.generate_content.return_value = mock_response
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        result = await agent.generate_report_narrative(
            fusion_result={"included_modules": ["FDG_PET"], "confidence_score": 85.0, "concordance_score": 0.9, "results": {}},
            service_config={"service_name": "Dementia Diagnosis", "clinical_purpose": "치매 진단"},
        )

    assert result.success is True
    assert "검사 소견" in result.output["text"]


async def test_gemini_agent_clinical_summary():
    """Clinical summary synthesizes multi-technique results."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "종합 분석: 3개 기법 모두 일치하는 소견을 보입니다."
    mock_response.usage_metadata = MagicMock(total_token_count=180)
    mock_client.models.generate_content.return_value = mock_response
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        result = await agent.summarize_technique_outputs([
            {"module": "FDG_PET", "qc_score": 90, "features": {"score": 0.8}},
            {"module": "Cortical_Thickness", "qc_score": 85, "features": {"score": 0.7}},
        ])

    assert result.success is True
    assert result.agent_type == "CLINICAL_SUMMARY"


async def test_gemini_agent_qc_anomaly_detection():
    """QC anomaly detection flags outliers correctly."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"anomaly_detected": true, "anomaly_flags": ["low_qc"], "severity": "medium"}'
    mock_response.usage_metadata = MagicMock(total_token_count=100)
    mock_client.models.generate_content.return_value = mock_response
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        result = await agent.detect_qc_anomalies(
            {"module": "EEG_Spectrum", "qc_score": 35, "features": {}},
            {"mean_qc": 80, "std_qc": 10},
        )

    assert result.success is True
    assert result.agent_type == "QC_ANOMALY"


async def test_gemini_agent_timeout_handled():
    """Slow response → graceful fallback, no crash."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("timed out")
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        result = await agent.review_pre_qc([], "MRI")

    assert result.success is False
    assert "timed out" in result.error


async def test_gemini_agent_api_error_non_blocking():
    """API error → logs warning, returns failure gracefully."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("API quota exceeded")
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        result = await agent.generate_report_narrative({}, {})

    assert result.success is False
    assert "quota" in result.error.lower()


async def test_ai_agent_run_tracked_in_db(db: AsyncSession):
    """AIAgentRun row created with tokens/latency."""
    run = await _create_run(db)

    response = AgentResponse(
        agent_type="PRE_QC_REVIEW",
        model_id="gemini-3-flash-preview",
        output={"text": "All checks passed."},
        tokens_used=150,
        latency_ms=320,
        success=True,
    )

    agent_run = await track_agent_run(db, run.id, response)

    assert agent_run.id is not None
    assert agent_run.agent_type == "PRE_QC_REVIEW"
    assert agent_run.tokens_used == 150
    assert agent_run.latency_ms == 320
    assert agent_run.status == "COMPLETED"

    # Verify in DB
    loaded = (await db.execute(
        select(AIAgentRun).where(AIAgentRun.id == agent_run.id)
    )).scalar_one()
    assert loaded.model_id == "gemini-3-flash-preview"


async def test_gemini_agent_prompt_includes_context():
    """Correct patient/service context in prompt."""
    agent = GeminiAgent()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "분석 결과"
    mock_response.usage_metadata = MagicMock(total_token_count=50)
    mock_client.models.generate_content.return_value = mock_response
    agent._client = mock_client

    with patch("app.services.gemini_agent.settings") as mock_settings:
        mock_settings.gemini_enabled = True
        mock_settings.gemini_model = "gemini-3-flash-preview"
        mock_settings.gemini_max_tokens = 4096
        await agent.generate_report_narrative(
            fusion_result={"included_modules": ["FDG_PET"], "confidence_score": 90, "concordance_score": 1.0, "results": {"score": 0.85}},
            service_config={"service_name": "Epilepsy Lesion Analysis", "clinical_purpose": "간질 병변 분석"},
        )

    # Verify the prompt contained service info
    call_args = mock_client.models.generate_content.call_args
    prompt = call_args.kwargs.get("contents", call_args[1].get("contents", "")) if call_args.kwargs else call_args[1]["contents"]
    assert "Epilepsy Lesion Analysis" in prompt or "간질 병변 분석" in prompt


async def test_gemini_agent_failed_run_tracked(db: AsyncSession):
    """Failed agent run is tracked with error detail."""
    run = await _create_run(db)

    response = AgentResponse(
        agent_type="REPORT_NARRATIVE",
        model_id="gemini-3-flash-preview",
        output={},
        tokens_used=0,
        latency_ms=50,
        success=False,
        error="Connection refused",
    )

    agent_run = await track_agent_run(db, run.id, response)
    assert agent_run.status == "FAILED"
    assert agent_run.error_detail == "Connection refused"
