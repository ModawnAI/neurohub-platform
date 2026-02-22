"use client";

import { Check } from "phosphor-react";

interface StepIndicatorProps {
  steps: string[];
  current: number;
}

export function StepIndicator({ steps, current }: StepIndicatorProps) {
  return (
    <div className="step-indicator">
      {steps.map((label, i) => {
        const stepNum = i + 1;
        const state = current === stepNum ? "active" : current > stepNum ? "done" : "";
        return (
          <div key={label} style={{ display: "flex", alignItems: "center" }}>
            {i > 0 && <div className="step-indicator-line" />}
            <div className={`step-indicator-item ${state}`}>
              <div className="step-indicator-dot">
                {current > stepNum ? <Check size={12} /> : stepNum}
              </div>
              <span>{label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
