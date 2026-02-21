"use client";

import type { RequestRead } from "@/lib/api";
import {
  CheckCircle,
  Clock,
  Spinner,
  XCircle,
  ArrowRight,
  ArchiveTray,
} from "phosphor-react";
import type { ReactNode } from "react";

const STATUS_META: Record<string, { icon: ReactNode; bg: string; color: string; label: string }> = {
  CREATED: {
    icon: <Clock size={14} weight="bold" />,
    bg: "#e2e8f0",
    color: "#334155",
    label: "생성됨",
  },
  RECEIVING: {
    icon: <ArrowRight size={14} weight="bold" />,
    bg: "#dbeafe",
    color: "#1d4ed8",
    label: "수신 중",
  },
  STAGING: {
    icon: <ArchiveTray size={14} weight="bold" />,
    bg: "#ede9fe",
    color: "#6d28d9",
    label: "준비 중",
  },
  COMPUTING: {
    icon: <Spinner size={14} weight="bold" />,
    bg: "#dbeafe",
    color: "#1e40af",
    label: "분석 중",
  },
  FINAL: {
    icon: <CheckCircle size={14} weight="bold" />,
    bg: "#dcfce7",
    color: "#166534",
    label: "완료",
  },
  FAILED: {
    icon: <XCircle size={14} weight="bold" />,
    bg: "#fee2e2",
    color: "#b91c1c",
    label: "실패",
  },
  CANCELLED: {
    icon: <XCircle size={14} weight="bold" />,
    bg: "#f1f5f9",
    color: "#475569",
    label: "취소됨",
  },
};

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const diff = now - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);

  if (seconds < 60) return "방금 전";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  return `${days}일 전`;
}

export function ActivityFeed({ items }: { items: RequestRead[] }) {
  const sorted = [...items]
    .sort((a, b) => {
      const ta = a.updated_at ?? a.created_at;
      const tb = b.updated_at ?? b.created_at;
      return new Date(tb).getTime() - new Date(ta).getTime();
    })
    .slice(0, 10);

  if (sorted.length === 0) {
    return <p className="muted-text" style={{ textAlign: "center", padding: 20 }}>활동 내역이 없습니다.</p>;
  }

  return (
    <div className="activity-list">
      {sorted.map((item) => {
        const meta = STATUS_META[item.status] ?? STATUS_META.CREATED!;
        const time = item.updated_at ?? item.created_at;
        const bg = meta?.bg ?? "#e2e8f0";
        const color = meta?.color ?? "#334155";
        const icon = meta?.icon ?? <Clock size={14} weight="bold" />;
        const label = meta?.label ?? item.status;
        return (
          <div key={`${item.id}-${time}`} className="activity-item">
            <div
              className="activity-icon"
              style={{ background: bg, color }}
            >
              {icon}
            </div>
            <div className="activity-body">
              <p className="activity-text">
                요청 <span className="mono-cell">{item.id.slice(0, 8)}</span> 상태가{" "}
                <strong>{label}</strong>(으)로 변경
              </p>
              <p className="activity-time">{relativeTime(time)}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
