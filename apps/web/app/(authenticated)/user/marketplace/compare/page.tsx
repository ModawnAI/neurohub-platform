"use client";

import { Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQueries } from "@tanstack/react-query";
import { apiFetch, getServicePerformance, type ServiceRead } from "@/lib/api";
import { ArrowRight, Star } from "phosphor-react";
import { useTranslation } from "@/lib/i18n";

function MetricRow({ label, values }: { label: string; values: (string | number | null)[] }) {
  return (
    <div style={{ display: "contents" }}>
      <div style={{ padding: "10px 12px", fontSize: 13, fontWeight: 600, color: "var(--color-text-secondary)", background: "var(--color-surface-secondary)", borderBottom: "1px solid var(--color-border)" }}>
        {label}
      </div>
      {values.map((v, i) => (
        <div key={i} style={{ padding: "10px 12px", fontSize: 14, borderBottom: "1px solid var(--color-border)", textAlign: "center" }}>
          {v ?? <span style={{ color: "var(--color-text-secondary)" }}>—</span>}
        </div>
      ))}
    </div>
  );
}

function CompareModelsInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { t } = useTranslation();
  const idsParam = searchParams.get("ids") ?? "";
  const ids = idsParam.split(",").filter(Boolean).slice(0, 3);

  const serviceQueries = useQueries({
    queries: ids.map(id => ({
      queryKey: ["service", id],
      queryFn: () => apiFetch<ServiceRead>(`/services/${id}`),
    })),
  });

  const perfQueries = useQueries({
    queries: ids.map(id => ({
      queryKey: ["service-performance", id],
      queryFn: () => getServicePerformance(id, 30),
    })),
  });

  const isLoading = serviceQueries.some(q => q.isLoading);
  const services = serviceQueries.map(q => q.data ?? null);
  const perfs = perfQueries.map(q => {
    const pts = q.data?.data_points ?? [];
    return pts[pts.length - 1] ?? null;
  });

  if (ids.length < 2) {
    return (
      <div className="stack-lg">
        <div className="page-header">
          <h1 className="page-title">{t("marketplace.compare")}</h1>
        </div>
        <div className="empty-state">
          <p className="empty-state-text">{t("marketplace.selectMin")}</p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => router.push("/user/marketplace")}>
            {t("marketplace.browseMarketplace")}
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;

  const gridTemplate = `180px ${ids.map(() => "1fr").join(" ")}`;

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("marketplace.compare")}</h1>
          <p className="page-subtitle">{t("marketplace.compareSubtitle")}</p>
        </div>
        <button className="btn btn-secondary" onClick={() => router.push("/user/marketplace")}>
          &larr; {t("marketplace.browseMarketplace")}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: gridTemplate, gap: 0, border: "1px solid var(--color-border)", borderRadius: 8, overflow: "hidden" }}>
        {/* Header row */}
        <div style={{ padding: "16px 12px", background: "var(--color-surface-secondary)", fontWeight: 700, fontSize: 13, borderBottom: "2px solid var(--color-border)" }} />
        {services.map((svc, i) => (
          <div key={i} style={{ padding: "16px 12px", background: "var(--color-surface-secondary)", borderBottom: "2px solid var(--color-border)", textAlign: "center" }}>
            {svc ? (
              <>
                <p style={{ fontWeight: 700, fontSize: 15 }}>{svc.display_name || svc.name}</p>
                <div style={{ display: "flex", gap: 6, justifyContent: "center", marginTop: 4 }}>
                  {svc.category && <span className="badge badge-default">{svc.category}</span>}
                  <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>v{svc.version_label ?? svc.version}</span>
                </div>
              </>
            ) : <span style={{ color: "var(--color-text-secondary)" }}>—</span>}
          </div>
        ))}

        <MetricRow label={t("common.status")} values={services.map(s => s?.status ?? "-")} />
        <MetricRow label={t("adminServices.category") || "카테고리"} values={services.map(s => s?.category ?? "-")} />
        <MetricRow label={t("adminServices.serviceType") || "서비스 유형"} values={services.map(s => s?.service_type ?? "-")} />
        <MetricRow label={t("adminServices.department") || "부서"} values={services.map(s => s?.department ?? "-")} />

        {/* Performance metrics */}
        <MetricRow label={t("marketplace.accuracy")} values={perfs.map(p => p?.accuracy != null ? `${(p.accuracy * 100).toFixed(1)}%` : "-")} />
        <MetricRow label={t("marketplace.sensitivity")} values={perfs.map(p => p?.sensitivity != null ? `${(p.sensitivity * 100).toFixed(1)}%` : "-")} />
        <MetricRow label={t("marketplace.aucRoc")} values={perfs.map(p => p?.auc_roc != null ? p.auc_roc.toFixed(3) : "-")} />
        <MetricRow label={t("marketplace.f1Score")} values={perfs.map(p => p?.f1_score != null ? p.f1_score.toFixed(3) : "-")} />
        <MetricRow label={t("marketplace.avgLatency")} values={perfs.map(p => p?.avg_latency_s != null ? `${p.avg_latency_s.toFixed(1)}s` : "-")} />
        <MetricRow label={t("marketplace.expertApproval")} values={perfs.map(p => p?.expert_approval_rate != null ? `${(p.expert_approval_rate * 100).toFixed(0)}%` : "-")} />
        <MetricRow label={t("marketplace.totalRuns")} values={perfs.map(p => p?.total_runs ?? "-")} />

        {/* Pricing */}
        <MetricRow label={t("marketplace.basePrice")} values={services.map(s => s?.pricing ? `${s.pricing.base_price?.toLocaleString()}${s.pricing.currency === "KRW" ? "원" : ` ${s.pricing.currency}`}` : "-")} />
        <MetricRow label={t("marketplace.perCasePrice")} values={services.map(s => s?.pricing ? `${s.pricing.per_case_price?.toLocaleString()}${s.pricing.currency === "KRW" ? "원" : ` ${s.pricing.currency}`}` : "-")} />

        {/* Action row */}
        <div style={{ padding: "16px 12px", background: "var(--color-surface-secondary)", fontWeight: 700, fontSize: 13 }}>{t("marketplace.select")}</div>
        {services.map((svc, i) => (
          <div key={i} style={{ padding: 12, textAlign: "center", background: "var(--color-surface-secondary)" }}>
            {svc && (
              <button className="btn btn-primary btn-sm" onClick={() => router.push(`/user/new-request?service=${svc.id}`)}>
                <Star size={14} /> {t("marketplace.select")} <ArrowRight size={14} />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CompareModelsPage() {
  return (
    <Suspense fallback={<div className="loading-center"><span className="spinner" /></div>}>
      <CompareModelsInner />
    </Suspense>
  );
}
