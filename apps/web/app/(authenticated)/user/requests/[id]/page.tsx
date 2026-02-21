"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "phosphor-react";
import { getRequest, cancelRequest, type RequestStatus } from "@/lib/api";
import { Timeline } from "@/components/timeline";
import { useState } from "react";

const STATUS_LABELS: Record<RequestStatus, string> = {
  CREATED: "생성됨", RECEIVING: "수신 중", STAGING: "준비 중",
  READY_TO_COMPUTE: "분석 대기", COMPUTING: "분석 중", QC: "품질 검증",
  REPORTING: "보고서 생성", EXPERT_REVIEW: "전문가 검토", FINAL: "완료",
  FAILED: "실패", CANCELLED: "취소됨",
};

const CANCELLABLE: RequestStatus[] = ["CREATED", "RECEIVING", "STAGING", "READY_TO_COMPUTE"];

export default function UserRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);

  const { data: request, isLoading } = useQuery({
    queryKey: ["request", id],
    queryFn: () => getRequest(id),
    enabled: !!id,
  });

  const cancelMut = useMutation({
    mutationFn: () => cancelRequest(id, cancelReason || "사용자 취소"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["request", id] });
      setShowCancel(false);
    },
  });

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (!request) return <div className="empty-state"><p className="empty-state-text">요청을 찾을 수 없습니다.</p></div>;

  const serviceSnapshot = (request as any).service_snapshot;
  const canCancel = CANCELLABLE.includes(request.status);

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/user/requests")}>
        <ArrowLeft size={16} /> 내 요청으로 돌아가기
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">{serviceSnapshot?.display_name || "AI 분석 요청"}</h1>
          <p className="page-subtitle">요청 #{id.slice(0, 8)}</p>
        </div>
        <span className={`status-chip status-${request.status.toLowerCase()}`}>
          {STATUS_LABELS[request.status]}
        </span>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px" }}>진행 상태</h3>
          <Timeline currentStatus={request.status} createdAt={request.created_at} updatedAt={request.updated_at} />
        </div>

        <div className="stack-md">
          <div className="panel">
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px" }}>요청 정보</h3>
            <div className="stack-md">
              <div>
                <p className="detail-label">서비스</p>
                <p className="detail-value">{serviceSnapshot?.display_name || "-"}</p>
              </div>
              <div>
                <p className="detail-label">케이스 수</p>
                <p className="detail-value">{request.case_count}건</p>
              </div>
              <div>
                <p className="detail-label">생성일</p>
                <p className="detail-value">{new Date(request.created_at).toLocaleString("ko-KR")}</p>
              </div>
              {request.cancel_reason && (
                <div>
                  <p className="detail-label">취소 사유</p>
                  <p className="detail-value">{request.cancel_reason}</p>
                </div>
              )}
            </div>
          </div>

          {request.status === "FINAL" && (
            <div className="panel" style={{ background: "var(--success-light)", borderColor: "#86efac" }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 8px", color: "var(--success)" }}>분석 완료</h3>
              <p className="muted-text">AI 분석이 완료되었습니다. 보고서를 확인하세요.</p>
              <button className="btn btn-primary btn-sm" style={{ marginTop: 12 }}>
                보고서 보기
              </button>
            </div>
          )}

          {canCancel && !showCancel && (
            <button className="btn btn-danger" onClick={() => setShowCancel(true)}>
              요청 취소
            </button>
          )}

          {showCancel && (
            <div className="panel">
              <label className="field">
                취소 사유
                <textarea
                  className="textarea"
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="취소 사유를 입력하세요"
                  rows={3}
                />
              </label>
              <div className="action-row" style={{ marginTop: 12 }}>
                <button className="btn btn-danger btn-sm" onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}>
                  {cancelMut.isPending ? <span className="spinner" /> : "취소 확인"}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowCancel(false)}>닫기</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
