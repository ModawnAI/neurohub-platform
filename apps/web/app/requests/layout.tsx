import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "요청 관리",
  description: "요청 상태 전이와 실행 제출을 한 화면에서 관리합니다.",
};

export default function RequestsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
