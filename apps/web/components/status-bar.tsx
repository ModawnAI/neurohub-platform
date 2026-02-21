"use client";

import type { RequestRead } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  CREATED: "#94a3b8",
  RECEIVING: "#3b82f6",
  STAGING: "#8b5cf6",
  READY_TO_COMPUTE: "#a855f7",
  COMPUTING: "#2563eb",
  QC: "#d97706",
  REPORTING: "#0284c7",
  EXPERT_REVIEW: "#ca8a04",
  FINAL: "#16a34a",
  FAILED: "#dc2626",
  CANCELLED: "#64748b",
};

const STATUS_LABELS: Record<string, string> = {
  CREATED: "생성됨",
  RECEIVING: "수신 중",
  STAGING: "준비 중",
  READY_TO_COMPUTE: "분석 대기",
  COMPUTING: "분석 중",
  QC: "품질 검증",
  REPORTING: "보고서 작성",
  EXPERT_REVIEW: "전문가 검토",
  FINAL: "완료",
  FAILED: "실패",
  CANCELLED: "취소",
};

export function StatusBar({ items }: { items: RequestRead[] }) {
  const total = items.length;
  if (total === 0) return null;

  const counts: Record<string, number> = {};
  for (const item of items) {
    counts[item.status] = (counts[item.status] ?? 0) + 1;
  }

  const entries = Object.entries(counts).sort(
    ([a], [b]) =>
      Object.keys(STATUS_COLORS).indexOf(a) - Object.keys(STATUS_COLORS).indexOf(b),
  );

  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div className="status-bar">
        {entries.map(([status, count]) => (
          <div
            key={status}
            className="status-bar-segment"
            style={{
              width: `${(count / total) * 100}%`,
              background: STATUS_COLORS[status] ?? "#94a3b8",
            }}
            title={`${STATUS_LABELS[status] ?? status}: ${count}건`}
          />
        ))}
      </div>
      <div className="status-bar-legend">
        {entries.map(([status, count]) => (
          <span key={status} className="status-bar-legend-item">
            <span
              className="status-bar-legend-dot"
              style={{ background: STATUS_COLORS[status] ?? "#94a3b8" }}
            />
            {STATUS_LABELS[status] ?? status} {count}
          </span>
        ))}
      </div>
    </div>
  );
}
