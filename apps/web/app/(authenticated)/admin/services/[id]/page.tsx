"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChartBar, Gear, FileText, Cpu, Trash, Warning, ChartLine } from "phosphor-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import * as Dialog from "@radix-ui/react-dialog";
import { listServices, listRequests, deleteService, type ServiceRead, type RequestRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { SkeletonCards } from "@/components/skeleton";
import { EmptyState } from "@/components/empty-state";
import { Breadcrumb } from "@/components/breadcrumb";

import { ServiceBasicInfo } from "./components/service-basic-info";
import { ServicePricing } from "./components/service-pricing";
import { ServiceSchemaEditor } from "./components/service-schema-editor";
import { ServicePipelines } from "./components/service-pipelines";
import { ServiceDeployment } from "./components/service-deployment";
import { TechniqueWeightEditor } from "@/components/technique-weight-editor";

type TabId = "settings" | "schema" | "execution" | "analytics";

interface Tab {
  id: TabId;
  label: string;
  labelEn: string;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  { id: "settings", label: "기본 설정", labelEn: "Settings", icon: <Gear size={14} /> },
  { id: "schema", label: "입출력 스키마", labelEn: "Schema", icon: <FileText size={14} /> },
  { id: "execution", label: "실행 환경", labelEn: "Execution", icon: <Cpu size={14} /> },
  { id: "analytics", label: "사용 현황", labelEn: "Analytics", icon: <ChartLine size={14} /> },
];

export default function ServiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>("settings");
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");

  const deleteMut = useMutation({
    mutationFn: () => deleteService(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      router.push("/admin/services");
    },
  });

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
      <Breadcrumb
        items={[
          { label: ko ? "관리자" : "Admin", href: "/admin/dashboard" },
          { label: t("adminServices.title"), href: "/admin/services" },
          { label: service.display_name },
        ]}
      />

      {/* Compact Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{service.display_name}</h1>
          <p className="page-subtitle">{service.name} v{service.version}</p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className={`status-chip ${service.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>
            {service.status === "ACTIVE" ? t("common.active") : t("common.inactive")}
          </span>
          <button
            className="btn btn-sm btn-danger"
            onClick={() => { setShowDeleteDialog(true); setDeleteConfirmText(""); deleteMut.reset(); }}
          >
            <Trash size={14} /> {ko ? "삭제" : "Delete"}
          </button>
        </div>
      </div>

      {/* Schema Completeness Indicator */}
      <div className="panel" style={{ padding: "12px 16px" }}>
        <p className="detail-label" style={{ marginBottom: 8 }}>{ko ? "서비스 구성 현황" : "Configuration Status"}</p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {[
            { label: ko ? "입력 필드" : "Input Fields", count: hasInput, tab: "schema" as TabId },
            { label: ko ? "업로드 슬롯" : "Upload Slots", count: hasUpload, tab: "schema" as TabId },
            { label: ko ? "분석 옵션" : "Options", count: hasOptions, tab: "schema" as TabId },
            { label: ko ? "출력 필드" : "Output Fields", count: hasOutput, tab: "schema" as TabId },
            { label: ko ? "가격" : "Pricing", count: hasPricing ? 1 : 0, tab: "settings" as TabId },
          ].map(({ label, count, tab }) => (
            <button
              key={label}
              type="button"
              className={`status-chip ${count ? "status-final" : "status-pending"}`}
              style={{ cursor: "pointer", fontSize: 11 }}
              onClick={() => setActiveTab(tab)}
            >
              {count ? "✓" : "○"} {label} {typeof count === "number" && count > 0 ? `(${count})` : ""}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Navigation — 4 tabs */}
      <div className="filter-tabs" role="tablist" aria-label={t("serviceDetail.tabsLabel")}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            className={`filter-tab ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
            style={{ display: "flex", alignItems: "center", gap: 4 }}
            aria-selected={activeTab === tab.id}
          >
            {tab.icon}
            {ko ? tab.label : tab.labelEn}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "settings" && (
        <div className="stack-lg">
          <ServiceBasicInfo service={service} />
          <ServicePricing service={service} />
        </div>
      )}

      {activeTab === "schema" && <ServiceSchemaEditor service={service} />}

      {activeTab === "execution" && (
        <div className="stack-lg">
          <ServicePipelines service={service} />
          <ServiceDeployment service={service} />
          <div className="panel">
            <TechniqueWeightEditor serviceId={service.id} />
          </div>
        </div>
      )}

      {activeTab === "analytics" && (
        <div className="stack-lg">
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

          {/* Recent Requests */}
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
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog.Root open={showDeleteDialog} onOpenChange={(open) => { if (!open) { setShowDeleteDialog(false); setDeleteConfirmText(""); deleteMut.reset(); } }}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content" style={{ maxWidth: 440 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <div style={{
                width: 40, height: 40, borderRadius: "50%", backgroundColor: "var(--danger-light, #fef2f2)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
              }}>
                <Warning size={22} weight="fill" style={{ color: "var(--danger)" }} />
              </div>
              <Dialog.Title className="dialog-title" style={{ margin: 0 }}>
                {ko ? "서비스 삭제" : "Delete Service"}
              </Dialog.Title>
            </div>

            <div style={{ marginBottom: 16, padding: "12px 14px", borderRadius: 8, backgroundColor: "var(--danger-light, #fef2f2)", border: "1px solid var(--danger-border, #fecaca)" }}>
              <p style={{ fontSize: 13, color: "var(--danger)", fontWeight: 600, marginBottom: 4 }}>
                {ko ? "이 작업은 되돌릴 수 없습니다." : "This action cannot be undone."}
              </p>
              <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                {ko
                  ? "서비스와 관련된 파이프라인, 기법 가중치, 평가자 설정이 모두 삭제됩니다. 이 서비스를 참조하는 분석 요청이 있으면 삭제할 수 없습니다."
                  : "All pipelines, technique weights, and evaluator assignments will be deleted. Deletion is blocked if any requests reference this service."}
              </p>
            </div>

            <p style={{ fontSize: 13, marginBottom: 6 }}>
              {ko
                ? <>확인을 위해 서비스명 <strong>{service.name}</strong>을 입력하세요:</>
                : <>Type <strong>{service.name}</strong> to confirm:</>}
            </p>
            <input
              className="input"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              placeholder={service.name}
              autoFocus
            />

            {deleteMut.isError && (
              <p className="error-text" style={{ marginTop: 8 }}>
                {(deleteMut.error as Error).message}
              </p>
            )}

            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <Dialog.Close asChild>
                <button className="btn btn-secondary">{t("common.cancel")}</button>
              </Dialog.Close>
              <button
                className="btn btn-danger"
                disabled={deleteConfirmText !== service.name || deleteMut.isPending}
                onClick={() => deleteMut.mutate()}
              >
                {deleteMut.isPending ? <span className="spinner" /> : <Trash size={14} />}
                {ko ? " 삭제" : " Delete"}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
