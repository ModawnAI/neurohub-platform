"use client";

import { ArrowRight } from "phosphor-react";
import type { ServiceRead } from "@/lib/api";

interface StepServiceSelectProps {
  services: ServiceRead[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNext: () => void;
}

export function StepServiceSelect({ services, selectedId, onSelect, onNext }: StepServiceSelectProps) {
  return (
    <div className="stack-lg">
      <p className="muted-text">분석할 서비스를 선택하세요</p>
      {services.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-text">사용 가능한 서비스가 없습니다.</p>
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
          다음 <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
