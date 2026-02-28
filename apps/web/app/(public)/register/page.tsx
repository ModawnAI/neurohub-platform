"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Brain, Globe } from "phosphor-react";
import { useAuth, getRoleHomePath } from "@/lib/auth";
import { useT, useLocale } from "@/lib/i18n";

export default function RegisterPage() {
  const t = useT();
  const router = useRouter();
  const { locale, setLocale } = useLocale();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { signUp, refreshUser } = useAuth();

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
      const user = await refreshUser();
      const dest = user ? getRoleHomePath(user.userType) : "/onboarding";
      window.location.href = dest;
    } catch (err: any) {
      setError(err?.message || t("auth.errorSignUpFailed"));
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <button
        onClick={() => setLocale(locale === "ko" ? "en" : "ko")}
        className="auth-lang-btn"
      >
        <Globe size={16} />
        {locale === "ko" ? "EN" : "KO"}
      </button>
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

          {error && <p className="error-text" role="alert" aria-live="assertive">{error}</p>}

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
