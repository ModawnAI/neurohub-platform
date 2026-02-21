"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, CheckCircle, XCircle, ArrowsClockwise, Check } from "phosphor-react";
import { getReviewDetail, submitQCDecision, submitReportReview } from "@/lib/api";

export default function ExpertReviewDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [decision, setDecision] = useState<string | null>(null);
  const [comments, setComments] = useState("");
  const [qcScore, setQcScore] = useState<number | undefined>(undefined);

  const { data, isLoading } = useQuery({
    queryKey: ["review-detail", id],
    queryFn: () => getReviewDetail(id),
    enabled: !!id,
  });

  const qcMut = useMutation({
    mutationFn: () => submitQCDecision(id, { decision: decision!, qc_score: qcScore, comments: comments || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review-detail", id] });
      queryClient.invalidateQueries({ queryKey: ["review-queue"] });
      router.push("/expert/reviews");
    },
  });

  const reportMut = useMutation({
    mutationFn: () => submitReportReview(id, { decision: decision!, comments: comments || undefined }),
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
        <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 12px" }}>요청 정보</h3>
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

      {/* Cases */}
      {cases.length > 0 && (
        <div className="panel">
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 12px" }}>케이스 목록</h3>
          <div className="stack-md">
            {cases.map((c: any, i: number) => (
              <div key={c.id || i} style={{ fontSize: 14 }}>
                <strong>#{i + 1}</strong> {c.patient_ref} <span className="muted-text" style={{ fontSize: 12 }}>({c.status})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Previous QC Decisions */}
      {qc_decisions.length > 0 && (
        <div className="panel">
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 12px" }}>이전 결정 이력</h3>
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
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px" }}>QC 결정</h3>
          <div className="review-action-grid">
            <button
              className={`review-action-card ${decision === "APPROVE" ? "approve" : ""}`}
              onClick={() => setDecision("APPROVE")}
            >
              <div className="review-action-icon" style={{ color: "var(--success)" }}><CheckCircle size={28} /></div>
              <div className="review-action-label">승인</div>
            </button>
            <button
              className={`review-action-card ${decision === "REJECT" ? "reject" : ""}`}
              onClick={() => setDecision("REJECT")}
            >
              <div className="review-action-icon" style={{ color: "var(--danger)" }}><XCircle size={28} /></div>
              <div className="review-action-label">반려</div>
            </button>
            <button
              className={`review-action-card ${decision === "RERUN" ? "rerun" : ""}`}
              onClick={() => setDecision("RERUN")}
            >
              <div className="review-action-icon" style={{ color: "var(--warning)" }}><ArrowsClockwise size={28} /></div>
              <div className="review-action-label">재분석 요청</div>
            </button>
          </div>

          {decision && (
            <div className="stack-md" style={{ marginTop: 16 }}>
              <label className="field">
                코멘트
                <textarea className="textarea" value={comments} onChange={(e) => setComments(e.target.value)} placeholder="리뷰 의견을 입력하세요" rows={3} />
              </label>
              <button className="btn btn-primary" onClick={() => qcMut.mutate()} disabled={qcMut.isPending}>
                {qcMut.isPending ? <span className="spinner" /> : <>결정 제출 <Check size={16} /></>}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Report Review Panel */}
      {isExpertReview && (
        <div className="panel">
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px" }}>보고서 검토</h3>
          <div className="review-action-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
            <button
              className={`review-action-card ${decision === "APPROVE" ? "approve" : ""}`}
              onClick={() => setDecision("APPROVE")}
            >
              <div className="review-action-icon" style={{ color: "var(--success)" }}><CheckCircle size={28} /></div>
              <div className="review-action-label">승인</div>
            </button>
            <button
              className={`review-action-card ${decision === "REVISION_NEEDED" ? "rerun" : ""}`}
              onClick={() => setDecision("REVISION_NEEDED")}
            >
              <div className="review-action-icon" style={{ color: "var(--warning)" }}><ArrowsClockwise size={28} /></div>
              <div className="review-action-label">수정 요청</div>
            </button>
          </div>

          {decision && (
            <div className="stack-md" style={{ marginTop: 16 }}>
              <label className="field">
                코멘트
                <textarea className="textarea" value={comments} onChange={(e) => setComments(e.target.value)} placeholder="검토 의견을 입력하세요" rows={3} />
              </label>
              <button className="btn btn-primary" onClick={() => reportMut.mutate()} disabled={reportMut.isPending}>
                {reportMut.isPending ? <span className="spinner" /> : <>결정 제출 <Check size={16} /></>}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
