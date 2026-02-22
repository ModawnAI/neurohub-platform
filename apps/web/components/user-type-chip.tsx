"use client";

import { useT } from "@/lib/i18n";

const STYLE_MAP: Record<string, { bg: string; color: string }> = {
  SERVICE_USER: { bg: "#dbeafe", color: "#1d4ed8" },
  EXPERT: { bg: "#ede9fe", color: "#6d28d9" },
  ADMIN: { bg: "#f1f5f9", color: "#334155" },
};

const DEFAULT_STYLE = { bg: "#f3f4f6", color: "#6b7280" };

export function UserTypeChip({ userType }: { userType: string | null | undefined }) {
  const t = useT();
  const style = (userType && STYLE_MAP[userType]) || DEFAULT_STYLE;

  let label: string;
  switch (userType) {
    case "SERVICE_USER":
      label = t("userType.SERVICE_USER");
      break;
    case "EXPERT":
      label = t("userType.EXPERT");
      break;
    case "ADMIN":
      label = t("userType.ADMIN");
      break;
    default:
      label = t("userType.unspecified");
      break;
  }

  return (
    <span
      className="user-type-chip"
      style={{ background: style.bg, color: style.color }}
    >
      {label}
    </span>
  );
}
