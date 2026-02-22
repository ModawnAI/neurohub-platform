"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listAllRequests, transitionRequest, confirmRequest, submitRequest, type RequestStatus } from "@/lib/api";
import { CaretLeft, CaretRight } from "phosphor-react";

const PAGE_SIZE = 20;

const STATUS_LABELS: Record<RequestStatus, string> = {
  CREATED: "생성됨", RECEIVING: "수신 중", STAGING: "준비 중",
  READY_TO_COMPUTE: "분석 대기", COMPUTING: "분석 중", QC: "품질 검증",
  REPORTING: "보고서 생성", EXPERT_REVIEW: "전문가 검토", FINAL: "완료",
  FAILED: "실패", CANCELLED: "취소됨",
};

const ALL_STATUSES: RequestStatus[] = ["CREATED", "RECEIVING", "STAGING", "READY_TO_COMPUTE", "COMPUTING", "QC", "REPORTING", "EXPERT_REVIEW", "FINAL", "FAILED", "CANCELLED"];

const NEXT_STATUS: Partial<Record<RequestStatus, { target: RequestStatus; label: string }>> = {
  CREATED: { target: "RECEIVING", label: "수신 시작" },
  RECEIVING: { target: "STAGING", label: "준비 완료" },
};

export default function AdminRequestsPage() {
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
          <h1 className="page-title">요청 관리</h1>
          <p className="page-subtitle">시스템 전체 요청을 관리합니다 ({data?.total ?? 0}건)</p>
        </div>
      </div>

      <div className="filter-tabs" style={{ overflowX: "auto" }}>
        <button className={`filter-tab ${filter === "all" ? "active" : ""}`} onClick={() => handleFilterChange("all")}>전체</button>
        {ALL_STATUSES.map((s) => (
          <button key={s} className={`filter-tab ${filter === s ? "active" : ""}`} onClick={() => handleFilterChange(s)}>
            {STATUS_LABELS[s]}
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
                  <th>서비스</th>
                  <th>상태</th>
                  <th>케이스</th>
                  <th>생성일</th>
                  <th>작업</th>
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
                      <td><span className={`status-chip status-${req.status.toLowerCase()}`}>{STATUS_LABELS[req.status]}</span></td>
                      <td>{req.case_count}</td>
                      <td>{new Date(req.created_at).toLocaleDateString("ko-KR")}</td>
                      <td>
                        <div className="action-row" onClick={(e) => e.stopPropagation()}>
                          {next && (
                            <button className="btn btn-sm btn-primary" onClick={() => advanceMut.mutate({ id: req.id, target: next.target })}>
                              {next.label}
                            </button>
                          )}
                          {req.status === "STAGING" && (
                            <button className="btn btn-sm btn-primary" onClick={() => confirmMut.mutate(req.id)}>확정</button>
                          )}
                          {req.status === "READY_TO_COMPUTE" && (
                            <button className="btn btn-sm btn-primary" onClick={() => submitMut.mutate(req.id)}>제출</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
                {requests.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>요청이 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination" style={{ marginTop: 16 }}>
              <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <CaretLeft size={14} /> 이전
              </button>
              <span className="pagination-info">{page + 1} / {totalPages}</span>
              <button className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                다음 <CaretRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
