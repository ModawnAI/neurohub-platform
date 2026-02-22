"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle, XCircle, ArrowsClockwise, Check, DownloadSimple, File } from "phosphor-react";
import {
  getReviewDetail,
  submitQCDecision,
  submitReportReview,
  listCaseFiles,
  getDownloadUrl,
  type CaseFileRead,
} from "@/lib/api";
import { useZodForm } from "@/lib/use-zod-form";
import { qcDecisionSchema, reportReviewSchema, type QCDecisionValues, type ReportReviewValues } from "@/lib/schemas";

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function CaseFileList({ requestId, caseItem }: { requestId: string; caseItem: { id: string; patient_ref: string; status: string } }) {
  const [expanded, setExpanded] = useState(false);

  const { data: filesData, isLoading } = useQuery({
    queryKey: ["case-files", requestId, caseItem.id],
    queryFn: () => listCaseFiles(requestId, caseItem.id),
    enabled: expanded,
  });

  const handleDownload = async (file: CaseFileRead) => {
    try {
      const { download_url } = await getDownloadUrl(requestId, caseItem.id, file.id);
      window.open(download_url, "_blank");
    } catch {
      alert("다운로드 URL을 가져올 수 없습니다.");
    }
  };

  const files = filesData?.items ?? [];

  return (
    <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          background: "none", border: "none", cursor: "pointer", width: "100%",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "8px 0", fontSize: 14,
        }}
      >
        <span>
          <strong>#{caseItem.patient_ref}</strong>{" "}
          <span className="muted-text" style={{ fontSize: 12 }}>({caseItem.status})</span>
        </span>
        <span style={{ fontSize: 12, color: "var(--primary)" }}>{expanded ? "접기" : "파일 보기"}</span>
      </button>

      {expanded && (
        <div style={{ paddingLeft: 16, marginTop: 8 }}>
          {isLoading ? (
            <span className="spinner" />
          ) : files.length === 0 ? (
            <p className="muted-text" style={{ fontSize: 13 }}>파일 없음</p>
          ) : (
            <div className="stack-sm">
              {files.map((file) => (
                <div key={file.id} className="file-info-card">
                  <div className="file-info-card-icon"><File size={20} /></div>
                  <div className="file-info-card-body">
                    <p className="file-info-card-name">{file.filename}</p>
                    <p className="file-info-card-meta">{file.slot} &middot; {formatBytes(file.size_bytes)}</p>
                  </div>
                  {file.status === "COMPLETED" && (
                    <button className="btn btn-sm btn-secondary" onClick={() => handleDownload(file)} title="다운로드">
                      <DownloadSimple size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ExpertReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const qcForm = useZodForm<QCDecisionValues>(qcDecisionSchema, {
    decision: "APPROVE",
    comments: "",
  });

  const reportForm = useZodForm<ReportReviewValues>(reportReviewSchema, {
    decision: "APPROVE",
    comments: "",
  });

  const { data, isLoading } = useQuery({
    queryKey: ["review-detail", id],
    queryFn: () => getReviewDetail(id),
    enabled: !!id,
  });

  const qcMut = useMutation({
    mutationFn: () => {
      const validated = qcForm.validate();
      if (!validated) throw new Error("입력값을 확인하세요");
      return submitQCDecision(id, {
        decision: validated.decision,
        qc_score: validated.qc_score,
        comments: validated.comments || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-detail", id] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      router.push("/expert/reviews");
    },
  });

  const reportMut = useMutation({
    mutationFn: () => {
      const validated = reportForm.validate();
      if (!validated) throw new Error("입력값을 확인하세요");
      return submitReportReview(id, {
        decision: validated.decision,
        comments: validated.comments || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-detail", id] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      router.push("/expert/reviews");
    },
  });

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (!data) return <div className="empty-state"><p className="empty-state-text">리뷰를 찾을 수 없습니다.</p></div>;

  const { request, cases, runs, reports, qc_decisions } = data;
  const isQC = request.status === "QC";
  const isExpertReview = request.status === "EXPERT_REVIEW";
  const serviceSnapshot = (request as any).service_snapshot;

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/expert/reviews")}>
        <ArrowLeft size={16} /> 리뷰 대기열로 돌아가기
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">{serviceSnapshot?.display_name || "AI 분석 리뷰"}</h1>
          <p className="page-subtitle">요청 #{id.slice(0, 8)}</p>
        </div>
        <span className={`status-chip status-${request.status.toLowerCase()}`}>
          {isQC ? "품질 검증" : "전문가 검토"}
        </span>
      </div>

      {/* Request Info */}
      <div className="panel">
        <h3 className="panel-title-mb">요청 정보</h3>
        <div className="grid-3">
          <div>
            <p className="detail-label">케이스 수</p>
            <p className="detail-value">{request.case_count}건</p>
          </div>
          <div>
            <p className="detail-label">우선순위</p>
            <p className="detail-value">{request.priority}</p>
          </div>
          <div>
            <p className="detail-label">생성일</p>
            <p className="detail-value">{new Date(request.created_at).toLocaleDateString("ko-KR")}</p>
          </div>
        </div>
      </div>

      {/* Cases with File Downloads */}
      {cases.length > 0 && (
        <div className="panel">
          <h3 className="panel-title-mb">케이스 및 파일</h3>
          <div className="stack-sm">
            {cases.map((c: any, i: number) => (
              <CaseFileList
                key={c.id || i}
                requestId={id}
                caseItem={{ id: c.id, patient_ref: c.patient_ref, status: c.status }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Run Results */}
      {runs.length > 0 && (
        <div className="panel">
          <h3 className="panel-title-mb">실행 결과</h3>
          <div className="stack-sm">
            {runs.map((run: any, i: number) => (
              <div key={run.id || i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 14 }}>
                <span>Run #{i + 1}</span>
                <span className={`status-chip status-${(run.status || "").toLowerCase()}`}>{run.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Reports */}
      {reports.length > 0 && (
        <div className="panel">
          <h3 className="panel-title-mb">보고서</h3>
          <div className="stack-sm">
            {reports.map((report: any, i: number) => (
              <div key={report.id || i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 14 }}>
                <span>보고서 #{i + 1} — {report.report_type || "일반"}</span>
                <span className={`status-chip status-${(report.status || "").toLowerCase()}`}>{report.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Previous QC Decisions */}
      {qc_decisions.length > 0 && (
        <div className="panel">
          <h3 className="panel-title-mb">이전 결정 이력</h3>
          <div className="stack-md">
            {qc_decisions.map((qc: any, i: number) => (
              <div key={qc.id || i} className="activity-item" style={{ borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600, margin: 0 }}>
                    {qc.decision === "APPROVE" ? "승인" : qc.decision === "REJECT" ? "반려" : "재분석 요청"}
                  </p>
                  {qc.comments && <p className="muted-text" style={{ fontSize: 12, margin: "4px 0 0" }}>{qc.comments}</p>}
                  {qc.created_at && <p className="muted-text" style={{ fontSize: 11, margin: "2px 0 0" }}>{new Date(qc.created_at).toLocaleString("ko-KR")}</p>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* QC Decision Panel */}
      {isQC && (
        <div className="panel">
          <h3 className="panel-title-mb">QC 결정</h3>
          <div className="review-action-grid">
            <button
              className={`review-action-card ${qcForm.values.decision === "APPROVE" ? "approve" : ""}`}
              onClick={() => qcForm.setField("decision", "APPROVE")}
            >
              <div className="review-action-icon" style={{ color: "var(--success)" }}><CheckCircle size={28} /></div>
              <div className="review-action-label">승인</div>
            </button>
            <button
              className={`review-action-card ${qcForm.values.decision === "REJECT" ? "reject" : ""}`}
              onClick={() => qcForm.setField("decision", "REJECT")}
            >
              <div className="review-action-icon" style={{ color: "var(--danger)" }}><XCircle size={28} /></div>
              <div className="review-action-label">반려</div>
            </button>
            <button
              className={`review-action-card ${qcForm.values.decision === "RERUN" ? "rerun" : ""}`}
              onClick={() => qcForm.setField("decision", "RERUN")}
            >
              <div className="review-action-icon" style={{ color: "var(--warning)" }}><ArrowsClockwise size={28} /></div>
              <div className="review-action-label">재분석 요청</div>
            </button>
          </div>

          <div className="stack-md" style={{ marginTop: 16 }}>
            <label className="field">
              코멘트
              <textarea
                className="textarea"
                value={qcForm.values.comments ?? ""}
                onChange={(e) => qcForm.setField("comments", e.target.value)}
                placeholder="리뷰 의견을 입력하세요"
                rows={3}
              />
              {qcForm.errors.comments && <span className="error-text">{qcForm.errors.comments}</span>}
            </label>
            {qcMut.isError && <p className="error-text">{(qcMut.error as Error).message}</p>}
            <button className="btn btn-primary" onClick={() => qcMut.mutate()} disabled={qcMut.isPending}>
              {qcMut.isPending ? <span className="spinner" /> : <>결정 제출 <Check size={16} /></>}
            </button>
          </div>
        </div>
      )}

      {/* Report Review Panel */}
      {isExpertReview && (
        <div className="panel">
          <h3 className="panel-title-mb">보고서 검토</h3>
          <div className="review-action-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
            <button
              className={`review-action-card ${reportForm.values.decision === "APPROVE" ? "approve" : ""}`}
              onClick={() => reportForm.setField("decision", "APPROVE")}
            >
              <div className="review-action-icon" style={{ color: "var(--success)" }}><CheckCircle size={28} /></div>
              <div className="review-action-label">승인</div>
            </button>
            <button
              className={`review-action-card ${reportForm.values.decision === "REVISION_NEEDED" ? "rerun" : ""}`}
              onClick={() => reportForm.setField("decision", "REVISION_NEEDED")}
            >
              <div className="review-action-icon" style={{ color: "var(--warning)" }}><ArrowsClockwise size={28} /></div>
              <div className="review-action-label">수정 요청</div>
            </button>
          </div>

          <div className="stack-md" style={{ marginTop: 16 }}>
            <label className="field">
              코멘트
              <textarea
                className="textarea"
                value={reportForm.values.comments ?? ""}
                onChange={(e) => reportForm.setField("comments", e.target.value)}
                placeholder="검토 의견을 입력하세요"
                rows={3}
              />
              {reportForm.errors.comments && <span className="error-text">{reportForm.errors.comments}</span>}
            </label>
            {reportMut.isError && <p className="error-text">{(reportMut.error as Error).message}</p>}
            <button className="btn btn-primary" onClick={() => reportMut.mutate()} disabled={reportMut.isPending}>
              {reportMut.isPending ? <span className="spinner" /> : <>결정 제출 <Check size={16} /></>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
