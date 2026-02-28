"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listAllArtifacts, approveArtifact, rejectArtifact, type ArtifactRead } from "@/lib/api";
import { CheckCircle, XCircle } from "phosphor-react";
import { useT } from "@/lib/i18n";

type FilterTab = "all" | "PENDING_SCAN" | "APPROVED" | "REJECTED";

function StatusChip({ status }: { status: string }) {
  const map: Record<string, string> = {
    PENDING_SCAN: "badge-warning", SCANNING: "badge-info", APPROVED: "badge-success",
    REJECTED: "badge-danger", FLAGGED: "badge-orange",
  };
  return <span className={`badge ${map[status] ?? "badge-default"}`}>{status}</span>;
}

function BuildChip({ status }: { status: string | null }) {
  if (!status) return <span style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>—</span>;
  const map: Record<string, string> = { BUILT: "badge-success", FAILED: "badge-danger", BUILDING: "badge-info", PENDING: "badge-default" };
  return <span className={`badge ${map[status] ?? "badge-default"}`}>{status}</span>;
}

function ScanSummary({ scans }: { scans: ArtifactRead["security_scans"] }) {
  const t = useT();
  if (!scans?.length) return <span style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>{t("artifacts.noScans")}</span>;
  const pass = scans.filter(s => s.status === "PASS").length;
  const warn = scans.filter(s => s.status === "WARN").length;
  const fail = scans.filter(s => s.status === "FAIL").length;
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {pass > 0 && <span className="badge badge-success">{pass} {t("artifacts.pass")}</span>}
      {warn > 0 && <span className="badge badge-warning">{warn} {t("artifacts.warn")}</span>}
      {fail > 0 && <span className="badge badge-danger">{fail} {t("artifacts.fail")}</span>}
    </div>
  );
}

export default function AdminModelArtifactsPage() {
  const t = useT();
  const [filter, setFilter] = useState<FilterTab>("all");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["admin-artifacts", filter],
    queryFn: () => listAllArtifacts(filter === "all" ? undefined : filter),
  });

  const approveMutation = useMutation({
    mutationFn: (id: string) => approveArtifact(id, { trigger_build: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-artifacts"] }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) => rejectArtifact(id, { review_notes: note }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["admin-artifacts"] }); setRejectId(null); setRejectNote(""); },
  });

  const artifacts = data?.items ?? [];

  const TABS: Array<{ key: FilterTab; label: string }> = [
    { key: "all", label: t("artifacts.tabAll") },
    { key: "PENDING_SCAN", label: t("artifacts.tabPendingScan") },
    { key: "APPROVED", label: t("artifacts.tabApproved") },
    { key: "REJECTED", label: t("artifacts.tabRejected") },
  ];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("artifacts.title")}</h1>
          <p className="page-subtitle">{t("artifacts.subtitle")}</p>
        </div>
      </div>

      <div className="filter-tabs">
        {TABS.map(t => (
          <button key={t.key} className={`filter-tab ${filter === t.key ? "active" : ""}`} onClick={() => setFilter(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : artifacts.length === 0 ? (
        <div className="empty-state"><p className="empty-state-text">{t("artifacts.noArtifacts")}</p></div>
      ) : (
        <div className="stack-md">
          {artifacts.map((artifact) => (
            <div key={artifact.id} className="card" style={{ padding: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, fontFamily: "monospace", fontSize: 13 }}>{artifact.file_name}</span>
                    <span className="badge badge-default">{artifact.artifact_type}</span>
                    <StatusChip status={artifact.status} />
                  </div>
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, color: "var(--color-text-secondary)" }}>
                    <span>{t("artifacts.build")}: <BuildChip status={artifact.build_status} /></span>
                    <span>{t("artifacts.scans")}: <ScanSummary scans={artifact.security_scans} /></span>
                    <span>{t("artifacts.created")}: {new Date(artifact.created_at).toLocaleDateString()}</span>
                  </div>
                  {artifact.review_notes && (
                    <p style={{ fontSize: 12, marginTop: 6, color: "var(--color-text-secondary)" }}>{t("artifacts.note")} {artifact.review_notes}</p>
                  )}
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <button className="btn btn-sm btn-secondary" disabled={approveMutation.isPending}
                    onClick={() => approveMutation.mutate(artifact.id)}>
                    <CheckCircle size={14} /> {t("artifacts.approve")}
                  </button>
                  <button className="btn btn-sm btn-danger"
                    onClick={() => { setRejectId(artifact.id); setRejectNote(""); }}>
                    <XCircle size={14} /> {t("artifacts.reject")}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {rejectId && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ padding: 24, width: 420 }}>
            <h3 style={{ marginBottom: 12 }}>{t("artifacts.rejectTitle")}</h3>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>{t("artifacts.rejectDesc")}</p>
            <textarea className="input" rows={4} placeholder={t("artifacts.rejectPlaceholder")} value={rejectNote}
              onChange={e => setRejectNote(e.target.value)} style={{ width: "100%", marginBottom: 12 }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn btn-secondary" onClick={() => setRejectId(null)}>{t("common.cancel")}</button>
              <button className="btn btn-danger" disabled={!rejectNote.trim() || rejectMutation.isPending}
                onClick={() => rejectMutation.mutate({ id: rejectId, note: rejectNote })}>
                {t("artifacts.reject")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
