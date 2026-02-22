"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ClockCounterClockwise, CheckCircle, CalendarBlank } from "phosphor-react";
import { listReviewQueue } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MetricCard } from "@/components/metric-card";
import { useTranslation } from "@/lib/i18n";

function getWeekStart(): Date {
  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(now);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(diff);
  return monday;
}

export default function ExpertDashboard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const router = useRouter();
  const { data: queueData } = useQuery({ queryKey: ["review-queue"], queryFn: () => listReviewQueue() });
  const { data: completedData } = useQuery({ queryKey: ["review-completed"], queryFn: () => listReviewQueue("completed") });

  const pendingCount = queueData?.total ?? 0;
  const completedCount = completedData?.total ?? 0;

  const thisWeekCount = (() => {
    const weekStart = getWeekStart();
    const items = completedData?.items ?? [];
    return items.filter((item) => {
      const updated = item.updated_at ? new Date(item.updated_at) : null;
      return updated && updated >= weekStart;
    }).length;
  })();

  return (
    <div className="stack-lg">
      <div>
        <h1 className="greeting">{t("expertDashboard.greeting").replace("{name}", user?.displayName || "전문가")}</h1>
        <p className="greeting-sub">{t("expertDashboard.subtitle")}</p>
      </div>

      <div className="grid-3">
        <MetricCard
          icon={<ClockCounterClockwise size={20} />}
          label={t("expertDashboard.pendingReviews")}
          value={pendingCount}
          iconBg="var(--warning-light)"
          iconColor="var(--warning)"
        />
        <MetricCard
          icon={<CheckCircle size={20} />}
          label={t("expertDashboard.completedReviews")}
          value={completedCount}
          iconBg="var(--success-light)"
          iconColor="var(--success)"
        />
        <MetricCard
          icon={<CalendarBlank size={20} />}
          label={t("expertDashboard.thisWeekReviews")}
          value={thisWeekCount}
          iconBg="var(--primary-light)"
          iconColor="var(--primary)"
        />
      </div>

      {pendingCount > 0 && (
        <div className="cta-card" onClick={() => router.push("/expert/reviews")}>
          <div className="cta-card-icon"><ClockCounterClockwise size={32} /></div>
          <p className="cta-card-title">{t("expertDashboard.ctaPendingMsg").replace("{count}", String(pendingCount))}</p>
          <p className="cta-card-desc">{t("expertDashboard.ctaPendingDesc")}</p>
        </div>
      )}

      {pendingCount === 0 && (
        <div className="empty-state">
          <p className="empty-state-text">{t("expertDashboard.noPending")}</p>
        </div>
      )}
    </div>
  );
}
