"use client";

import { ArrowLeft, Check } from "phosphor-react";
import { useT } from "@/lib/i18n";
import type { ServiceRead } from "@/lib/api";
import type { WizardCaseInput } from "./types";

interface StepReviewSubmitProps {
  service: ServiceRead | undefined;
  cases: WizardCaseInput[];
  uploadedFiles: Record<number, string[]>;
  onPrev: () => void;
  onSubmit: () => void;
  isPending: boolean;
  error: string;
}

export function StepReviewSubmit({
  service,
  cases,
  uploadedFiles,
  onPrev,
  onSubmit,
  isPending,
  error,
}: StepReviewSubmitProps) {
  const t = useT();
  const validCases = cases.filter((c) => c.patient_ref.trim());
  const totalFiles = Object.values(uploadedFiles).reduce((sum, ids) => sum + ids.length, 0);

  return (
    <div className="stack-lg">
      <div className="panel">
        <h3 className="panel-title-mb">{t("wizard.requestSummary")}</h3>
        <div className="stack-md">
          <div>
            <p className="detail-label">{t("requestDetail.service")}</p>
            <p className="detail-value">{service?.display_name || "-"}</p>
          </div>
          <div>
            <p className="detail-label">{t("requestDetail.caseCount")}</p>
            <p className="detail-value">{validCases.length}건</p>
          </div>
          <div>
            <p className="detail-label">{t("wizard.uploadedFiles")}</p>
            <p className="detail-value">{totalFiles}개</p>
          </div>
          <div>
            <p className="detail-label">{t("wizard.patientRefIds")}</p>
            <p className="detail-value">
              {validCases.map((c) => c.patient_ref).join(", ")}
            </p>
          </div>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="nav-buttons">
        <button className="btn btn-secondary" onClick={onPrev}>
          <ArrowLeft size={16} /> {t("common.prev")}
        </button>
        <button className="btn btn-primary" onClick={onSubmit} disabled={isPending}>
          {isPending ? <span className="spinner" /> : <>{t("wizard.submitRequest")} <Check size={16} /></>}
        </button>
      </div>
    </div>
  );
}
