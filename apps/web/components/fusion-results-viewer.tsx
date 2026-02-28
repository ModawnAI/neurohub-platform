"use client";

import { useQuery } from "@tanstack/react-query";
import { type FusionResultRead, getFusionResult } from "@/lib/api";
import { useT } from "@/lib/i18n";

function ConfidenceGauge({ score }: { score: number }) {
  // QC policy from spec: 60+ normal, 40-59 weight reduced, <40 excluded
  const color = score >= 60 ? "var(--color-green-9)" : score >= 40 ? "var(--color-yellow-9)" : "var(--color-red-9)";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "4px" }}>
      <div
        style={{
          width: "80px",
          height: "80px",
          borderRadius: "50%",
          border: `4px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "20px",
          fontWeight: 700,
          color,
        }}
      >
        {score.toFixed(0)}
      </div>
      <span style={{ fontSize: "12px", color: "var(--color-gray-11)" }}>신뢰도</span>
    </div>
  );
}

function ConcordanceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px" }}>
        <span>일치도</span>
        <span>{pct}%</span>
      </div>
      <div style={{ height: "8px", backgroundColor: "var(--color-gray-4)", borderRadius: "4px", overflow: "hidden" }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            backgroundColor: pct >= 80 ? "var(--color-green-9)" : pct >= 50 ? "var(--color-yellow-9)" : "var(--color-red-9)",
            borderRadius: "4px",
          }}
        />
      </div>
    </div>
  );
}

function ResultSection({ title, data }: { title: string; data: Record<string, number> | undefined }) {
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div>
      <h5 style={{ fontSize: "13px", fontWeight: 600, marginBottom: "6px", color: "var(--color-gray-11)" }}>{title}</h5>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: "6px" }}>
        {Object.entries(data).map(([key, value]) => (
          <div
            key={key}
            style={{
              padding: "6px 8px",
              border: "1px solid var(--color-gray-6)",
              borderRadius: "6px",
              fontSize: "12px",
            }}
          >
            <div style={{ color: "var(--color-gray-11)", fontSize: "11px" }}>{key}</div>
            <div style={{ fontWeight: 600 }}>{typeof value === "number" ? value.toFixed(4) : String(value)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FusionResultsViewer({
  requestId,
  runId,
}: {
  requestId: string;
  runId: string;
}) {
  const t = useT();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["fusion-result", requestId, runId],
    queryFn: () => getFusionResult(requestId, runId),
    retry: false,
  });

  if (isLoading) return <p>{t("common.loading")}</p>;
  if (isError || !data) return <p style={{ color: "var(--color-gray-11)" }}>{t("fusion.noResult")}</p>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{t("fusion.title")}</h3>
        {data.fusion_engine && (
          <span style={{ fontSize: "11px", color: "var(--color-gray-11)", padding: "2px 8px", borderRadius: "4px", backgroundColor: "var(--color-gray-3)" }}>
            {data.fusion_engine} v{data.fusion_version}
          </span>
        )}
      </div>

      <div style={{ display: "flex", gap: "24px", alignItems: "flex-start" }}>
        <ConfidenceGauge score={data.confidence_score} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "8px" }}>
          <ConcordanceBar score={data.concordance_score} />
          {data.qc_summary && (
            <div style={{ display: "flex", gap: "16px", fontSize: "12px", color: "var(--color-gray-11)" }}>
              <span>평균 QC: <strong>{data.qc_summary.mean_qc.toFixed(1)}</strong></span>
              <span>최소 QC: <strong>{data.qc_summary.min_qc.toFixed(1)}</strong></span>
            </div>
          )}
        </div>
      </div>

      <div>
        <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>{t("fusion.includedModules")}</h4>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {data.included_modules.map((mod) => (
            <span
              key={mod}
              style={{
                padding: "2px 10px",
                borderRadius: "12px",
                backgroundColor: "var(--color-green-3)",
                color: "var(--color-green-11)",
                fontSize: "12px",
              }}
            >
              {mod}
            </span>
          ))}
        </div>
      </div>

      {data.excluded_modules.length > 0 && (
        <div>
          <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>{t("fusion.excludedModules")}</h4>
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {data.excluded_modules.map((ex) => (
              <span
                key={ex.module}
                style={{
                  padding: "2px 10px",
                  borderRadius: "12px",
                  backgroundColor: "var(--color-red-3)",
                  color: "var(--color-red-11)",
                  fontSize: "12px",
                }}
                title={`${ex.reason} (QC: ${ex.qc_score})`}
              >
                {ex.module}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Results sections from PDF spec: probabilities, roi_scores, composite_indices */}
      {data.results && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h4 style={{ fontSize: "14px", fontWeight: 600 }}>{t("fusion.results")}</h4>
          <ResultSection title="확률 지도 (Probabilities)" data={data.results.probabilities} />
          <ResultSection title="ROI 점수 (ROI Scores)" data={data.results.roi_scores} />
          <ResultSection title="복합 지표 (Composite Indices)" data={data.results.composite_indices} />
        </div>
      )}

      {/* Probability map paths (NIfTI viewer links) */}
      {data.probability_maps && Object.keys(data.probability_maps).length > 0 && (
        <div>
          <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>확률 맵 파일</h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            {Object.entries(data.probability_maps).map(([name, path]) => (
              <div key={name} style={{ fontSize: "12px", display: "flex", gap: "8px", alignItems: "center" }}>
                <code style={{ color: "var(--color-blue-11)" }}>{name}</code>
                <span style={{ color: "var(--color-gray-11)" }}>{path}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
