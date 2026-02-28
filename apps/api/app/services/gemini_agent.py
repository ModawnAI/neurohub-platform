"""Gemini AI Agent — AI co-pilot for clinical analysis pipeline.

Uses Google Gemini 3 Flash Preview for:
  - Pre-QC review interpretation
  - Report narrative generation (Korean)
  - Clinical summary synthesis
  - QC anomaly detection

All agent calls are optional (toggle via GEMINI_ENABLED) and non-blocking.
Pipeline continues even if Gemini fails.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_agent import AIAgentRun

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Structured response from the Gemini agent."""

    agent_type: str
    model_id: str
    output: dict
    tokens_used: int = 0
    latency_ms: int = 0
    success: bool = True
    error: str | None = None


class GeminiAgent:
    """Gemini 3 Flash Preview wrapper for clinical AI assistance."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-init the Gemini client."""
        if self._client is not None:
            return self._client

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        try:
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
            return self._client
        except ImportError:
            raise RuntimeError("google-genai package not installed")

    async def review_pre_qc(
        self,
        pre_qc_results: list[dict],
        modality: str,
    ) -> AgentResponse:
        """Pre-QC Interpretation: Analyzes QC results and provides
        human-readable summary of data quality issues and recommended actions.
        """
        prompt = f"""당신은 의료 영상 품질 관리 전문가입니다.
다음 {modality} 영상의 사전 QC 검사 결과를 분석하고 한국어로 요약해주세요.

QC 결과:
{_format_dict_list(pre_qc_results)}

다음을 포함해주세요:
1. 데이터 품질 종합 평가
2. 발견된 문제점 및 임상적 영향
3. 분석 진행 권고 사항
4. 데이터 재촬영/재업로드 필요 여부"""

        return await self._call("PRE_QC_REVIEW", prompt, {"pre_qc_results": pre_qc_results, "modality": modality})

    async def generate_report_narrative(
        self,
        fusion_result: dict,
        service_config: dict,
        patient_demographics: dict | None = None,
    ) -> AgentResponse:
        """Report Narrative Generation: Converts raw fusion engine output
        into a structured Korean clinical narrative for the final PDF report.
        """
        svc_name = service_config.get('service_name', '알 수 없음')
        svc_purpose = service_config.get('clinical_purpose', '')
        incl = fusion_result.get('included_modules', [])
        excl = fusion_result.get('excluded_modules', [])
        conf = fusion_result.get('confidence_score', 0)
        conc = fusion_result.get('concordance_score', 0)
        results_data = fusion_result.get('results', {})
        prompt = f"""당신은 신경영상 분석 결과를 임상 보고서로 작성하는 전문가입니다.
다음 융합 분석 결과를 한국어 임상 보고서 형식으로 작성해주세요.

서비스: {svc_name}
분석 유형: {svc_purpose}

융합 분석 결과:
- 포함된 기법: {incl}
- 제외된 기법: {excl}
- 신뢰도: {conf:.1f}%
- 일치도: {conc:.2f}
- 분석 수치: {results_data}

다음 구조로 작성해주세요:
1. 검사 소견 (Findings)
2. 분석 해석 (Interpretation)
3. 임상적 의의 (Clinical Significance)
4. 권고 사항 (Recommendations)"""

        return await self._call("REPORT_NARRATIVE", prompt, {
            "fusion_result": fusion_result,
            "service_config": service_config,
        })

    async def summarize_technique_outputs(
        self,
        technique_outputs: list[dict],
    ) -> AgentResponse:
        """Clinical Summary: Synthesizes individual technique results into
        a concise clinical interpretation before fusion.
        """
        prompt = f"""당신은 다중 모달리티 뇌영상 분석 결과를 종합하는 전문가입니다.
다음 개별 분석 기법 결과들을 종합하여 한국어로 임상 요약을 작성해주세요.

개별 기법 결과:
{_format_dict_list(technique_outputs)}

다음을 포함해주세요:
1. 주요 발견사항 (각 기법별)
2. 기법 간 일치/불일치 소견
3. 교차 모달리티 관찰
4. 종합 임상 해석"""

        return await self._call("CLINICAL_SUMMARY", prompt, {"technique_outputs": technique_outputs})

    async def detect_qc_anomalies(
        self,
        technique_output: dict,
        historical_stats: dict | None = None,
    ) -> AgentResponse:
        """QC Anomaly Detection: Compares technique output against historical
        distributions to flag statistical outliers.
        """
        hist_info = ""
        if historical_stats:
            hist_info = f"\n과거 통계:\n평균 QC: {historical_stats.get('mean_qc', 'N/A')}, 표준편차: {historical_stats.get('std_qc', 'N/A')}"

        mod_name = technique_output.get('module', '알 수 없음')
        qc = technique_output.get('qc_score', 'N/A')
        feats = technique_output.get('features', {})
        prompt = f"""당신은 의료 영상 분석 품질 관리 전문가입니다.
다음 분석 결과에서 비정상적인 패턴이나 이상치를 감지해주세요.

기법: {mod_name}
QC 점수: {qc}
특성값: {feats}
{hist_info}

다음을 JSON 형식으로 응답해주세요:
- anomaly_detected: true/false
- anomaly_flags: [이상치 목록]
- explanation: 설명
- severity: low/medium/high"""

        return await self._call("QC_ANOMALY", prompt, {
            "technique_output": technique_output,
            "historical_stats": historical_stats,
        })

    async def _call(
        self,
        agent_type: str,
        prompt: str,
        input_data: dict,
    ) -> AgentResponse:
        """Internal: Execute a Gemini API call with error handling."""
        if not settings.gemini_enabled:
            return AgentResponse(
                agent_type=agent_type,
                model_id=settings.gemini_model,
                output={"skipped": True, "reason": "GEMINI_ENABLED=false"},
                success=True,
            )

        start = time.monotonic()
        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config={
                    "max_output_tokens": settings.gemini_max_tokens,
                    "temperature": 0.3,
                },
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)
            text = response.text or ""
            tokens = getattr(response, "usage_metadata", None)
            total_tokens = getattr(tokens, "total_token_count", 0) if tokens else 0

            return AgentResponse(
                agent_type=agent_type,
                model_id=settings.gemini_model,
                output={"text": text},
                tokens_used=total_tokens,
                latency_ms=elapsed_ms,
                success=True,
            )

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.warning("Gemini agent %s failed: %s", agent_type, e)
            return AgentResponse(
                agent_type=agent_type,
                model_id=settings.gemini_model,
                output={},
                latency_ms=elapsed_ms,
                success=False,
                error=str(e),
            )


async def track_agent_run(
    db: AsyncSession,
    run_id: uuid.UUID,
    response: AgentResponse,
) -> AIAgentRun:
    """Persist an agent invocation to the database."""
    agent_run = AIAgentRun(
        run_id=run_id,
        agent_type=response.agent_type,
        model_id=response.model_id,
        output_data=response.output,
        tokens_used=response.tokens_used,
        latency_ms=response.latency_ms,
        status="COMPLETED" if response.success else "FAILED",
        error_detail=response.error,
    )
    db.add(agent_run)
    await db.flush()
    return agent_run


def _format_dict_list(items: list[dict]) -> str:
    """Format a list of dicts for prompt readability."""
    lines = []
    for i, item in enumerate(items):
        lines.append(f"  [{i+1}] {item}")
    return "\n".join(lines) if lines else "  (없음)"


# Module-level singleton
gemini_agent = GeminiAgent()
