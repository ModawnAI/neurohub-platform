"use client";

import { ArrowLeft, Check } from "phosphor-react";
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
  const validCases = cases.filter((c) => c.patient_ref.trim());
  const totalFiles = Object.values(uploadedFiles).reduce((sum, ids) => sum + ids.length, 0);

  return (
    <div className="stack-lg">
      <div className="panel">
        <h3 className="panel-title-mb">요청 요약</h3>
        <div className="stack-md">
          <div>
            <p className="detail-label">서비스</p>
            <p className="detail-value">{service?.display_name || "-"}</p>
          </div>
          <div>
            <p className="detail-label">케이스 수</p>
            <p className="detail-value">{validCases.length}건</p>
          </div>
          <div>
            <p className="detail-label">업로드된 파일</p>
            <p className="detail-value">{totalFiles}개</p>
          </div>
          <div>
            <p className="detail-label">환자 참조 ID</p>
            <p className="detail-value">
              {validCases.map((c) => c.patient_ref).join(", ")}
            </p>
          </div>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="nav-buttons">
        <button className="btn btn-secondary" onClick={onPrev}>
          <ArrowLeft size={16} /> 이전
        </button>
        <button className="btn btn-primary" onClick={onSubmit} disabled={isPending}>
          {isPending ? <span className="spinner" /> : <>요청 제출 <Check size={16} /></>}
        </button>
      </div>
    </div>
  );
}
