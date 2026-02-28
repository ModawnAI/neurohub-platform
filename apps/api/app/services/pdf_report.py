"""PDF report generation service using WeasyPrint.

Generates professional medical PDF reports with Korean-first layout.
"""

import logging
from datetime import datetime, timezone
from io import BytesIO

logger = logging.getLogger("neurohub.pdf_report")

# HTML template for medical reports (Korean-first)
_REPORT_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<style>
@page {{
    size: A4;
    margin: 2cm;
    @top-center {{ content: "NeuroHub 분석 보고서"; font-size: 9pt; color: #666; }}
    @bottom-center {{ content: "Page " counter(page) " / " counter(pages); font-size: 8pt; color: #999; }}
}}
body {{
    font-family: "Noto Sans KR", "Malgun Gothic", sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #222;
}}
h1 {{ font-size: 18pt; color: #1a3a5c; border-bottom: 2px solid #1a3a5c; padding-bottom: 6px; }}
h2 {{ font-size: 13pt; color: #2c5f8a; margin-top: 1.5em; border-left: 4px solid #2c5f8a; padding-left: 8px; }}
h3 {{ font-size: 11pt; color: #444; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; font-size: 9pt; }}
th {{ background: #f0f4f8; font-weight: 600; }}
.info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 10px 0; }}
.info-item {{ display: flex; }}
.info-label {{ font-weight: 600; min-width: 100px; color: #555; }}
.badge {{
    display: inline-block; padding: 2px 8px; border-radius: 4px;
    font-size: 8pt; font-weight: 600; color: #fff;
}}
.badge-success {{ background: #22a06b; }}
.badge-fail {{ background: #cf222e; }}
.badge-review {{ background: #d97706; }}
.summary-box {{
    background: #f7f9fc; border: 1px solid #d0d7de; border-radius: 6px;
    padding: 12px 16px; margin: 12px 0;
}}
.footer {{ margin-top: 2em; padding-top: 1em; border-top: 1px solid #ddd; font-size: 8pt; color: #888; }}
</style>
</head>
<body>
<h1>{title}</h1>

<div class="info-grid">
    <div class="info-item"><span class="info-label">요청 ID:</span> <span>{request_id_short}</span></div>
    <div class="info-item"><span class="info-label">생성일시:</span> <span>{generated_at}</span></div>
    <div class="info-item"><span class="info-label">서비스:</span> <span>{service_name}</span></div>
    <div class="info-item"><span class="info-label">상태:</span> <span class="badge {status_class}">{status}</span></div>
</div>

{patient_section}

<h2>분석 결과 요약</h2>
<div class="summary-box">{summary}</div>

{runs_section}

{qc_section}

{review_section}

<div class="footer">
    본 보고서는 NeuroHub AI 분석 플랫폼에 의해 자동 생성되었습니다.<br>
    생성 시각: {generated_at_full} (UTC)
</div>
</body>
</html>
"""


def _status_badge_class(status: str) -> str:
    if status in ("FINAL", "SUCCEEDED", "APPROVE"):
        return "badge-success"
    if status in ("FAILED", "REJECT"):
        return "badge-fail"
    return "badge-review"


def _build_patient_section(cases: list[dict]) -> str:
    if not cases:
        return ""
    rows = []
    for i, c in enumerate(cases, 1):
        demo = c.get("demographics") or {}
        rows.append(
            f"<tr><td>{i}</td>"
            f"<td>{c.get('patient_ref', '-')}</td>"
            f"<td>{demo.get('age', '-')}</td>"
            f"<td>{demo.get('sex', '-')}</td>"
            f"<td>{c.get('status', '-')}</td></tr>"
        )
    return (
        "<h2>환자 정보</h2>"
        "<table><tr><th>#</th><th>환자 참조</th><th>나이</th><th>성별</th><th>상태</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _build_runs_section(runs: list[dict]) -> str:
    if not runs:
        return ""
    rows = []
    for r in runs:
        badge = _status_badge_class(r.get("status", ""))
        rows.append(
            f"<tr><td>{r.get('run_id', '-')[:8]}...</td>"
            f"<td><span class='badge {badge}'>{r.get('status', '-')}</span></td>"
            f"<td>{r.get('started_at', '-')}</td>"
            f"<td>{r.get('completed_at', '-')}</td></tr>"
        )
    return (
        "<h2>분석 실행 내역</h2>"
        "<table><tr><th>Run ID</th><th>상태</th><th>시작</th><th>완료</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _build_qc_section(qc_decisions: list[dict]) -> str:
    if not qc_decisions:
        return ""
    rows = []
    for q in qc_decisions:
        badge = _status_badge_class(q.get("decision", ""))
        score = q.get("qc_score")
        score_str = f"{score:.1f}" if score is not None else "-"
        rows.append(
            f"<tr><td><span class='badge {badge}'>{q.get('decision', '-')}</span></td>"
            f"<td>{score_str}</td>"
            f"<td>{q.get('comments', '-')}</td>"
            f"<td>{q.get('created_at', '-')}</td></tr>"
        )
    return (
        "<h2>QC 검증 결과</h2>"
        "<table><tr><th>결정</th><th>점수</th><th>코멘트</th><th>일시</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def _build_review_section(reviews: list[dict]) -> str:
    if not reviews:
        return ""
    rows = []
    for rv in reviews:
        badge = _status_badge_class(rv.get("decision", ""))
        rows.append(
            f"<tr><td><span class='badge {badge}'>{rv.get('decision', '-')}</span></td>"
            f"<td>{rv.get('severity', '-')}</td>"
            f"<td>{rv.get('category', '-')}</td>"
            f"<td>{rv.get('comments', '-')}</td>"
            f"<td>{rv.get('created_at', '-')}</td></tr>"
        )
    return (
        "<h2>전문가 검토 내역</h2>"
        "<table><tr><th>결정</th><th>심각도</th><th>분류</th><th>코멘트</th><th>일시</th></tr>"
        + "".join(rows)
        + "</table>"
    )


def generate_report_html(
    *,
    title: str,
    request_id: str,
    service_name: str,
    status: str,
    summary: str,
    cases: list[dict] | None = None,
    runs: list[dict] | None = None,
    qc_decisions: list[dict] | None = None,
    reviews: list[dict] | None = None,
    generated_at: datetime | None = None,
) -> str:
    """Build the HTML content for a medical report."""
    now = generated_at or datetime.now(timezone.utc)
    return _REPORT_TEMPLATE.format(
        title=title,
        request_id_short=request_id[:8] + "..." if len(request_id) > 8 else request_id,
        generated_at=now.strftime("%Y-%m-%d %H:%M"),
        generated_at_full=now.isoformat(),
        service_name=service_name,
        status=status,
        status_class=_status_badge_class(status),
        summary=summary,
        patient_section=_build_patient_section(cases or []),
        runs_section=_build_runs_section(runs or []),
        qc_section=_build_qc_section(qc_decisions or []),
        review_section=_build_review_section(reviews or []),
    )


def render_pdf(html: str) -> bytes:
    """Render HTML to PDF bytes using WeasyPrint."""
    try:
        from weasyprint import HTML

        buf = BytesIO()
        HTML(string=html).write_pdf(buf)
        return buf.getvalue()
    except ImportError:
        logger.warning("WeasyPrint not installed, returning empty PDF placeholder")
        # Return a minimal valid PDF as fallback
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
            b"0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
        )


def upload_pdf_to_storage(
    pdf_bytes: bytes,
    *,
    institution_id: str,
    request_id: str,
    report_id: str,
) -> str:
    """Upload PDF to storage. Returns the storage path."""
    from app.config import settings
    from app.services.storage import put_object_sync

    bucket = settings.storage_bucket_reports
    path = f"institutions/{institution_id}/requests/{request_id}/reports/{report_id}.pdf"

    try:
        put_object_sync(bucket, path, pdf_bytes, content_type="application/pdf")
        logger.info("PDF uploaded to %s/%s", bucket, path)
    except Exception as e:
        logger.error("Failed to upload PDF: %s", e)
        raise

    return path
