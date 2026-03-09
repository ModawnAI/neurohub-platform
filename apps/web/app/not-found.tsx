"use client";

import Link from "next/link";
import { useTranslation } from "@/lib/i18n";

export default function NotFound() {
  const { t } = useTranslation();

  return (
    <div className="auth-page">
      <div style={{ textAlign: "center" }}>
        <p style={{ fontSize: 72, fontWeight: 800, color: "var(--muted)", margin: "0 0 8px", opacity: 0.3 }}>
          404
        </p>
        <h1 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 8px" }}>
          {t("notFound.title")}
        </h1>
        <p className="muted-text" style={{ marginBottom: 24 }}>
          {t("notFound.description")}
        </p>
        <Link href="/" className="btn btn-primary" style={{ display: "inline-flex" }}>
          {t("notFound.backHome")}
        </Link>
      </div>
    </div>
  );
}
