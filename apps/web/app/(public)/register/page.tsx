"use client";

import { useState } from "react";
import Link from "next/link";
import { Brain, EnvelopeSimple } from "phosphor-react";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [resending, setResending] = useState(false);
  const [resent, setResent] = useState(false);
  const { signUp } = useAuth();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다.");
      return;
    }
    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    setLoading(true);

    try {
      await signUp(email, password);
      setRegistered(true);
    } catch (err: any) {
      setError(err?.message || "회원가입에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!supabase || resending) return;
    setResending(true);
    setResent(false);
    try {
      const { error: resendError } = await supabase.auth.resend({ type: "signup", email });
      if (resendError) throw resendError;
      setResent(true);
    } catch {
      // silently fail — don't reveal if email exists
    } finally {
      setResending(false);
    }
  }

  if (registered) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: "1rem" }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: "50%",
                background: "#dbeafe",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#1d4ed8",
              }}
            >
              <EnvelopeSimple size={28} weight="duotone" />
            </div>
          </div>

          <h1 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "0 0 0.5rem" }}>
            이메일을 확인해 주세요
          </h1>

          <p style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.6, margin: "0 0 1.5rem" }}>
            <strong>{email}</strong>로 인증 메일을 보냈습니다.
            <br />
            메일함을 확인하고 인증 링크를 클릭하세요.
          </p>

          <div
            style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "12px 16px",
              fontSize: "0.85rem",
              color: "var(--muted)",
              marginBottom: "1.5rem",
            }}
          >
            메일이 보이지 않으면 스팸 폴더를 확인해 주세요.
          </div>

          <button
            className="btn btn-secondary"
            onClick={handleResend}
            disabled={resending || resent}
            style={{ width: "100%", justifyContent: "center", marginBottom: "0.75rem" }}
          >
            {resent ? "인증 메일을 다시 보냈습니다" : resending ? "발송 중..." : "인증 메일 재발송"}
          </button>

          <p className="auth-footer">
            <Link href="/login">로그인 페이지로 돌아가기</Link>
          </p>
        </div>
      </div>
    );
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
        <p className="auth-subtitle">새 계정을 만들고 의료 AI 분석을 시작하세요</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            이름
            <input
              className="input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="홍길동"
              required
            />
          </label>

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
              placeholder="8자 이상"
              required
              minLength={8}
              autoComplete="new-password"
            />
          </label>

          <label className="field">
            비밀번호 확인
            <input
              className="input"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="비밀번호를 다시 입력하세요"
              required
              autoComplete="new-password"
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
            {loading ? <span className="spinner" /> : "회원가입"}
          </button>
        </form>

        <p className="auth-footer">
          이미 계정이 있으신가요? <Link href="/login">로그인</Link>
        </p>
      </div>
    </div>
  );
}
