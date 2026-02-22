"use client";

import { ArrowRight } from "phosphor-react";
import type { ServiceRead } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface StepServiceSelectProps {
  services: ServiceRead[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNext: () => void;
}

export function StepServiceSelect({ services, selectedId, onSelect, onNext }: StepServiceSelectProps) {
  const t = useT();

  return (
    <div className="stack-lg">
      <p className="muted-text">{t("wizard.selectService")}</p>
      {services.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-text">{t("wizard.noServicesAvailable")}</p>
        </div>
      ) : (
        <div className="grid-2">
          {services.map((svc) => (
            <button
              key={svc.id}
              className={`type-selector-card ${selectedId === svc.id ? "selected" : ""}`}
              onClick={() => onSelect(svc.id)}
              style={{ textAlign: "left" }}
            >
              <p className="type-selector-title">{svc.display_name}</p>
              <p className="type-selector-desc">
                {svc.department || svc.name} &middot; v{svc.version}
              </p>
            </button>
          ))}
        </div>
      )}
      <div className="nav-buttons-end">
        <button className="btn btn-primary" disabled={!selectedId} onClick={onNext}>
          {t("common.next")} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
