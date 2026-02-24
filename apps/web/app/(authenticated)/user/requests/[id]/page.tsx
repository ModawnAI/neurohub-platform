"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, DownloadSimple, File, FileText } from "phosphor-react";
import {
  getRequest,
  cancelRequest,
  listCases,
  listCaseFiles,
  getDownloadUrl,
  getReportDownloadUrl,
  getWatermarkedDownloadUrl,
  type RequestStatus,
  type CaseRead,
  type CaseFileRead,
} from "@/lib/api";
import { Timeline } from "@/components/timeline";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

const CANCELLABLE: RequestStatus[] = ["CREATED", "RECEIVING", "STAGING", "READY_TO_COMPUTE"];

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function CaseFilesSection({ requestId, caseItem }: { requestId: string; caseItem: CaseRead }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const { data: filesData, isLoading } = useQuery({
    queryKey: ["case-files", requestId, caseItem.id],
    queryFn: () => listCaseFiles(requestId, caseItem.id),
    enabled: expanded,
  });

  const handleDownload = async (file: CaseFileRead) => {
    try {
      const { download_url } = await getDownloadUrl(requestId, caseItem.id, file.id);
      window.open(download_url, "_blank");
    } catch {
      alert(t("requestDetail.errorDownloadUrl"));
    }
  };

  const files = filesData?.items ?? [];

  return (
    <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          background: "none", border: "none", cursor: "pointer", width: "100%",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "8px 0", fontSize: 14,
        }}
      >
        <span>
          <strong>{t("requestDetail.caseLabel")}</strong> {caseItem.patient_ref}{" "}
          <span className="muted-text" style={{ fontSize: 12 }}>({caseItem.status})</span>
        </span>
        <span style={{ fontSize: 12, color: "var(--primary)" }}>{expanded ? t("common.collapse") : t("common.viewFiles")}</span>
      </button>

      {expanded && (
        <div style={{ paddingLeft: 16, marginTop: 8 }}>
          {isLoading ? (
            <span className="spinner" />
          ) : files.length === 0 ? (
            <p className="muted-text" style={{ fontSize: 13 }}>{t("requestDetail.noFilesUploaded")}</p>
          ) : (
            <div className="stack-sm">
              {files.map((file) => (
                <div key={file.id} className="file-info-card">
                  <div className="file-info-card-icon"><File size={20} /></div>
                  <div className="file-info-card-body">
                    <p className="file-info-card-name">{file.file_name}</p>
                    <p className="file-info-card-meta">{file.slot_name} &middot; {formatBytes(file.file_size)}</p>
                  </div>
                  {file.upload_status === "COMPLETED" && (
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleDownload(file)}
                      title={t("requestDetail.download")}
                    >
                      <DownloadSimple size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function UserRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, locale } = useTranslation();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);

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

  const cancelMut = useMutation({
    mutationFn: () => cancelRequest(id, cancelReason || t("apiError.confirmedFromWeb")),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["request", id] });
      setShowCancel(false);
      addToast("success", t("toast.transitionSuccess"));
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (!request) return <div className="empty-state"><p className="empty-state-text">{t("requestDetail.notFound")}</p></div>;

  const serviceSnapshot = request.service_snapshot;
  const reportData = request.report;
  const canCancel = CANCELLABLE.includes(request.status);
  const cases: CaseRead[] = casesData?.items ?? [];

  const handleDownloadReport = () => {
    if (!reportData) return;
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-${id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/user/requests")}>
        <ArrowLeft size={16} /> {t("requestDetail.backToRequests")}
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">{serviceSnapshot?.display_name || t("requestDetail.analysisRequest")}</h1>
          <p className="page-subtitle">{t("requestDetail.requestNumber")}{id.slice(0, 8)}</p>
        </div>
        <span className={`status-chip status-${request.status.toLowerCase()}`}>
          {t(`status.${request.status}`)}
        </span>
      </div>

      <div className="detail-grid">
        <div className="panel">
          <h3 className="panel-title-mb">{t("requestDetail.progressStatus")}</h3>
          <Timeline currentStatus={request.status} createdAt={request.created_at} updatedAt={request.updated_at} />
        </div>

        <div className="stack-md">
          <div className="panel">
            <h3 className="panel-title-mb">{t("requestDetail.requestInfo")}</h3>
            <div className="stack-md">
              <div>
                <p className="detail-label">{t("requestDetail.service")}</p>
                <p className="detail-value">{serviceSnapshot?.display_name || "-"}</p>
              </div>
              <div>
                <p className="detail-label">{t("requestDetail.caseCount")}</p>
                <p className="detail-value">{request.case_count}{locale === "ko" ? "건" : ` ${request.case_count === 1 ? "case" : "cases"}`}</p>
              </div>
              <div>
                <p className="detail-label">{t("requestDetail.createdDate")}</p>
                <p className="detail-value">{new Date(request.created_at).toLocaleString(locale === "ko" ? "ko-KR" : "en-US")}</p>
              </div>
              {request.cancel_reason && (
                <div>
                  <p className="detail-label">{t("requestDetail.cancelReason")}</p>
                  <p className="detail-value">{request.cancel_reason}</p>
                </div>
              )}
            </div>
          </div>

          {/* Case Files Section */}
          {cases.length > 0 && (
            <div className="panel">
              <h3 className="panel-title-mb">{t("requestDetail.casesAndFiles")}</h3>
              <div className="stack-sm">
                {cases.map((c) => (
                  <CaseFilesSection key={c.id} requestId={id} caseItem={c} />
                ))}
              </div>
            </div>
          )}

          {request.status === "FINAL" && (
            <div className="panel" style={{ background: "var(--success-light)", borderColor: "#86efac" }}>
              <h3 className="panel-title" style={{ marginBottom: 8, color: "var(--success)" }}>{t("requestDetail.analysisComplete")}</h3>
              <p className="muted-text">{t("requestDetail.analysisCompleteMsg")}</p>
              {reportData ? (
                <div style={{ marginTop: 12 }}>
                  <div className="stack-sm" style={{ fontSize: 13, marginBottom: 12 }}>
                    {reportData.summary && (
                      <div>
                        <p className="detail-label">{t("report.summary")}</p>
                        <p className="detail-value">{typeof reportData.summary === "string" ? reportData.summary : JSON.stringify(reportData.summary)}</p>
                      </div>
                    )}
                    {reportData.generated_at && (
                      <div>
                        <p className="detail-label">{t("report.generatedAt")}</p>
                        <p className="detail-value">{new Date(reportData.generated_at).toLocaleString(locale === "ko" ? "ko-KR" : "en-US")}</p>
                      </div>
                    )}
                    {reportData.conclusions && (
                      <div>
                        <p className="detail-label">{t("report.conclusions")}</p>
                        <p className="detail-value">{typeof reportData.conclusions === "string" ? reportData.conclusions : JSON.stringify(reportData.conclusions)}</p>
                      </div>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={async () => {
                        try {
                          const { download_url } = await getReportDownloadUrl(id);
                          window.open(download_url, "_blank");
                        } catch {
                          handleDownloadReport();
                        }
                      }}
                    >
                      <FileText size={16} /> {t("download.reportPdf")}
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={async () => {
                        try {
                          const { download_url } = await getWatermarkedDownloadUrl(id);
                          window.open(download_url, "_blank");
                        } catch {
                          addToast("error", t("download.noWatermarked"));
                        }
                      }}
                    >
                      <DownloadSimple size={16} /> {t("download.watermarkedFile")}
                    </button>
                    <button className="btn btn-secondary btn-sm" onClick={handleDownloadReport}>
                      <DownloadSimple size={16} /> {t("report.downloadJson")}
                    </button>
                  </div>
                </div>
              ) : (
                <p className="muted-text" style={{ marginTop: 8 }}>{t("report.noReport")}</p>
              )}
            </div>
          )}

          {canCancel && !showCancel && (
            <button className="btn btn-danger" onClick={() => setShowCancel(true)}>
              {t("requestDetail.cancelRequest")}
            </button>
          )}

          {showCancel && (
            <div className="panel">
              <label className="field">
                {t("requestDetail.cancelReasonLabel")}
                <textarea
                  className="textarea"
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder={t("requestDetail.cancelReasonPlaceholder")}
                  rows={3}
                />
              </label>
              <div className="action-row" style={{ marginTop: 12 }}>
                <button className="btn btn-danger btn-sm" onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}>
                  {cancelMut.isPending ? <span className="spinner" /> : t("requestDetail.confirmCancel")}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => setShowCancel(false)}>{t("common.close")}</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
