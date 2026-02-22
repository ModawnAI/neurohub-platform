"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { createOrganization, joinOrganization, listOrgMembers, inviteMember, type MemberRead } from "@/lib/api";
import { UserCircle, Copy, Check } from "phosphor-react";

const ROLE_LABELS: Record<string, string> = {
  PHYSICIAN: "의사",
  TECHNICIAN: "기사",
  REVIEWER: "리뷰어",
  SYSTEM_ADMIN: "관리자",
};

export default function OrganizationSettingsPage() {
  const { user, refreshUser } = useAuth();
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
      setSuccess("기관이 생성되었습니다.");
      setMode("view");
      await refreshUser();
    } catch (e: any) {
      setError(e.message || "기관 생성에 실패했습니다.");
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
      setSuccess("기관에 참여했습니다.");
      setMode("view");
      await refreshUser();
    } catch (e: any) {
      setError(e.message || "참여에 실패했습니다.");
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
      setError(e.message || "초대에 실패했습니다.");
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
      <h1 className="page-title">기관 설정</h1>

      {error && <div className="banner banner-warning">{error}</div>}
      {success && <div className="banner banner-success">{success}</div>}

      {user?.institutionName && (
        <div className="panel">
          <p className="detail-label">현재 소속 기관</p>
          <p className="section-title" style={{ marginBottom: 0 }}>{user.institutionName}</p>
        </div>
      )}

      {/* Member List */}
      {orgId && members && members.length > 0 && (
        <div className="panel">
          <h2 className="panel-title-mb">구성원 ({members.length}명)</h2>
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
          <h2 className="panel-title-mb">구성원 초대</h2>
          {inviteToken && (
            <div className="banner banner-success" style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ flex: 1, wordBreak: "break-all", fontSize: 13 }}>초대 코드: <strong>{inviteToken}</strong></span>
              <button className="btn btn-sm btn-secondary" onClick={handleCopy}>
                {copied ? <><Check size={14} /> 복사됨</> : <><Copy size={14} /> 복사</>}
              </button>
            </div>
          )}
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "end" }}>
            <label className="field" style={{ flex: 1, minWidth: 200 }}>
              이메일
              <input className="input" type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="user@example.com" />
            </label>
            <label className="field" style={{ width: 140 }}>
              역할
              <select className="input" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                <option value="PHYSICIAN">의사</option>
                <option value="TECHNICIAN">기사</option>
                <option value="REVIEWER">리뷰어</option>
              </select>
            </label>
            <button className="btn btn-primary" onClick={handleInvite} disabled={!inviteEmail.trim() || inviteLoading} style={{ height: 40 }}>
              {inviteLoading ? "초대 중..." : "초대"}
            </button>
          </div>
        </div>
      )}

      {/* Create / Join (only if no org) */}
      {!orgId && mode === "view" && (
        <div className="grid-2">
          <button className="type-selector-card" onClick={() => setMode("create")}>
            <p style={{ fontWeight: 600 }}>새 기관 만들기</p>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              병원이나 의원을 새로 등록합니다.
            </p>
          </button>
          <button className="type-selector-card" onClick={() => setMode("join")}>
            <p style={{ fontWeight: 600 }}>초대 코드로 참여</p>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)" }}>
              기존 기관의 초대 코드를 입력합니다.
            </p>
          </button>
        </div>
      )}

      {mode === "create" && (
        <div className="panel" style={{ maxWidth: "min(480px, 100%)" }}>
          <h2 className="section-title">새 기관 만들기</h2>
          <label className="field">
            기관명
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="예: 서울대학교병원" />
          </label>
          <label className="field">
            연락처 이메일 (선택)
            <input className="input" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="contact@hospital.kr" />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={handleCreate} disabled={!name.trim() || loading}>
              {loading ? "생성 중..." : "기관 생성"}
            </button>
            <button className="btn btn-secondary" onClick={() => setMode("view")}>취소</button>
          </div>
        </div>
      )}

      {mode === "join" && (
        <div className="panel" style={{ maxWidth: "min(480px, 100%)" }}>
          <h2 className="section-title">초대 코드로 참여</h2>
          <label className="field">
            초대 코드
            <input className="input" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="초대 코드를 입력하세요" />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={handleJoin} disabled={!inviteCode.trim() || loading}>
              {loading ? "참여 중..." : "참여하기"}
            </button>
            <button className="btn btn-secondary" onClick={() => setMode("view")}>취소</button>
          </div>
        </div>
      )}
    </div>
  );
}
