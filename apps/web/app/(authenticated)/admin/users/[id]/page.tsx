"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getUser, approveExpert, rejectExpert } from "@/lib/api";
import { UserTypeChip } from "@/components/user-type-chip";
import { ArrowLeft } from "phosphor-react";
import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function AdminUserDetailPage() {
  const t = useT();
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
  if (!user) return <div className="banner banner-warning">{t("adminUsers.notFound")}</div>;

  const actionPending = approveMut.isPending || rejectMut.isPending;

  return (
    <div className="stack-lg">
      <Link href="/admin/users" className="back-link">
        <ArrowLeft size={16} /> {t("adminUsers.backToList")}
      </Link>

      <div className="page-header">
        <h1 className="page-title">{user.display_name || user.username}</h1>
        <UserTypeChip userType={user.user_type} />
      </div>

      <div className="detail-grid">
        <div className="stack-md">
          <div className="panel">
            <h2 className="panel-title-mb">{t("adminUsers.userInfo")}</h2>
            <div className="stack-md">
              <div><p className="detail-label">{t("adminUsers.fieldId")}</p><p className="detail-value" style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{user.id}</p></div>
              <div><p className="detail-label">{t("adminUsers.fieldUsername")}</p><p className="detail-value">{user.username}</p></div>
              <div><p className="detail-label">{t("auth.email")}</p><p className="detail-value">{user.email || "—"}</p></div>
              <div><p className="detail-label">{t("adminUsers.fieldDisplayName")}</p><p className="detail-value">{user.display_name || "—"}</p></div>
              <div><p className="detail-label">{t("adminUsers.fieldOrg")}</p><p className="detail-value">{user.institution_name || "—"}</p></div>
              <div><p className="detail-label">{t("adminUsers.fieldActiveStatus")}</p><p className="detail-value">{user.is_active ? t("common.active") : t("common.inactive")}</p></div>
              <div><p className="detail-label">{t("adminUsers.fieldOnboarding")}</p><p className="detail-value">{user.onboarding_completed ? t("common.completed") : t("common.incomplete")}</p></div>
              <div><p className="detail-label">{t("adminUsers.tableSignupDate")}</p><p className="detail-value">{user.created_at ? new Date(user.created_at).toLocaleString("ko-KR") : "—"}</p></div>
              {user.last_login_at && <div><p className="detail-label">{t("adminUsers.fieldLastLogin")}</p><p className="detail-value">{new Date(user.last_login_at).toLocaleString("ko-KR")}</p></div>}
            </div>
          </div>

          {user.user_type === "EXPERT" && (
            <div className="panel">
              <h2 className="panel-title-mb">{t("adminUsers.expertInfo")}</h2>
              <div className="stack-md">
                <div><p className="detail-label">{t("adminUsers.fieldSpecialization")}</p><p className="detail-value">{user.specialization || "—"}</p></div>
                <div>
                  <p className="detail-label">{t("adminUsers.fieldApprovalStatus")}</p>
                  <p className="detail-value">
                    {user.expert_status === "PENDING_APPROVAL" ? t("adminUsers.statusPending") : user.expert_status === "APPROVED" ? t("adminUsers.statusApproved") : user.expert_status === "REJECTED" ? t("adminUsers.statusRejected") : user.expert_status || "—"}
                  </p>
                </div>
              </div>

              {user.expert_status === "PENDING_APPROVAL" && (
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1.5rem" }}>
                  <button className="btn btn-primary" onClick={() => approveMut.mutate()} disabled={actionPending}>
                    {approveMut.isPending ? t("common.loading") : t("adminUsers.approveExpert")}
                  </button>
                  <button className="btn btn-danger" onClick={() => rejectMut.mutate()} disabled={actionPending}>
                    {rejectMut.isPending ? t("common.loading") : t("adminUsers.rejectExpert")}
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
