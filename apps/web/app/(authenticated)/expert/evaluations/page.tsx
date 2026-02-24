"use client";

import { useQuery } from "@tanstack/react-query";
import { Stamp, ArrowRight } from "phosphor-react";
import { useRouter } from "next/navigation";
import { listEvaluationQueue, type EvaluationQueueItem } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

export default function EvaluationQueuePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { data, isLoading } = useQuery({
    queryKey: ["evaluation-queue"],
    queryFn: listEvaluationQueue,
    refetchInterval: 15_000,
  });
  const items = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("evaluation.queueTitle")}</h1>
          <p className="page-subtitle">{t("evaluation.queueSubtitle")}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : items.length === 0 ? (
        <div className="panel" style={{ textAlign: "center", padding: 48, color: "var(--muted)" }}>
          <Stamp size={48} style={{ marginBottom: 12, opacity: 0.4 }} />
          <p>{t("evaluation.noItems")}</p>
        </div>
      ) : (
        <div className="stack-md">
          {items.map((item: EvaluationQueueItem) => (
            <button
              key={item.request_id}
              className="panel"
              style={{ cursor: "pointer", textAlign: "left", width: "100%", border: "1px solid var(--border)" }}
              onClick={() => router.push(`/expert/evaluations/${item.request_id}`)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 16 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15 }}>{item.service_display_name}</div>
                  <div style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
                    {t("evaluation.requestId")}: {item.request_id.slice(0, 8)} &middot; {item.case_count} {t("evaluation.caseCount")}
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>
                    {new Date(item.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="status-chip status-pending">{item.request_status}</span>
                  <ArrowRight size={16} />
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
