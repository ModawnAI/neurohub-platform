"use client";

import { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowLeft, ArrowRight, Check, UploadSimple, Package, Cpu,
  Brain, FirstAid, Heartbeat, WaveSquare, MagnifyingGlass, Lightning,
} from "phosphor-react";
import {
  createService, createPipeline,
  presignPackageUpload, completePackageUpload, uploadFileToStorage,
  type ServiceRead,
} from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

/* ─── Templates ─── */
const TEMPLATES = [
  { key: "brain_mri", icon: <Brain size={28} />, ko: "뇌 MRI 분석", en: "Brain MRI Analysis", desc_ko: "T1, FLAIR, DWI 등 뇌 MRI 영상 분석", desc_en: "Cortical thickness, VBM, lesion segmentation", inputs: ["DICOM", "NIfTI"], category: "neuroimaging" },
  { key: "pet_analysis", icon: <MagnifyingGlass size={28} />, ko: "PET 분석", en: "PET Analysis", desc_ko: "FDG, Amyloid, Tau PET 정량 분석", desc_en: "FDG, Amyloid, Tau PET quantification", inputs: ["DICOM", "NIfTI"], category: "nuclear_medicine" },
  { key: "eeg_analysis", icon: <WaveSquare size={28} />, ko: "EEG 분석", en: "EEG Analysis", desc_ko: "EEG 소스 분석, 스펙트럼 분석", desc_en: "Source localization, spectral analysis", inputs: ["EEG", "EDF", "SET"], category: "neurophysiology" },
  { key: "cardiac", icon: <Heartbeat size={28} />, ko: "심장 영상 분석", en: "Cardiac Imaging", desc_ko: "심장 MRI/CT 기반 기능 분석", desc_en: "Cardiac MRI/CT functional analysis", inputs: ["DICOM"], category: "cardiology" },
  { key: "pathology", icon: <FirstAid size={28} />, ko: "병리 분석", en: "Pathology Analysis", desc_ko: "병리 슬라이드 디지털 분석", desc_en: "Digital pathology slide analysis", inputs: ["PNG", "JPEG", "ZIP"], category: "pathology" },
  { key: "custom", icon: <Lightning size={28} />, ko: "커스텀 서비스", en: "Custom Service", desc_ko: "직접 구성하는 맞춤형 서비스", desc_en: "Build your own custom service", inputs: [], category: "custom" },
] as const;

type Step = 1 | 2 | 3;

