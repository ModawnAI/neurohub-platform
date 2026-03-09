"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Brain, Globe } from "phosphor-react";
import { useAuth, getRoleHomePath } from "@/lib/auth";
import { useT, useLocale } from "@/lib/i18n";

export default function LoginPage() {
  const t = useT();
  const { locale, setLocale } = useLocale();
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
      const authUser = await refreshUser();
      window.location.href = getRoleHomePath(authUser?.userType);
    } catch (err: any) {
      setError(err?.message || t("auth.loginFailed"));
    } finally {
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
        <p className="auth-subtitle">{t("auth.loginSubtitle")}</p>

        <form className="auth-form" onSubmit={handleSubmit}>
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
              placeholder={t("auth.passwordPlaceholder")}
              required
              autoComplete="current-password"
            />
          </label>

          {error && <p className="error-text" role="alert" aria-live="assertive">{error}</p>}

          <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: "100%", justifyContent: "center" }}>
            {loading ? <span className="spinner" /> : t("auth.login")}
          </button>
        </form>

        <p className="auth-footer">
          {t("auth.noAccount")} <Link href="/register">{t("auth.signUp")}</Link>
        </p>
      </div>
    </div>
  );
}
