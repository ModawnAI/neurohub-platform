"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { createOrganization, joinOrganization } from "@/lib/api";

export default function OrganizationSettingsPage() {
  const { user, refreshUser } = useAuth();
  const [mode, setMode] = useState<"view" | "create" | "join">("view");
  const [name, setName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

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

  return (
    <div>
      <h1 className="page-title">기관 설정</h1>

      {error && <div className="banner banner-warning">{error}</div>}
      {success && <div className="banner banner-success">{success}</div>}

      {user?.institutionName && (
        <div className="card" style={{ marginBottom: "1.5rem" }}>
          <p className="card-label">현재 소속 기관</p>
          <p style={{ fontSize: "1.125rem", fontWeight: 600 }}>{user.institutionName}</p>
        </div>
      )}

      {mode === "view" && (
        <div className="type-selector-grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
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
        <div className="card" style={{ maxWidth: 480 }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>새 기관 만들기</h2>
          <label className="field">
            기관명
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="예: 서울대학교병원" />
          </label>
          <label className="field">
            연락처 이메일 (선택)
            <input className="input" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="contact@hospital.kr" />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={handleCreate} disabled={!name.trim() || loading}>
              {loading ? "생성 중..." : "기관 생성"}
            </button>
            <button className="btn btn-secondary" onClick={() => setMode("view")}>취소</button>
          </div>
        </div>
      )}

      {mode === "join" && (
        <div className="card" style={{ maxWidth: 480 }}>
          <h2 style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>초대 코드로 참여</h2>
          <label className="field">
            초대 코드
            <input className="input" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="초대 코드를 입력하세요" />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
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
