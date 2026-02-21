import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "대시보드",
  description: "실시간 요청 현황 및 활동 요약을 확인합니다.",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return children;
}
