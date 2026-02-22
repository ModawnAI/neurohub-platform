"use client";

import Link from "next/link";
import {
  FeatureCards,
  WorkflowSteps,
  AudienceCards,
  VisionarySection,
  LandingNav,
} from "@/components/landing-sections";
import { useT } from "@/lib/i18n";

export function LandingPageContent() {
  const t = useT();

  return (
    <div>
      {/* 상단 네비게이션 */}
      <LandingNav />

      <div className="container">
        {/* 히어로 */}
        <section className="landing-hero">
          <span className="hero-badge">{t("landing.badge")}</span>
          <h1 className="landing-hero-title">
            {t("landing.heroTitle").split("\n").map((line, i, arr) => (
              <span key={i}>
                {line}
                {i < arr.length - 1 && <br />}
              </span>
            ))}
          </h1>
          <p className="landing-hero-subtitle">
            {t("landing.heroSubtitle")}
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" href="/register">
              {t("landing.ctaStartFree")}
            </Link>
            <Link className="btn btn-secondary" href="/login">
              {t("landing.ctaLogin")}
            </Link>
          </div>
        </section>

        {/* 핵심 장점 */}
        <section className="landing-section">
          <h2 className="landing-section-title">{t("landing.sectionTitleWhy")}</h2>
          <p className="landing-section-subtitle">
            {t("landing.sectionSubtitleFeatures")}
          </p>
          <FeatureCards />
        </section>

        {/* 처리 과정 */}
        <section className="landing-section">
          <h2 className="landing-section-title">{t("landing.sectionTitleWorkflow")}</h2>
          <p className="landing-section-subtitle">
            {t("landing.sectionSubtitleWorkflow")}
          </p>
          <WorkflowSteps />
        </section>

        {/* 대상 사용자 */}
        <section className="landing-section">
          <h2 className="landing-section-title">{t("landing.sectionTitleAudience")}</h2>
          <p className="landing-section-subtitle">
            {t("landing.sectionSubtitleAudience")}
          </p>
          <AudienceCards />
        </section>

        {/* Visionary */}
        <section className="landing-section">
          <h2 className="landing-section-title">{t("landing.sectionVisionary")}</h2>
          <p className="landing-section-subtitle">
            {t("landing.sectionSubtitleVisionary")}
          </p>
          <VisionarySection />
        </section>

        {/* 하단 CTA */}
        <section className="footer-cta">
          <h2 className="footer-cta-title">{t("landing.footerCtaTitle")}</h2>
          <p className="footer-cta-subtitle">
            {t("landing.footerCtaSubtitle")}
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" href="/register">
              {t("landing.ctaStartFree")}
            </Link>
            <Link className="btn btn-secondary" href="/login">
              {t("landing.ctaLogin")}
            </Link>
          </div>
        </section>
      </div>

      {/* Copyright footer */}
      <footer className="landing-footer">
        <p className="landing-footer-text">
          &copy; 2026 NeuroHub. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
