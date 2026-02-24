"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { MagnifyingGlass, DownloadSimple, Funnel, CaretLeft, CaretRight } from "phosphor-react";
import { listRequests, type RequestRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { SkeletonTable } from "@/components/skeleton";
import { EmptyState } from "@/components/empty-state";

type StatusFilter = "all" | "FINAL" | "EXPERT_REVIEW" | "REPORTING";
const PAGE_SIZE = 10;

export default function UserReportsPage() {
  const router = useRouter();
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(0);
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["requests"],
    queryFn: listRequests,
  });

  const REPORTABLE_STATUSES = ["FINAL", "EXPERT_REVIEW", "REPORTING"];

  const filtered = (data?.items ?? []).filter((r: RequestRead) => {
    if (!REPORTABLE_STATUSES.includes(r.status) && statusFilter === "all") {
      return r.status === "FINAL";
    }
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (statusFilter === "all" && !REPORTABLE_STATUSES.includes(r.status)) return false;
    if (search && !r.id.toLowerCase().includes(search.toLowerCase())) return false;
    if (dateFrom && new Date(r.created_at) < new Date(dateFrom)) return false;
    if (dateTo && new Date(r.created_at) > new Date(`${dateTo}T23:59:59`)) return false;
    return true;
  });

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleFilterChange = (status: StatusFilter) => {
    setStatusFilter(status);
    setPage(0);
  };

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("reports.title")}</h1>
          <p className="page-subtitle">{t("reports.subtitle")}</p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={() => setShowFilters(!showFilters)}
          aria-expanded={showFilters}
          aria-controls="report-filters"
        >
          <Funnel size={16} /> {t("reports.filters")}
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="panel" id="report-filters" role="search" aria-label={t("reports.filterLabel")}>
          <div className="form-grid" style={{ gap: "1rem" }}>
            <label className="field">
              {t("reports.searchById")}
              <div style={{ position: "relative" }}>
                <MagnifyingGlass size={16} style={{ position: "absolute", left: 10, top: 10, color: "var(--muted)" }} />
                <input
                  className="input"
                  style={{ paddingLeft: 32 }}
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                  placeholder={t("reports.searchPlaceholder")}
                />
              </div>
            </label>
            <label className="field">
              {t("reports.dateFrom")}
              <input className="input" type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(0); }} />
            </label>
            <label className="field">
              {t("reports.dateTo")}
              <input className="input" type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(0); }} />
            </label>
          </div>
        </div>
      )}

      {/* Status tabs */}
      <div className="filter-tabs" role="tablist" aria-label={t("reports.statusFilter")}>
        {([
          { key: "all" as StatusFilter, label: t("reports.filterAll") },
          { key: "FINAL" as StatusFilter, label: t("reports.filterCompleted") },
          { key: "EXPERT_REVIEW" as StatusFilter, label: t("reports.filterReview") },
          { key: "REPORTING" as StatusFilter, label: t("reports.filterGenerating") },
        ]).map((tab) => (
          <button
            key={tab.key}
            role="tab"
            className={`filter-tab ${statusFilter === tab.key ? "active" : ""}`}
            onClick={() => handleFilterChange(tab.key)}
            aria-selected={statusFilter === tab.key}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {isLoading ? (
        <SkeletonTable rows={5} cols={5} />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<DownloadSimple size={48} weight="light" />}
          title={t("reports.noReports")}
          description={t("reports.noReportsDesc")}
        />
      ) : (
        <>
          {/* Desktop table */}
          <div className="panel hide-mobile">
            <div className="table-wrap">
              <table className="table" aria-label={t("reports.tableLabel")}>
                <thead>
                  <tr>
                    <th scope="col">{t("reports.tableId")}</th>
                    <th scope="col">{t("reports.tableStatus")}</th>
                    <th scope="col">{t("reports.tableCases")}</th>
                    <th scope="col">{t("reports.tableDate")}</th>
                    <th scope="col">{t("reports.tableActions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {paged.map((req: RequestRead) => (
                    <tr key={req.id}>
                      <td className="mono-cell">{req.id.slice(0, 8)}</td>
                      <td>
                        <span className={`status-chip status-${req.status.toLowerCase()}`}>
                          {t(`status.${req.status}`)}
                        </span>
                      </td>
                      <td>{req.case_count}{locale === "ko" ? "건" : ""}</td>
                      <td>{new Date(req.created_at).toLocaleDateString(dateLocale)}</td>
                      <td>
                        <button
                          className="btn btn-sm btn-primary"
                          onClick={() => router.push(`/user/reports/${req.id}`)}
                          aria-label={`${t("reports.viewReport")} ${req.id.slice(0, 8)}`}
                        >
                          {t("reports.viewReport")}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile cards */}
          <div className="show-mobile stack-md">
            {paged.map((req: RequestRead) => (
              <button
                key={req.id}
                className="request-card"
                onClick={() => router.push(`/user/reports/${req.id}`)}
                type="button"
                aria-label={`${t("reports.viewReport")} ${req.id.slice(0, 8)}`}
              >
                <div className="request-card-body">
                  <p className="request-card-title">#{req.id.slice(0, 8)}</p>
                  <p className="request-card-meta">
                    <span className={`status-chip status-${req.status.toLowerCase()}`}>
                      {t(`status.${req.status}`)}
                    </span>
                    <span>{req.case_count}{locale === "ko" ? "건" : " cases"}</span>
                    <span>{new Date(req.created_at).toLocaleDateString(dateLocale)}</span>
                  </p>
                </div>
              </button>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="btn btn-sm btn-secondary"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                aria-label={t("common.paginationPrev")}
              >
                <CaretLeft size={14} /> {t("common.paginationPrev")}
              </button>
              <span className="pagination-info" aria-live="polite">{page + 1} / {totalPages}</span>
              <button
                className="btn btn-sm btn-secondary"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
                aria-label={t("common.paginationNext")}
              >
                {t("common.paginationNext")} <CaretRight size={14} />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
