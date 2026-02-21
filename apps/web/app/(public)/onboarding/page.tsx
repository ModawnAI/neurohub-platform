"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Brain, User, MagnifyingGlass, GearSix, ArrowRight, ArrowLeft, Check } from "phosphor-react";
import { TypeSelector } from "@/components/type-selector";
import { completeOnboarding } from "@/lib/api";
import { useAuth, getRoleHomePath } from "@/lib/auth";

type UserType = "SERVICE_USER" | "EXPERT" | "ADMIN";
type OrgType = "individual" | "hospital";

const USER_TYPE_OPTIONS = [
  {
    value: "SERVICE_USER" as UserType,
    icon: <User size={24} weight="bold" />,
    title: "서비스 사용자",
    description: "의료 데이터를 AI 분석에 제출하고 결과를 확인합니다",
  },
  {
    value: "EXPERT" as UserType,
    icon: <MagnifyingGlass size={24} weight="bold" />,
    title: "전문가 리뷰어",
    description: "AI 분석 결과를 검토하고 품질을 검증합니다",
  },
  {
    value: "ADMIN" as UserType,
    icon: <GearSix size={24} weight="bold" />,
    title: "관리자",
    description: "시스템을 관리하고 사용자와 서비스를 운영합니다",
  },
];

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [userType, setUserType] = useState<UserType | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [phone, setPhone] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [bio, setBio] = useState("");
  const [orgType, setOrgType] = useState<OrgType>("individual");
  const [orgName, setOrgName] = useState("");
  const [orgCode, setOrgCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { refreshUser } = useAuth();

  function canProceedStep1() {
    return userType !== null;
  }

  function canProceedStep2() {
    if (!displayName.trim()) return false;
    if (userType === "ADMIN" && !orgName.trim()) return false;
    if (userType === "SERVICE_USER" && orgType === "hospital" && !orgName.trim()) return false;
    return true;
  }

  async function handleComplete() {
    setError("");
    setLoading(true);

    try {
      await completeOnboarding({
        user_type: userType!,
        display_name: displayName,
        phone: phone || undefined,
        specialization: userType === "EXPERT" ? specialization || undefined : undefined,
        bio: userType === "EXPERT" ? bio || undefined : undefined,
        organization_name: orgType === "hospital" || userType === "ADMIN" ? orgName : undefined,
        organization_code: orgType === "hospital" || userType === "ADMIN" ? orgCode || undefined : undefined,
        organization_type: userType === "ADMIN" ? "hospital" : orgType,
      });

      await refreshUser();
      router.push(getRoleHomePath(userType));
    } catch (err: any) {
      setError(err?.message || "온보딩에 실패했습니다.");
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ width: "min(640px, 100%)" }}>
        <div className="auth-brand">
          <div className="auth-brand-icon">
            <Brain size={22} weight="bold" />
          </div>
          <span className="auth-brand-text">NeuroHub</span>
        </div>

        {/* Step indicator */}
        <div className="step-indicator" style={{ justifyContent: "center", marginBottom: 24 }}>
          {[1, 2, 3].map((s, i) => (
            <div key={s} style={{ display: "flex", alignItems: "center" }}>
              {i > 0 && <div className="step-indicator-line" />}
              <div className={`step-indicator-item ${step === s ? "active" : step > s ? "done" : ""}`}>
                <div className="step-indicator-dot">{step > s ? <Check size={12} /> : s}</div>
                <span>{s === 1 ? "유형 선택" : s === 2 ? "프로필" : "완료"}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Step 1: User Type */}
        {step === 1 && (
          <div className="stack-lg">
            <div style={{ textAlign: "center" }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 6px" }}>어떤 역할로 사용하시겠어요?</h2>
              <p className="muted-text">사용 목적에 맞는 유형을 선택하세요</p>
            </div>
            <TypeSelector options={USER_TYPE_OPTIONS} selected={userType} onSelect={setUserType} />
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button className="btn btn-primary" disabled={!canProceedStep1()} onClick={() => setStep(2)}>
                다음 <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Profile */}
        {step === 2 && (
          <div className="stack-lg">
            <div style={{ textAlign: "center" }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 6px" }}>프로필을 설정하세요</h2>
              <p className="muted-text">기본 정보를 입력해주세요</p>
            </div>

            <div className="auth-form">
              <label className="field">
                표시 이름
                <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="홍길동" required />
              </label>

              <label className="field">
                연락처 (선택)
                <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="010-0000-0000" />
              </label>

              {userType === "EXPERT" && (
                <>
                  <label className="field">
                    전문 분야
                    <input className="input" value={specialization} onChange={(e) => setSpecialization(e.target.value)} placeholder="예: 신경영상, 뇌 MRI 분석" />
                  </label>
                  <label className="field">
                    소개 (선택)
                    <textarea className="textarea" value={bio} onChange={(e) => setBio(e.target.value)} placeholder="간단한 자기 소개를 입력하세요" rows={3} />
                  </label>
                </>
              )}

              {userType === "SERVICE_USER" && (
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>소속 유형</p>
                  <div className="grid-2">
                    <button
                      type="button"
                      className={`type-selector-card ${orgType === "individual" ? "selected" : ""}`}
                      onClick={() => setOrgType("individual")}
                      style={{ padding: 16 }}
                    >
                      <p className="type-selector-title" style={{ fontSize: 14 }}>개인 사용</p>
                      <p className="type-selector-desc">개인적으로 서비스를 이용합니다</p>
                    </button>
                    <button
                      type="button"
                      className={`type-selector-card ${orgType === "hospital" ? "selected" : ""}`}
                      onClick={() => setOrgType("hospital")}
                      style={{ padding: 16 }}
                    >
                      <p className="type-selector-title" style={{ fontSize: 14 }}>병원/의원 소속</p>
                      <p className="type-selector-desc">소속 기관에서 서비스를 이용합니다</p>
                    </button>
                  </div>
                </div>
              )}

              {(orgType === "hospital" || userType === "ADMIN") && (
                <>
                  <label className="field">
                    기관명
                    <input className="input" value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="OO 병원" required />
                  </label>
                  <label className="field">
                    기관 코드 (선택)
                    <input className="input" value={orgCode} onChange={(e) => setOrgCode(e.target.value)} placeholder="영문/숫자 조합 (예: hospital-01)" />
                  </label>
                </>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                <ArrowLeft size={16} /> 이전
              </button>
              <button className="btn btn-primary" disabled={!canProceedStep2()} onClick={() => setStep(3)}>
                다음 <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirmation */}
        {step === 3 && (
          <div className="stack-lg">
            <div style={{ textAlign: "center" }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 6px" }}>설정을 확인하세요</h2>
              <p className="muted-text">모든 정보가 올바른지 확인한 후 시작하세요</p>
            </div>

            <div className="panel" style={{ padding: 20 }}>
              <div className="stack-md">
                <div>
                  <p className="detail-label">사용자 유형</p>
                  <p className="detail-value">
                    {userType === "SERVICE_USER" ? "서비스 사용자" : userType === "EXPERT" ? "전문가 리뷰어" : "관리자"}
                  </p>
                </div>
                <div>
                  <p className="detail-label">이름</p>
                  <p className="detail-value">{displayName}</p>
                </div>
                {phone && (
                  <div>
                    <p className="detail-label">연락처</p>
                    <p className="detail-value">{phone}</p>
                  </div>
                )}
                {userType === "EXPERT" && specialization && (
                  <div>
                    <p className="detail-label">전문 분야</p>
                    <p className="detail-value">{specialization}</p>
                  </div>
                )}
                {(orgType === "hospital" || userType === "ADMIN") && orgName && (
                  <div>
                    <p className="detail-label">소속 기관</p>
                    <p className="detail-value">{orgName}</p>
                  </div>
                )}
              </div>
            </div>

            {userType === "EXPERT" && (
              <div className="banner banner-info">
                전문가 계정은 관리자 승인 후 리뷰 기능이 활성화됩니다.
              </div>
            )}

            {error && <p className="error-text">{error}</p>}

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <button className="btn btn-secondary" onClick={() => setStep(2)}>
                <ArrowLeft size={16} /> 이전
              </button>
              <button className="btn btn-primary" onClick={handleComplete} disabled={loading}>
                {loading ? <span className="spinner" /> : <>시작하기 <ArrowRight size={16} /></>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
