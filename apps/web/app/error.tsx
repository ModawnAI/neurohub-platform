"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
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
        오류가 발생했습니다
      </h1>
      <p style={{ color: "#64748b", marginBottom: 8, maxWidth: 480 }}>
        {error.message || "알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."}
      </p>
      {error.digest && (
        <p style={{ color: "#94a3b8", fontSize: 12, marginBottom: 24 }}>
          오류 코드: {error.digest}
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
        다시 시도
      </button>
    </div>
  );
}
