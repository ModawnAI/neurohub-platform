"use client";

import { useEffect } from "react";
import { useTranslation } from "@/lib/i18n";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useTranslation();

  useEffect(() => {
    console.error("Global error:", error);
  }, [error]);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
        textAlign: "center",
      }}
    >
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>
        {t("errorPage.title")}
      </h1>
      <p style={{ color: "#64748b", marginBottom: 8, maxWidth: 480 }}>
        {error.message || t("errorPage.unknownError")}
      </p>
      {error.digest && (
        <p style={{ color: "#94a3b8", fontSize: 12, marginBottom: 24 }}>
          {t("errorPage.errorCode")}: {error.digest}
        </p>
      )}
      <button
        onClick={reset}
        style={{
          padding: "10px 24px",
          backgroundColor: "#0b6bcb",
          color: "#fff",
          borderRadius: 8,
          border: "none",
          cursor: "pointer",
          fontWeight: 600,
        }}
      >
        {t("common.retry")}
      </button>
    </div>
  );
}
