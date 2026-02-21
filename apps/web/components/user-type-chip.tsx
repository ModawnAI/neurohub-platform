"use client";

export function UserTypeChip({ userType }: { userType: string | null | undefined }) {
  const config = getUserTypeConfig(userType);
  return (
    <span
      className="user-type-chip"
      style={{ background: config.bg, color: config.color }}
    >
      {config.label}
    </span>
  );
}

function getUserTypeConfig(userType: string | null | undefined) {
  switch (userType) {
    case "SERVICE_USER":
      return { label: "서비스 사용자", bg: "#dbeafe", color: "#1d4ed8" };
    case "EXPERT":
      return { label: "전문가", bg: "#ede9fe", color: "#6d28d9" };
    case "ADMIN":
      return { label: "관리자", bg: "#f1f5f9", color: "#334155" };
    default:
      return { label: "미지정", bg: "#f3f4f6", color: "#6b7280" };
  }
}
