"use client";

import { useTranslation } from "@/lib/i18n";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  count?: number;
}

export function Skeleton({ width, height = "1rem", borderRadius = 4, count = 1 }: SkeletonProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="skeleton-block"
          style={{
            width: width ?? "100%",
            height,
            borderRadius,
            marginBottom: count > 1 && i < count - 1 ? "0.5rem" : undefined,
          }}
        />
      ))}
    </>
  );
}

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <tr className="skeleton-row">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="table-cell">
          <div className="skeleton-block" style={{ width: `${60 + ((i * 17) % 30)}%` }} />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonTable({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  const { t } = useTranslation();
  return (
    <div className="panel" role="status" aria-label={t("aria.loadingTable")}>
      <table className="data-table">
        <tbody>
          {Array.from({ length: rows }).map((_, i) => (
            <SkeletonRow key={i} cols={cols} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function SkeletonCard() {
  const { t } = useTranslation();
  return (
    <div className="panel skeleton-card" role="status" aria-label={t("aria.loadingCard")} style={{ padding: 20 }}>
      {/* Icon + title row */}
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 16 }}>
        <div className="skeleton-block" style={{ width: 44, height: 44, borderRadius: 10, flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <div className="skeleton-block" style={{ width: "70%", height: "1.125rem", marginBottom: 6 }} />
          <div className="skeleton-block" style={{ width: "40%", height: "0.75rem" }} />
        </div>
      </div>
      {/* Description lines */}
      <div className="skeleton-block" style={{ width: "90%", height: "0.75rem", marginBottom: 6 }} />
      <div className="skeleton-block" style={{ width: "65%", height: "0.75rem", marginBottom: 16 }} />
      {/* Button */}
      <div className="skeleton-block" style={{ width: "100%", height: 36, borderRadius: "var(--radius-sm)" }} />
    </div>
  );
}

export function SkeletonCards({ count = 3 }: { count?: number }) {
  const { t } = useTranslation();
  return (
    <div
      style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}
      role="status"
      aria-label={t("aria.loadingContent")}
    >
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonMetricCards({ count = 3 }: { count?: number }) {
  return (
    <div className="grid-3" role="status" aria-busy="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="metric-card">
          <div className="skeleton-block" style={{ width: 40, height: 40, borderRadius: 10, flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div className="skeleton-block" style={{ width: "50%", height: "0.75rem", marginBottom: 6 }} />
            <div className="skeleton-block" style={{ width: "30%", height: "1.25rem" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
