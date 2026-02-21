"use client";

import {
  ShieldCheck,
  CurrencyKrw,
  ArrowsClockwise,
  ClipboardText,
  Desktop,
  FirstAidKit,
  ChartLineUp,
} from "phosphor-react";

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

export function AudienceCards() {
  const audiences = [
    {
      icon: <Desktop size={22} weight="duotone" />,
      title: "병원 IT 관리자",
      desc: "AI 파이프라인 운영 자동화, API 키 관리, 시스템 모니터링",
    },
    {
      icon: <FirstAidKit size={22} weight="duotone" />,
      title: "영상의학과 전문의",
      desc: "분석 요청 생성, 결과 검토, 진단 보고서 확인",
    },
    {
      icon: <ChartLineUp size={22} weight="duotone" />,
      title: "의료기관 경영진",
      desc: "비용 현황 파악, 규제 준수 보고, 운영 효율성 모니터링",
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
