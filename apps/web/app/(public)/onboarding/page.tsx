"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Brain, User, MagnifyingGlass, GearSix, ArrowRight, ArrowLeft, Check } from "phosphor-react";
import { TypeSelector } from "@/components/type-selector";
import { completeOnboarding } from "@/lib/api";
import { useAuth, getRoleHomePath } from "@/lib/auth";
import { useZodForm } from "@/lib/use-zod-form";
import { onboardingSchema, type OnboardingFormValues } from "@/lib/schemas";
import { useT } from "@/lib/i18n";

type UserType = "SERVICE_USER" | "EXPERT" | "ADMIN";
type OrgType = "individual" | "hospital";

const INITIAL: OnboardingFormValues = {
  user_type: "SERVICE_USER",
  display_name: "",
  phone: "",
  specialization: "",
  bio: "",
  organization_name: "",
  organization_code: "",
  organization_type: "individual",
};

export default function OnboardingPage() {
  const t = useT();
  const [step, setStep] = useState(1);

  const USER_TYPE_OPTIONS = [
    {
      value: "SERVICE_USER" as UserType,
      icon: <User size={24} weight="bold" />,
      title: t("userType.SERVICE_USER"),
      description: t("onboarding.serviceUserDesc"),
    },
    {
      value: "EXPERT" as UserType,
      icon: <MagnifyingGlass size={24} weight="bold" />,
      title: t("userType.EXPERT"),
      description: t("onboarding.expertDesc"),
    },
    {
      value: "ADMIN" as UserType,
      icon: <GearSix size={24} weight="bold" />,
      title: t("userType.ADMIN"),
      description: t("onboarding.adminDesc"),
    },
  ];
  const [orgType, setOrgType] = useState<OrgType>("individual");
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { refreshUser } = useAuth();

  const { values, errors, setField, validate } = useZodForm(onboardingSchema, INITIAL);

  const userType = values.user_type as UserType;

  function canProceedStep1() {
    return !!userType;
  }

  function canProceedStep2() {
    if (!values.display_name.trim()) return false;
    if (userType === "ADMIN" && !values.organization_name?.trim()) return false;
    if (userType === "SERVICE_USER" && orgType === "hospital" && !values.organization_name?.trim()) return false;
    return true;
  }

  function handleNextToStep3() {
    setField("organization_type", userType === "ADMIN" ? "hospital" : orgType);
    const result = validate();
    if (!result) return;
    setStep(3);
  }

  async function handleComplete() {
    setApiError("");
    setLoading(true);

    try {
      await completeOnboarding({
        user_type: userType,
        display_name: values.display_name,
        phone: values.phone || undefined,
        specialization: userType === "EXPERT" ? values.specialization || undefined : undefined,
        bio: userType === "EXPERT" ? values.bio || undefined : undefined,
        organization_name: orgType === "hospital" || userType === "ADMIN" ? values.organization_name : undefined,
        organization_code: orgType === "hospital" || userType === "ADMIN" ? values.organization_code || undefined : undefined,
        organization_type: userType === "ADMIN" ? "hospital" : orgType,
      });

      await refreshUser();
      router.push(getRoleHomePath(userType));
    } catch (err: any) {
      setApiError(err?.message || t("onboarding.errorFailed"));
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
                <span>{s === 1 ? t("onboarding.stepTypeSelection") : s === 2 ? t("onboarding.stepProfile") : t("onboarding.stepCompletion")}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Step 1: User Type */}
        {step === 1 && (
          <div className="stack-lg">
            <div style={{ textAlign: "center" }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 6px" }}>{t("onboarding.titleStep1")}</h2>
              <p className="muted-text">{t("onboarding.subtitleStep1")}</p>
            </div>
            <TypeSelector
              options={USER_TYPE_OPTIONS}
              selected={userType}
              onSelect={(val) => setField("user_type", val)}
            />
            <div className="nav-buttons-end">
              <button className="btn btn-primary" disabled={!canProceedStep1()} onClick={() => setStep(2)}>
                {t("common.next")} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Profile */}
        {step === 2 && (
          <div className="stack-lg">
            <div style={{ textAlign: "center" }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 6px" }}>{t("onboarding.titleStep2")}</h2>
              <p className="muted-text">{t("onboarding.subtitleStep2")}</p>
            </div>

            <div className="auth-form">
              <label className="field">
                {t("onboarding.displayName")}
                <input
                  className="input"
                  value={values.display_name}
                  onChange={(e) => setField("display_name", e.target.value)}
                  placeholder={t("onboarding.namePlaceholder")}
                />
                {errors.display_name && <span className="error-text">{errors.display_name}</span>}
              </label>

              <label className="field">
                {t("onboarding.phoneOptional")}
                <input
                  className="input"
                  value={values.phone ?? ""}
                  onChange={(e) => setField("phone", e.target.value)}
                  placeholder={t("onboarding.phonePlaceholder")}
                />
              </label>

              {userType === "EXPERT" && (
                <>
                  <label className="field">
                    {t("onboarding.specialization")}
                    <input
                      className="input"
                      value={values.specialization ?? ""}
                      onChange={(e) => setField("specialization", e.target.value)}
                      placeholder={t("onboarding.specializationPlaceholder")}
                    />
                  </label>
                  <label className="field">
                    {t("onboarding.bioOptional")}
                    <textarea
                      className="textarea"
                      value={values.bio ?? ""}
                      onChange={(e) => setField("bio", e.target.value)}
                      placeholder={t("onboarding.bioPlaceholder")}
                      rows={3}
                    />
                  </label>
                </>
              )}

              {userType === "SERVICE_USER" && (
                <div>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginBottom: 8 }}>{t("onboarding.orgType")}</p>
                  <div className="grid-2">
                    <button
                      type="button"
                      className={`type-selector-card ${orgType === "individual" ? "selected" : ""}`}
                      onClick={() => setOrgType("individual")}
                      style={{ padding: 16 }}
                    >
                      <p className="type-selector-title" style={{ fontSize: 14 }}>{t("onboarding.orgTypeIndividual")}</p>
                      <p className="type-selector-desc">{t("onboarding.orgTypeIndividualDesc")}</p>
                    </button>
                    <button
                      type="button"
                      className={`type-selector-card ${orgType === "hospital" ? "selected" : ""}`}
                      onClick={() => setOrgType("hospital")}
                      style={{ padding: 16 }}
                    >
                      <p className="type-selector-title" style={{ fontSize: 14 }}>{t("onboarding.orgTypeHospital")}</p>
                      <p className="type-selector-desc">{t("onboarding.orgTypeHospitalDesc")}</p>
                    </button>
                  </div>
                </div>
              )}

              {(orgType === "hospital" || userType === "ADMIN") && (
                <>
                  <label className="field">
                    {t("onboarding.orgName")}
                    <input
                      className="input"
                      value={values.organization_name ?? ""}
                      onChange={(e) => setField("organization_name", e.target.value)}
                      placeholder={t("onboarding.orgNamePlaceholder")}
                    />
                    {errors.organization_name && <span className="error-text">{errors.organization_name}</span>}
                  </label>
                  <label className="field">
                    {t("onboarding.orgCodeOptional")}
                    <input
                      className="input"
                      value={values.organization_code ?? ""}
                      onChange={(e) => setField("organization_code", e.target.value)}
                      placeholder={t("onboarding.orgCodePlaceholder")}
                    />
                  </label>
                </>
              )}
            </div>

            <div className="nav-buttons">
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                <ArrowLeft size={16} /> {t("common.prev")}
              </button>
              <button className="btn btn-primary" disabled={!canProceedStep2()} onClick={handleNextToStep3}>
                {t("common.next")} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirmation */}
        {step === 3 && (
          <div className="stack-lg">
            <div style={{ textAlign: "center" }}>
              <h2 style={{ fontSize: 20, fontWeight: 800, margin: "0 0 6px" }}>{t("onboarding.titleStep3")}</h2>
              <p className="muted-text">{t("onboarding.subtitleStep3")}</p>
            </div>

            <div className="panel" style={{ padding: 20 }}>
              <div className="stack-md">
                <div>
                  <p className="detail-label">{t("onboarding.summaryUserType")}</p>
                  <p className="detail-value">
                    {t(`userType.${userType}` as any)}
                  </p>
                </div>
                <div>
                  <p className="detail-label">{t("onboarding.summaryName")}</p>
                  <p className="detail-value">{values.display_name}</p>
                </div>
                {values.phone && (
                  <div>
                    <p className="detail-label">{t("onboarding.summaryPhone")}</p>
                    <p className="detail-value">{values.phone}</p>
                  </div>
                )}
                {userType === "EXPERT" && values.specialization && (
                  <div>
                    <p className="detail-label">{t("onboarding.summarySpecialization")}</p>
                    <p className="detail-value">{values.specialization}</p>
                  </div>
                )}
                {(orgType === "hospital" || userType === "ADMIN") && values.organization_name && (
                  <div>
                    <p className="detail-label">{t("onboarding.summaryOrg")}</p>
                    <p className="detail-value">{values.organization_name}</p>
                  </div>
                )}
              </div>
            </div>

            {userType === "EXPERT" && (
              <div className="banner banner-info">
                {t("onboarding.expertAccountNote")}
              </div>
            )}

            {apiError && <p className="error-text">{apiError}</p>}

            <div className="nav-buttons">
              <button className="btn btn-secondary" onClick={() => setStep(2)}>
                <ArrowLeft size={16} /> {t("common.prev")}
              </button>
              <button className="btn btn-primary" onClick={handleComplete} disabled={loading}>
                {loading ? <span className="spinner" /> : <>{t("onboarding.startNow")} <ArrowRight size={16} /></>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
