"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, DownloadSimple, File } from "phosphor-react";
import {
  getRequest,
  advanceRequest,
  listCases,
  listCaseFiles,
  getDownloadUrl,
  type RequestStatus,
  type CaseRead,
  type CaseFileRead,
} from "@/lib/api";
import { Timeline } from "@/components/timeline";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

const TRANSITIONS: Record<string, string[]> = {
  CREATED: ["RECEIVING"],
  RECEIVING: ["STAGING"],
  STAGING: ["READY_TO_COMPUTE"],
  READY_TO_COMPUTE: ["COMPUTING"],
  COMPUTING: ["QC", "FAILED"],
  QC: ["REPORTING", "COMPUTING", "FAILED"],
  REPORTING: ["EXPERT_REVIEW", "FINAL"],
  EXPERT_REVIEW: ["FINAL", "REPORTING"],
};


function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AdminCaseFiles({ requestId, caseItem }: { requestId: string; caseItem: CaseRead }) {
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
      alert(t("adminRequests.errorDownloadFailed"));
    }
  };

  const files = filesData?.items ?? [];

  return (
    <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{ background: "none", border: "none", cursor: "pointer", width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", fontSize: 14 }}
      >
        <span><strong>{caseItem.patient_ref}</strong> <span className="muted-text" style={{ fontSize: 12 }}>({caseItem.status})</span></span>
        <span style={{ fontSize: 12, color: "var(--primary)" }}>{expanded ? t("common.collapse") : t("common.viewFiles")}</span>
      </button>
      {expanded && (
        <div style={{ paddingLeft: 16, marginTop: 8 }}>
          {isLoading ? <span className="spinner" /> : files.length === 0 ? (
            <p className="muted-text" style={{ fontSize: 13 }}>{t("common.noFiles")}</p>
          ) : (
            <div className="stack-sm">
              {files.map((file) => (
                <div key={file.id} className="file-info-card">
                  <div className="file-info-card-icon"><File size={20} /></div>
                  <div className="file-info-card-body">
                    <p className="file-info-card-name">{file.filename}</p>
                    <p className="file-info-card-meta">{file.slot} &middot; {formatBytes(file.size_bytes)}</p>
                  </div>
                  {file.status === "COMPLETED" && (
                    <button className="btn btn-sm btn-secondary" onClick={() => handleDownload(file)} title={t("common.download")}>
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

export default function AdminRequestDetailPage() {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const { data: request, isLoading } = useQuery({
    queryKey: ["admin-request", id],
    queryFn: () => getRequest(id),
    enabled: !!id,
  });

  const { data: casesData } = useQuery({
    queryKey: ["request-cases", id],
    queryFn: () => listCases(id),
    enabled: !!id,
  });

  const transitionMut = useMutation({
    mutationFn: (targetStatus: string) => advanceRequest(id, targetStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-request", id] });
      addToast("success", t("toast.transitionSuccess"));
    },
    onError: () => addToast("error", t("toast.transitionError")),
  });

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (!request) return <div className="banner banner-warning">{t("requestDetail.notFound")}</div>;

  const possibleTransitions = TRANSITIONS[request.status] || [];
  const serviceSnapshot = (request as any).service_snapshot;
  const cases: CaseRead[] = casesData?.items ?? [];

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/admin/requests")}>
        <ArrowLeft size={16} /> {t("adminRequests.backToList")}
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">{t("adminRequests.requestDetail")}</h1>
          <p className="page-subtitle">#{id.slice(0, 8)}</p>
        </div>
        <span className={`status-chip status-${request.status.toLowerCase()}`}>
          {t(`status.${request.status}` as any) || request.status}
        </span>
      </div>

      <div className="detail-grid">
        <div className="stack-md">
          <div className="panel">
            <h2 className="panel-title-mb">{t("requestDetail.requestInfo")}</h2>
            <div className="stack-md">
              <div><p className="detail-label">{t("adminRequests.requestId")}</p><p className="detail-value" style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{request.id}</p></div>
              <div><p className="detail-label">{t("requestDetail.service")}</p><p className="detail-value">{serviceSnapshot?.display_name || "-"}</p></div>
              <div><p className="detail-label">{t("requestDetail.caseCount")}</p><p className="detail-value">{request.case_count}{t("common.unitCount")}</p></div>
              <div><p className="detail-label">{t("adminRequests.priority")}</p><p className="detail-value">{request.priority}</p></div>
              <div><p className="detail-label">{t("requestDetail.createdDate")}</p><p className="detail-value">{new Date(request.created_at).toLocaleString(dateLocale)}</p></div>
              {request.updated_at && <div><p className="detail-label">{t("adminRequests.lastModified")}</p><p className="detail-value">{new Date(request.updated_at).toLocaleString(dateLocale)}</p></div>}
            </div>
          </div>

          {/* Case Files */}
          {cases.length > 0 && (
            <div className="panel">
              <h2 className="panel-title-mb">{t("requestDetail.casesAndFiles")}</h2>
              <div className="stack-sm">
                {cases.map((c) => (
                  <AdminCaseFiles key={c.id} requestId={id} caseItem={c} />
                ))}
              </div>
            </div>
          )}

          {possibleTransitions.length > 0 && (
            <div className="panel">
              <h2 className="panel-title-mb">{t("adminRequests.stateTransitions")}</h2>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {possibleTransitions.map((target) => (
                  <button
                    key={target}
                    className={`btn ${target === "FAILED" || target === "CANCELLED" ? "btn-danger" : "btn-primary"}`}
                    onClick={() => transitionMut.mutate(target)}
                    disabled={transitionMut.isPending}
                  >
                    → {t(`status.${target}` as any) || target}
                  </button>
                ))}
              </div>
              {transitionMut.isError && <p className="error-text" style={{ marginTop: 8 }}>{(transitionMut.error as Error).message}</p>}
            </div>
          )}
        </div>

        <div>
          <div className="panel">
            <h2 className="panel-title-mb">{t("requestDetail.progressStatus")}</h2>
            <Timeline currentStatus={request.status as RequestStatus} createdAt={request.created_at} updatedAt={request.updated_at ?? undefined} />
          </div>
        </div>
      </div>
    </div>
  );
}
