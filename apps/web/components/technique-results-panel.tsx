"use client";

import { useQuery } from "@tanstack/react-query";
import { type TechniqueRunRead, listTechniqueRuns } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { CheckCircle, XCircle, Clock, Spinner } from "phosphor-react";

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  PENDING: { icon: <Clock size={16} />, color: "var(--color-gray-11)", label: "대기 중" },
  RUNNING: { icon: <Spinner size={16} />, color: "var(--color-blue-11)", label: "실행 중" },
  COMPLETED: { icon: <CheckCircle size={16} weight="fill" />, color: "var(--color-green-11)", label: "완료" },
  FAILED: { icon: <XCircle size={16} weight="fill" />, color: "var(--color-red-11)", label: "실패" },
};

function QcBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  // QC policy from spec: 60+ normal, 40-59 weight reduced, <40 excluded
  const color = score >= 60 ? "var(--color-green-11)" : score >= 40 ? "var(--color-yellow-11)" : "var(--color-red-11)";
  return (
    <span style={{ fontSize: "12px", fontWeight: 600, color }}>
      QC {score.toFixed(1)}
    </span>
  );
}

export function TechniqueResultsPanel({
  requestId,
  runId,
}: {
  requestId: string;
  runId: string;
}) {
  const t = useT();
  const { data, isLoading } = useQuery({
    queryKey: ["technique-runs", requestId, runId],
    queryFn: () => listTechniqueRuns(requestId, runId),
    refetchInterval: 5000,
  });

  const runs = data?.items ?? [];

  if (isLoading) return <p>{t("common.loading")}</p>;
  if (runs.length === 0) return <p style={{ color: "var(--color-gray-11)" }}>{t("techniqueRuns.noRuns")}</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{t("techniqueRuns.title")}</h3>
      {runs.map((run) => (
        <TechniqueRunCard key={run.id} run={run} />
      ))}
    </div>
  );
}

function TechniqueRunCard({ run }: { run: TechniqueRunRead }) {
  const config = (STATUS_CONFIG[run.status] ?? STATUS_CONFIG.PENDING)!;

  return (
    <div
      style={{
        border: "1px solid var(--color-gray-6)",
        borderRadius: "8px",
        padding: "12px 16px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ color: config.color }}>{config.icon}</span>
        <code style={{ fontSize: "13px", fontWeight: 600 }}>{run.technique_key}</code>
        <span style={{ fontSize: "12px", color: config.color }}>{config.label}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <QcBadge score={run.qc_score} />
        {run.error_detail && (
          <span style={{ fontSize: "12px", color: "var(--color-red-11)" }}>
            {run.error_detail.slice(0, 50)}
          </span>
        )}
      </div>
    </div>
  );
}
