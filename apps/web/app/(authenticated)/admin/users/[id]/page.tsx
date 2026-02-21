"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiFetch, approveExpert, rejectExpert } from "@/lib/api";
import { UserTypeChip } from "@/components/user-type-chip";
import { ArrowLeft } from "phosphor-react";
import Link from "next/link";

interface UserDetail {
  id: string;
  username: string;
  display_name: string | null;
  email: string | null;
  user_type: string | null;
  is_active: boolean;
  institution_id: string | null;
  institution_name: string | null;
  expert_status: string | null;
  specialization: string | null;
  onboarding_completed: boolean;
  created_at: string;
}

const EXPERT_STATUS_LABELS: Record<string, string> = {
  PENDING_APPROVAL: "승인 대기",
  APPROVED: "승인됨",
  REJECTED: "거절됨",
};

export default function AdminUserDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [user, setUser] = useState<UserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchUser = async () => {
    try {
      const data = await apiFetch<UserDetail>(`/users/${id}`);
      setUser(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUser(); }, [id]);

  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await approveExpert(id);
      await fetchUser();
    } catch {
      // ignore
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    setActionLoading(true);
    try {
      await rejectExpert(id);
      await fetchUser();
    } catch {
      // ignore
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) return <div className="loading-center"><div className="spinner" /></div>;
  if (!user) return <div className="banner banner-warning">사용자를 찾을 수 없습니다.</div>;

  return (
    <div>
      <Link href="/admin/users" className="back-link">
        <ArrowLeft size={16} /> 사용자 목록으로
      </Link>

      <div className="detail-header">
        <h1 className="page-title">{user.display_name || user.username}</h1>
        <UserTypeChip userType={user.user_type} />
      </div>

      <div className="detail-grid">
        <div>
          <div className="card" style={{ marginBottom: "1.5rem" }}>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>사용자 정보</h2>
            <div className="info-rows">
              <div className="info-row"><span className="info-label">ID</span><span className="info-value" style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{user.id}</span></div>
              <div className="info-row"><span className="info-label">사용자명</span><span className="info-value">{user.username}</span></div>
              <div className="info-row"><span className="info-label">이메일</span><span className="info-value">{user.email || "—"}</span></div>
              <div className="info-row"><span className="info-label">표시 이름</span><span className="info-value">{user.display_name || "—"}</span></div>
              <div className="info-row"><span className="info-label">기관</span><span className="info-value">{user.institution_name || "—"}</span></div>
              <div className="info-row"><span className="info-label">활성 상태</span><span className="info-value">{user.is_active ? "활성" : "비활성"}</span></div>
              <div className="info-row"><span className="info-label">온보딩</span><span className="info-value">{user.onboarding_completed ? "완료" : "미완료"}</span></div>
              <div className="info-row"><span className="info-label">가입일</span><span className="info-value">{new Date(user.created_at).toLocaleString("ko-KR")}</span></div>
            </div>
          </div>

          {user.user_type === "EXPERT" && (
            <div className="card">
              <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>전문가 정보</h2>
              <div className="info-rows">
                <div className="info-row"><span className="info-label">전문 분야</span><span className="info-value">{user.specialization || "—"}</span></div>
                <div className="info-row">
                  <span className="info-label">승인 상태</span>
                  <span className="info-value">
                    {EXPERT_STATUS_LABELS[user.expert_status || ""] || user.expert_status || "—"}
                  </span>
                </div>
              </div>

              {user.expert_status === "PENDING_APPROVAL" && (
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "1.5rem" }}>
                  <button className="btn btn-primary" onClick={handleApprove} disabled={actionLoading}>
                    {actionLoading ? "처리 중..." : "전문가 승인"}
                  </button>
                  <button className="btn btn-danger" onClick={handleReject} disabled={actionLoading}>
                    {actionLoading ? "처리 중..." : "승인 거절"}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
