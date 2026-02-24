"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useT } from "@/lib/i18n";
import { useLocale } from "@/lib/i18n";
import {
  ShieldCheck,
  ArrowsClockwise,
  Desktop,
  FirstAidKit,
  ChartLineUp,
  Brain,
  List,
  X,
  Globe,
  Exam,
  CreditCard,
  Stamp,
  DownloadSimple,
  UserCircle,
  MagnifyingGlass,
  ClipboardText,
  ListChecks,
  FileSearch,
  CheckCircle,
  Gear,
  Monitor,
  Buildings,
} from "phosphor-react";

export function LandingNav() {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [menuOpen, setMenuOpen] = useState(false);

  const toggleLocale = () => setLocale(locale === "ko" ? "en" : "ko");

  return (
    <nav className="lnav">
      <div className="lnav-inner container">
        {/* Brand */}
        <Link href="/" className="lnav-brand">
          <div className="lnav-logo">
            <Brain size={18} weight="bold" />
          </div>
          <span className="lnav-wordmark">NeuroHub</span>
        </Link>

        {/* Desktop actions */}
        <div className="lnav-actions">
          <button
            onClick={toggleLocale}
            className="lnav-lang-btn"
            title={locale === "ko" ? t("sidebar.switchToEn") : t("sidebar.switchToKo")}
          >
            <Globe size={16} />
            {locale === "ko" ? "EN" : "KO"}
          </button>
          <Link href="/login" className="lnav-link">
            {t("landing.ctaLogin")}
          </Link>
          <Link href="/register" className="lnav-cta">
            {t("landing.ctaStartFree")}
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="lnav-hamburger"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? t("landing.menuClose") : t("landing.menuOpen")}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={22} weight="bold" /> : <List size={22} weight="bold" />}
        </button>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="lnav-mobile">
          <div className="lnav-mobile-inner container">
            <button onClick={toggleLocale} className="lnav-mobile-lang">
              <Globe size={16} />
              {locale === "ko" ? "English" : "한국어"}
            </button>
            <Link href="/login" className="lnav-mobile-link" onClick={() => setMenuOpen(false)}>
              {t("landing.ctaLogin")}
            </Link>
            <Link href="/register" className="lnav-mobile-cta" onClick={() => setMenuOpen(false)}>
              {t("landing.ctaStartFree")}
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

export function FeatureCards() {
  const t = useT();

  const features = [
    {
      icon: <Exam size={22} weight="duotone" />,
      bg: "#dbeafe",
      color: "#1d4ed8",
      title: t("landing.featureEvaluation"),
      desc: t("landing.featureEvaluationDesc"),
    },
    {
      icon: <CreditCard size={22} weight="duotone" />,
      bg: "#dcfce7",
      color: "#166534",
      title: t("landing.featurePayment"),
      desc: t("landing.featurePaymentDesc"),
    },
    {
      icon: <Stamp size={22} weight="duotone" />,
      bg: "#ede9fe",
      color: "#6d28d9",
      title: t("landing.featureWatermark"),
      desc: t("landing.featureWatermarkDesc"),
    },
    {
      icon: <DownloadSimple size={22} weight="duotone" />,
      bg: "#fef3c7",
      color: "#b45309",
      title: t("landing.featureDownload"),
      desc: t("landing.featureDownloadDesc"),
    },
    {
      icon: <ShieldCheck size={22} weight="duotone" />,
      bg: "#fce4ec",
      color: "#c62828",
      title: t("landing.featureCompliance"),
      desc: t("landing.featureComplianceDesc"),
    },
    {
      icon: <ArrowsClockwise size={22} weight="duotone" />,
      bg: "#e0f2f1",
      color: "#00695c",
      title: t("landing.featureReliability"),
      desc: t("landing.featureReliabilityDesc"),
    },
  ];

  return (
    <div className="feature-grid">
      {features.map((f) => (
        <div key={f.title} className="feature-card">
          <div className="feature-card-icon" style={{ background: f.bg, color: f.color }}>
            {f.icon}
          </div>
          <p className="feature-card-title">{f.title}</p>
          <p className="feature-card-desc">{f.desc}</p>
        </div>
      ))}
    </div>
  );
}

