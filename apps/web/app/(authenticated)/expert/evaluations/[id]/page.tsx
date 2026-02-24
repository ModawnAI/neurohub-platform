"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, XCircle, ArrowCounterClockwise } from "phosphor-react";
import { getEvaluationDetail, submitEvaluation } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

export default function EvaluationDetailPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [comments, setComments] = useState("");
  const [watermarkText, setWatermarkText] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["evaluation-detail", id],
    queryFn: () => getEvaluationDetail(id),
    enabled: !!id,
  });

  // Auto-populate watermark text
  const serviceName = data?.service_display_name || "";
  const defaultWatermark = `${serviceName} - ${new Date().toLocaleDateString()}`;
  const effectiveWatermark = watermarkText || defaultWatermark;

  const decideMut = useMutation({
    mutationFn: (decision: string) =>
      submitEvaluation(id, {
        decision,
        comments: comments || undefined,
        watermark_text: decision === "APPROVE" ? effectiveWatermark : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evaluation-queue"] });
      queryClient.invalidateQueries({ queryKey: ["evaluation-detail", id] });
      router.push("/expert/evaluations");
    },
  });

  if (isLoading) {
    return <div className="loading-center"><span className="spinner" /></div>;
  }

  if (!data) {
    return <div className="panel" style={{ padding: 24 }}>Not found</div>;
  }

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("evaluation.detailTitle")}</h1>
          <p className="page-subtitle">{data.service_display_name} &middot; {data.request_id.slice(0, 8)}</p>
        </div>
        <span className={`status-chip ${data.request_status === "QC" ? "status-pending" : "status-final"}`}>
          {data.request_status}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Left: Files & History */}
        <div className="stack-md">
          <div className="panel">
            <div className="panel-header">{t("evaluation.filesAndData")}</div>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Slot</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.files.map((f: Record<string, unknown>) => (
                    <tr key={f.id as string}>
                      <td className="mono-cell">{f.filename as string}</td>
                      <td>{f.slot as string}</td>
                      <td><span className="status-chip status-final">{f.status as string}</span></td>
                    </tr>
                  ))}
                  {data.files.length === 0 && (
                    <tr><td colSpan={3} style={{ textAlign: "center", color: "var(--muted)" }}>No files</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">{t("evaluation.previousEvaluations")}</div>
            {data.evaluations.length === 0 ? (
              <p style={{ padding: 16, color: "var(--muted)" }}>{t("evaluation.noPrevious")}</p>
            ) : (
              <div className="stack-sm" style={{ padding: 16 }}>
                {data.evaluations.map((ev) => (
                  <div key={ev.id} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span className={`status-chip ${ev.decision === "APPROVE" ? "status-final" : ev.decision === "REJECT" ? "status-cancelled" : "status-pending"}`}>
                        {ev.decision}
                      </span>
                      <span style={{ fontSize: 12, color: "var(--muted)" }}>{new Date(ev.created_at).toLocaleString()}</span>
                    </div>
                    {ev.comments && <p style={{ marginTop: 8, fontSize: 14 }}>{ev.comments}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Decision Form */}
        <div className="panel">
          <div className="panel-header">{t("evaluation.decisionForm")}</div>
          <div className="stack-md" style={{ padding: 16 }}>
            {data.request_status !== "QC" && (
              <p className="error-text">{t("evaluation.notQcStatus")}</p>
            )}

            <label className="field">
              {t("evaluation.comments")}
              <textarea
                className="textarea"
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder={t("evaluation.commentsPlaceholder")}
                rows={4}
              />
            </label>

            <label className="field">
              {t("evaluation.watermarkText")}
              <input
                className="input"
                value={watermarkText}
                onChange={(e) => setWatermarkText(e.target.value)}
                placeholder={defaultWatermark}
              />
              <span style={{ fontSize: 12, color: "var(--muted)" }}>{t("evaluation.watermarkHint")}</span>
            </label>

            {decideMut.isError && (
              <p className="error-text">{(decideMut.error as Error).message}</p>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 8 }}>
              <button
                className="btn btn-primary"
                onClick={() => decideMut.mutate("APPROVE")}
                disabled={decideMut.isPending || data.request_status !== "QC"}
              >
                <CheckCircle size={16} /> {t("evaluation.approve")}
              </button>
              <span style={{ fontSize: 12, color: "var(--muted)", marginLeft: 4 }}>
                {t("evaluation.approveDescription")}
              </span>

              <button
                className="btn btn-secondary"
                onClick={() => decideMut.mutate("REVISION_NEEDED")}
                disabled={decideMut.isPending || data.request_status !== "QC"}
              >
                <ArrowCounterClockwise size={16} /> {t("evaluation.revisionNeeded")}
              </button>
              <span style={{ fontSize: 12, color: "var(--muted)", marginLeft: 4 }}>
                {t("evaluation.revisionDescription")}
              </span>

              <button
                className="btn btn-danger"
                onClick={() => decideMut.mutate("REJECT")}
                disabled={decideMut.isPending || data.request_status !== "QC"}
              >
                <XCircle size={16} /> {t("evaluation.reject")}
              </button>
              <span style={{ fontSize: 12, color: "var(--muted)", marginLeft: 4 }}>
                {t("evaluation.rejectDescription")}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
