"use client";

import type { RequestRead, RequestStatus } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { CaretRight } from "phosphor-react";

function useRelativeTime() {
  const t = useT();
  return (iso: string): string => {
    const diff = Date.now() - new Date(iso).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return t("relativeTime.justNow");
    if (min < 60) return t("relativeTime.minutesAgo").replace("{n}", String(min));
    const hr = Math.floor(min / 60);
    if (hr < 24) return t("relativeTime.hoursAgo").replace("{n}", String(hr));
    const day = Math.floor(hr / 24);
    return t("relativeTime.daysAgo").replace("{n}", String(day));
  };
}

interface RequestCardProps {
  request: RequestRead;
  onClick: () => void;
  showService?: boolean;
}

export function RequestCard({ request, onClick, showService }: RequestCardProps) {
  const t = useT();
  const relativeTime = useRelativeTime();
  const serviceName = (request as any).service_snapshot?.display_name || "AI 분석";

  return (
    <div className="request-card" onClick={onClick} role="button" tabIndex={0}>
      <div className="request-card-body">
        <p className="request-card-title">{showService !== false ? serviceName : `요청 #${request.id.slice(0, 8)}`}</p>
        <p className="request-card-meta">
          <span className={`status-chip status-${request.status.toLowerCase()}`}>
            {t(`status.${request.status}` as `status.${RequestStatus}`)}
          </span>
          <span>{t("expertReviews.cases")} {request.case_count}건</span>
          <span>{relativeTime(request.created_at)}</span>
        </p>
      </div>
      <div className="request-card-chevron">
        <CaretRight size={18} />
      </div>
    </div>
  );
}
