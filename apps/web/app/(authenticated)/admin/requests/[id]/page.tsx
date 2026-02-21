"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiFetch, advanceRequest } from "@/lib/api";
import { Timeline } from "@/components/timeline";
import { ArrowLeft } from "phosphor-react";
import Link from "next/link";

interface RequestDetail {
  id: string;
  service_name: string;
  status: string;
  priority: number;
  case_count: number;
  created_at: string;
  updated_at: string;
  institution_name?: string;
  created_by_name?: string;
  idempotency_key?: string;
}

const TRANSITIONS: Record<string, string[]> = {
  CREATED: ["RECEIVING"],
  RECEIVING: ["STAGING"],
  STAGING: ["READY_TO_COMPUTE"],
  READY_TO_COMPUTE: ["COMPUTING"],
  COMPUTING: ["QC", "FAILED"],
  QC: ["REPORTING", "COMPUTING", "FAILED"],
  REPORTING: ["EXPERT_REVIEW", "FINAL"],
  EXPERT_REVIEW: ["FINAL", "REPORTING"],
};

const STATUS_LABELS: Record<string, string> = {
  CREATED: "생성됨", RECEIVING: "데이터 수신 중", STAGING: "검증 중",
  READY_TO_COMPUTE: "분석 대기", COMPUTING: "분석 중", QC: "품질 검증",
  REPORTING: "보고서 생성", EXPERT_REVIEW: "전문가 검토", FINAL: "완료",
  FAILED: "실패", CANCELLED: "취소됨",
};

export default function AdminRequestDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [request, setRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);

  const fetchRequest = async () => {
    try {
      const data = await apiFetch<RequestDetail>(`/requests/${id}`);
      setRequest(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchRequest(); }, [id]);

  const handleTransition = async (targetStatus: string) => {
    setTransitioning(true);
    try {
      await advanceRequest(id, targetStatus);
      await fetchRequest();
    } catch {
      // ignore
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (!request) return <div className="banner banner-warning">요청을 찾을 수 없습니다.</div>;

  const possibleTransitions = TRANSITIONS[request.status] || [];

  return (
    <div>
      <Link href="/admin/requests" className="back-link">
        <ArrowLeft size={16} /> 요청 목록으로
      </Link>

      <div className="detail-header">
        <h1 className="page-title">요청 상세</h1>
        <span className={`status-chip status-${request.status.toLowerCase()}`}>
          {STATUS_LABELS[request.status] || request.status}
        </span>
      </div>

      <div className="detail-grid">
        <div>
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>요청 정보</h2>
            <div className="info-rows">
              <div className="info-row"><span className="info-label">요청 ID</span><span className="info-value" style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{request.id}</span></div>
              <div className="info-row"><span className="info-label">서비스</span><span className="info-value">{request.service_name}</span></div>
              <div className="info-row"><span className="info-label">케이스 수</span><span className="info-value">{request.case_count}건</span></div>
              <div className="info-row"><span className="info-label">우선순위</span><span className="info-value">{request.priority}</span></div>
              <div className="info-row"><span className="info-label">생성일</span><span className="info-value">{new Date(request.created_at).toLocaleString("ko-KR")}</span></div>
              <div className="info-row"><span className="info-label">최종 수정</span><span className="info-value">{new Date(request.updated_at).toLocaleString("ko-KR")}</span></div>
              {request.institution_name && <div className="info-row"><span className="info-label">기관</span><span className="info-value">{request.institution_name}</span></div>}
            </div>
          </div>

          {possibleTransitions.length > 0 && (
            <div className="card">
              <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>상태 전이</h2>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {possibleTransitions.map((target) => (
                  <button
                    key={target}
                    className={`btn ${target === "FAILED" || target === "CANCELLED" ? "btn-danger" : "btn-primary"}`}
                    onClick={() => handleTransition(target)}
                    disabled={transitioning}
                  >
                    → {STATUS_LABELS[target] || target}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <div>
          <div className="card">
            <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>진행 상태</h2>
            <Timeline currentStatus={request.status} />
          </div>
        </div>
      </div>
    </div>
  );
}
