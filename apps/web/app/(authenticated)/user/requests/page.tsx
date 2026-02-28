"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listRequests, type RequestStatus } from "@/lib/api";
import { RequestCard } from "@/components/request-card";
import { CaretLeft, CaretRight } from "phosphor-react";
import { useT } from "@/lib/i18n";

type FilterTab = "all" | "in_progress" | "completed" | "failed";
const PAGE_SIZE = 10;

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
  const t = useT();
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
          <h1 className="page-title">{t("userRequests.title")}</h1>
          <p className="page-subtitle">{t("userRequests.subtitle")}</p>
        </div>
        <button className="btn btn-primary" onClick={() => router.push("/user/new-request")}>
          {t("userRequests.newRequest")}
        </button>
      </div>

      <div className="filter-tabs" role="tablist" aria-label={t("userRequests.title")}>
        {([
          { key: "all" as FilterTab, label: t("userRequests.filterAll") },
          { key: "in_progress" as FilterTab, label: t("userRequests.filterInProgress") },
          { key: "completed" as FilterTab, label: t("userRequests.filterCompleted") },
          { key: "failed" as FilterTab, label: t("userRequests.filterFailedCanceled") },
        ]).map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            className={`filter-tab ${filter === tab.key ? "active" : ""}`}
            onClick={() => handleFilterChange(tab.key)}
            aria-selected={filter === tab.key}
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
            {filter === "all" ? t("userRequests.emptyAll") : t("userRequests.emptyFiltered")}
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
            <nav className="pagination" aria-label={t("common.pagination")}>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                <CaretLeft size={14} /> {t("common.paginationPrev")}
              </button>
              <span className="pagination-info">{page + 1} / {totalPages}</span>
              <button
                type="button"
                className="btn btn-sm btn-secondary"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                {t("common.paginationNext")} <CaretRight size={14} />
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}
