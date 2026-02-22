"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Spinner, CheckCircle, XCircle, PlusCircle } from "phosphor-react";
import { listRequests } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useT } from "@/lib/i18n";
import { MetricCard } from "@/components/metric-card";
import { RequestCard } from "@/components/request-card";

export default function UserDashboard() {
  const router = useRouter();
  const { user } = useAuth();
  const t = useT();
  const { data } = useQuery({ queryKey: ["requests"], queryFn: listRequests });

  const requests = data?.items ?? [];
  const inProgress = requests.filter((r) => !["FINAL", "FAILED", "CANCELLED"].includes(r.status)).length;
  const completed = requests.filter((r) => r.status === "FINAL").length;
  const failed = requests.filter((r) => r.status === "FAILED").length;
  const recent = requests.slice(0, 5);

  return (
    <div className="stack-lg">
      <div>
        <h1 className="greeting">{t("userDashboard.greeting").replace("{name}", user?.displayName || "사용자")}</h1>
        <p className="greeting-sub">{t("userDashboard.subtitle")}</p>
      </div>

      <div className="grid-3">
        <MetricCard
          icon={<Spinner size={20} />}
          label={t("userDashboard.inProgress")}
          value={inProgress}
          iconBg="var(--primary-light)"
          iconColor="var(--primary)"
        />
        <MetricCard
          icon={<CheckCircle size={20} />}
          label={t("userDashboard.completed")}
          value={completed}
          iconBg="var(--success-light)"
          iconColor="var(--success)"
        />
        <MetricCard
          icon={<XCircle size={20} />}
          label={t("userDashboard.failed")}
          value={failed}
          iconBg="var(--danger-light)"
          iconColor="var(--danger)"
        />
      </div>

      <div className="cta-card" onClick={() => router.push("/user/new-request")}>
        <div className="cta-card-icon"><PlusCircle size={32} /></div>
        <p className="cta-card-title">{t("userDashboard.ctaNewRequest")}</p>
        <p className="cta-card-desc">{t("userDashboard.ctaNewRequestDesc")}</p>
      </div>

      <div className="panel">
        <div className="panel-header-row" style={{ marginBottom: 16 }}>
          <h2 className="panel-title">{t("userDashboard.recentRequests")}</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => router.push("/user/requests")}>
            {t("common.viewAll")}
          </button>
        </div>
        {recent.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state-text">{t("userDashboard.emptyRequests")}</p>
          </div>
        ) : (
          <div className="stack-md">
            {recent.map((req) => (
              <RequestCard key={req.id} request={req} onClick={() => router.push(`/user/requests/${req.id}`)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
