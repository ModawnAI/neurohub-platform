import { FeatureCards, WorkflowSteps, AudienceCards } from "@/components/landing-sections";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "NeuroHub — 의료 영상 AI 분석, 안전하고 체계적으로",
  description:
    "요청 접수부터 AI 분석, 품질 검증, 보고서 생성까지 전 과정을 자동화하는 의료 AI 오케스트레이션 플랫폼",
};

export default function HomePage() {
  return (
    <div>
      {/* 히어로 */}
      <section className="landing-hero">
        <span className="hero-badge">의료 AI 워크플로우 플랫폼</span>
        <h1 className="landing-hero-title">
          의료 영상 AI 분석,
          <br />
          안전하고 체계적으로
        </h1>
        <p className="landing-hero-subtitle">
          NeuroHub는 의료 AI 파이프라인의 요청 접수부터 분석, 품질 검증, 보고서 생성까지 전 과정을
          자동화하고 추적하는 오케스트레이션 플랫폼입니다.
        </p>
        <div className="hero-actions">
          <Link className="btn btn-primary" href="/dashboard">
            대시보드 시작하기
          </Link>
          <Link className="btn btn-secondary" href="/new-request">
            첫 요청 만들기
          </Link>
        </div>
      </section>

      {/* 핵심 장점 */}
      <section className="landing-section">
        <h2 className="landing-section-title">왜 NeuroHub인가?</h2>
        <p className="landing-section-subtitle">
          의료 AI 워크플로우에 필요한 핵심 요소를 하나의 플랫폼에서 제공합니다.
        </p>
        <FeatureCards />
      </section>

      {/* 처리 과정 */}
      <section className="landing-section">
        <h2 className="landing-section-title">처리 과정</h2>
        <p className="landing-section-subtitle">
          요청 생성부터 최종 보고서까지, 5단계로 체계적으로 처리됩니다.
        </p>
        <WorkflowSteps />
      </section>

      {/* 대상 사용자 */}
      <section className="landing-section">
        <h2 className="landing-section-title">누구를 위한 플랫폼인가?</h2>
        <p className="landing-section-subtitle">
          병원 내 다양한 역할의 사용자가 각자의 업무에 맞게 활용합니다.
        </p>
        <AudienceCards />
      </section>

      {/* 하단 CTA */}
      <section className="footer-cta">
        <h2 className="footer-cta-title">NeuroHub로 의료 AI 워크플로우를 시작하세요</h2>
        <p className="footer-cta-subtitle">
          안정적인 실행, 완전한 감사 추적, 비용 관리까지 — 지금 바로 경험해 보세요.
        </p>
        <div className="hero-actions">
          <Link className="btn btn-primary" href="/dashboard">
            대시보드 바로가기
          </Link>
          <Link className="btn btn-secondary" href="/new-request">
            신규 요청 생성
          </Link>
        </div>
      </section>
    </div>
  );
}
