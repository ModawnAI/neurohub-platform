"use client";

import type { RequestRead } from "@/lib/api";
import { useT } from "@/lib/i18n";
import {
  CheckCircle,
  Clock,
  Spinner,
  XCircle,
  ArrowRight,
  ArchiveTray,
} from "phosphor-react";
import type { ReactNode } from "react";

const STATUS_ICON: Record<string, { icon: ReactNode; bg: string; color: string }> = {
  CREATED: {
    icon: <Clock size={14} weight="bold" />,
    bg: "#e2e8f0",
    color: "#334155",
  },
  RECEIVING: {
    icon: <ArrowRight size={14} weight="bold" />,
    bg: "#dbeafe",
    color: "#1d4ed8",
  },
  STAGING: {
    icon: <ArchiveTray size={14} weight="bold" />,
    bg: "#ede9fe",
    color: "#6d28d9",
  },
  COMPUTING: {
    icon: <Spinner size={14} weight="bold" />,
    bg: "#dbeafe",
    color: "#1e40af",
  },
  FINAL: {
    icon: <CheckCircle size={14} weight="bold" />,
    bg: "#dcfce7",
    color: "#166534",
  },
  FAILED: {
    icon: <XCircle size={14} weight="bold" />,
    bg: "#fee2e2",
    color: "#b91c1c",
  },
  CANCELLED: {
    icon: <XCircle size={14} weight="bold" />,
    bg: "#f1f5f9",
    color: "#475569",
  },
};

export function ActivityFeed({ items }: { items: RequestRead[] }) {
  const t = useT();

  const sorted = [...items]
    .sort((a, b) => {
      const ta = a.updated_at ?? a.created_at;
      const tb = b.updated_at ?? b.created_at;
      return new Date(tb).getTime() - new Date(ta).getTime();
    })
    .slice(0, 10);

  if (sorted.length === 0) {
    return <p className="muted-text" style={{ textAlign: "center", padding: 20 }}>{t("activityFeed.noActivity")}</p>;
  }

  function relativeTime(dateStr: string): string {
    const now = Date.now();
    const diff = now - new Date(dateStr).getTime();
    const seconds = Math.floor(diff / 1000);

    if (seconds < 60) return t("relativeTime.justNow");
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return t("relativeTime.minutesAgo").replace("{n}", String(minutes));
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return t("relativeTime.hoursAgo").replace("{n}", String(hours));
    const days = Math.floor(hours / 24);
    return t("relativeTime.daysAgo").replace("{n}", String(days));
  }

  return (
    <div className="activity-list">
      {sorted.map((item) => {
        const meta = STATUS_ICON[item.status] ?? STATUS_ICON.CREATED!;
        const time = item.updated_at ?? item.created_at;
        const bg = meta?.bg ?? "#e2e8f0";
        const color = meta?.color ?? "#334155";
        const icon = meta?.icon ?? <Clock size={14} weight="bold" />;

        const statusKey = `status.${item.status}` as const;
        const label = t(statusKey as any) !== statusKey ? t(statusKey as any) : item.status;

        const statusChangedText = t("activityFeed.statusChanged")
          .replace("{id}", item.id.slice(0, 8))
          .replace("{label}", label);

        return (
          <div key={`${item.id}-${time}`} className="activity-item">
            <div
              className="activity-icon"
              style={{ background: bg, color }}
            >
              {icon}
            </div>
            <div className="activity-body">
              <p className="activity-text" dangerouslySetInnerHTML={{
                __html: statusChangedText
                  .replace(item.id.slice(0, 8), `<span class="mono-cell">${item.id.slice(0, 8)}</span>`)
                  .replace(label, `<strong>${label}</strong>`)
              }} />
              <p className="activity-time">{relativeTime(time)}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
