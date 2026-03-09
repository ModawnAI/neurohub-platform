"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Stack, Users, UserCircleGear, Cube } from "phosphor-react";
import { getAdminStats } from "@/lib/api";
import { MetricCard } from "@/components/metric-card";
import { StatusBar } from "@/components/status-bar";
import { useT } from "@/lib/i18n";
import { SkeletonMetricCards } from "@/components/skeleton";

export default function AdminDashboard() {
  const t = useT();
  const router = useRouter();
  const { data: stats, isLoading } = useQuery({ queryKey: ["admin-stats"], queryFn: getAdminStats });

  const statusCounts = stats?.status_counts ?? {};
  const mockRequests = Object.entries(statusCounts).map(([status, count]) => ({
    status,
    count: count as number,
  }));

  return (
    <div className="stack-lg">
      <div>
        <h1 className="page-title">{t("adminDashboard.title")}</h1>
        <p className="page-subtitle">{t("adminDashboard.subtitle")}</p>
      </div>

      {isLoading ? (
        <SkeletonMetricCards count={4} />
      ) : (
        <div className="panel-grid">
          <MetricCard
            icon={<Stack size={20} />}
            label={t("adminDashboard.totalRequests")}
            value={stats?.total_requests ?? 0}
            iconBg="var(--primary-light)"
            iconColor="var(--primary)"
          />
          <MetricCard
            icon={<Users size={20} />}
            label={t("adminDashboard.activeUsers")}
            value={stats?.active_users ?? 0}
            iconBg="var(--success-light)"
            iconColor="var(--success)"
          />
          <MetricCard
            icon={<UserCircleGear size={20} />}
            label={t("adminDashboard.pendingExperts")}
            value={stats?.pending_experts ?? 0}
            iconBg="var(--warning-light)"
            iconColor="var(--warning)"
          />
          <MetricCard
            icon={<Cube size={20} />}
            label={t("adminDashboard.activeServices")}
            value={stats?.total_services ?? 0}
            iconBg="#ede9fe"
            iconColor="#6d28d9"
          />
        </div>
      )}

      {mockRequests.length > 0 && (
        <div className="panel">
          <h3 className="panel-title-mb">{t("adminDashboard.statusDistribution")}</h3>
          <StatusBar items={mockRequests.map(r => ({ status: r.status } as any))} />
        </div>
      )}

      <div className="dashboard-columns">
        <div className="panel">
          <div className="panel-header-row" style={{ marginBottom: 12 }}>
            <h3 className="panel-title">{t("adminDashboard.quickActions")}</h3>
          </div>
          <div className="stack-md">
            <button className="btn btn-secondary" onClick={() => router.push("/admin/requests")} style={{ width: "100%" }}>
              {t("adminDashboard.manageRequests")}
            </button>
            <button className="btn btn-secondary" onClick={() => router.push("/admin/users?expert_status=PENDING_APPROVAL")} style={{ width: "100%" }}>
              {t("adminDashboard.approveExperts").replace("{count}", String(stats?.pending_experts ?? 0))}
            </button>
            <button className="btn btn-secondary" onClick={() => router.push("/admin/organizations")} style={{ width: "100%" }}>
              {t("adminDashboard.manageOrgs")}
            </button>
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title-mb">{t("adminDashboard.systemSummary")}</h3>
          <div className="stack-md">
            <div>
              <p className="detail-label">{t("adminDashboard.totalOrgs")}</p>
              <p className="detail-value">{t("adminDashboard.countOrgs").replace("{count}", String(stats?.total_organizations ?? 0))}</p>
            </div>
            <div>
              <p className="detail-label">{t("adminDashboard.approvedExperts")}</p>
              <p className="detail-value">{t("adminDashboard.countPeople").replace("{count}", String(stats?.approved_experts ?? 0))}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
