"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listOrganizations,
  listOrgMembers,
  updateOrganization,
  inviteMember,
  type OrgRead,
  type MemberRead,
} from "@/lib/api";
import { X, UserCircle, Copy, Check } from "phosphor-react";
import { useT } from "@/lib/i18n";

function OrgDetailPanel({ org, onClose }: { org: OrgRead; onClose: () => void }) {
  const t = useT();
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("PHYSICIAN");
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [editName, setEditName] = useState(org.name);
  const [editEmail, setEditEmail] = useState(org.contact_email || "");
  const [editing, setEditing] = useState(false);

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ["org-members", org.id],
    queryFn: () => listOrgMembers(org.id),
  });

  const updateMut = useMutation({
    mutationFn: () => updateOrganization(org.id, { name: editName, contact_email: editEmail || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-orgs"] });
      setEditing(false);
    },
  });

  const inviteMut = useMutation({
    mutationFn: () => inviteMember(org.id, inviteEmail, inviteRole),
    onSuccess: (data) => {
      setInviteToken(data.invite_token);
      setInviteEmail("");
      queryClient.invalidateQueries({ queryKey: ["org-members", org.id] });
    },
  });

  const toggleStatusMut = useMutation({
    mutationFn: () => updateOrganization(org.id, { status: org.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-orgs"] }),
  });

  const handleCopy = async () => {
    if (!inviteToken) return;
    await navigator.clipboard.writeText(inviteToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="stack-md">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 className="section-title" style={{ margin: 0 }}>{org.name}</h2>
        <button className="btn btn-sm btn-secondary" onClick={onClose}><X size={16} /></button>
      </div>

      {/* Org Info / Edit */}
      <div className="panel">
        <h3 className="panel-title-mb">{t("adminOrgs.orgInfo")}</h3>
        {editing ? (
          <div className="stack-md">
            <label className="field">{t("adminOrgs.orgNameLabel")} <input className="input" value={editName} onChange={(e) => setEditName(e.target.value)} /></label>
            <label className="field">{t("adminOrgs.contactEmail")} <input className="input" type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} /></label>
            <div className="action-row">
              <button className="btn btn-primary btn-sm" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>{t("common.save")}</button>
              <button className="btn btn-secondary btn-sm" onClick={() => setEditing(false)}>{t("common.cancel")}</button>
            </div>
          </div>
        ) : (
          <div className="stack-sm">
            <div><p className="detail-label">{t("adminOrgs.code")}</p><p className="detail-value mono-cell">{org.code}</p></div>
            <div><p className="detail-label">{t("adminOrgs.type")}</p><p className="detail-value">{org.institution_type === "HOSPITAL" ? t("adminOrgs.typeHospital") : org.institution_type === "CLINIC" ? t("adminOrgs.typeClinic") : org.institution_type === "INDIVIDUAL" ? t("adminOrgs.typeIndividual") : org.institution_type}</p></div>
            <div><p className="detail-label">{t("adminOrgs.contactEmail")}</p><p className="detail-value">{org.contact_email || "—"}</p></div>
            <div><p className="detail-label">{t("adminUsers.tableStatus")}</p><p className="detail-value">{org.status === "ACTIVE" ? t("common.active") : t("common.inactive")}</p></div>
            <div className="action-row">
              <button className="btn btn-sm btn-secondary" onClick={() => setEditing(true)}>{t("common.edit")}</button>
              <button
                className={`btn btn-sm ${org.status === "ACTIVE" ? "btn-danger" : "btn-primary"}`}
                onClick={() => toggleStatusMut.mutate()}
                disabled={toggleStatusMut.isPending}
              >
                {org.status === "ACTIVE" ? t("common.deactivate") : t("common.activate")}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Members */}
      <div className="panel">
        <h3 className="panel-title-mb">{t("adminOrgs.membersCount").replace("{count}", String(members?.length ?? 0))}</h3>
        {membersLoading ? <span className="spinner" /> : (
          <div className="stack-sm">
            {(members ?? []).map((m: MemberRead) => (
              <div key={m.user_id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                <UserCircle size={28} weight="thin" style={{ color: "var(--muted)", flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontWeight: 500, fontSize: 13 }}>{m.display_name || m.username || "—"}</p>
                  <p className="muted-text" style={{ margin: 0, fontSize: 11 }}>{m.email || "—"}</p>
                </div>
                <span style={{ fontSize: 11, color: "var(--muted)" }}>{m.role_scope === "PHYSICIAN" ? t("adminOrgs.rolePhysician") : m.role_scope === "TECHNICIAN" ? t("adminOrgs.roleTechnician") : m.role_scope === "REVIEWER" ? t("adminOrgs.roleReviewer") : m.role_scope === "SYSTEM_ADMIN" ? t("adminOrgs.roleAdmin") : m.user_type || "—"}</span>
              </div>
            ))}
            {(members ?? []).length === 0 && <p className="muted-text" style={{ fontSize: 13 }}>{t("adminOrgs.noMembers")}</p>}
          </div>
        )}
      </div>

      {/* Invite */}
      <div className="panel">
        <h3 className="panel-title-mb">{t("adminOrgs.inviteMembers")}</h3>
        {inviteToken && (
          <div className="banner banner-success" style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ flex: 1, wordBreak: "break-all", fontSize: 12 }}>{t("adminOrgs.inviteCode").replace("{token}", inviteToken)}</span>
            <button className="btn btn-sm btn-secondary" onClick={handleCopy}>
              {copied ? <><Check size={14} /> {t("common.copied")}</> : <><Copy size={14} /> {t("common.copy")}</>}
            </button>
          </div>
        )}
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "end" }}>
          <label className="field" style={{ flex: 1, minWidth: 180 }}>
            {t("adminOrgs.emailLabel")}
            <input className="input" type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="user@example.com" />
          </label>
          <label className="field" style={{ width: 120 }}>
            {t("adminOrgs.roleLabel")}
            <select className="input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
              <option value="PHYSICIAN">{t("adminOrgs.rolePhysician")}</option>
              <option value="TECHNICIAN">{t("adminOrgs.roleTechnician")}</option>
              <option value="REVIEWER">{t("adminOrgs.roleReviewer")}</option>
            </select>
          </label>
          <button className="btn btn-primary" onClick={() => inviteMut.mutate()} disabled={!inviteEmail.trim() || inviteMut.isPending} style={{ height: 40 }}>
            {inviteMut.isPending ? t("adminOrgs.inviting") : t("adminOrgs.invite")}
          </button>
        </div>
        {inviteMut.isError && <p className="error-text" style={{ marginTop: 8 }}>{(inviteMut.error as Error).message}</p>}
      </div>
    </div>
  );
}

