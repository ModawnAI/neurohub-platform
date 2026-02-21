"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ShieldCheck,
  CurrencyKrw,
  ArrowsClockwise,
  ClipboardText,
  Desktop,
  FirstAidKit,
  ChartLineUp,
  Brain,
  List,
  X,
} from "phosphor-react";

export function LandingNav() {
  const [menuOpen, setMenuOpen] = useState(false);

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
          <Link href="/login" className="lnav-link">
            로그인
          </Link>
          <Link href="/register" className="lnav-cta">
            무료 시작하기
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="lnav-hamburger"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? "메뉴 닫기" : "메뉴 열기"}
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X size={22} weight="bold" /> : <List size={22} weight="bold" />}
        </button>
      </div>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div className="lnav-mobile">
          <div className="lnav-mobile-inner container">
            <Link href="/login" className="lnav-mobile-link" onClick={() => setMenuOpen(false)}>
              로그인
            </Link>
            <Link href="/register" className="lnav-mobile-cta" onClick={() => setMenuOpen(false)}>
              무료 시작하기
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}

export function FeatureCards() {
  const features = [
    {
      icon: <ShieldCheck size={22} weight="duotone" />,
      bg: "#dbeafe",
      color: "#1d4ed8",
      title: "규제 준수",
      desc: "의료 데이터 처리 규정에 맞춘 감사 추적과 접근 제어를 기본 제공합니다.",
    },
    {
      icon: <CurrencyKrw size={22} weight="duotone" />,
      bg: "#dcfce7",
      color: "#166534",
      title: "비용 관리",
      desc: "파이프라인별 리소스 사용량을 추적하고 우선순위 기반 스케줄링으로 비용을 절감합니다.",
    },
    {
      icon: <ArrowsClockwise size={22} weight="duotone" />,
      bg: "#ede9fe",
      color: "#6d28d9",
      title: "안정적 실행",
      desc: "멱등성 키, 트랜잭셔널 아웃박스, 자동 재시도로 데이터 유실 없는 실행을 보장합니다.",
    },
    {
      icon: <ClipboardText size={22} weight="duotone" />,
      bg: "#fef3c7",
      color: "#b45309",
      title: "완전한 감사 로그",
      desc: "모든 상태 전이, 사용자 행위, 취소 사유가 시간순으로 불변 기록됩니다.",
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
  const steps = [
    { num: 1, title: "요청 생성", desc: "서비스와 파이프라인을 선택하고 환자 케이스를 등록합니다." },
    { num: 2, title: "데이터 수신", desc: "DICOM 등 의료 데이터를 안전하게 업로드하고 무결성을 검증합니다." },
    { num: 3, title: "AI 분석", desc: "Celery 워커가 우선순위에 따라 분석을 비동기로 실행합니다." },
    { num: 4, title: "품질 검증", desc: "자동 QC와 전문가 검토를 통해 결과 품질을 보장합니다." },
    { num: 5, title: "보고서 생성", desc: "최종 검증된 결과를 PDF/JSON 보고서로 자동 생성합니다." },
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

export function VisionarySection() {
  return (
    <div className="visionary-card">
      <div className="visionary-photo">
        <Image
          src="/prof-park.png"
          alt="박해정 교수"
          width={180}
          height={180}
          className="visionary-img"
        />
      </div>
      <div className="visionary-body">
        <p className="visionary-label">Visionary</p>
        <h3 className="visionary-name">박해정 교수</h3>
        <p className="visionary-affiliation">
          연세대학교 의과대학 핵의학교실
        </p>
        <p className="visionary-bio">
          서울대학교 의용생체공학 박사, 하버드 의대 연구원 출신으로 시스템 뇌과학, 뇌영상학,
          인공지능 의학 응용 분야의 세계적 연구자입니다. 현재 연세대 시스템과학융합연구원 원장,
          중개뇌인지시스템 센터장을 맡고 있으며, 2024년 국제뇌기능매핑학회(OHBM) 조직위원장을
          역임했습니다. 뇌 연결망 모델링과 AI 기반 의료 영상 분석을 결합하여 NeuroHub의 비전을
          제시하고 있습니다.
        </p>
        <div className="visionary-fields">
          <span className="visionary-tag">시스템 뇌과학</span>
          <span className="visionary-tag">뇌영상학</span>
          <span className="visionary-tag">AI 의학 응용</span>
          <span className="visionary-tag">신경핵의학</span>
        </div>
      </div>
    </div>
  );
}

export function AudienceCards() {
  const audiences = [
    {
      icon: <FirstAidKit size={22} weight="duotone" />,
      title: "서비스 사용자",
      desc: "의료 데이터를 제출하고, AI 분석 결과와 보고서를 간편하게 확인하세요.",
    },
    {
      icon: <ChartLineUp size={22} weight="duotone" />,
      title: "전문가 리뷰어",
      desc: "AI 분석 결과를 검토하고, 품질 검증과 전문가 의견을 제공하세요.",
    },
    {
      icon: <Desktop size={22} weight="duotone" />,
      title: "관리자",
      desc: "시스템 운영, 사용자 관리, 서비스 구성을 한 곳에서 관리하세요.",
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
