"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listRequests, type RequestStatus } from "@/lib/api";
import { RequestCard } from "@/components/request-card";
import { CaretLeft, CaretRight } from "phosphor-react";

type FilterTab = "all" | "in_progress" | "completed" | "failed";
const PAGE_SIZE = 10;

const FILTER_TABS: Array<{ key: FilterTab; label: string }> = [
  { key: "all", label: "전체" },
  { key: "in_progress", label: "진행 중" },
  { key: "completed", label: "완료" },
  { key: "failed", label: "실패/취소" },
];

function matchFilter(status: RequestStatus, filter: FilterTab): boolean {
  if (filter === "all") return true;
  if (filter === "in_progress") return !["FINAL", "FAILED", "CANCELLED"].includes(status);
  if (filter === "completed") return status === "FINAL";
  return status === "FAILED" || status === "CANCELLED";
}

export default function UserRequestsPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [page, setPage] = useState(0);
  const router = useRouter();
  const { data, isLoading } = useQuery({ queryKey: ["requests"], queryFn: listRequests });

  const allFiltered = (data?.items ?? []).filter((r) => matchFilter(r.status, filter));
  const totalPages = Math.max(1, Math.ceil(allFiltered.length / PAGE_SIZE));
  const requests = allFiltered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleFilterChange = (key: FilterTab) => {
    setFilter(key);
    setPage(0);
  };

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">내 요청</h1>
          <p className="page-subtitle">제출한 AI 분석 요청 목록입니다</p>
        </div>
        <button className="btn btn-primary" onClick={() => router.push("/user/new-request")}>
          새 요청
        </button>
      </div>

      <div className="filter-tabs">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            className={`filter-tab ${filter === tab.key ? "active" : ""}`}
            onClick={() => handleFilterChange(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : requests.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-text">
            {filter === "all" ? "아직 요청이 없습니다." : "해당 상태의 요청이 없습니다."}
          </p>
        </div>
      ) : (
        <>
          <div className="stack-md">
            {requests.map((req) => (
              <RequestCard key={req.id} request={req} onClick={() => router.push(`/user/requests/${req.id}`)} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-sm btn-secondary"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                <CaretLeft size={14} /> 이전
              </button>
              <span className="pagination-info">{page + 1} / {totalPages}</span>
              <button
                className="btn btn-sm btn-secondary"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                다음 <CaretRight size={14} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
