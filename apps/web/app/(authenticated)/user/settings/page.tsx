"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile } from "@/lib/api";

export default function UserSettingsPage() {
  const { user, refreshUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.displayName || "");
  const [phone, setPhone] = useState("");
  const [success, setSuccess] = useState(false);

  const updateMut = useMutation({
    mutationFn: () => updateProfile({ display_name: displayName, phone: phone || undefined }),
    onSuccess: () => {
      refreshUser();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    },
  });

  return (
    <div className="stack-lg">
      <h1 className="page-title">설정</h1>

      <div className="panel">
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px" }}>프로필</h2>
        <div className="auth-form">
          <label className="field">
            이메일
            <input className="input" value={user?.email || ""} disabled style={{ opacity: 0.6 }} />
          </label>
          <label className="field">
            표시 이름
            <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <label className="field">
            연락처
            <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="010-0000-0000" />
          </label>
          {success && <div className="banner banner-success">프로필이 업데이트되었습니다.</div>}
          <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
            {updateMut.isPending ? <span className="spinner" /> : "저장"}
          </button>
        </div>
      </div>

      <div className="panel">
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px" }}>소속 기관</h2>
        {user?.institutionName ? (
          <div className="stack-md">
            <div>
              <p className="detail-label">기관명</p>
              <p className="detail-value">{user.institutionName}</p>
            </div>
          </div>
        ) : (
          <p className="muted-text">소속 기관이 없습니다.</p>
        )}
      </div>
    </div>
  );
}
