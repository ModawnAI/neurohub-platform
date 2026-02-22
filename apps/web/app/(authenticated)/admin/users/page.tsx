"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { listUsers, approveExpert, rejectExpert, type UserRead } from "@/lib/api";
import { CaretLeft, CaretRight } from "phosphor-react";

type FilterTab = "all" | "SERVICE_USER" | "EXPERT" | "ADMIN" | "PENDING";
const PAGE_SIZE = 20;

const FILTER_TABS: Array<{ key: FilterTab; label: string }> = [
  { key: "all", label: "전체" },
  { key: "SERVICE_USER", label: "서비스 사용자" },
  { key: "EXPERT", label: "전문가" },
  { key: "ADMIN", label: "관리자" },
  { key: "PENDING", label: "승인 대기" },
];

const USER_TYPE_LABELS: Record<string, string> = {
  SERVICE_USER: "서비스 사용자",
  EXPERT: "전문가",
  ADMIN: "관리자",
};

export default function AdminUsersPage() {
  const [filter, setFilter] = useState<FilterTab>("all");
  const [page, setPage] = useState(0);
  const router = useRouter();
  const queryClient = useQueryClient();

  const params = filter === "PENDING"
    ? { user_type: "EXPERT", expert_status: "PENDING_APPROVAL" }
    : filter !== "all"
    ? { user_type: filter }
    : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", filter],
    queryFn: () => listUsers(params),
  });

  const approveMut = useMutation({
    mutationFn: (userId: string) => approveExpert(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const rejectMut = useMutation({
    mutationFn: (userId: string) => rejectExpert(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const allUsers = data?.items ?? [];
  const totalPages = Math.max(1, Math.ceil(allUsers.length / PAGE_SIZE));
  const users = allUsers.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleFilterChange = (key: FilterTab) => {
    setFilter(key);
    setPage(0);
  };

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">사용자 관리</h1>
          <p className="page-subtitle">시스템 사용자를 관리합니다 ({data?.total ?? 0}명)</p>
        </div>
      </div>

      <div className="filter-tabs">
        {FILTER_TABS.map((tab) => (
          <button key={tab.key} className={`filter-tab ${filter === tab.key ? "active" : ""}`} onClick={() => handleFilterChange(tab.key)}>
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
                  <th>이름</th>
                  <th>이메일</th>
                  <th>유형</th>
                  <th>상태</th>
                  <th>기관</th>
                  <th>가입일</th>
                  <th>작업</th>
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
                          {USER_TYPE_LABELS[u.user_type] || u.user_type}
                        </span>
                      )}
                    </td>
                    <td>
                      {u.user_type === "EXPERT" && u.expert_status === "PENDING_APPROVAL" && (
                        <span className="status-chip status-qc">승인 대기</span>
                      )}
                      {u.user_type === "EXPERT" && u.expert_status === "APPROVED" && (
                        <span className="status-chip status-final">승인됨</span>
                      )}
                      {u.user_type === "EXPERT" && u.expert_status === "REJECTED" && (
                        <span className="status-chip status-failed">거부됨</span>
                      )}
                      {!u.is_active && <span className="status-chip status-cancelled">비활성</span>}
                    </td>
                    <td>{u.institution_name || "-"}</td>
                    <td>{u.created_at ? new Date(u.created_at).toLocaleDateString("ko-KR") : "-"}</td>
                    <td>
                      <div className="action-row" onClick={(e) => e.stopPropagation()}>
                        {u.user_type === "EXPERT" && u.expert_status === "PENDING_APPROVAL" && (
                          <>
                            <button className="btn btn-sm btn-primary" onClick={() => approveMut.mutate(u.id)} disabled={approveMut.isPending}>
                              승인
                            </button>
                            <button className="btn btn-sm btn-danger" onClick={() => rejectMut.mutate(u.id)} disabled={rejectMut.isPending}>
                              거부
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr><td colSpan={7} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>사용자가 없습니다.</td></tr>
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