export default function NewServicePage() {
  const router = useRouter();
  const { locale } = useTranslation();
  const ko = locale === "ko";
  const { addToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>(1);

  // Step 1: Template + Upload
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  // Step 2: Basic info
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [department, setDepartment] = useState("");
  const [description, setDescription] = useState("");
  const [serviceType, setServiceType] = useState<"AUTOMATIC" | "HUMAN_IN_LOOP">("AUTOMATIC");

  // Step 3: Pipeline
  const [containerImage, setContainerImage] = useState("");
  const [memoryGb, setMemoryGb] = useState(2);
  const [cpuCount, setCpuCount] = useState(2);
  const [timeout, setTimeoutSec] = useState(300);

  // Created service ref
  const [createdService, setCreatedService] = useState<ServiceRead | null>(null);

  // Auto-fill from template
  const selectTemplate = (key: string) => {
    setSelectedTemplate(key);
    const tmpl = TEMPLATES.find((t) => t.key === key);
    if (tmpl && key !== "custom") {
      setName(key);
      setDisplayName(ko ? tmpl.ko : tmpl.en);
      setDescription(ko ? tmpl.desc_ko : tmpl.desc_en);
    }
  };

  // File upload handler
  const handleFile = useCallback((file: File) => {
    const allowed = [".zip", ".tar.gz", ".tgz", ".py", ".whl"];
    if (!allowed.some((ext) => file.name.toLowerCase().endsWith(ext))) {
      addToast("error", ko ? `허용 형식: ${allowed.join(", ")}` : `Allowed: ${allowed.join(", ")}`);
      return;
    }
    setUploadedFile(file);
  }, [ko, addToast]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  // Create service + upload package + create pipeline in one go
  const submitMut = useMutation({
    mutationFn: async () => {
      // 1. Create the service
      const svc = await createService({
        name: name.toLowerCase().replace(/[^a-z0-9_-]/g, "_"),
        display_name: displayName,
        department: department || undefined,
        description: description || undefined,
        service_type: serviceType,
      });
      setCreatedService(svc);

      // 2. Upload package if provided
      if (uploadedFile) {
        setUploading(true);
        setUploadProgress(0);
        const presign = await presignPackageUpload(svc.id, {
          file_name: uploadedFile.name,
          content_type: uploadedFile.type || "application/octet-stream",
          file_size: uploadedFile.size,
        });
        await uploadFileToStorage(presign.presigned_url, uploadedFile, (pct) => setUploadProgress(pct));
        await completePackageUpload(svc.id, {
          storage_path: presign.storage_path,
          file_name: uploadedFile.name,
          file_size: uploadedFile.size,
        });
        setUploading(false);
      }

      // 3. Create default pipeline with container step
      const image = containerImage || `registry.fly.io/neurohub-svc-${svc.name}:${svc.version_label}`;
      await createPipeline(svc.id, {
        name: "default",
        version: "1.0.0",
        is_default: true,
        steps: [
          {
            index: 0,
            name: "compute",
            image,
            timeout_seconds: timeout,
            resources: { memory_gb: memoryGb, cpus: cpuCount, gpu: 0 },
          },
        ],
      });

      return svc;
    },
    onSuccess: (svc) => {
      addToast("success", ko ? "서비스가 등록되었습니다!" : "Service registered!");
      router.push(`/admin/services/${svc.id}`);
    },
    onError: (err) => {
      setUploading(false);
      addToast("error", `${ko ? "등록 실패" : "Registration failed"}: ${(err as Error).message}`);
    },
  });

  const canProceedStep1 = selectedTemplate !== null;
  const canProceedStep2 = name.trim().length > 0 && displayName.trim().length > 0;

  const STEPS = [
    { num: 1, label: ko ? "서비스 선택" : "Choose Type", labelShort: "1" },
    { num: 2, label: ko ? "기본 정보" : "Details", labelShort: "2" },
    { num: 3, label: ko ? "실행 환경" : "Runtime", labelShort: "3" },
  ];

  return (
    <div className="stack-lg" style={{ maxWidth: 720, margin: "0 auto" }}>
      {/* Back link */}
      <button className="back-link" onClick={() => router.push("/admin/services")}>
        <ArrowLeft size={16} /> {ko ? "서비스 목록으로" : "Back to services"}
      </button>

      {/* Header */}
      <div style={{ textAlign: "center" }}>
        <h1 className="page-title">{ko ? "새 서비스 등록" : "Register New Service"}</h1>
        <p className="page-subtitle">{ko ? "AI 분석 서비스를 등록하고 배포하세요" : "Register and deploy your AI analysis service"}</p>
      </div>

      {/* Step indicator */}
      <div style={{ display: "flex", justifyContent: "center", gap: 0, marginBottom: 8 }}>
        {STEPS.map((s, i) => (
          <div key={s.num} style={{ display: "flex", alignItems: "center" }}>
            <div
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "6px 14px", borderRadius: 20,
                background: step === s.num ? "var(--primary)" : step > s.num ? "var(--success)" : "var(--surface-2)",
                color: step >= s.num ? "#fff" : "var(--muted)",
                fontSize: 12, fontWeight: 600,
                transition: "all 0.2s",
              }}
            >
              {step > s.num ? <Check size={12} weight="bold" /> : s.labelShort}
              <span>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ width: 32, height: 2, background: step > s.num ? "var(--success)" : "var(--border)" }} />
            )}
          </div>
        ))}
      </div>

      {/* ── Step 1: Template + Upload ── */}
      {step === 1 && (
        <div className="stack-lg">
          {/* Template Grid */}
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
              {ko ? "서비스 유형을 선택하세요" : "Choose a service type"}
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
              {TEMPLATES.map((tmpl) => (
                <button
                  key={tmpl.key}
                  onClick={() => selectTemplate(tmpl.key)}
                  style={{
                    display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 8,
                    padding: 16, borderRadius: "var(--radius-md)",
                    border: `2px solid ${selectedTemplate === tmpl.key ? "var(--primary)" : "var(--border)"}`,
                    background: selectedTemplate === tmpl.key ? "var(--primary-subtle)" : "var(--surface)",
                    cursor: "pointer", textAlign: "left", transition: "all 0.15s",
                  }}
                >
                  <div style={{ color: selectedTemplate === tmpl.key ? "var(--primary)" : "var(--muted)" }}>
                    {tmpl.icon}
                  </div>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: 600 }}>{ko ? tmpl.ko : tmpl.en}</p>
                    <p className="muted-text" style={{ fontSize: 11, marginTop: 2 }}>{ko ? tmpl.desc_ko : tmpl.desc_en}</p>
                  </div>
                  {tmpl.inputs.length > 0 && (
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {tmpl.inputs.map((t) => (
                        <span key={t} className="status-chip" style={{ fontSize: 9, padding: "1px 6px" }}>{t}</span>
                      ))}
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Upload Zone */}
          <div>
            <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
              {ko ? "AI 모델 패키지 업로드" : "Upload AI Model Package"}
              <span className="muted-text" style={{ fontSize: 11, fontWeight: 400, marginLeft: 6 }}>({ko ? "선택사항" : "optional"})</span>
            </p>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${dragOver ? "var(--primary)" : uploadedFile ? "var(--success)" : "var(--border)"}`,
                borderRadius: "var(--radius-md)", padding: "24px 16px",
                textAlign: "center", cursor: "pointer",
                background: dragOver ? "var(--primary-subtle)" : uploadedFile ? "var(--success-light)" : "transparent",
                transition: "all 0.15s",
              }}
            >
              <input ref={fileInputRef} type="file" accept=".zip,.tar.gz,.tgz,.py,.whl" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }} style={{ display: "none" }} />
              {uploadedFile ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                  <Package size={20} style={{ color: "var(--success)" }} />
                  <span style={{ fontSize: 13, fontWeight: 500 }}>{uploadedFile.name}</span>
                  <span className="muted-text" style={{ fontSize: 11 }}>({(uploadedFile.size / 1024 / 1024).toFixed(1)} MB)</span>
                  <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); setUploadedFile(null); }} style={{ fontSize: 10, padding: "2px 8px" }}>
                    {ko ? "제거" : "Remove"}
                  </button>
                </div>
              ) : (
                <>
                  <UploadSimple size={28} weight="light" style={{ color: "var(--muted)", marginBottom: 4 }} />
                  <p style={{ fontSize: 13, fontWeight: 500 }}>{ko ? "파일을 드래그하거나 클릭" : "Drag & drop or click"}</p>
                  <p className="muted-text" style={{ fontSize: 11 }}>.zip, .tar.gz, .py, .whl</p>
                </>
              )}
            </div>
          </div>

          {/* Next */}
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" onClick={() => setStep(2)} disabled={!canProceedStep1}>
              {ko ? "다음" : "Next"} <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: Basic Info ── */}
      {step === 2 && (
        <div className="panel">
          <div className="stack-md">
            <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>{ko ? "서비스 기본 정보" : "Service Details"}</p>

            <label className="field">
              {ko ? "서비스 표시 이름" : "Display Name"} *
              <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder={ko ? "예: 뇌 MRI 피질 두께 분석" : "e.g. Brain MRI Cortical Thickness"} autoFocus />
            </label>

            <label className="field">
              {ko ? "내부명 (영문, 자동생성)" : "Internal Name (auto-generated)"} *
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""))}
                placeholder="brain_mri_cortical"
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
              <span className="muted-text" style={{ fontSize: 10 }}>{ko ? "영문 소문자, 숫자, 하이픈, 언더스코어만" : "lowercase, numbers, hyphens, underscores"}</span>
            </label>

            <label className="field">
              {ko ? "설명" : "Description"}
              <textarea className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder={ko ? "서비스에 대한 간단한 설명" : "Brief description of the service"} />
            </label>

            <div className="form-grid">
              <label className="field">
                {ko ? "부서" : "Department"}
                <input className="input" value={department} onChange={(e) => setDepartment(e.target.value)} placeholder={ko ? "신경과" : "Neurology"} />
              </label>
              <label className="field">
                {ko ? "처리 방식" : "Processing Type"}
                <select className="input" value={serviceType} onChange={(e) => setServiceType(e.target.value as "AUTOMATIC" | "HUMAN_IN_LOOP")}>
                  <option value="AUTOMATIC">{ko ? "자동 처리" : "Automatic"}</option>
                  <option value="HUMAN_IN_LOOP">{ko ? "전문가 검토 필요" : "Expert Review Required"}</option>
                </select>
              </label>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <button className="btn btn-secondary" onClick={() => setStep(1)}>
                <ArrowLeft size={14} /> {ko ? "이전" : "Back"}
              </button>
              <button className="btn btn-primary" onClick={() => setStep(3)} disabled={!canProceedStep2}>
                {ko ? "다음" : "Next"} <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Step 3: Runtime Config + Submit ── */}
      {step === 3 && (
        <div className="stack-md">
          <div className="panel">
            <div className="stack-md">
              <p style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                <Cpu size={16} /> {ko ? "실행 환경 설정" : "Runtime Configuration"}
              </p>

              <label className="field">
                {ko ? "컨테이너 이미지" : "Container Image"}
                <input
                  className="input"
                  value={containerImage}
                  onChange={(e) => setContainerImage(e.target.value)}
                  placeholder={`registry.fly.io/neurohub-svc-${name || "my-service"}:1.0.0`}
                  style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
                />
                <span className="muted-text" style={{ fontSize: 10 }}>{ko ? "비어있으면 기본 이미지 사용" : "Leave empty for default image"}</span>
              </label>

              <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr" }}>
                <label className="field">
                  {ko ? "메모리" : "Memory"}
                  <select className="input" value={memoryGb} onChange={(e) => setMemoryGb(Number(e.target.value))}>
                    <option value={0.5}>512 MB</option>
                    <option value={1}>1 GB</option>
                    <option value={2}>2 GB</option>
                    <option value={4}>4 GB</option>
                    <option value={8}>8 GB</option>
                  </select>
                </label>
                <label className="field">
                  CPUs
                  <select className="input" value={cpuCount} onChange={(e) => setCpuCount(Number(e.target.value))}>
                    <option value={1}>1 vCPU</option>
                    <option value={2}>2 vCPU</option>
                    <option value={4}>4 vCPU</option>
                  </select>
                </label>
                <label className="field">
                  {ko ? "타임아웃" : "Timeout"}
                  <select className="input" value={timeout} onChange={(e) => setTimeoutSec(Number(e.target.value))}>
                    <option value={60}>1 {ko ? "분" : "min"}</option>
                    <option value={300}>5 {ko ? "분" : "min"}</option>
                    <option value={600}>10 {ko ? "분" : "min"}</option>
                    <option value={1800}>30 {ko ? "분" : "min"}</option>
                    <option value={3600}>1 {ko ? "시간" : "hour"}</option>
                  </select>
                </label>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="panel" style={{ background: "var(--primary-subtle)", border: "1px solid var(--primary-light)" }}>
            <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>{ko ? "등록 요약" : "Registration Summary"}</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 16px", fontSize: 12 }}>
              <span className="muted-text">{ko ? "서비스명" : "Name"}:</span>
              <span style={{ fontWeight: 500 }}>{displayName || "—"}</span>
              <span className="muted-text">{ko ? "내부명" : "Internal"}:</span>
              <span className="mono-cell" style={{ fontSize: 11 }}>{name || "—"}</span>
              <span className="muted-text">{ko ? "유형" : "Type"}:</span>
              <span>{selectedTemplate ? (ko ? TEMPLATES.find((t) => t.key === selectedTemplate)?.ko : TEMPLATES.find((t) => t.key === selectedTemplate)?.en) : "—"}</span>
              <span className="muted-text">{ko ? "패키지" : "Package"}:</span>
              <span>{uploadedFile ? uploadedFile.name : (ko ? "없음" : "None")}</span>
              <span className="muted-text">{ko ? "리소스" : "Resources"}:</span>
              <span>{memoryGb} GB / {cpuCount} vCPU / {timeout}s</span>
            </div>
          </div>

          {/* Upload progress */}
          {uploading && (
            <div className="panel">
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span className="spinner" />
                <span style={{ fontSize: 13 }}>{ko ? "패키지 업로드 중..." : "Uploading package..."} {uploadProgress}%</span>
              </div>
              <div style={{ height: 4, background: "var(--surface-2)", borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${uploadProgress}%`, background: "var(--primary)", transition: "width 0.2s" }} />
              </div>
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button className="btn btn-secondary" onClick={() => setStep(2)} disabled={submitMut.isPending}>
              <ArrowLeft size={14} /> {ko ? "이전" : "Back"}
            </button>
            <button
              className="btn btn-primary"
              onClick={() => submitMut.mutate()}
              disabled={submitMut.isPending || uploading}
              style={{ fontSize: 14, padding: "10px 24px" }}
            >
              {submitMut.isPending ? <span className="spinner" /> : <Check size={16} />}
              {ko ? "서비스 등록" : "Register Service"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
