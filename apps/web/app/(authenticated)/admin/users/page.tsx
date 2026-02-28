"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listUsers, approveExpert, rejectExpert, type UserRead } from "@/lib/api";
import { CaretLeft, CaretRight } from "phosphor-react";
import { useTranslation } from "@/lib/i18n";

type FilterTab = "all" | "SERVICE_USER" | "EXPERT" | "ADMIN" | "PENDING";
const PAGE_SIZE = 20;

export default function AdminUsersPage() {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const [filter, setFilter] = useState<FilterTab>("all");
  const [page, setPage] = useState(0);
  const router = useRouter();

  const FILTER_TABS: Array<{ key: FilterTab; label: string }> = [
    { key: "all", label: t("adminUsers.filterAll") },
    { key: "SERVICE_USER", label: t("adminUsers.filterServiceUser") },
    { key: "EXPERT", label: t("adminUsers.filterExpert") },
    { key: "ADMIN", label: t("adminUsers.filterAdmin") },
    { key: "PENDING", label: t("adminUsers.filterPending") },
  ];
  const queryClient = useQueryClient();

  const params = filter === "PENDING"
    ? { user_type: "EXPERT", expert_status: "PENDING_APPROVAL" }
    : filter !== "all"
    ? { user_type: filter }
    : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", filter, page],
    queryFn: () =>
      listUsers({
        ...params,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const approveMut = useMutation({
    mutationFn: (userId: string) => approveExpert(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const rejectMut = useMutation({
    mutationFn: (userId: string) => rejectExpert(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const users = data?.items ?? [];
  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));

  const handleFilterChange = (key: FilterTab) => {
    setFilter(key);
    setPage(0);
  };

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("adminUsers.title")}</h1>
          <p className="page-subtitle">{t("adminUsers.subtitle").replace("{count}", String(data?.total ?? 0))}</p>
        </div>
      </div>

      <div className="filter-tabs" role="tablist" aria-label={t("adminUsers.title")}>
        {FILTER_TABS.map((tab) => (
          <button type="button" role="tab" aria-selected={filter === tab.key} key={tab.key} className={`filter-tab ${filter === tab.key ? "active" : ""}`} onClick={() => handleFilterChange(tab.key)}>
            {tab.label}
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
                  <th>{t("adminUsers.tableName")}</th>
                  <th>{t("adminUsers.tableEmail")}</th>
                  <th>{t("adminUsers.tableType")}</th>
                  <th>{t("adminUsers.tableStatus")}</th>
                  <th>{t("adminUsers.tableOrg")}</th>
                  <th>{t("adminUsers.tableSignupDate")}</th>
                  <th>{t("adminUsers.tableActions")}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u: UserRead) => (
                  <tr key={u.id} style={{ cursor: "pointer" }} onClick={() => router.push(`/admin/users/${u.id}`)}>
                    <td>{u.display_name || u.username}</td>
                    <td>{u.email || "-"}</td>
                    <td>
                      {u.user_type && (
                        <span className={`user-type-chip user-type-${u.user_type === "SERVICE_USER" ? "service" : u.user_type === "EXPERT" ? "expert" : "admin"}`}>
                          {t(`userType.${u.user_type}` as any) || u.user_type}
                        </span>
                      )}
                    </td>
                    <td>
                      {u.user_type === "EXPERT" && u.expert_status === "PENDING_APPROVAL" && (
                        <span className="status-chip status-qc">{t("adminUsers.statusPending")}</span>
                      )}
                      {u.user_type === "EXPERT" && u.expert_status === "APPROVED" && (
                        <span className="status-chip status-final">{t("adminUsers.statusApproved")}</span>
                      )}
                      {u.user_type === "EXPERT" && u.expert_status === "REJECTED" && (
                        <span className="status-chip status-failed">{t("adminUsers.statusRejected")}</span>
                      )}
                      {!u.is_active && <span className="status-chip status-cancelled">{t("common.inactive")}</span>}
                    </td>
                    <td>{u.institution_name || "-"}</td>
                    <td>{u.created_at ? new Date(u.created_at).toLocaleDateString(dateLocale) : "-"}</td>
                    <td>
                      <div className="action-row" onClick={(e) => e.stopPropagation()}>
                        {u.user_type === "EXPERT" && u.expert_status === "PENDING_APPROVAL" && (
                          <>
                            <button type="button" className="btn btn-sm btn-primary" onClick={() => approveMut.mutate(u.id)} disabled={approveMut.isPending}>
                              {t("common.approve")}
                            </button>
                            <button type="button" className="btn btn-sm btn-danger" onClick={() => rejectMut.mutate(u.id)} disabled={rejectMut.isPending}>
                              {t("common.reject")}
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr><td colSpan={7} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>{t("adminUsers.noUsers")}</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <nav className="pagination" style={{ marginTop: 16 }} aria-label={t("common.pagination")}>
              <button type="button" className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                <CaretLeft size={14} /> {t("common.paginationPrev")}
              </button>
              <span className="pagination-info">{page + 1} / {totalPages}</span>
              <button type="button" className="btn btn-sm btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                {t("common.paginationNext")} <CaretRight size={14} />
              </button>
            </nav>
          )}
        </div>
      )}
    </div>
  );
}