export default function AdminOrganizationsPage() {
  const t = useT();
  const [selectedOrg, setSelectedOrg] = useState<OrgRead | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["admin-orgs"], queryFn: listOrganizations });
  const orgs = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("adminOrgs.title")}</h1>
          <p className="page-subtitle">{t("adminOrgs.subtitle")}</p>
        </div>
      </div>

      {selectedOrg ? (
        <OrgDetailPanel org={selectedOrg} onClose={() => setSelectedOrg(null)} />
      ) : isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : (
        <div className="panel">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("adminOrgs.tableOrgName")}</th>
                  <th>{t("adminOrgs.tableCode")}</th>
                  <th>{t("adminOrgs.tableType")}</th>
                  <th>{t("adminOrgs.tableMemberCount")}</th>
                  <th>{t("adminOrgs.tableStatus")}</th>
                  <th>{t("adminOrgs.tableCreatedDate")}</th>
                </tr>
              </thead>
              <tbody>
                {orgs.map((org: OrgRead) => (
                  <tr key={org.id} style={{ cursor: "pointer" }} onClick={() => setSelectedOrg(org)}>
                    <td style={{ fontWeight: 600 }}>{org.name}</td>
                    <td className="mono-cell">{org.code}</td>
                    <td>{org.institution_type === "HOSPITAL" ? t("adminOrgs.typeHospital") : org.institution_type === "CLINIC" ? t("adminOrgs.typeClinic") : org.institution_type === "INDIVIDUAL" ? t("adminOrgs.typeIndividual") : org.institution_type}</td>
                    <td>{t("adminOrgs.memberCountFormat").replace("{count}", String(org.member_count))}</td>
                    <td><span className={`status-chip ${org.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>{org.status === "ACTIVE" ? t("common.active") : t("common.inactive")}</span></td>
                    <td>{org.created_at ? new Date(org.created_at).toLocaleDateString("ko-KR") : "-"}</td>
                  </tr>
                ))}
                {orgs.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>{t("adminOrgs.noOrgs")}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
