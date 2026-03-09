"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, DownloadSimple, Printer, File } from "phosphor-react";
import {
  getRequest,
  listCases,
  listCaseFiles,
  getDownloadUrl,
  type CaseRead,
  type CaseFileRead,
} from "@/lib/api";
import { Timeline } from "@/components/timeline";
import { useTranslation } from "@/lib/i18n";
import { SkeletonCards } from "@/components/skeleton";
import { EmptyState } from "@/components/empty-state";
import { Breadcrumb } from "@/components/breadcrumb";

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ReportFiles({ requestId, caseItem }: { requestId: string; caseItem: CaseRead }) {
  const { t } = useTranslation();
  const { data, isLoading } = useQuery({
    queryKey: ["case-files", requestId, caseItem.id],
    queryFn: () => listCaseFiles(requestId, caseItem.id),
  });

  const handleDownload = async (file: CaseFileRead) => {
    const { url } = await getDownloadUrl(requestId, caseItem.id, file.id);
    window.open(url, "_blank");
  };

  const files = data?.items ?? [];

  if (isLoading) return <span className="spinner" />;
  if (files.length === 0) return <p className="muted-text" style={{ fontSize: 13 }}>{t("common.noFiles")}</p>;

  return (
    <div className="stack-sm">
      {files.map((file) => (
        <div key={file.id} className="file-info-card">
          <div className="file-info-card-icon"><File size={20} /></div>
          <div className="file-info-card-body">
            <p className="file-info-card-name">{file.file_name}</p>
            <p className="file-info-card-meta">{file.slot_name} · {formatBytes(file.file_size)}</p>
          </div>
          {file.upload_status === "COMPLETED" && (
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => handleDownload(file)}
              aria-label={`${t("common.download")} ${file.file_name}`}
            >
              <DownloadSimple size={14} />
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";

  const { data: request, isLoading } = useQuery({
    queryKey: ["request", id],
    queryFn: () => getRequest(id),
    enabled: !!id,
  });

  const { data: casesData } = useQuery({
    queryKey: ["request-cases", id],
    queryFn: () => listCases(id),
    enabled: !!id,
  });

  const reportData = (request as any)?.report;
  const cases: CaseRead[] = casesData?.items ?? [];

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadJson = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) return <SkeletonCards count={3} />;
  if (!request) {
    return (
      <EmptyState
        icon={<File size={48} weight="light" />}
        title={t("reports.notFound")}
        actionLabel={t("reports.backToList")}
        onAction={() => router.push("/user/reports")}
      />
    );
  }

  const serviceSnapshot = (request as any).service_snapshot;

  return (
    <div className="stack-lg print-report">
      {/* Navigation - hidden in print */}
      <div className="no-print">
        <Breadcrumb
          items={[
            { label: t("reports.title"), href: "/user/reports" },
            { label: `${serviceSnapshot?.display_name || t("requestDetail.analysisRequest")} #${id.slice(0, 8)}` },
          ]}
        />
      </div>

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("reports.reportTitle")}</h1>
          <p className="page-subtitle">
            {serviceSnapshot?.display_name || t("requestDetail.analysisRequest")} — #{id.slice(0, 8)}
          </p>
        </div>
        <div className="page-header-actions no-print">
          <button className="btn btn-secondary" onClick={handlePrint} aria-label={t("reports.print")}>
            <Printer size={16} /> {t("reports.print")}
          </button>
          {reportData && (
            <button className="btn btn-primary" onClick={handleDownloadJson} aria-label={t("reports.downloadPdf")}>
              <DownloadSimple size={16} /> {t("reports.downloadPdf")}
            </button>
          )}
        </div>
      </div>

      {/* Request Summary */}
      <div className="panel">
        <h3 className="panel-title-mb">{t("reports.requestSummary")}</h3>
        <div className="grid-3">
          <div>
            <p className="detail-label">{t("reports.status")}</p>
            <p className="detail-value">
              <span className={`status-chip status-${request.status.toLowerCase()}`}>
                {t(`status.${request.status}`)}
              </span>
            </p>
          </div>
          <div>
            <p className="detail-label">{t("reports.caseCount")}</p>
            <p className="detail-value">{request.case_count}{locale === "ko" ? "건" : ""}</p>
          </div>
          <div>
            <p className="detail-label">{t("reports.createdDate")}</p>
            <p className="detail-value">{new Date(request.created_at).toLocaleDateString(dateLocale)}</p>
          </div>
        </div>
      </div>

      {/* Progress Timeline */}
      <div className="panel">
        <h3 className="panel-title-mb">{t("requestDetail.progressStatus")}</h3>
        <Timeline currentStatus={request.status} createdAt={request.created_at} updatedAt={request.updated_at} />
      </div>

      {/* Report Data */}
      {reportData ? (
        <div className="panel" style={{ borderLeft: "4px solid var(--success)" }}>
          <h3 className="panel-title-mb">{t("reports.analysisResult")}</h3>
          <div className="stack-md">
            {reportData.summary && (
              <div>
                <p className="detail-label">{t("report.summary")}</p>
                <p className="detail-value" style={{ whiteSpace: "pre-wrap" }}>
                  {typeof reportData.summary === "string" ? reportData.summary : JSON.stringify(reportData.summary, null, 2)}
                </p>
              </div>
            )}
            {reportData.conclusions && (
              <div>
                <p className="detail-label">{t("report.conclusions")}</p>
                <p className="detail-value" style={{ whiteSpace: "pre-wrap" }}>
                  {typeof reportData.conclusions === "string" ? reportData.conclusions : JSON.stringify(reportData.conclusions, null, 2)}
                </p>
              </div>
            )}
            {reportData.generated_at && (
              <div>
                <p className="detail-label">{t("report.generatedAt")}</p>
                <p className="detail-value">{new Date(reportData.generated_at).toLocaleString(dateLocale)}</p>
              </div>
            )}
            {/* Structured data display */}
            {reportData.findings && (
              <div>
                <p className="detail-label">{t("reports.findings")}</p>
                <div className="structured-data">
                  {Array.isArray(reportData.findings) ? (
                    <ul style={{ margin: 0, paddingLeft: 20 }}>
                      {reportData.findings.map((f: string, i: number) => (
                        <li key={i} style={{ marginBottom: 4, fontSize: 14 }}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    <pre className="code-block">{JSON.stringify(reportData.findings, null, 2)}</pre>
                  )}
                </div>
              </div>
            )}
            {reportData.metrics && (
              <div>
                <p className="detail-label">{t("reports.metrics")}</p>
                <div className="stats-grid">
                  {Object.entries(reportData.metrics as Record<string, unknown>).map(([key, val]) => (
                    <div key={key} className="panel" style={{ padding: 12 }}>
                      <p className="detail-label">{key}</p>
                      <p className="detail-value" style={{ fontSize: 18, fontWeight: 700 }}>{String(val)}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="panel">
          <EmptyState
            icon={<File size={48} weight="light" />}
            title={t("reports.noReportYet")}
            description={t("reports.noReportYetDesc")}
          />
        </div>
      )}

      {/* Case Files */}
      {cases.length > 0 && (
        <div className="panel no-print">
          <h3 className="panel-title-mb">{t("requestDetail.casesAndFiles")}</h3>
          <div className="stack-md">
            {cases.map((c) => (
              <div key={c.id}>
                <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>
                  {t("requestDetail.caseLabel")} {c.patient_ref}
                </p>
                <ReportFiles requestId={id} caseItem={c} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
