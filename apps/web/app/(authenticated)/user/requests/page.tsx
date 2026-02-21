"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listRequests, type RequestStatus } from "@/lib/api";
import { RequestCard } from "@/components/request-card";

type FilterTab = "all" | "in_progress" | "completed" | "failed";

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
  const router = useRouter();
  const { data, isLoading } = useQuery({ queryKey: ["requests"], queryFn: listRequests });

  const requests = (data?.items ?? []).filter((r) => matchFilter(r.status, filter));

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
            onClick={() => setFilter(tab.key)}
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
        <div className="stack-md">
          {requests.map((req) => (
            <RequestCard key={req.id} request={req} onClick={() => router.push(`/user/requests/${req.id}`)} />
          ))}
        </div>
      )}
    </div>
  );
}
