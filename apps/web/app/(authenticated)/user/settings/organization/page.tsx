"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { createOrganization, joinOrganization, listOrgMembers, inviteMember, type MemberRead } from "@/lib/api";
import { UserCircle, Copy, Check } from "phosphor-react";
import { useT } from "@/lib/i18n";

export default function OrganizationSettingsPage() {
  const { user, refreshUser } = useAuth();
  const t = useT();

  const ROLE_LABELS: Record<string, string> = {
    PHYSICIAN: t("userOrgSettings.rolePhysician"),
    TECHNICIAN: t("userOrgSettings.roleTechnician"),
    REVIEWER: t("userOrgSettings.roleReviewer"),
    SYSTEM_ADMIN: t("userOrgSettings.roleAdmin"),
  };
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"view" | "create" | "join">("view");
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  // Invite member state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("PHYSICIAN");
  const [inviteLoading, setInviteLoading] = useState(false);
  const [inviteToken, setInviteToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const orgId = user?.institutionId;

  const { data: members } = useQuery({
    queryKey: ["org-members", orgId],
    queryFn: () => listOrgMembers(orgId!),
    enabled: !!orgId,
  });

  const handleCreate = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await createOrganization({ name, institution_type: "HOSPITAL", contact_email: contactEmail || undefined });
      setSuccess(t("userOrgSettings.orgCreated"));
      setMode("view");
      await refreshUser();
    } catch (e: any) {
      setError(e.message || t("userOrgSettings.errorCreateFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await joinOrganization(inviteCode);
      setSuccess(t("userOrgSettings.orgJoined"));
      setMode("view");
      await refreshUser();
    } catch (e: any) {
      setError(e.message || t("userOrgSettings.errorJoinFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async () => {
    setError("");
    setInviteLoading(true);
    try {
      const result = await inviteMember(orgId!, inviteEmail, inviteRole);
      setInviteToken(result.invite_token);
      setInviteEmail("");
      queryClient.invalidateQueries({ queryKey: ["org-members", orgId] });
    } catch (e: any) {
      setError(e.message || t("userOrgSettings.errorInviteFailed"));
    } finally {
      setInviteLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!inviteToken) return;
    await navigator.clipboard.writeText(inviteToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="stack-lg">
      <h1 className="page-title">{t("userOrgSettings.title")}</h1>

      {error && <div className="banner banner-warning">{error}</div>}
      {success && <div className="banner banner-success">{success}</div>}

      {user?.institutionName && (
        <div className="panel">
          <p className="detail-label">{t("userOrgSettings.currentOrg")}</p>
          <p className="section-title" style={{ marginBottom: 0 }}>{user.institutionName}</p>
        </div>
      )}

      {/* Member List */}
      {orgId && members && members.length > 0 && (
        <div className="panel">
          <h2 className="panel-title-mb">{t("userOrgSettings.membersCount").replace("{count}", String(members.length))}</h2>
          <div className="stack-sm">
            {members.map((m: MemberRead) => (
              <div key={m.user_id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--border)" }}>
                <UserCircle size={32} weight="thin" style={{ color: "var(--muted)", flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontWeight: 500, fontSize: 14 }}>{m.display_name || m.username || "—"}</p>
                  <p className="muted-text" style={{ margin: 0, fontSize: 12 }}>{m.email || "—"}</p>
                </div>
                <span className="status-chip" style={{ fontSize: 11 }}>
                  {ROLE_LABELS[m.role_scope ?? ""] || m.user_type || "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invite Member */}
      {orgId && (
        <div className="panel">
          <h2 className="panel-title-mb">{t("userOrgSettings.inviteMembers")}</h2>
          {inviteToken && (
            <div className="banner banner-success" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ flex: 1, wordBreak: "break-all", fontSize: 13 }}>{t("userOrgSettings.inviteCode").replace("{token}", inviteToken)}</span>
              <button className="btn btn-sm btn-secondary" onClick={handleCopy}>
                {copied ? <><Check size={14} /> {t("common.copied")}</> : <><Copy size={14} /> {t("common.copy")}</>}
              </button>
            </div>
          )}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "end" }}>
            <label className="field" style={{ flex: 1, minWidth: 200 }}>
              {t("userOrgSettings.emailLabel")}
              <input className="input" type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="user@example.com" />
            </label>
            <label className="field" style={{ width: 140 }}>
              {t("userOrgSettings.roleLabel")}
              <select className="input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                <option value="PHYSICIAN">{t("userOrgSettings.rolePhysician")}</option>
                <option value="TECHNICIAN">{t("userOrgSettings.roleTechnician")}</option>
                <option value="REVIEWER">{t("userOrgSettings.roleReviewer")}</option>
              </select>
            </label>
            <button className="btn btn-primary" onClick={handleInvite} disabled={!inviteEmail.trim() || inviteLoading} style={{ height: 40 }}>
              {inviteLoading ? t("userOrgSettings.inviting") : t("userOrgSettings.invite")}
            </button>
          </div>
        </div>
      )}

      {/* Create / Join (only if no org) */}
      {!orgId && mode === "view" && (
        <div className="grid-2">
          <button className="type-selector-card" onClick={() => setMode("create")}>
            <p style={{ fontWeight: 600 }}>{t("userOrgSettings.createNewOrg")}</p>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              {t("userOrgSettings.createNewOrgDesc")}
            </p>
          </button>
          <button className="type-selector-card" onClick={() => setMode("join")}>
            <p style={{ fontWeight: 600 }}>{t("userOrgSettings.joinByCode")}</p>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              {t("userOrgSettings.joinByCodeDesc")}
            </p>
          </button>
        </div>
      )}

      {mode === "create" && (
        <div className="panel" style={{ maxWidth: "min(480px, 100%)" }}>
          <h2 className="section-title">{t("userOrgSettings.createOrgTitle")}</h2>
          <label className="field">
            {t("userOrgSettings.orgNameLabel")}
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder={t("userOrgSettings.orgNamePlaceholder")} />
          </label>
          <label className="field">
            {t("userOrgSettings.contactEmailOptional")}
            <input className="input" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder={t("userOrgSettings.contactEmailPlaceholder")} />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={handleCreate} disabled={!name.trim() || loading}>
              {loading ? t("common.loading") : t("userOrgSettings.createOrgButton")}
            </button>
            <button className="btn btn-secondary" onClick={() => setMode("view")}>{t("common.cancel")}</button>
          </div>
        </div>
      )}

      {mode === "join" && (
        <div className="panel" style={{ maxWidth: "min(480px, 100%)" }}>
          <h2 className="section-title">{t("userOrgSettings.joinOrgTitle")}</h2>
          <label className="field">
            {t("userOrgSettings.inviteCodeLabel")}
            <input className="input" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder={t("userOrgSettings.inviteCodePlaceholder")} />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={handleJoin} disabled={!inviteCode.trim() || loading}>
              {loading ? t("common.loading") : t("userOrgSettings.joinOrgButton")}
            </button>
            <button className="btn btn-secondary" onClick={() => setMode("view")}>{t("common.cancel")}</button>
          </div>
        </div>
      )}
    </div>
  );
}
