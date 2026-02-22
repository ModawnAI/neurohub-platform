import type { Metadata } from "next";
import { LandingPageContent } from "@/components/landing-page-content";

export const metadata: Metadata = {
  title: "NeuroHub — 의료 영상 AI 분석, 안전하고 체계적으로",
  description:
    "요청 접수부터 AI 분석, 품질 검증, 보고서 생성까지 전 과정을 자동화하는 의료 AI 오케스트레이션 플랫폼",
};

export default function HomePage() {
  return <LandingPageContent />;
}
