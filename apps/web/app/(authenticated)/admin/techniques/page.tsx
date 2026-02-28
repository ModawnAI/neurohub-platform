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
  PET: "var(--color-orange-9)",
  MRI: "var(--color-blue-9)",
  EEG: "var(--color-green-9)",
  MEG: "var(--color-purple-9)",
  fMRI: "var(--color-cyan-9)",
  SPECT: "var(--color-red-9)",
};

function ModalityBadge({ modality }: { modality: string }) {
  const bg = MODALITY_COLORS[modality] ?? "var(--color-gray-9)";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "4px",
        backgroundColor: bg,
        color: "white",
        fontSize: "12px",
        fontWeight: 600,
      }}
    >
      {modality}
    </span>
  );
}

function StatusChip({ status }: { status: string }) {
  const isActive = status === "ACTIVE";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "4px",
        backgroundColor: isActive ? "var(--color-green-3)" : "var(--color-gray-3)",
        color: isActive ? "var(--color-green-11)" : "var(--color-gray-11)",
        fontSize: "12px",
      }}
    >
      {isActive ? "활성" : "비활성"}
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
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: 700 }}>{t("techniques.title")}</h1>
        <span style={{ color: "var(--color-gray-11)", fontSize: "14px" }}>
          {t("common.total")} {data?.total ?? 0}
        </span>
      </div>

      <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
        <button
          onClick={() => setFilterModality("")}
          style={{
            padding: "4px 12px",
            borderRadius: "6px",
            border: "1px solid var(--color-gray-6)",
            backgroundColor: !filterModality ? "var(--color-gray-3)" : "transparent",
            cursor: "pointer",
            fontSize: "13px",
          }}
        >
          전체
        </button>
        {modalities.map((mod) => (
          <button
            key={mod}
            onClick={() => setFilterModality(mod)}
            style={{
              padding: "4px 12px",
              borderRadius: "6px",
              border: "1px solid var(--color-gray-6)",
              backgroundColor: filterModality === mod ? "var(--color-gray-3)" : "transparent",
              cursor: "pointer",
              fontSize: "13px",
            }}
          >
            {mod}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p>{t("common.loading")}</p>
      ) : techniques.length === 0 ? (
        <p style={{ color: "var(--color-gray-11)" }}>{t("techniques.noTechniques")}</p>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: "16px",
          }}
        >
          {techniques.map((tech) => (
            <TechniqueCard
              key={tech.id}
              technique={tech}
              onDeprecate={() => deprecateMutation.mutate(tech.id)}
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
}: {
  technique: TechniqueModuleRead;
  onDeprecate: () => void;
}) {
  const gpu = (technique.resource_requirements as Record<string, unknown>)?.gpu;
  const memGb = (technique.resource_requirements as Record<string, unknown>)?.memory_gb;

  return (
    <div
      style={{
        border: "1px solid var(--color-gray-6)",
        borderRadius: "8px",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <code style={{ fontSize: "14px", fontWeight: 600 }}>{technique.key}</code>
        <StatusChip status={technique.status} />
      </div>

      <div style={{ fontSize: "15px" }}>{technique.title_ko}</div>
      <div style={{ fontSize: "13px", color: "var(--color-gray-11)" }}>{technique.title_en}</div>

      <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "4px" }}>
        <ModalityBadge modality={technique.modality} />
        <span style={{ fontSize: "12px", color: "var(--color-gray-11)" }}>
          {technique.category}
        </span>
      </div>

      <div style={{ fontSize: "12px", color: "var(--color-gray-11)", marginTop: "4px" }}>
        <code>{technique.docker_image}</code>
      </div>

      <div style={{ display: "flex", gap: "12px", fontSize: "12px", color: "var(--color-gray-11)" }}>
        <span>v{technique.version}</span>
        {gpu !== undefined && <span>GPU: {gpu ? "필요" : "불필요"}</span>}
        {memGb !== undefined && <span>{String(memGb)}GB RAM</span>}
      </div>

      {technique.status === "ACTIVE" && (
        <button
          onClick={onDeprecate}
          style={{
            marginTop: "8px",
            padding: "4px 12px",
            borderRadius: "6px",
            border: "1px solid var(--color-red-6)",
            color: "var(--color-red-11)",
            backgroundColor: "transparent",
            cursor: "pointer",
            fontSize: "12px",
            alignSelf: "flex-end",
          }}
        >
          비활성화
        </button>
      )}
    </div>
  );
}
