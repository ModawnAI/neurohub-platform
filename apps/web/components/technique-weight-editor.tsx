"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  type ServiceTechniqueWeightRead,
  type TechniqueModuleRead,
  listServiceTechniqueWeights,
  listTechniqueModules,
  bulkSetServiceTechniqueWeights,
} from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useCallback, useEffect, useState } from "react";

interface WeightEntry {
  technique_module_id: string;
  technique_key: string;
  base_weight: number;
  is_required: boolean;
}

export function TechniqueWeightEditor({ serviceId }: { serviceId: string }) {
  const t = useT();
  const queryClient = useQueryClient();

  const { data: weightsData, isLoading: loadingWeights } = useQuery({
    queryKey: ["service-technique-weights", serviceId],
    queryFn: () => listServiceTechniqueWeights(serviceId),
  });

  const { data: techniquesData } = useQuery({
    queryKey: ["techniques"],
    queryFn: () => listTechniqueModules(),
  });

  const [entries, setEntries] = useState<WeightEntry[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (weightsData?.items) {
      setEntries(
        weightsData.items.map((w) => ({
          technique_module_id: w.technique_module_id,
          technique_key: w.technique_key ?? "",
          base_weight: w.base_weight,
          is_required: w.is_required,
        })),
      );
    }
  }, [weightsData]);

  const saveMutation = useMutation({
    mutationFn: (weights: { technique_module_id: string; base_weight: number; is_required: boolean }[]) =>
      bulkSetServiceTechniqueWeights(serviceId, weights),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["service-technique-weights", serviceId] });
      setDirty(false);
    },
  });

  const totalWeight = entries.reduce((sum, e) => sum + e.base_weight, 0);
  const weightWarning = totalWeight > 1.05 || totalWeight < 0.95;

  const updateWeight = useCallback((idx: number, value: number) => {
    setEntries((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx]!, base_weight: Math.round(value * 10000) / 10000 };
      return next;
    });
    setDirty(true);
  }, []);

  const removeEntry = useCallback((idx: number) => {
    setEntries((prev) => prev.filter((_, i) => i !== idx));
    setDirty(true);
  }, []);

  const addTechnique = useCallback(
    (tech: TechniqueModuleRead) => {
      if (entries.some((e) => e.technique_module_id === tech.id)) return;
      setEntries((prev) => [
        ...prev,
        {
          technique_module_id: tech.id,
          technique_key: tech.key,
          base_weight: 0.1,
          is_required: true,
        },
      ]);
      setDirty(true);
    },
    [entries],
  );

  const handleSave = () => {
    saveMutation.mutate(
      entries.map((e) => ({
        technique_module_id: e.technique_module_id,
        base_weight: e.base_weight,
        is_required: e.is_required,
      })),
    );
  };

  if (loadingWeights) return <p>{t("common.loading")}</p>;

  const availableTechniques = (techniquesData?.items ?? []).filter(
    (tech) => !entries.some((e) => e.technique_module_id === tech.id),
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600 }}>기법 프로필 (가중치)</h3>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span
            style={{
              fontSize: "13px",
              color: weightWarning ? "var(--color-red-11)" : "var(--color-gray-11)",
              fontWeight: weightWarning ? 600 : 400,
            }}
          >
            합계: {totalWeight.toFixed(4)}
          </span>
          {dirty && (
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending}
              style={{
                padding: "4px 16px",
                borderRadius: "6px",
                border: "none",
                backgroundColor: "var(--color-blue-9)",
                color: "white",
                cursor: "pointer",
                fontSize: "13px",
              }}
            >
              {saveMutation.isPending ? "저장 중..." : t("common.save")}
            </button>
          )}
        </div>
      </div>

      {entries.length === 0 ? (
        <p style={{ color: "var(--color-gray-11)", fontSize: "14px" }}>
          연결된 분석 기법이 없습니다. 아래에서 기법을 추가하세요.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {entries.map((entry, idx) => (
            <div
              key={entry.technique_module_id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "8px 12px",
                border: "1px solid var(--color-gray-6)",
                borderRadius: "6px",
              }}
            >
              <code style={{ fontSize: "13px", minWidth: "140px" }}>{entry.technique_key}</code>

              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={entry.base_weight}
                onChange={(e) => updateWeight(idx, Number(e.target.value))}
                style={{ flex: 1 }}
              />

              <span style={{ fontSize: "13px", minWidth: "50px", textAlign: "right" }}>
                {(entry.base_weight * 100).toFixed(1)}%
              </span>

              <div
                style={{
                  width: "60px",
                  height: "8px",
                  backgroundColor: "var(--color-gray-4)",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${entry.base_weight * 100}%`,
                    height: "100%",
                    backgroundColor: "var(--color-blue-9)",
                    borderRadius: "4px",
                  }}
                />
              </div>

              <button
                onClick={() => removeEntry(idx)}
                style={{
                  padding: "2px 8px",
                  border: "1px solid var(--color-red-6)",
                  borderRadius: "4px",
                  color: "var(--color-red-11)",
                  backgroundColor: "transparent",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {availableTechniques.length > 0 && (
        <div>
          <p style={{ fontSize: "13px", color: "var(--color-gray-11)", marginBottom: "8px" }}>
            기법 추가:
          </p>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {availableTechniques.map((tech) => (
              <button
                key={tech.id}
                onClick={() => addTechnique(tech)}
                style={{
                  padding: "4px 10px",
                  borderRadius: "6px",
                  border: "1px solid var(--color-gray-6)",
                  backgroundColor: "transparent",
                  cursor: "pointer",
                  fontSize: "12px",
                }}
              >
                + {tech.key}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
