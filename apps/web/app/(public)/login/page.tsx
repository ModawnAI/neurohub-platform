"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Brain } from "phosphor-react";
import { useAuth, getRoleHomePath } from "@/lib/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { signIn, refreshUser } = useAuth();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await signIn(email, password);
      // Wait for auth state to propagate
      await new Promise((r) => setTimeout(r, 500));
      await refreshUser();
      // Read cookie to determine redirect
      const userType = document.cookie
        .split("; ")
        .find((c) => c.startsWith("nh-user-type="))
        ?.split("=")[1];
      router.push(getRoleHomePath(userType));
    } catch (err: any) {
      setError(err?.message || "로그인에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-icon">
            <Brain size={22} weight="bold" />
          </div>
          <span className="auth-brand-text">NeuroHub</span>
        </div>
        <p className="auth-subtitle">의료 AI 워크플로우 플랫폼에 로그인하세요</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            이메일
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              required
              autoComplete="email"
            />
          </label>

          <label className="field">
            비밀번호
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="비밀번호를 입력하세요"
              required
              autoComplete="current-password"
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
            {loading ? <span className="spinner" /> : "로그인"}
          </button>
        </form>

        <p className="auth-footer">
          계정이 없으신가요? <Link href="/register">회원가입</Link>
        </p>
      </div>
    </div>
  );
}
