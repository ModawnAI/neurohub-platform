import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "신규 요청 생성",
  description: "서비스와 파이프라인을 선택하고 환자 케이스를 등록하여 새 분석 요청을 생성합니다.",
};

export default function NewRequestLayout({ children }: { children: React.ReactNode }) {
  return children;
}
