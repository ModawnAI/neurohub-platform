"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, DownloadSimple, File, FileText, Brain, Flask, Eye, CheckCircle } from "phosphor-react";
import {
  getRequest,
  cancelRequest,
  confirmRequest,
  listCases,
  listCaseFiles,
  getDownloadUrl,
  getReportDownloadUrl,
  getWatermarkedDownloadUrl,
  fetchPreQCResults,
  overridePreQC,
  type RequestStatus,
  type CaseRead,
  type CaseFileRead,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Timeline } from "@/components/timeline";
import { TechniqueResultsPanel } from "@/components/technique-results-panel";
import { FusionResultsViewer } from "@/components/fusion-results-viewer";
import { PreQCViewer } from "@/components/pre-qc-viewer";
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
      const { url } = await getDownloadUrl(requestId, caseItem.id, file.id);
      window.open(url, "_blank");
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

function PreQCSection({ requestId, caseId }: { requestId: string; caseId: string }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { data, isLoading } = useQuery({
    queryKey: ["pre-qc", requestId, caseId],
    queryFn: () => fetchPreQCResults(requestId, caseId),
  });

  const overrideMut = useMutation({
    mutationFn: () => overridePreQC(requestId, caseId, { reason: "관리자 재정" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pre-qc", requestId, caseId] });
      addToast("success", t("preqc.overrideSuccess"));
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  if (isLoading) return <span className="spinner" />;
  if (!data || data.items.length === 0) return null;

  const isAdmin = user?.roles?.includes("SYSTEM_ADMIN") || user?.roles?.includes("REVIEWER");
  const hasFailures = data.items.some((c) => c.status === "FAIL");

  return (
    <div>
      <PreQCViewer
        checks={data.items}
        canProceed={data.can_proceed}
        failMessages={data.fail_messages}
        warnMessages={data.warn_messages}
      />
      {/* Admin/Reviewer override button per PDF spec */}
      {isAdmin && hasFailures && !data.can_proceed && (
        <button
          className="btn btn-secondary btn-sm"
          style={{ marginTop: 8 }}
          onClick={() => overrideMut.mutate()}
          disabled={overrideMut.isPending}
        >
          {overrideMut.isPending ? <span className="spinner" /> : t("preqc.override")}
        </button>
      )}
    </div>
  );
}

function ViewerConfirmSection({ requestId }: { requestId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const confirmMut = useMutation({
    mutationFn: () => confirmRequest(requestId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["request", requestId] });
      addToast("success", t("preqc.viewerConfirmed"));
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  return (
    <div className="panel" style={{ background: "var(--color-blue-2)", borderColor: "var(--color-blue-6)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Eye size={18} color="var(--color-blue-11)" />
        <h3 className="panel-title" style={{ color: "var(--color-blue-11)", margin: 0 }}>
          {t("preqc.viewerConfirmTitle")}
        </h3>
      </div>
      <p className="muted-text" style={{ fontSize: 13, marginBottom: 12 }}>
        {t("preqc.viewerConfirmDesc")}
      </p>
      <button
        className="btn btn-primary btn-sm"
        onClick={() => confirmMut.mutate()}
        disabled={confirmMut.isPending}
      >
        {confirmMut.isPending ? <span className="spinner" /> : (
          <>
            <CheckCircle size={16} weight="fill" /> {t("preqc.confirmData")}
          </>
        )}
      </button>
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

  const serviceSnapshot = request.service_snapshot as { display_name?: string; name?: string } | null | undefined;
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
          <h1 className="page-title">{serviceSnapshot?.display_name || (t("requestDetail.analysisRequest") as string)}</h1>
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

          {/* Pre-QC Results (shown after STAGING) */}
          {cases.length > 0 && !["CREATED", "RECEIVING"].includes(request.status) && (
            <div className="panel">
              <h3 className="panel-title-mb" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Flask size={18} /> {t("preqc.title")}
              </h3>
              <div className="stack-md">
                {cases.map((c) => (
                  <div key={c.id}>
                    <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>
                      {t("requestDetail.caseLabel")} {c.patient_ref}
                    </p>
                    <PreQCSection requestId={id} caseId={c.id} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Viewer Confirmation (PDF spec step 5: user_confirm → READY_FOR_ANALYSIS) */}
          {request.status === "STAGING" && cases.length > 0 && (
            <ViewerConfirmSection requestId={id} />
          )}

          {/* Technique Runs + Fusion Results (shown when COMPUTING or later) */}
          {["COMPUTING", "QC", "REPORTING", "EXPERT_REVIEW", "FINAL"].includes(request.status) && (
            <>
              <div className="panel">
                <TechniqueResultsPanel requestId={id} runId={id} />
              </div>
              <div className="panel">
                <FusionResultsViewer requestId={id} runId={id} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
