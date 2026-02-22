"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { updateProfile } from "@/lib/api";

export default function ExpertSettingsPage() {
  const { user, refreshUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.displayName || "");
  const [specialization, setSpecialization] = useState(user?.specialization || "");
  const [bio, setBio] = useState("");
  const [success, setSuccess] = useState(false);

  const updateMut = useMutation({
    mutationFn: () => updateProfile({
      display_name: displayName,
      specialization: specialization || undefined,
      bio: bio || undefined,
    }),
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
        <h2 className="panel-title-mb">프로필</h2>
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
            전문 분야
            <input className="input" value={specialization} onChange={(e) => setSpecialization(e.target.value)} placeholder="예: 신경영상, 뇌 MRI 분석" />
          </label>
          <label className="field">
            소개
            <textarea className="textarea" value={bio} onChange={(e) => setBio(e.target.value)} placeholder="간단한 자기 소개를 입력하세요" rows={3} />
          </label>
          {success && <div className="banner banner-success">프로필이 업데이트되었습니다.</div>}
          <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
            {updateMut.isPending ? <span className="spinner" /> : "저장"}
          </button>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title-mb">전문가 상태</h2>
        {user?.expertStatus === "APPROVED" ? (
          <div className="banner banner-success">승인된 전문가입니다. 리뷰 기능을 사용할 수 있습니다.</div>
        ) : user?.expertStatus === "PENDING_APPROVAL" ? (
          <div className="banner banner-warning">관리자 승인 대기 중입니다.</div>
        ) : (
          <div className="banner banner-info">전문가 상태: {user?.expertStatus || "알 수 없음"}</div>
        )}
      </div>
    </div>
  );
}
