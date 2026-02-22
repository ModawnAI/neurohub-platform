"use client";

import { useTranslation } from "@/lib/i18n";

export function SkeletonRow({ cols = 5 }: { cols?: number }) {
  return (
    <tr className="skeleton-row">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="table-cell">
          <div className="skeleton-block" style={{ width: `${60 + Math.random() * 30}%` }} />
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
    <div className="panel skeleton-card" role="status" aria-label={t("aria.loadingCard")}>
      <div className="skeleton-block" style={{ width: "60%", height: "1.25rem", marginBottom: "0.75rem" }} />
      <div className="skeleton-block" style={{ width: "40%", height: "1rem", marginBottom: "0.5rem" }} />
      <div className="skeleton-block" style={{ width: "80%", height: "1rem" }} />
    </div>
  );
}

export function SkeletonCards({ count = 3 }: { count?: number }) {
  const { t } = useTranslation();
  return (
    <div className="stats-grid" role="status" aria-label={t("aria.loadingContent")}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
