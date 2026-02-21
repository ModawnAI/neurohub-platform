"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ClockCounterClockwise, CheckCircle, CalendarBlank } from "phosphor-react";
import { listReviewQueue } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MetricCard } from "@/components/metric-card";

export default function ExpertDashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const { data: queueData } = useQuery({ queryKey: ["review-queue"], queryFn: () => listReviewQueue() });
  const { data: completedData } = useQuery({ queryKey: ["review-completed"], queryFn: () => listReviewQueue("completed") });

  const pendingCount = queueData?.total ?? 0;
  const completedCount = completedData?.total ?? 0;

  return (
    <div className="stack-lg">
      <div>
        <h1 className="greeting">안녕하세요, {user?.displayName || "전문가"}님</h1>
        <p className="greeting-sub">리뷰 현황을 확인하세요</p>
      </div>

      <div className="grid-3">
        <MetricCard
          icon={<ClockCounterClockwise size={20} />}
          label="대기 중 리뷰"
          value={pendingCount}
          iconBg="var(--warning-light)"
          iconColor="var(--warning)"
        />
        <MetricCard
          icon={<CheckCircle size={20} />}
          label="완료한 리뷰"
          value={completedCount}
          iconBg="var(--success-light)"
          iconColor="var(--success)"
        />
        <MetricCard
          icon={<CalendarBlank size={20} />}
          label="이번 주 리뷰"
          value={0}
          iconBg="var(--primary-light)"
          iconColor="var(--primary)"
        />
      </div>

      {pendingCount > 0 && (
        <div className="cta-card" onClick={() => router.push("/expert/reviews")}>
          <div className="cta-card-icon"><ClockCounterClockwise size={32} /></div>
          <p className="cta-card-title">대기 중인 리뷰가 {pendingCount}건 있습니다</p>
          <p className="cta-card-desc">리뷰 대기열로 이동하여 검토를 시작하세요</p>
        </div>
      )}

      {pendingCount === 0 && (
        <div className="empty-state">
          <p className="empty-state-text">현재 대기 중인 리뷰가 없습니다.</p>
        </div>
      )}
    </div>
  );
}
