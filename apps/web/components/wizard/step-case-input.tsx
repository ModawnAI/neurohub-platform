"use client";

import { ArrowLeft, ArrowRight, Plus, Trash } from "phosphor-react";
import { useT } from "@/lib/i18n";
import type { WizardCaseInput } from "./types";

interface StepCaseInputProps {
  cases: WizardCaseInput[];
  onChange: (cases: WizardCaseInput[]) => void;
  onNext: () => void;
  onPrev: () => void;
}

export function StepCaseInput({ cases, onChange, onNext, onPrev }: StepCaseInputProps) {
  const t = useT();

  function updatePatientRef(idx: number, val: string) {
    const next = [...cases];
    if (next[idx]) next[idx] = { ...next[idx], patient_ref: val };
    onChange(next);
  }

  function addCase() {
    onChange([...cases, { patient_ref: "", demographics: {} }]);
  }

  function removeCase(idx: number) {
    onChange(cases.filter((_, i) => i !== idx));
  }

  const hasValidCase = cases.some((c) => c.patient_ref.trim());

  return (
    <div className="stack-lg">
      <p className="muted-text">{t("wizard.enterCases")}</p>
      <div className="stack-md">
        {cases.map((c, idx) => (
          <div
            key={idx}
            className="panel"
            style={{ display: "flex", alignItems: "center", gap: 12, padding: 16, flexWrap: "wrap" }}
          >
            <span style={{ fontWeight: 700, color: "var(--muted)", fontSize: 13, flexShrink: 0 }}>
              #{idx + 1}
            </span>
            <input
              className="input"
              placeholder={t("wizard.patientRefPlaceholder")}
              value={c.patient_ref}
              onChange={(e) => updatePatientRef(idx, e.target.value)}
              style={{ flex: 1 }}
            />
            {cases.length > 1 && (
              <button className="btn btn-danger btn-sm" onClick={() => removeCase(idx)} title={t("common.delete")}>
                <Trash size={14} />
              </button>
            )}
          </div>
        ))}
      </div>
      <button className="btn btn-secondary btn-sm" onClick={addCase}>
        <Plus size={14} /> {t("wizard.addCase")}
      </button>
      <div className="nav-buttons">
        <button className="btn btn-secondary" onClick={onPrev}>
          <ArrowLeft size={16} /> {t("common.prev")}
        </button>
        <button className="btn btn-primary" disabled={!hasValidCase} onClick={onNext}>
          {t("common.next")} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
