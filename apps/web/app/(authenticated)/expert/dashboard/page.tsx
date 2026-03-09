"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  ClockCounterClockwise,
  CheckCircle,
  CalendarBlank,
  CaretRight,
  Timer,
  ListChecks,
  ChartLine,
} from "phosphor-react";
import { listReviewQueue, type ReviewQueueItem } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MetricCard } from "@/components/metric-card";
import { SkeletonMetricCards } from "@/components/skeleton";
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

function getMonthStart(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1);
}

function relativeTime(iso: string, locale: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return locale === "ko" ? "방금 전" : "Just now";
  if (min < 60) return locale === "ko" ? `${min}분 전` : `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return locale === "ko" ? `${hr}시간 전` : `${hr}h ago`;
  const days = Math.floor(hr / 24);
  return locale === "ko" ? `${days}일 전` : `${days}d ago`;
}

export default function ExpertDashboard() {
  const { t, locale } = useTranslation();
  const ko = locale === "ko";
  const { user } = useAuth();
  const router = useRouter();

  const { data: queueData, isLoading: loadingQueue } = useQuery({
    queryKey: ["review-queue"],
    queryFn: () => listReviewQueue(),
  });
  const { data: completedData, isLoading: loadingCompleted } = useQuery({
    queryKey: ["review-completed"],
    queryFn: () => listReviewQueue("completed"),
  });

  const pendingItems: ReviewQueueItem[] = queueData?.items ?? [];
  const completedItems: ReviewQueueItem[] = completedData?.items ?? [];
  const pendingCount = queueData?.total ?? 0;
  const completedCount = completedData?.total ?? 0;
  const isLoading = loadingQueue || loadingCompleted;

  const thisWeekCount = (() => {
    const weekStart = getWeekStart();
    return completedItems.filter((item) => {
      const updated = item.updated_at ? new Date(item.updated_at) : null;
      return updated && updated >= weekStart;
    }).length;
  })();

  const thisMonthCount = (() => {
    const monthStart = getMonthStart();
    return completedItems.filter((item) => {
      const updated = item.updated_at ? new Date(item.updated_at) : null;
      return updated && updated >= monthStart;
    }).length;
  })();

  // Average turnaround (completed items only)
  const avgTurnaround = (() => {
    const withDuration = completedItems.filter((item) => item.created_at && item.updated_at);
    if (withDuration.length === 0) return null;
    const totalMs = withDuration.reduce((sum, item) => {
      return sum + (new Date(item.updated_at!).getTime() - new Date(item.created_at).getTime());
    }, 0);
    const avgHours = totalMs / withDuration.length / (1000 * 60 * 60);
    if (avgHours < 1) return ko ? `${Math.round(avgHours * 60)}분` : `${Math.round(avgHours * 60)}m`;
    if (avgHours < 24) return ko ? `${avgHours.toFixed(1)}시간` : `${avgHours.toFixed(1)}h`;
    return ko ? `${(avgHours / 24).toFixed(1)}일` : `${(avgHours / 24).toFixed(1)}d`;
  })();

  return (
    <div className="stack-lg">
      <div>
        <h1 className="greeting">
          {t("expertDashboard.greeting").replace("{name}", user?.displayName || t("userType.EXPERT"))}
        </h1>
        <p className="greeting-sub">{t("expertDashboard.subtitle")}</p>
      </div>

      {/* Stats */}
      {isLoading ? (
        <SkeletonMetricCards count={3} />
      ) : (
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
            label={ko ? "이번 달 완료" : "Completed This Month"}
            value={thisMonthCount}
            iconBg="var(--success-light)"
            iconColor="var(--success)"
          />
          <MetricCard
            icon={<Timer size={20} />}
            label={ko ? "평균 처리 시간" : "Avg. Turnaround"}
            value={avgTurnaround ?? "—"}
            iconBg="var(--primary-light)"
            iconColor="var(--primary)"
          />
        </div>
      )}

      {/* CTA card for pending reviews */}
      {pendingCount > 0 && (
        <div className="cta-card" onClick={() => router.push("/expert/reviews")}>
          <div className="cta-card-icon"><ClockCounterClockwise size={32} /></div>
          <p className="cta-card-title">{t("expertDashboard.ctaPendingMsg").replace("{count}", String(pendingCount))}</p>
          <p className="cta-card-desc">{t("expertDashboard.ctaPendingDesc")}</p>
        </div>
      )}

      <div className="dashboard-columns">
        {/* Pending Review Queue */}
        <div className="panel">
          <div className="panel-header-row" style={{ marginBottom: 12 }}>
            <h3 className="panel-title" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <ListChecks size={18} />
              {ko ? "대기 중인 리뷰" : "Pending Reviews"}
            </h3>
            {pendingCount > 0 && (
              <button className="btn btn-secondary btn-sm" onClick={() => router.push("/expert/reviews")}>
                {ko ? "전체 보기" : "View All"}
              </button>
            )}
          </div>
          {pendingItems.length === 0 ? (
            <div className="empty-state" style={{ padding: "24px 16px" }}>
              <div className="empty-state-icon">
                <CheckCircle size={40} weight="light" />
              </div>
              <p className="empty-state-text">{t("expertDashboard.noPending")}</p>
            </div>
          ) : (
            <div className="stack-sm">
              {pendingItems.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  className="request-card"
                  onClick={() => router.push(`/expert/reviews/${item.id}`)}
                  style={{ cursor: "pointer" }}
                >
                  <div className="request-card-body">
                    <p className="request-card-title" style={{ fontSize: 14 }}>
                      {item.service_display_name || item.service_name || (ko ? "분석 요청" : "Analysis Request")}
                    </p>
                    <p className="request-card-meta">
                      <span className={`status-chip status-${item.status.toLowerCase()}`}>
                        {item.status === "QC" ? "QC" : ko ? "전문가 검토" : "Expert Review"}
                      </span>
                      <span>{item.case_count}{ko ? "건" : ` case${item.case_count === 1 ? "" : "s"}`}</span>
                      <span>{relativeTime(item.created_at, locale)}</span>
                    </p>
                  </div>
                  <div className="request-card-chevron">
                    <CaretRight size={16} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Review History + Quick Stats */}
        <div className="panel">
          <h3 className="panel-title" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 16 }}>
            <ChartLine size={18} />
            {ko ? "리뷰 요약" : "Review Summary"}
          </h3>
          <div className="stack-md">
            <div>
              <p className="detail-label">{ko ? "전체 완료" : "Total Completed"}</p>
              <p className="detail-value">{completedCount}{ko ? "건" : ""}</p>
            </div>
            <div>
              <p className="detail-label">{ko ? "이번 주 완료" : "This Week"}</p>
              <p className="detail-value">{thisWeekCount}{ko ? "건" : ""}</p>
            </div>
            <div>
              <p className="detail-label">{ko ? "이번 달 완료" : "This Month"}</p>
              <p className="detail-value">{thisMonthCount}{ko ? "건" : ""}</p>
            </div>
            <div>
              <p className="detail-label">{ko ? "평균 처리 시간" : "Avg. Turnaround"}</p>
              <p className="detail-value">{avgTurnaround ?? "—"}</p>
            </div>
          </div>

          {/* Quick action */}
          <div style={{ borderTop: "1px solid var(--border)", marginTop: 16, paddingTop: 16 }}>
            <button
              className="btn btn-secondary"
              onClick={() => router.push("/expert/reviews")}
              style={{ width: "100%" }}
            >
              {ko ? "리뷰 큐로 이동" : "Go to Review Queue"}
            </button>
          </div>
        </div>
      </div>

      {/* Recent completed reviews */}
      {completedItems.length > 0 && (
        <div className="panel">
          <div className="panel-header-row" style={{ marginBottom: 12 }}>
            <h3 className="panel-title">{ko ? "최근 완료된 리뷰" : "Recent Completed Reviews"}</h3>
          </div>
          <div className="stack-sm">
            {completedItems.slice(0, 5).map((item) => (
              <div
                key={item.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "10px 0",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 14,
                }}
              >
                <div>
                  <p style={{ fontWeight: 600, margin: 0, fontSize: 13 }}>
                    {item.service_display_name || item.service_name || (ko ? "분석 요청" : "Analysis Request")}
                  </p>
                  <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
                    {item.case_count}{ko ? "건" : ` case${item.case_count === 1 ? "" : "s"}`}
                    {item.updated_at && ` — ${relativeTime(item.updated_at, locale)}`}
                  </p>
                </div>
                <span className="status-chip status-final">
                  {ko ? "완료" : "Done"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
