import { Providers } from "@/components/providers";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "NeuroHub — 의료 AI 워크플로우 플랫폼",
    template: "%s | NeuroHub",
  },
  description:
    "의료 영상 AI 분석의 요청 접수부터 품질 검증, 보고서 생성까지 전 과정을 자동화하고 추적하는 오케스트레이션 플랫폼입니다.",
  openGraph: {
    title: "NeuroHub — 의료 AI 워크플로우 플랫폼",
    description:
      "의료 영상 AI 분석의 요청 접수부터 품질 검증, 보고서 생성까지 전 과정을 자동화하고 추적하는 오케스트레이션 플랫폼입니다.",
    siteName: "NeuroHub",
    locale: "ko_KR",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>
        <a href="#main-content" className="skip-nav">메인 콘텐츠로 건너뛰기</a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
