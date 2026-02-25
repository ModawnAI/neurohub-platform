"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChartBar, Gear, UploadSimple, Sliders, FileText, CurrencyKrw, Cpu, CloudArrowUp } from "phosphor-react";
import { useState } from "react";
import { listServices, listRequests, type ServiceRead, type RequestRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { SkeletonCards } from "@/components/skeleton";
import { EmptyState } from "@/components/empty-state";

import { ServiceBasicInfo } from "./components/service-basic-info";
import { ServiceInputSchema } from "./components/service-input-schema";
import { ServiceUploadSlots } from "./components/service-upload-slots";
import { ServiceOptionsSchema } from "./components/service-options-schema";
import { ServiceOutputSchema } from "./components/service-output-schema";
import { ServicePricing } from "./components/service-pricing";
import { ServicePipelines } from "./components/service-pipelines";
import { ServiceDeployment } from "./components/service-deployment";

type TabId = "overview" | "input" | "upload" | "options" | "output" | "pricing" | "pipeline" | "deploy";

interface Tab {
  id: TabId;
  label: string;
  labelEn: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  { id: "overview", label: "기본 정보", labelEn: "Overview", icon: <Gear size={14} /> },
  { id: "input", label: "입력 스키마", labelEn: "Input Schema", icon: <FileText size={14} /> },
  { id: "upload", label: "업로드 슬롯", labelEn: "Upload Slots", icon: <UploadSimple size={14} /> },
  { id: "options", label: "분석 옵션", labelEn: "Options", icon: <Sliders size={14} /> },
  { id: "output", label: "출력 스키마", labelEn: "Output", icon: <FileText size={14} /> },
  { id: "pricing", label: "가격 설정", labelEn: "Pricing", icon: <CurrencyKrw size={14} /> },
  { id: "pipeline", label: "파이프라인", labelEn: "Pipelines", icon: <Cpu size={14} /> },
  { id: "deploy", label: "배포", labelEn: "Deploy", icon: <CloudArrowUp size={14} /> },
];

export default function ServiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const ko = locale === "ko";
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  const { data: servicesData, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: listServices,
  });

  const { data: requestsData } = useQuery({
    queryKey: ["requests"],
    queryFn: listRequests,
  });

  const service = (servicesData?.items ?? []).find((s: ServiceRead) => s.id === id);
  const allRequests: RequestRead[] = requestsData?.items ?? [];

  // Usage stats
  const serviceRequests = allRequests.filter((r: RequestRead) => r.service_id === id || (r.service_snapshot as Record<string, unknown> | null)?.id === id);
  const totalRequests = serviceRequests.length;
  const completedRequests = serviceRequests.filter((r) => r.status === "FINAL").length;
  const failedRequests = serviceRequests.filter((r) => r.status === "FAILED").length;
  const inProgressRequests = serviceRequests.filter((r) => !["FINAL", "FAILED", "CANCELLED"].includes(r.status)).length;

  // Schema completeness
  const hasInput = (service?.input_schema as Record<string, unknown[]> | null)?.fields?.length ?? 0;
  const hasUpload = service?.upload_slots?.length ?? 0;
  const hasOptions = (service?.options_schema as Record<string, unknown[]> | null)?.fields?.length ?? 0;
  const hasOutput = service?.output_schema?.fields?.length ?? 0;
  const hasPricing = service?.pricing?.base_price || service?.pricing?.per_case_price;

  if (isLoading) return <SkeletonCards count={3} />;
  if (!service) {
    return (
      <EmptyState
        title={t("serviceDetail.notFound")}
        actionLabel={t("serviceDetail.backToList")}
        onAction={() => router.push("/admin/services")}
      />
    );
  }

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/admin/services")}>
        <ArrowLeft size={16} /> {t("serviceDetail.backToList")}
      </button>

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{service.display_name}</h1>
          <p className="page-subtitle">{service.name} v{service.version}</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className={`status-chip ${service.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>
            {service.status === "ACTIVE" ? t("common.active") : t("common.inactive")}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div className="stats-grid" aria-label={t("serviceDetail.usageStats")}>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.totalRequests")}</p>
          <p className="stat-value">{totalRequests}</p>
        </div>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.completed")}</p>
          <p className="stat-value" style={{ color: "var(--success)" }}>{completedRequests}</p>
        </div>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.inProgress")}</p>
          <p className="stat-value" style={{ color: "var(--primary)" }}>{inProgressRequests}</p>
        </div>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.failed")}</p>
          <p className="stat-value" style={{ color: "var(--danger)" }}>{failedRequests}</p>
        </div>
      </div>

      {/* Schema Completeness Indicator */}
      <div className="panel" style={{ padding: "12px 16px" }}>
        <p className="detail-label" style={{ marginBottom: 8 }}>{ko ? "서비스 구성 현황" : "Configuration Status"}</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {[
            { label: ko ? "입력 필드" : "Input Fields", count: hasInput, tab: "input" as TabId },
            { label: ko ? "업로드 슬롯" : "Upload Slots", count: hasUpload, tab: "upload" as TabId },
            { label: ko ? "분석 옵션" : "Options", count: hasOptions, tab: "options" as TabId },
            { label: ko ? "출력 필드" : "Output Fields", count: hasOutput, tab: "output" as TabId },
            { label: ko ? "가격" : "Pricing", count: hasPricing ? 1 : 0, tab: "pricing" as TabId },
          ].map(({ label, count, tab }) => (
            <button
              key={tab}
              className={`status-chip ${count ? "status-final" : "status-pending"}`}
              style={{ cursor: "pointer", fontSize: 11 }}
              onClick={() => setActiveTab(tab)}
            >
              {count ? "✓" : "○"} {label} {typeof count === "number" && count > 0 ? `(${count})` : ""}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="filter-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`filter-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
            style={{ display: "flex", alignItems: "center", gap: 4 }}
          >
            {tab.icon}
            {ko ? tab.label : tab.labelEn}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && <ServiceBasicInfo service={service} />}
      {activeTab === "input" && <ServiceInputSchema service={service} />}
      {activeTab === "upload" && <ServiceUploadSlots service={service} />}
      {activeTab === "options" && <ServiceOptionsSchema service={service} />}
      {activeTab === "output" && <ServiceOutputSchema service={service} />}
      {activeTab === "pricing" && <ServicePricing service={service} />}
      {activeTab === "pipeline" && <ServicePipelines service={service} />}
      {activeTab === "deploy" && <ServiceDeployment service={service} />}

      {/* Recent Requests (always shown below tabs) */}
      {activeTab === "overview" && (
        <div className="panel">
          <h3 className="panel-title-mb">{t("serviceDetail.recentRequests")}</h3>
          {serviceRequests.length === 0 ? (
            <div className="empty-state" style={{ padding: "2rem 0" }}>
              <ChartBar size={32} weight="light" style={{ color: "var(--muted)" }} />
              <p className="muted-text">{t("serviceDetail.noRequests")}</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="table" aria-label={t("serviceDetail.recentRequests")}>
                <thead>
                  <tr>
                    <th scope="col">{t("reports.tableId")}</th>
                    <th scope="col">{t("reports.tableStatus")}</th>
                    <th scope="col">{t("reports.tableCases")}</th>
                    <th scope="col">{t("reports.tableDate")}</th>
                  </tr>
                </thead>
                <tbody>
                  {serviceRequests.slice(0, 10).map((req) => (
                    <tr key={req.id}>
                      <td className="mono-cell">{req.id.slice(0, 8)}</td>
                      <td>
                        <span className={`status-chip status-${req.status.toLowerCase()}`}>
                          {t(`status.${req.status}`)}
                        </span>
                      </td>
                      <td>{req.case_count}{ko ? "건" : ""}</td>
                      <td>{new Date(req.created_at).toLocaleDateString(dateLocale)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
