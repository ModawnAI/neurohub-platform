"use client";

import { type PreQCCheckRead } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { CheckCircle, Warning, XCircle } from "phosphor-react";

const STATUS_ICON: Record<string, React.ReactNode> = {
  PASS: <CheckCircle size={16} weight="fill" color="var(--color-green-11)" />,
  WARN: <Warning size={16} weight="fill" color="var(--color-yellow-11)" />,
  FAIL: <XCircle size={16} weight="fill" color="var(--color-red-11)" />,
};

const STATUS_BG: Record<string, string> = {
  PASS: "var(--color-green-3)",
  WARN: "var(--color-yellow-3)",
  FAIL: "var(--color-red-3)",
};

export function PreQCViewer({
  checks,
  canProceed,
  failMessages,
  warnMessages,
}: {
  checks: PreQCCheckRead[];
  canProceed: boolean;
  failMessages: string[];
  warnMessages: string[];
}) {
  const t = useT();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{t("preqc.title")}</h3>

      <div
        style={{
          padding: "12px 16px",
          borderRadius: "8px",
          backgroundColor: canProceed ? "var(--color-green-3)" : "var(--color-red-3)",
          color: canProceed ? "var(--color-green-11)" : "var(--color-red-11)",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          fontWeight: 600,
        }}
      >
        {canProceed ? <CheckCircle size={20} weight="fill" /> : <XCircle size={20} weight="fill" />}
        {canProceed ? t("preqc.canProceed") : t("preqc.blocked")}
      </div>

      {failMessages.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {failMessages.map((msg, i) => (
            <div
              key={`fail-${i}`}
              style={{
                padding: "8px 12px",
                borderRadius: "6px",
                backgroundColor: "var(--color-red-3)",
                color: "var(--color-red-11)",
                fontSize: "13px",
              }}
            >
              {msg}
            </div>
          ))}
        </div>
      )}

      {warnMessages.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {warnMessages.map((msg, i) => (
            <div
              key={`warn-${i}`}
              style={{
                padding: "8px 12px",
                borderRadius: "6px",
                backgroundColor: "var(--color-yellow-3)",
                color: "var(--color-yellow-11)",
                fontSize: "13px",
              }}
            >
              {msg}
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        {checks.map((check, i) => (
          <div
            key={`${check.modality}-${check.check_type}-${i}`}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 12px",
              borderRadius: "6px",
              backgroundColor: STATUS_BG[check.status] ?? "var(--color-gray-3)",
              fontSize: "13px",
            }}
          >
            {STATUS_ICON[check.status]}
            <span style={{ fontWeight: 600, minWidth: "40px" }}>{check.modality}</span>
            <span style={{ color: "var(--color-gray-11)", minWidth: "140px" }}>
              {check.check_type}
            </span>
            <span style={{ flex: 1 }}>{check.message_ko}</span>
            {check.auto_resolved && (
              <span style={{ fontSize: "11px", padding: "1px 6px", borderRadius: 3, backgroundColor: "var(--color-blue-3)", color: "var(--color-blue-11)" }}>
                관리자 재정
              </span>
            )}
            {check.score != null && (
              <span style={{ fontSize: "12px", color: "var(--color-gray-11)" }}>
                {check.score.toFixed(1)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
