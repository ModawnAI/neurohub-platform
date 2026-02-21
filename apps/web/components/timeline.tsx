"use client";

import type { RequestStatus } from "@/lib/api";
import clsx from "clsx";

const STATUS_STEPS: Array<{ status: RequestStatus; label: string }> = [
  { status: "CREATED", label: "요청 생성" },
  { status: "RECEIVING", label: "데이터 수신" },
  { status: "STAGING", label: "준비 중" },
  { status: "READY_TO_COMPUTE", label: "분석 대기" },
  { status: "COMPUTING", label: "AI 분석 중" },
  { status: "QC", label: "품질 검증" },
  { status: "REPORTING", label: "보고서 생성" },
  { status: "EXPERT_REVIEW", label: "전문가 검토" },
  { status: "FINAL", label: "완료" },
];

const TERMINAL_STATUSES: RequestStatus[] = ["FAILED", "CANCELLED"];

interface TimelineProps {
  currentStatus: RequestStatus | string;
  createdAt?: string;
  updatedAt?: string | null;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function Timeline({ currentStatus, createdAt, updatedAt }: TimelineProps) {
  if (TERMINAL_STATUSES.includes(currentStatus as RequestStatus)) {
    const label = currentStatus === "FAILED" ? "실패" : "취소됨";
    return (
      <div className="timeline">
        <div className="timeline-item">
          <div className={clsx("timeline-dot", currentStatus === "FAILED" ? "completed" : "pending")}
            style={{ background: currentStatus === "FAILED" ? "var(--danger)" : "var(--muted)", borderColor: currentStatus === "FAILED" ? "var(--danger)" : "var(--muted)" }} />
          <p className="timeline-label" style={{ color: currentStatus === "FAILED" ? "var(--danger)" : "var(--muted)" }}>{label}</p>
          {updatedAt && <p className="timeline-time">{formatDate(updatedAt)}</p>}
        </div>
      </div>
    );
  }

  const currentIdx = STATUS_STEPS.findIndex((s) => s.status === currentStatus);

  return (
    <div className="timeline">
      {STATUS_STEPS.map((step, idx) => {
        let state: "completed" | "current" | "pending";
        if (idx < currentIdx) state = "completed";
        else if (idx === currentIdx) state = "current";
        else state = "pending";

        return (
          <div key={step.status} className="timeline-item">
            <div className={clsx("timeline-dot", state)} />
            <p className={clsx("timeline-label", state)}>{step.label}</p>
            {state === "completed" && idx === 0 && createdAt && <p className="timeline-time">{formatDate(createdAt)}</p>}
            {state === "current" && updatedAt && <p className="timeline-time">{formatDate(updatedAt)}</p>}
          </div>
        );
      })}
    </div>
  );
}