export function WorkflowSteps() {
  const t = useT();

  const steps = [
    { num: 1, title: t("landing.workflowStep1Title"), desc: t("landing.workflowStep1Desc") },
    { num: 2, title: t("landing.workflowStep2Title"), desc: t("landing.workflowStep2Desc") },
    { num: 3, title: t("landing.workflowStep3Title"), desc: t("landing.workflowStep3Desc") },
    { num: 4, title: t("landing.workflowStep4Title"), desc: t("landing.workflowStep4Desc") },
    { num: 5, title: t("landing.workflowStep5Title"), desc: t("landing.workflowStep5Desc") },
    { num: 6, title: t("landing.workflowStep6Title"), desc: t("landing.workflowStep6Desc") },
    { num: 7, title: t("landing.workflowStep7Title"), desc: t("landing.workflowStep7Desc") },
  ];

  return (
    <div className="workflow-steps">
      {steps.map((s, i) => (
        <div key={s.num} className="workflow-step">
          {i < steps.length - 1 && <div className="workflow-connector" />}
          <div className="workflow-step-number">{s.num}</div>
          <div>
            <p className="workflow-step-title">{s.title}</p>
            <p className="workflow-step-desc">{s.desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export function UsageGuide() {
  const t = useT();
  const [activeTab, setActiveTab] = useState<"user" | "expert" | "admin">("user");

  const tabs = [
    { key: "user" as const, label: t("landing.guideTabUser"), icon: <FirstAidKit size={16} /> },
    { key: "expert" as const, label: t("landing.guideTabExpert"), icon: <ChartLineUp size={16} /> },
    { key: "admin" as const, label: t("landing.guideTabAdmin"), icon: <Desktop size={16} /> },
  ];

  const guides = {
    user: [
      { icon: <ClipboardText size={20} weight="duotone" />, title: t("landing.guideUserStep1Title"), desc: t("landing.guideUserStep1Desc") },
      { icon: <MagnifyingGlass size={20} weight="duotone" />, title: t("landing.guideUserStep2Title"), desc: t("landing.guideUserStep2Desc") },
      { icon: <DownloadSimple size={20} weight="duotone" />, title: t("landing.guideUserStep3Title"), desc: t("landing.guideUserStep3Desc") },
    ],
    expert: [
      { icon: <ListChecks size={20} weight="duotone" />, title: t("landing.guideExpertStep1Title"), desc: t("landing.guideExpertStep1Desc") },
      { icon: <FileSearch size={20} weight="duotone" />, title: t("landing.guideExpertStep2Title"), desc: t("landing.guideExpertStep2Desc") },
      { icon: <CheckCircle size={20} weight="duotone" />, title: t("landing.guideExpertStep3Title"), desc: t("landing.guideExpertStep3Desc") },
    ],
    admin: [
      { icon: <Gear size={20} weight="duotone" />, title: t("landing.guideAdminStep1Title"), desc: t("landing.guideAdminStep1Desc") },
      { icon: <Monitor size={20} weight="duotone" />, title: t("landing.guideAdminStep2Title"), desc: t("landing.guideAdminStep2Desc") },
      { icon: <Buildings size={20} weight="duotone" />, title: t("landing.guideAdminStep3Title"), desc: t("landing.guideAdminStep3Desc") },
    ],
  };

  const steps = guides[activeTab];

  return (
    <div className="guide-section">
      <div className="guide-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`guide-tab${activeTab === tab.key ? " guide-tab--active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>
      <div className="guide-content">
        {steps.map((step, i) => (
          <div key={i} className="guide-step">
            <div className="guide-step-number">{i + 1}</div>
            <div className="guide-step-icon">{step.icon}</div>
            <div>
              <p className="guide-step-title">{step.title}</p>
              <p className="guide-step-desc">{step.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function VisionarySection() {
  const t = useT();

  return (
    <div className="visionary-card">
      <div className="visionary-photo">
        <Image
          src="/prof-park.png"
          alt={t("landing.visionaryName")}
          width={180}
          height={180}
          className="visionary-img"
        />
      </div>
      <div className="visionary-body">
        <p className="visionary-label">{t("landing.sectionVisionary")}</p>
        <h3 className="visionary-name">{t("landing.visionaryName")}</h3>
        <p className="visionary-affiliation">
          {t("landing.visionaryAffiliation")}
        </p>
        <p className="visionary-bio">
          {t("landing.visionaryBio")}
        </p>
        <div className="visionary-fields">
          <span className="visionary-tag">{t("landing.visionaryTag1")}</span>
          <span className="visionary-tag">{t("landing.visionaryTag2")}</span>
          <span className="visionary-tag">{t("landing.visionaryTag3")}</span>
          <span className="visionary-tag">{t("landing.visionaryTag4")}</span>
        </div>
      </div>
    </div>
  );
}

export function AudienceCards() {
  const t = useT();

  const audiences = [
    {
      icon: <FirstAidKit size={22} weight="duotone" />,
      title: t("landing.audienceUser"),
      desc: t("landing.audienceUserDesc"),
    },
    {
      icon: <ChartLineUp size={22} weight="duotone" />,
      title: t("landing.audienceExpert"),
      desc: t("landing.audienceExpertDesc"),
    },
    {
      icon: <Desktop size={22} weight="duotone" />,
      title: t("landing.audienceAdmin"),
      desc: t("landing.audienceAdminDesc"),
    },
  ];

  return (
    <div className="audience-grid">
      {audiences.map((a) => (
        <div key={a.title} className="audience-card">
          <div className="audience-card-icon">{a.icon}</div>
          <p className="audience-card-title">{a.title}</p>
          <p className="audience-card-desc">{a.desc}</p>
        </div>
      ))}
    </div>
  );
}
