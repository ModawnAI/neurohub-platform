"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listArtifactsFull, getServicePerformance, approveArtifact, rejectArtifact, type ArtifactRead, type PerformancePoint } from "@/lib/api";
import { apiFetch, type ServiceRead } from "@/lib/api";
import { CaretDown, CaretRight, CheckCircle, XCircle } from "phosphor-react";

type Tab = "artifacts" | "scans" | "performance";

function formatSize(bytes: number | null): string {
  if (bytes == null) return "-";
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(1)} GB`;
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function StatusChip({ status }: { status: string }) {
  const map: Record<string, string> = {
    PENDING_SCAN: "badge-warning", SCANNING: "badge-info", APPROVED: "badge-success",
    REJECTED: "badge-danger", FLAGGED: "badge-orange",
  };
  return <span className={`badge ${map[status] ?? "badge-default"}`}>{status}</span>;
}

function BuildChip({ status }: { status: string | null }) {
  if (!status) return null;
  const map: Record<string, string> = { BUILT: "badge-success", FAILED: "badge-danger", BUILDING: "badge-info", PENDING: "badge-default" };
  return <span className={`badge ${map[status] ?? "badge-default"}`} style={{ marginLeft: 6 }}>🐳 {status}</span>;
}

function ScanBadge({ status }: { status: string }) {
  const map: Record<string, string> = { PASS: "badge-success", WARN: "badge-warning", FAIL: "badge-danger" };
  return <span className={`badge ${map[status] ?? "badge-default"}`}>{status}</span>;
}

function ArtifactCard({ artifact, onApprove, onReject }: { artifact: ArtifactRead; onApprove: (id: string) => void; onReject: (id: string) => void }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <p style={{ fontWeight: 600, fontFamily: "monospace", marginBottom: 4 }}>{artifact.file_name}</p>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <span className="badge badge-default">{artifact.artifact_type}</span>
            <StatusChip status={artifact.status} />
            <BuildChip status={artifact.build_status} />
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{formatSize(artifact.file_size)}</span>
            <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{new Date(artifact.created_at).toLocaleDateString()}</span>
          </div>
          {artifact.review_notes && (
            <p style={{ fontSize: 12, color: "var(--color-text-secondary)", marginTop: 6 }}>Note: {artifact.review_notes}</p>
          )}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-sm btn-secondary" onClick={() => onApprove(artifact.id)}>
            <CheckCircle size={14} /> Approve
          </button>
          <button className="btn btn-sm btn-danger" onClick={() => onReject(artifact.id)}>
            <XCircle size={14} /> Reject
          </button>
        </div>
      </div>
    </div>
  );
}

function ScanExpand({ artifact }: { artifact: ArtifactRead }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const scans = artifact.security_scans ?? [];
  if (scans.length === 0) return <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>No scans for {artifact.file_name}</p>;
  return (
    <div style={{ marginBottom: 16 }}>
      <p style={{ fontWeight: 600, marginBottom: 8, fontFamily: "monospace", fontSize: 13 }}>{artifact.file_name}</p>
      {scans.map((scan) => (
        <div key={scan.id ?? scan.scanner} style={{ marginBottom: 8, borderLeft: "3px solid var(--color-border)", paddingLeft: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontWeight: 600, fontSize: 13 }}>{scan.scanner}</span>
            <ScanBadge status={scan.status} />
            {(scan.findings?.length ?? 0) > 0 && (
              <button className="btn btn-xs btn-secondary" onClick={() => setExpanded(e => ({ ...e, [scan.scanner]: !e[scan.scanner] }))}>
                {expanded[scan.scanner] ? <CaretDown size={12} /> : <CaretRight size={12} />}
                {scan.findings!.length} findings
              </button>
            )}
          </div>
          {expanded[scan.scanner] && scan.findings && (
            <div style={{ marginTop: 8 }}>
              {scan.findings.map((f, i) => (
                <div key={i} style={{ fontSize: 12, padding: "6px 8px", background: "var(--color-surface-secondary)", borderRadius: 4, marginBottom: 4 }}>
                  <span className="badge badge-warning" style={{ marginRight: 6 }}>{f.severity}</span>
                  <strong>{f.rule}</strong> — {f.message}
                  {f.line && <span style={{ color: "var(--color-text-secondary)", marginLeft: 6 }}>line {f.line}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function PerformanceTab({ serviceId }: { serviceId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["service-performance", serviceId],
    queryFn: () => getServicePerformance(serviceId, 90),
  });
  const points = data?.data_points ?? [];
  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (points.length === 0) return (
    <div className="empty-state"><p className="empty-state-text">No performance data yet.</p></div>
  );
  const latest = points[points.length - 1];
  const maxAcc = Math.max(...points.map(p => p.accuracy ?? 0), 0.01);
  return (
    <div className="stack-md">
      <div className="grid-4" style={{ "--grid-cols": 4 } as React.CSSProperties}>
        {[
          { label: "Latest Accuracy", value: latest.accuracy != null ? `${(latest.accuracy * 100).toFixed(1)}%` : "-" },
          { label: "Total Runs", value: latest.total_runs ?? "-" },
          { label: "Expert Approval Rate", value: latest.expert_approval_rate != null ? `${(latest.expert_approval_rate * 100).toFixed(1)}%` : "-" },
          { label: "Evaluations", value: latest.evaluation_count ?? "-" },
        ].map(({ label, value }) => (
          <div key={label} className="card" style={{ padding: "16px 20px", textAlign: "center" }}>
            <p style={{ fontSize: 24, fontWeight: 700 }}>{String(value)}</p>
            <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>{label}</p>
          </div>
        ))}
      </div>
      <div className="card" style={{ padding: 20 }}>
        <p style={{ fontWeight: 600, marginBottom: 12 }}>Accuracy Trend (90 days)</p>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 80 }}>
          {points.map((p, i) => {
            const pct = ((p.accuracy ?? 0) / maxAcc) * 100;
            return (
              <div key={i} title={`${p.metric_date}: ${p.accuracy != null ? (p.accuracy * 100).toFixed(1) + "%" : "-"}`}
                style={{ flex: 1, height: `${pct}%`, background: "var(--primary)", borderRadius: "2px 2px 0 0", minWidth: 4, opacity: 0.8 }} />
            );
          })}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--color-text-secondary)", marginTop: 4 }}>
          <span>{points[0]?.metric_date}</span>
          <span>{points[points.length - 1]?.metric_date}</span>
        </div>
      </div>
    </div>
  );
}

export default function ExpertModelDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>("artifacts");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  const { data: service } = useQuery({
    queryKey: ["service", id],
    queryFn: () => apiFetch<ServiceRead>(`/services/${id}`),
  });

  const { data, isLoading } = useQuery({
    queryKey: ["artifacts", id],
    queryFn: () => listArtifactsFull(id),
  });

  const artifacts = data?.items ?? [];

  const approveMutation = useMutation({
    mutationFn: (artifactId: string) => approveArtifact(artifactId, { trigger_build: true }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["artifacts", id] }),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ artifactId, note }: { artifactId: string; note: string }) =>
      rejectArtifact(artifactId, { review_notes: note }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["artifacts", id] }); setRejectId(null); setRejectNote(""); },
  });

  const TABS: Array<{ key: Tab; label: string }> = [
    { key: "artifacts", label: "Artifacts" },
    { key: "scans", label: "Security Scans" },
    { key: "performance", label: "Performance" },
  ];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{service?.display_name ?? service?.name ?? "Model Detail"}</h1>
          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            {service?.status && <span className={`status-chip status-${service.status.toLowerCase()}`}>{service.status}</span>}
            {service?.version_label && <span className="badge badge-default">v{service.version_label}</span>}
          </div>
        </div>
      </div>

      <div className="filter-tabs">
        {TABS.map(t => (
          <button key={t.key} className={`filter-tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>

      {isLoading && <div className="loading-center"><span className="spinner" /></div>}

      {!isLoading && tab === "artifacts" && (
        artifacts.length === 0 ? (
          <div className="empty-state"><p className="empty-state-text">No artifacts uploaded yet.</p></div>
        ) : (
          <div className="stack-md">
            {artifacts.map(a => (
              <ArtifactCard key={a.id} artifact={a}
                onApprove={(aid) => approveMutation.mutate(aid)}
                onReject={(aid) => { setRejectId(aid); setRejectNote(""); }}
              />
            ))}
          </div>
        )
      )}

      {!isLoading && tab === "scans" && (
        artifacts.length === 0 ? (
          <div className="empty-state"><p className="empty-state-text">No artifacts to scan.</p></div>
        ) : (
          <div className="card" style={{ padding: 20 }}>
            {artifacts.map(a => <ScanExpand key={a.id} artifact={a} />)}
          </div>
        )
      )}

      {tab === "performance" && <PerformanceTab serviceId={id} />}

      {rejectId && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="card" style={{ padding: 24, width: 400 }}>
            <h3 style={{ marginBottom: 12 }}>Reject Artifact</h3>
            <textarea className="input" rows={3} placeholder="Reason for rejection..." value={rejectNote} onChange={e => setRejectNote(e.target.value)} style={{ width: "100%", marginBottom: 12 }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn btn-secondary" onClick={() => setRejectId(null)}>Cancel</button>
              <button className="btn btn-danger" disabled={!rejectNote.trim()} onClick={() => rejectMutation.mutate({ artifactId: rejectId, note: rejectNote })}>
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
