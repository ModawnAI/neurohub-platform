"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listAllArtifacts, approveArtifact, rejectArtifact, type ArtifactRead } from "@/lib/api";
import { CheckCircle, XCircle } from "phosphor-react";

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
  if (!scans?.length) return <span style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>No scans</span>;
  const pass = scans.filter(s => s.status === "PASS").length;
  const warn = scans.filter(s => s.status === "WARN").length;
  const fail = scans.filter(s => s.status === "FAIL").length;
  return (
    <div style={{ display: "flex", gap: 4 }}>
      {pass > 0 && <span className="badge badge-success">{pass} pass</span>}
      {warn > 0 && <span className="badge badge-warning">{warn} warn</span>}
      {fail > 0 && <span className="badge badge-danger">{fail} fail</span>}
    </div>
  );
}

export default function AdminModelArtifactsPage() {
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
    { key: "all", label: "All" },
    { key: "PENDING_SCAN", label: "Pending Scan" },
    { key: "APPROVED", label: "Approved" },
    { key: "REJECTED", label: "Rejected" },
  ];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">Model Artifacts</h1>
          <p className="page-subtitle">Review and approve AI model artifacts submitted by experts.</p>
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
        <div className="empty-state"><p className="empty-state-text">No artifacts found.</p></div>
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
                    <span>Build: <BuildChip status={artifact.build_status} /></span>
                    <span>Scans: <ScanSummary scans={artifact.security_scans} /></span>
                    <span>Created: {new Date(artifact.created_at).toLocaleDateString()}</span>
                  </div>
                  {artifact.review_notes && (
                    <p style={{ fontSize: 12, marginTop: 6, color: "var(--color-text-secondary)" }}>Note: {artifact.review_notes}</p>
                  )}
                </div>
                <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                  <button className="btn btn-sm btn-secondary" disabled={approveMutation.isPending}
                    onClick={() => approveMutation.mutate(artifact.id)}>
                    <CheckCircle size={14} /> Approve
                  </button>
                  <button className="btn btn-sm btn-danger"
                    onClick={() => { setRejectId(artifact.id); setRejectNote(""); }}>
                    <XCircle size={14} /> Reject
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
            <h3 style={{ marginBottom: 12 }}>Reject Artifact</h3>
            <p style={{ fontSize: 13, color: "var(--color-text-secondary)", marginBottom: 12 }}>Provide a reason for rejection. This will be visible to the submitter.</p>
            <textarea className="input" rows={4} placeholder="Reason for rejection..." value={rejectNote}
              onChange={e => setRejectNote(e.target.value)} style={{ width: "100%", marginBottom: 12 }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn btn-secondary" onClick={() => setRejectId(null)}>Cancel</button>
              <button className="btn btn-danger" disabled={!rejectNote.trim() || rejectMutation.isPending}
                onClick={() => rejectMutation.mutate({ id: rejectId, note: rejectNote })}>
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
