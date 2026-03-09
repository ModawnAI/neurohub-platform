"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { CaretRight, CheckCircle } from "phosphor-react";
import { listReviewQueue, type ReviewQueueItem } from "@/lib/api";
import { useT } from "@/lib/i18n";

type FilterTab = "QC" | "EXPERT_REVIEW" | "completed";

export default function ExpertReviewsPage() {
  const t = useT();
  const [filter, setFilter] = useState<FilterTab>("QC");
  const router = useRouter();

  const FILTER_TABS: Array<{ key: FilterTab; label: string }> = [
    { key: "QC", label: t("expertReviews.filterQC") },
    { key: "EXPERT_REVIEW", label: t("expertReviews.filterExpertReview") },
    { key: "completed", label: t("expertReviews.filterCompleted") },
  ];

  function relativeTime(iso: string): string {
    const diff = Date.now() - new Date(iso).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return t("relativeTime.justNow");
    if (min < 60) return t("relativeTime.minutesWaiting").replace("{n}", String(min));
    const hr = Math.floor(min / 60);
    if (hr < 24) return t("relativeTime.hoursWaiting").replace("{n}", String(hr));
    return t("relativeTime.daysWaiting").replace("{n}", String(Math.floor(hr / 24)));
  }
  const { data, isLoading } = useQuery({
    queryKey: ["review-queue", filter],
    queryFn: () => listReviewQueue(filter),
  });

  const items = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("expertReviews.title")}</h1>
          <p className="page-subtitle">{t("expertReviews.subtitle")}</p>
        </div>
      </div>

      <div className="filter-tabs">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            className={`filter-tab ${filter === tab.key ? "active" : ""}`}
            onClick={() => setFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><CheckCircle size={48} weight="light" /></div>
          <p className="empty-state-text">{t("expertReviews.noPending")}</p>
        </div>
      ) : (
        <div className="stack-md">
          {items.map((item: ReviewQueueItem) => (
            <div
              key={item.id}
              className="request-card"
              onClick={() => router.push(`/expert/reviews/${item.id}`)}
            >
              <div className="request-card-body">
                <p className="request-card-title">
                  {item.service_display_name || item.service_name || t("expertReviews.defaultServiceName")}
                </p>
                <p className="request-card-meta">
                  <span className={`status-chip status-${item.status.toLowerCase()}`}>
                    {item.status === "QC" ? t("status.QC") : t("status.EXPERT_REVIEW")}
                  </span>
                  <span>{t("expertReviews.cases")} {item.case_count}건</span>
                  <span>{relativeTime(item.created_at)}</span>
                </p>
              </div>
              <div className="request-card-chevron">
                <CaretRight size={18} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
