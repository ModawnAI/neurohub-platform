"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listAllRequests, transitionRequest, confirmRequest, submitRequest, type RequestStatus } from "@/lib/api";
import { CaretLeft, CaretRight } from "phosphor-react";
import { useT } from "@/lib/i18n";

const PAGE_SIZE = 20;

const ALL_STATUSES: RequestStatus[] = ["CREATED", "RECEIVING", "STAGING", "READY_TO_COMPUTE", "COMPUTING", "QC", "REPORTING", "EXPERT_REVIEW", "FINAL", "FAILED", "CANCELLED"];

const NEXT_STATUS: Partial<Record<RequestStatus, { target: RequestStatus; labelKey: "adminRequests.startReceiving" | "adminRequests.stagingComplete" }>> = {
  CREATED: { target: "RECEIVING", labelKey: "adminRequests.startReceiving" },
  RECEIVING: { target: "STAGING", labelKey: "adminRequests.stagingComplete" },
};

export default function AdminRequestsPage() {
  const t = useT();
  const [filter, setFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["admin-requests", filter],
    queryFn: () => listAllRequests(filter === "all" ? undefined : filter),
  });

  const advanceMut = useMutation({
    mutationFn: ({ id, target }: { id: string; target: RequestStatus }) => transitionRequest(id, target),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-requests"] }),
  });

  const confirmMut = useMutation({
    mutationFn: (id: string) => confirmRequest(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-requests"] }),
  });

  const submitMut = useMutation({
    mutationFn: (id: string) => submitRequest(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-requests"] }),
  });

  const allRequests = data?.items ?? [];
  const totalPages = Math.max(1, Math.ceil(allRequests.length / PAGE_SIZE));
  const requests = allRequests.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleFilterChange = (f: string) => {
    setFilter(f);
    setPage(0);
  };

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("adminRequests.title")}</h1>
          <p className="page-subtitle">{t("adminRequests.subtitle").replace("{count}", String(data?.total ?? 0))}</p>
        </div>
      </div>

      <div className="filter-tabs" style={{ overflowX: "auto" }}>
        <button className={`filter-tab ${filter === "all" ? "active" : ""}`} onClick={() => handleFilterChange("all")}>{t("adminRequests.filterAll")}</button>
        {ALL_STATUSES.map((s) => (
          <button key={s} className={`filter-tab ${filter === s ? "active" : ""}`} onClick={() => handleFilterChange(s)}>
            {t(`status.${s}` as any)}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : (
        <div className="panel">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>{t("requestDetail.service")}</th>
                  <th>{t("adminUsers.tableStatus")}</th>
                  <th>{t("requestDetail.caseCount")}</th>
                  <th>{t("requestDetail.createdDate")}</th>
                  <th>{t("adminUsers.tableActions")}</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((req) => {
                  const snapshot = (req as any).service_snapshot;
                  const next = NEXT_STATUS[req.status];
                  return (
                    <tr
                      key={req.id}
                      style={{ cursor: "pointer" }}
                      onClick={() => router.push(`/admin/requests/${req.id}`)}
                    >
                      <td className="mono-cell">{req.id.slice(0, 8)}</td>
                      <td>{snapshot?.display_name || "-"}</td>
                      <td><span className={`status-chip status-${req.status.toLowerCase()}`}>{t(`status.${req.status}` as any)}</span></td>
                      <td>{req.case_count}</td>
                      <td>{new Date(req.created_at).toLocaleDateString("ko-KR")}</td>
                      <td>
                        <div className="action-row" onClick={(e) => e.stopPropagation()}>
                          {next && (
                            <button className="btn btn-sm btn-primary" onClick={() => advanceMut.mutate({ id: req.id, target: next.target })}>
                              {t(next.labelKey)}
                            </button>
                          )}
                          {req.status === "STAGING" && (
                            <button className="btn btn-sm btn-primary" onClick={() => confirmMut.mutate(req.id)}>{t("common.confirm")}</button>
                          )}
                          {req.status === "READY_TO_COMPUTE" && (
                            <button className="btn btn-sm btn-primary" onClick={() => submitMut.mutate(req.id)}>{t("common.confirm")}</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {requests.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>{t("adminRequests.noRequests")}</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination" style={{ marginTop: 16 }}>
              <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <CaretLeft size={14} /> {t("common.paginationPrev")}
              </button>
              <span className="pagination-info">{page + 1} / {totalPages}</span>
              <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                {t("common.paginationNext")} <CaretRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
