"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash, Cpu, Package } from "phosphor-react";
import { listPipelines, createPipeline, type PipelineRead, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

interface PipelineStep {
  index: number;
  name: string;
  image: string;
  timeout_seconds: number;
  resources: {
    memory_gb: number;
    cpus: number;
    gpu: number;
    gpu_kind?: string;
  };
}

interface Props {
  service: ServiceRead;
}

export function ServicePipelines({ service }: Props) {
  const { locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const { data: pipelinesData, isLoading } = useQuery({
    queryKey: ["pipelines", service.id],
    queryFn: () => listPipelines(service.id),
  });
  const pipelines: PipelineRead[] = pipelinesData?.items ?? [];

  const [showCreate, setShowCreate] = useState(false);
  const [pipelineName, setPipelineName] = useState("");
  const [pipelineVersion, setPipelineVersion] = useState("1.0.0");
  const [steps, setSteps] = useState<PipelineStep[]>([]);

  const createMut = useMutation({
    mutationFn: () =>
      createPipeline(service.id, {
        name: pipelineName,
        version: pipelineVersion,
        steps: steps as unknown as Array<Record<string, unknown>>,
        is_default: pipelines.length === 0,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines", service.id] });
      setShowCreate(false);
      setPipelineName("");
      setSteps([]);
      addToast("success", ko ? "파이프라인 생성 완료" : "Pipeline created");
    },
    onError: () => addToast("error", ko ? "생성 실패" : "Create failed"),
  });

  const addStep = () => {
    setSteps([
      ...steps,
      {
        index: steps.length,
        name: `step_${steps.length + 1}`,
        image: `registry.fly.io/neurohub-svc-${service.name}:${service.version_label}`,
        timeout_seconds: 300,
        resources: { memory_gb: 2, cpus: 2, gpu: 0 },
      },
    ]);
  };

  const removeStep = (idx: number) => {
    setSteps(steps.filter((_, i) => i !== idx).map((s, i) => ({ ...s, index: i })));
  };

  const updateStep = (idx: number, patch: Partial<PipelineStep>) => {
    setSteps(steps.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };

  const updateStepResources = (idx: number, patch: Partial<PipelineStep["resources"]>) => {
    setSteps(steps.map((s, i) => (i === idx ? { ...s, resources: { ...s.resources, ...patch } } : s)));
  };

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 className="panel-title">{ko ? "파이프라인 & 컨테이너 스텝" : "Pipelines & Container Steps"}</h3>
          <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
            {ko ? "AI 분석을 실행할 파이프라인과 컨테이너 이미지를 설정합니다" : "Configure analysis pipelines with container steps"}
          </p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(!showCreate)}>
          <Plus size={14} /> {ko ? "파이프라인 생성" : "New Pipeline"}
        </button>
      </div>

      {/* Existing Pipelines */}
      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : pipelines.length === 0 && !showCreate ? (
        <p className="muted-text" style={{ fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          {ko ? "파이프라인이 없습니다. 새로 생성하세요." : "No pipelines. Create one to get started."}
        </p>
      ) : (
        <div className="stack-sm" style={{ marginBottom: showCreate ? 16 : 0 }}>
          {pipelines.map((p) => (
            <div key={p.id} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Cpu size={16} style={{ color: "var(--primary)" }} />
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</span>
                  <span className="mono-cell" style={{ fontSize: 11 }}>v{p.version}</span>
                  {p.is_default && <span className="status-chip status-final" style={{ fontSize: 10 }}>{ko ? "기본" : "Default"}</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Pipeline Form */}
      {showCreate && (
        <div style={{ border: "2px solid var(--primary)", borderRadius: "var(--radius-md)", padding: 16, background: "var(--primary-subtle)" }}>
          <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>{ko ? "새 파이프라인" : "New Pipeline"}</h4>
          <div className="stack-md">
            <div className="form-grid">
              <label className="field">
                {ko ? "파이프라인 이름" : "Pipeline Name"}
                <input className="input" value={pipelineName} onChange={(e) => setPipelineName(e.target.value)} placeholder={ko ? "기본 분석" : "default-analysis"} />
              </label>
              <label className="field">
                {ko ? "버전" : "Version"}
                <input className="input" value={pipelineVersion} onChange={(e) => setPipelineVersion(e.target.value)} />
              </label>
            </div>

            {/* Steps */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <p className="detail-label" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <Package size={14} /> {ko ? "실행 스텝" : "Execution Steps"} ({steps.length})
                </p>
                <button className="btn btn-secondary btn-sm" onClick={addStep} style={{ fontSize: 11 }}>
                  <Plus size={12} /> {ko ? "스텝 추가" : "Add Step"}
                </button>
              </div>

              {steps.length === 0 ? (
                <p className="muted-text" style={{ fontSize: 12, textAlign: "center", padding: 16 }}>
                  {ko ? "스텝을 추가하여 컨테이너 이미지와 리소스를 설정하세요" : "Add steps to configure container images and resources"}
                </p>
              ) : (
                <div className="stack-sm">
                  {steps.map((step, idx) => (
                    <div key={idx} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 12, background: "var(--surface)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>Step {idx + 1}</span>
                        <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={() => removeStep(idx)}>
                          <Trash size={12} />
                        </button>
                      </div>
                      <div className="stack-sm">
                        <div className="form-grid">
                          <label className="field">
                            {ko ? "스텝 이름" : "Step Name"}
                            <input className="input" value={step.name} onChange={(e) => updateStep(idx, { name: e.target.value })} placeholder="preprocess" />
                          </label>
                          <label className="field">
                            {ko ? "타임아웃 (초)" : "Timeout (sec)"}
                            <input className="input" type="number" min={10} value={step.timeout_seconds} onChange={(e) => updateStep(idx, { timeout_seconds: Number(e.target.value) })} />
                          </label>
                        </div>
                        <label className="field">
                          {ko ? "컨테이너 이미지" : "Container Image"}
                          <input
                            className="input"
                            value={step.image}
                            onChange={(e) => updateStep(idx, { image: e.target.value })}
                            placeholder="registry.fly.io/neurohub-svc-brain-mri:1.0.0"
                            style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
                          />
                        </label>
                        <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr" }}>
                          <label className="field">
                            {ko ? "메모리 (GB)" : "Memory (GB)"}
                            <input className="input" type="number" min={0.25} step={0.25} value={step.resources.memory_gb} onChange={(e) => updateStepResources(idx, { memory_gb: Number(e.target.value) })} />
                          </label>
                          <label className="field">
                            CPUs
                            <input className="input" type="number" min={1} value={step.resources.cpus} onChange={(e) => updateStepResources(idx, { cpus: Number(e.target.value) })} />
                          </label>
                          <label className="field">
                            GPUs
                            <input className="input" type="number" min={0} value={step.resources.gpu} onChange={(e) => updateStepResources(idx, { gpu: Number(e.target.value) })} />
                          </label>
                          {step.resources.gpu > 0 && (
                            <label className="field">
                              GPU Kind
                              <select className="input" value={step.resources.gpu_kind || "a100-pcie-40gb"} onChange={(e) => updateStepResources(idx, { gpu_kind: e.target.value })}>
                                <option value="a100-pcie-40gb">A100 40GB</option>
                                <option value="a100-sxm4-80gb">A100 80GB</option>
                                <option value="l40s">L40S</option>
                              </select>
                            </label>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="action-row">
              <button
                className="btn btn-primary"
                onClick={() => createMut.mutate()}
                disabled={!pipelineName || createMut.isPending}
              >
                {createMut.isPending ? <span className="spinner" /> : ko ? "파이프라인 생성" : "Create Pipeline"}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowCreate(false)}>
                {ko ? "취소" : "Cancel"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* SDK Guide */}
      <div style={{ marginTop: 16, padding: 12, background: "var(--surface-2)", borderRadius: "var(--radius-sm)" }}>
        <p style={{ fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{ko ? "SDK로 서비스 빌드" : "Build Service with SDK"}</p>
        <pre style={{ fontSize: 11, color: "var(--muted)", whiteSpace: "pre-wrap", margin: 0, fontFamily: "var(--font-mono)" }}>
{`pip install neurohub-sdk
neurohub init ${service.name}
cd ${service.name}
# ${ko ? "service.py 에 AI 모델 코드 작성" : "Write your AI model code in service.py"}
neurohub build
neurohub deploy`}
        </pre>
      </div>
    </div>
  );
}
