"use client";

import type { RequestRead, RequestStatus } from "@/lib/api";
import { CaretRight } from "phosphor-react";

const STATUS_LABELS: Record<RequestStatus, string> = {
  CREATED: "생성됨",
  RECEIVING: "수신 중",
  STAGING: "준비 중",
  READY_TO_COMPUTE: "분석 대기",
  COMPUTING: "분석 중",
  QC: "품질 검증",
  REPORTING: "보고서 생성",
  EXPERT_REVIEW: "전문가 검토",
  FINAL: "완료",
  FAILED: "실패",
  CANCELLED: "취소됨",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "방금 전";
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const day = Math.floor(hr / 24);
  return `${day}일 전`;
}

interface RequestCardProps {
  request: RequestRead;
  onClick: () => void;
  showService?: boolean;
}

export function RequestCard({ request, onClick, showService }: RequestCardProps) {
  const serviceName = (request as any).service_snapshot?.display_name || "AI 분석";

  return (
    <div className="request-card" onClick={onClick} role="button" tabIndex={0}>
      <div className="request-card-body">
        <p className="request-card-title">{showService !== false ? serviceName : `요청 #${request.id.slice(0, 8)}`}</p>
        <p className="request-card-meta">
          <span className={`status-chip status-${request.status.toLowerCase()}`}>
            {STATUS_LABELS[request.status]}
          </span>
          <span>케이스 {request.case_count}건</span>
          <span>{relativeTime(request.created_at)}</span>
        </p>
      </div>
      <div className="request-card-chevron">
        <CaretRight size={18} />
      </div>
    </div>
  );
}
