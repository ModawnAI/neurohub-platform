"use client";

import { useState } from "react";
import Link from "next/link";
import { Brain, EnvelopeSimple } from "phosphor-react";
import { useAuth } from "@/lib/auth";
import { supabase } from "@/lib/supabase";
import { useT } from "@/lib/i18n";

export default function RegisterPage() {
  const t = useT();
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
      setError(t("auth.errorPasswordMinLength"));
      return;
    }
    if (password !== confirmPassword) {
      setError(t("auth.errorPasswordMismatch"));
      return;
    }

    setLoading(true);

    try {
      await signUp(email, password);
      setRegistered(true);
    } catch (err: any) {
      setError(err?.message || t("auth.errorSignUpFailed"));
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
            {t("auth.verificationTitle")}
          </h1>

          <p style={{ color: "var(--muted)", fontSize: "0.9rem", lineHeight: 1.6, margin: "0 0 1.5rem" }}>
            <strong>{email}</strong>{t("auth.verificationMessage")}
            <br />
            {t("auth.verificationInstruction")}
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
            {t("auth.verificationSpamWarning")}
          </div>

          <button
            className="btn btn-secondary"
            onClick={handleResend}
            disabled={resending || resent}
            style={{ width: "100%", justifyContent: "center", marginBottom: "0.75rem" }}
          >
            {resent ? t("auth.resentEmail") : resending ? t("auth.sendingEmail") : t("auth.resendEmail")}
          </button>

          <p className="auth-footer">
            <Link href="/login">{t("auth.backToLogin")}</Link>
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
        <p className="auth-subtitle">{t("auth.signUpSubtitle")}</p>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label className="field">
            {t("auth.name")}
            <input
              className="input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("auth.namePlaceholder")}
              required
            />
          </label>

          <label className="field">
            {t("auth.email")}
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
            {t("auth.password")}
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t("auth.passwordMinHint")}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </label>

          <label className="field">
            {t("auth.confirmPassword")}
            <input
              className="input"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t("auth.confirmPasswordPlaceholder")}
              required
              autoComplete="new-password"
            />
          </label>

          {error && <p className="error-text">{error}</p>}

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
            {loading ? <span className="spinner" /> : t("auth.signUp")}
          </button>
        </form>

        <p className="auth-footer">
          {t("auth.alreadyHaveAccount")} <Link href="/login">{t("auth.login")}</Link>
        </p>
      </div>
    </div>
  );
}
