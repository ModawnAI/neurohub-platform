"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, Plus, Trash } from "phosphor-react";
import { listServices, listPipelines, createRequest } from "@/lib/api";

interface CaseInput {
  patient_ref: string;
  demographics: Record<string, string>;
}

export default function UserNewRequestPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [selectedServiceId, setSelectedServiceId] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseInput[]>([{ patient_ref: "", demographics: {} }]);
  const [error, setError] = useState("");

  const { data: servicesData } = useQuery({ queryKey: ["services"], queryFn: listServices });
  const services = servicesData?.items ?? [];

  const selectedService = services.find((s) => s.id === selectedServiceId);

  const { data: pipelinesData } = useQuery({
    queryKey: ["pipelines", selectedServiceId],
    queryFn: () => listPipelines(selectedServiceId!),
    enabled: !!selectedServiceId,
  });
  const defaultPipeline = pipelinesData?.items?.find((p) => p.is_default) || pipelinesData?.items?.[0];

  const createMut = useMutation({
    mutationFn: () =>
      createRequest({
        service_id: selectedServiceId!,
        pipeline_id: defaultPipeline!.id,
        priority: 5,
        cases: cases.filter((c) => c.patient_ref.trim()),
        idempotency_key: `web-${Date.now()}`,
      }),
    onSuccess: () => router.push("/user/requests"),
    onError: (err: any) => setError(err?.message || "요청 생성에 실패했습니다."),
  });

  function addCase() {
    setCases([...cases, { patient_ref: "", demographics: {} }]);
  }

  function removeCase(idx: number) {
    setCases(cases.filter((_, i) => i !== idx));
  }

  function updatePatientRef(idx: number, val: string) {
    const next = [...cases];
    if (next[idx]) next[idx].patient_ref = val;
    setCases(next);
  }

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/user/requests")}>
        <ArrowLeft size={16} /> 돌아가기
      </button>

      <h1 className="page-title">새 요청 만들기</h1>

      <div className="step-indicator">
        {["서비스 선택", "케이스 입력", "확인 및 제출"].map((label, i) => (
          <div key={label} style={{ display: "flex", alignItems: "center" }}>
            {i > 0 && <div className="step-indicator-line" />}
            <div className={`step-indicator-item ${step === i + 1 ? "active" : step > i + 1 ? "done" : ""}`}>
              <div className="step-indicator-dot">{step > i + 1 ? <Check size={12} /> : i + 1}</div>
              <span>{label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Step 1: Service Selection */}
      {step === 1 && (
        <div className="stack-lg">
          <p className="muted-text">분석할 서비스를 선택하세요</p>
          {services.length === 0 ? (
            <div className="empty-state"><p className="empty-state-text">사용 가능한 서비스가 없습니다.</p></div>
          ) : (
            <div className="grid-2">
              {services.map((svc) => (
                <button
                  key={svc.id}
                  className={`type-selector-card ${selectedServiceId === svc.id ? "selected" : ""}`}
                  onClick={() => setSelectedServiceId(svc.id)}
                  style={{ textAlign: "left" }}
                >
                  <p className="type-selector-title">{svc.display_name}</p>
                  <p className="type-selector-desc">{svc.department || svc.name} &middot; v{svc.version}</p>
                </button>
              ))}
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" disabled={!selectedServiceId} onClick={() => setStep(2)}>
              다음 <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Cases */}
      {step === 2 && (
        <div className="stack-lg">
          <p className="muted-text">환자 케이스 정보를 입력하세요</p>
          <div className="stack-md">
            {cases.map((c, idx) => (
              <div key={idx} className="panel" style={{ display: "flex", alignItems: "center", gap: 12, padding: 16 }}>
                <span style={{ fontWeight: 700, color: "var(--muted)", fontSize: 13, flexShrink: 0 }}>
                  #{idx + 1}
                </span>
                <input
                  className="input"
                  placeholder="환자 참조 ID"
                  value={c.patient_ref}
                  onChange={(e) => updatePatientRef(idx, e.target.value)}
                  style={{ flex: 1 }}
                />
                {cases.length > 1 && (
                  <button className="btn btn-danger btn-sm" onClick={() => removeCase(idx)} title="삭제">
                    <Trash size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-sm" onClick={addCase}>
            <Plus size={14} /> 케이스 추가
          </button>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button className="btn btn-secondary" onClick={() => setStep(1)}>
              <ArrowLeft size={16} /> 이전
            </button>
            <button
              className="btn btn-primary"
              disabled={!cases.some((c) => c.patient_ref.trim())}
              onClick={() => setStep(3)}
            >
              다음 <ArrowRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Confirm */}
      {step === 3 && (
        <div className="stack-lg">
          <div className="panel">
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: "0 0 16px" }}>요청 요약</h3>
            <div className="stack-md">
              <div>
                <p className="detail-label">서비스</p>
                <p className="detail-value">{selectedService?.display_name || "-"}</p>
              </div>
              <div>
                <p className="detail-label">케이스 수</p>
                <p className="detail-value">{cases.filter((c) => c.patient_ref.trim()).length}건</p>
              </div>
              <div>
                <p className="detail-label">환자 참조 ID</p>
                <p className="detail-value">{cases.filter((c) => c.patient_ref.trim()).map((c) => c.patient_ref).join(", ")}</p>
              </div>
            </div>
          </div>

          {error && <p className="error-text">{error}</p>}

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button className="btn btn-secondary" onClick={() => setStep(2)}>
              <ArrowLeft size={16} /> 이전
            </button>
            <button className="btn btn-primary" onClick={() => createMut.mutate()} disabled={createMut.isPending}>
              {createMut.isPending ? <span className="spinner" /> : <>요청 생성 <Check size={16} /></>}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
