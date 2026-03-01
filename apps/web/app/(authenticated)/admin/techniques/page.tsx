"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  type TechniqueModuleRead,
  listTechniqueModules,
  deprecateTechniqueModule,
} from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useState } from "react";

const MODALITY_COLORS: Record<string, string> = {
  PET: "#ea580c",
  MRI: "#2563eb",
  EEG: "#16a34a",
  MEG: "#9333ea",
  fMRI: "#0891b2",
  SPECT: "#dc2626",
  PSG: "#ca8a04",
};

function ModalityBadge({ modality }: { modality: string }) {
  const bg = MODALITY_COLORS[modality] ?? "var(--muted)";
  return (
    <span className="status-chip" style={{ backgroundColor: bg, color: "white", fontWeight: 600 }}>
      {modality}
    </span>
  );
}

function StatusChip({ status, t }: { status: string; t: (key: string) => string }) {
  const isActive = status === "ACTIVE";
  return (
    <span className={`status-chip ${isActive ? "status-final" : "status-cancelled"}`}>
      {isActive ? t("techniques.active") : t("techniques.deprecated")}
    </span>
  );
}

export default function TechniquesPage() {
  const t = useT();
  const queryClient = useQueryClient();
  const [filterModality, setFilterModality] = useState<string>("");

  const { data, isLoading } = useQuery({
    queryKey: ["techniques", filterModality],
    queryFn: () =>
      listTechniqueModules(filterModality ? { modality: filterModality } : undefined),
  });

  const deprecateMutation = useMutation({
    mutationFn: deprecateTechniqueModule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["techniques"] }),
  });

  const techniques = data?.items ?? [];
  const modalities = [...new Set(techniques.map((t) => t.modality))].sort();

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("techniques.title")}</h1>
          <p className="page-subtitle">{t("common.total")} {data?.total ?? 0}</p>
        </div>
      </div>

      <div className="filter-tabs">
        <button
          className={`filter-tab ${!filterModality ? "active" : ""}`}
          onClick={() => setFilterModality("")}
        >
          {t("adminRequests.filterAll")}
        </button>
        {modalities.map((mod) => (
          <button
            key={mod}
            className={`filter-tab ${filterModality === mod ? "active" : ""}`}
            onClick={() => setFilterModality(mod)}
          >
            {mod}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : techniques.length === 0 ? (
        <div className="banner banner-info">{t("techniques.noTechniques")}</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "16px" }}>
          {techniques.map((tech) => (
            <TechniqueCard
              key={tech.id}
              technique={tech}
              onDeprecate={() => deprecateMutation.mutate(tech.id)}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TechniqueCard({
  technique,
  onDeprecate,
  t,
}: {
  technique: TechniqueModuleRead;
  onDeprecate: () => void;
  t: (key: string) => string;
}) {
  const gpu = (technique.resource_requirements as Record<string, unknown>)?.gpu;
  const memGb = (technique.resource_requirements as Record<string, unknown>)?.memory_gb;

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      {/* Header: key + status */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <code style={{ fontSize: "14px", fontWeight: 700, color: "var(--text)" }}>{technique.key}</code>
        <StatusChip status={technique.status} t={t} />
      </div>

      {/* Titles */}
      <div>
        <p style={{ fontSize: "15px", fontWeight: 600, margin: 0 }}>{technique.title_ko}</p>
        <p className="muted-text" style={{ fontSize: "13px", marginTop: "2px" }}>{technique.title_en}</p>
      </div>

      {/* Modality + Category */}
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <ModalityBadge modality={technique.modality} />
        <span className="muted-text" style={{ fontSize: "12px" }}>{technique.category}</span>
      </div>

      {/* Docker image */}
      <div style={{ padding: "6px 10px", background: "var(--surface-2)", borderRadius: "var(--radius-sm)", fontSize: "12px", fontFamily: "monospace" }}>
        {technique.docker_image}
      </div>

      {/* Resource info */}
      <div style={{ display: "flex", gap: "12px", fontSize: "12px", flexWrap: "wrap" }}>
        <span className="muted-text" style={{ fontWeight: 600 }}>v{technique.version}</span>
        {gpu !== undefined && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: gpu ? "var(--success)" : "var(--muted)", display: "inline-block" }} />
            <span className="muted-text">GPU: {gpu ? t("techniques.gpuRequired" as any) : t("techniques.gpuNotRequired" as any)}</span>
          </span>
        )}
        {memGb !== undefined && (
          <span className="muted-text">{String(memGb)}GB RAM</span>
        )}
      </div>

      {/* Deprecate action */}
      {technique.status === "ACTIVE" && (
        <div style={{ marginTop: "4px", display: "flex", justifyContent: "flex-end" }}>
          <button className="btn btn-danger btn-sm" onClick={onDeprecate}>
            {t("techniques.deprecate")}
          </button>
        </div>
      )}
    </div>
  );
}
