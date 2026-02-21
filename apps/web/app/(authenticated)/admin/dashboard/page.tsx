"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Stack, Users, UserCircleGear, Cube } from "phosphor-react";
import { getAdminStats } from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import { StatusBar } from "@/components/status-bar";

export default function AdminDashboard() {
  const router = useRouter();
  const { data: stats } = useQuery({ queryKey: ["admin-stats"], queryFn: getAdminStats });

  const statusCounts = stats?.status_counts ?? {};
  const mockRequests = Object.entries(statusCounts).map(([status, count]) => ({
    status,
    count: count as number,
  }));

  return (
    <div className="stack-lg">
      <div>
        <h1 className="page-title">관리자 대시보드</h1>
        <p className="page-subtitle">시스템 전체 현황을 확인하세요</p>
      </div>

      <div className="panel-grid">
        <MetricCard
          icon={<Stack size={20} />}
          label="전체 요청"
          value={stats?.total_requests ?? 0}
          iconBg="var(--primary-light)"
          iconColor="var(--primary)"
        />
        <MetricCard
          icon={<Users size={20} />}
          label="활성 사용자"
          value={stats?.active_users ?? 0}
          iconBg="var(--success-light)"
          iconColor="var(--success)"
        />
        <MetricCard
          icon={<UserCircleGear size={20} />}
          label="승인 대기 전문가"
          value={stats?.pending_experts ?? 0}
          iconBg="var(--warning-light)"
          iconColor="var(--warning)"
        />
        <MetricCard
          icon={<Cube size={20} />}
          label="활성 서비스"
          value={stats?.total_services ?? 0}
          iconBg="#ede9fe"
          iconColor="#6d28d9"
        />
      </div>

      {mockRequests.length > 0 && (
        <div className="panel">
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 12px" }}>요청 상태 분포</h3>
          <StatusBar items={mockRequests.map(r => ({ status: r.status } as any))} />
        </div>
      )}

      <div className="dashboard-columns">
        <div className="panel">
          <div className="panel-header-row" style={{ marginBottom: 12 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>빠른 작업</h3>
          </div>
          <div className="stack-md">
            <button className="btn btn-secondary" onClick={() => router.push("/admin/requests")} style={{ width: "100%" }}>
              요청 관리 →
            </button>
            <button className="btn btn-secondary" onClick={() => router.push("/admin/users?expert_status=PENDING_APPROVAL")} style={{ width: "100%" }}>
              전문가 승인 대기 ({stats?.pending_experts ?? 0}건) →
            </button>
            <button className="btn btn-secondary" onClick={() => router.push("/admin/organizations")} style={{ width: "100%" }}>
              기관 관리 →
            </button>
          </div>
        </div>

        <div className="panel">
          <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 12px" }}>시스템 요약</h3>
          <div className="stack-md">
            <div>
              <p className="detail-label">전체 기관</p>
              <p className="detail-value">{stats?.total_organizations ?? 0}개</p>
            </div>
            <div>
              <p className="detail-label">승인된 전문가</p>
              <p className="detail-value">{stats?.approved_experts ?? 0}명</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
