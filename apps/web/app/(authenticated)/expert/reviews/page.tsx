"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { CaretRight } from "phosphor-react";
import { listReviewQueue, type ReviewQueueItem } from "@/lib/api";

type FilterTab = "QC" | "EXPERT_REVIEW" | "completed";

const FILTER_TABS: Array<{ key: FilterTab; label: string }> = [
  { key: "QC", label: "QC 대기" },
  { key: "EXPERT_REVIEW", label: "전문가 검토 대기" },
  { key: "completed", label: "완료" },
];

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "방금 전";
  if (min < 60) return `${min}분 대기 중`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 대기 중`;
  return `${Math.floor(hr / 24)}일 대기 중`;
}

export default function ExpertReviewsPage() {
  const [filter, setFilter] = useState<FilterTab>("QC");
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["review-queue", filter],
    queryFn: () => listReviewQueue(filter),
  });

  const items = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">리뷰 대기열</h1>
          <p className="page-subtitle">검토가 필요한 요청 목록입니다</p>
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
          <p className="empty-state-text">대기 중인 리뷰가 없습니다.</p>
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
                  {item.service_display_name || item.service_name || "AI 분석"}
                </p>
                <p className="request-card-meta">
                  <span className={`status-chip status-${item.status.toLowerCase()}`}>
                    {item.status === "QC" ? "품질 검증" : "전문가 검토"}
                  </span>
                  <span>케이스 {item.case_count}건</span>
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
