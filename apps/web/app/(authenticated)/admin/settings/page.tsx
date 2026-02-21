"use client";

import { useAuth } from "@/lib/auth";

export default function AdminSettingsPage() {
  const { user } = useAuth();

  return (
    <div className="stack-lg">
      <h1 className="page-title">시스템 설정</h1>

      <div className="panel">
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 16px" }}>관리자 정보</h2>
        <div className="stack-md">
          <div>
            <p className="detail-label">이메일</p>
            <p className="detail-value">{user?.email || "-"}</p>
          </div>
          <div>
            <p className="detail-label">이름</p>
            <p className="detail-value">{user?.displayName || "-"}</p>
          </div>
          <div>
            <p className="detail-label">소속 기관</p>
            <p className="detail-value">{user?.institutionName || "-"}</p>
          </div>
        </div>
      </div>

      <div className="panel">
        <h2 style={{ fontSize: 16, fontWeight: 700, margin: "0 0 12px" }}>시스템 정보</h2>
        <div className="stack-md">
          <div>
            <p className="detail-label">플랫폼</p>
            <p className="detail-value">NeuroHub v1.0</p>
          </div>
          <div>
            <p className="detail-label">환경</p>
            <p className="detail-value">Production</p>
          </div>
        </div>
      </div>
    </div>
  );
}
