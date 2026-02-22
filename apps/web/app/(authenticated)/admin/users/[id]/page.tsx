"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUser, approveExpert, rejectExpert } from "@/lib/api";
import { UserTypeChip } from "@/components/user-type-chip";
import { ArrowLeft } from "phosphor-react";
import Link from "next/link";

const EXPERT_STATUS_LABELS: Record<string, string> = {
  PENDING_APPROVAL: "승인 대기",
  APPROVED: "승인됨",
  REJECTED: "거절됨",
};

export default function AdminUserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery({
    queryKey: ["admin-user", id],
    queryFn: () => getUser(id),
    enabled: !!id,
  });

  const approveMut = useMutation({
    mutationFn: () => approveExpert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-user", id] }),
  });

  const rejectMut = useMutation({
    mutationFn: () => rejectExpert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-user", id] }),
  });

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (!user) return <div className="banner banner-warning">사용자를 찾을 수 없습니다.</div>;

  const actionPending = approveMut.isPending || rejectMut.isPending;

  return (
    <div className="stack-lg">
      <Link href="/admin/users" className="back-link">
        <ArrowLeft size={16} /> 사용자 목록으로
      </Link>

      <div className="page-header">
        <h1 className="page-title">{user.display_name || user.username}</h1>
        <UserTypeChip userType={user.user_type} />
      </div>

      <div className="detail-grid">
        <div className="stack-md">
          <div className="panel">
            <h2 className="panel-title-mb">사용자 정보</h2>
            <div className="stack-md">
              <div><p className="detail-label">ID</p><p className="detail-value" style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{user.id}</p></div>
              <div><p className="detail-label">사용자명</p><p className="detail-value">{user.username}</p></div>
              <div><p className="detail-label">이메일</p><p className="detail-value">{user.email || "—"}</p></div>
              <div><p className="detail-label">표시 이름</p><p className="detail-value">{user.display_name || "—"}</p></div>
              <div><p className="detail-label">기관</p><p className="detail-value">{user.institution_name || "—"}</p></div>
              <div><p className="detail-label">활성 상태</p><p className="detail-value">{user.is_active ? "활성" : "비활성"}</p></div>
              <div><p className="detail-label">온보딩</p><p className="detail-value">{user.onboarding_completed ? "완료" : "미완료"}</p></div>
              <div><p className="detail-label">가입일</p><p className="detail-value">{user.created_at ? new Date(user.created_at).toLocaleString("ko-KR") : "—"}</p></div>
              {user.last_login_at && <div><p className="detail-label">최근 로그인</p><p className="detail-value">{new Date(user.last_login_at).toLocaleString("ko-KR")}</p></div>}
            </div>
          </div>

          {user.user_type === "EXPERT" && (
            <div className="panel">
              <h2 className="panel-title-mb">전문가 정보</h2>
              <div className="stack-md">
                <div><p className="detail-label">전문 분야</p><p className="detail-value">{user.specialization || "—"}</p></div>
                <div>
                  <p className="detail-label">승인 상태</p>
                  <p className="detail-value">
                    {EXPERT_STATUS_LABELS[user.expert_status || ""] || user.expert_status || "—"}
                  </p>
                </div>
              </div>

              {user.expert_status === "PENDING_APPROVAL" && (
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1.5rem" }}>
                  <button className="btn btn-primary" onClick={() => approveMut.mutate()} disabled={actionPending}>
                    {approveMut.isPending ? "처리 중..." : "전문가 승인"}
                  </button>
                  <button className="btn btn-danger" onClick={() => rejectMut.mutate()} disabled={actionPending}>
                    {rejectMut.isPending ? "처리 중..." : "승인 거절"}
                  </button>
                </div>
              )}
              {approveMut.isError && <p className="error-text" style={{ marginTop: 8 }}>{(approveMut.error as Error).message}</p>}
              {rejectMut.isError && <p className="error-text" style={{ marginTop: 8 }}>{(rejectMut.error as Error).message}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
