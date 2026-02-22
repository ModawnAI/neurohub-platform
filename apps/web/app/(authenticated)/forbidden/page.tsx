"use client";

import { useRouter } from "next/navigation";
import { ShieldWarning } from "phosphor-react";

export default function ForbiddenPage() {
  const router = useRouter();

  return (
    <div className="auth-page">
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 48, color: "var(--danger)", marginBottom: 16, opacity: 0.5 }}>
          <ShieldWarning size={48} />
        </div>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>
          접근 권한이 없습니다
        </h1>
        <p className="muted-text" style={{ marginBottom: 24 }}>
          이 페이지에 접근할 수 있는 권한이 없습니다. 관리자에게 문의하세요.
        </p>
        <button className="btn btn-primary" onClick={() => router.back()}>
          뒤로 가기
        </button>
      </div>
    </div>
  );
}
