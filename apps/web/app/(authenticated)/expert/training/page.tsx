"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAllTrainingJobs, type TrainingJobFull } from "@/lib/api";
import { CaretDown, CaretRight, Robot } from "phosphor-react";

function StatusChip({ status }: { status: string }) {
  const map: Record<string, { cls: string; pulse?: boolean }> = {
    PENDING: { cls: "badge-default" },
    PREPARING: { cls: "badge-info" },
    TRAINING: { cls: "badge-purple", pulse: true },
    EVALUATING: { cls: "badge-warning" },
    COMPLETED: { cls: "badge-success" },
    FAILED: { cls: "badge-danger" },
  };
  const cfg = map[status] ?? { cls: "badge-default" };
  return (
    <span className={`badge ${cfg.cls}`} style={cfg.pulse ? { animation: "pulse 1.5s infinite" } : {}}>
      {status}
    </span>
  );
}

function duration(start: string | null, end: string | null): string {
  if (!start) return "—";
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const diff = Math.floor((e - s) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
}

function DetailPanel({ job }: { job: TrainingJobFull }) {
  const params = job.hyperparameters ?? {};
  const metrics = job.training_metrics ?? {};
  const epochs = (metrics as { epochs?: Array<{ epoch: number; train_loss: number; val_loss: number; accuracy: number }> }).epochs ?? [];

  return (
    <div style={{ padding: "16px 20px", background: "var(--color-surface-secondary)", borderTop: "1px solid var(--color-border)" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div>
          <p style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Hyperparameters</p>
          {Object.keys(params).length === 0 ? (
            <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>No hyperparameters</p>
          ) : (
            <div className="stack-xs">
              {Object.entries(params).map(([k, v]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, padding: "4px 0", borderBottom: "1px solid var(--color-border)" }}>
                  <span style={{ color: "var(--color-text-secondary)" }}>{k}</span>
                  <span style={{ fontWeight: 600 }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <p style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Training Metrics</p>
          {epochs.length > 0 ? (
            <div style={{ maxHeight: 200, overflowY: "auto" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, fontSize: 11, fontWeight: 700, background: "var(--color-border)", padding: "4px 8px", borderRadius: "4px 4px 0 0" }}>
                <span>Epoch</span><span>Train Loss</span><span>Val Loss</span><span>Accuracy</span>
              </div>
              {epochs.map((e) => (
                <div key={e.epoch} style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", fontSize: 12, padding: "4px 8px", borderBottom: "1px solid var(--color-border)" }}>
                  <span>{e.epoch}</span>
                  <span>{e.train_loss.toFixed(4)}</span>
                  <span>{e.val_loss.toFixed(4)}</span>
                  <span>{(e.accuracy * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>No epoch data available</p>
          )}
        </div>
      </div>

      {job.error_detail && (
        <div style={{ marginTop: 12, padding: 12, background: "#fee2e2", borderRadius: 6, fontSize: 12, color: "#991b1b" }}>
          <strong>Error:</strong> {job.error_detail}
        </div>
      )}
    </div>
  );
}

export default function ExpertTrainingPage() {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const { data, isLoading } = useQuery({
    queryKey: ["all-training-jobs"],
    queryFn: listAllTrainingJobs,
  });

  const jobs = data?.items ?? [];

  const toggle = (id: string) => setExpanded(e => ({ ...e, [id]: !e[id] }));

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Robot size={26} /> Training Jobs
          </h1>
          <p className="page-subtitle">Monitor model training jobs and review metrics.</p>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : jobs.length === 0 ? (
        <div className="empty-state">
          <Robot size={40} style={{ marginBottom: 12, opacity: 0.3 }} />
          <p className="empty-state-text">No training jobs found.</p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {jobs.map((job, idx) => (
            <div key={job.id} style={{ borderBottom: idx < jobs.length - 1 ? "1px solid var(--color-border)" : undefined }}>
              <div
                style={{ display: "grid", gridTemplateColumns: "24px 1fr 120px 120px 80px 160px 80px", gap: 12, alignItems: "center", padding: "14px 16px", cursor: "pointer" }}
                onClick={() => toggle(job.id)}
              >
                <span style={{ color: "var(--color-text-secondary)" }}>
                  {expanded[job.id] ? <CaretDown size={14} /> : <CaretRight size={14} />}
                </span>
                <div>
                  <p style={{ fontWeight: 600, fontSize: 14 }}>{job.service_id}</p>
                  <p style={{ fontSize: 11, color: "var(--color-text-secondary)", fontFamily: "monospace" }}>{job.id.slice(0, 8)}…</p>
                </div>
                <span className="badge badge-default" style={{ justifySelf: "start" }}>{job.trigger_type}</span>
                <StatusChip status={job.status} />
                <span style={{ fontSize: 13 }}>{job.feedback_count}</span>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                  {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                </span>
                <span style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                  {duration(job.started_at, job.completed_at)}
                </span>
              </div>
              {expanded[job.id] && <DetailPanel job={job} />}
            </div>
          ))}

          <div style={{ display: "grid", gridTemplateColumns: "24px 1fr 120px 120px 80px 160px 80px", gap: 12, padding: "8px 16px", background: "var(--color-surface-secondary)", fontSize: 11, fontWeight: 700, color: "var(--color-text-secondary)" }}>
            <span />
            <span>Service / Job ID</span>
            <span>Trigger</span>
            <span>Status</span>
            <span>Feedback</span>
            <span>Started</span>
            <span>Duration</span>
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .badge-purple { background: #ede9fe; color: #5b21b6; }
      `}</style>
    </div>
  );
}
