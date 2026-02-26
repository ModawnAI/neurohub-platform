"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getArtifact,
  listArtifacts,
  uploadArtifact,
  type ModelArtifactRead,
  type ServiceRead,
} from "@/lib/api";
import { apiFetch } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ArtifactSlot {
  artifactType: "script" | "requirements" | "weights";
  label: string;
  accept: string;
  runtime?: string;
  file: File | null;
  uploaded?: ModelArtifactRead;
  uploading: boolean;
  error: string | null;
}

const STEPS = ["서비스 선택", "파일 업로드", "보안 스캔", "검토 요청"] as const;

// ── Helpers ──────────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    PASS: "badge-success",
    WARN: "badge-warning",
    FAIL: "badge-error",
    APPROVED: "badge-success",
    REJECTED: "badge-error",
    SCANNING: "badge-info",
    PENDING_SCAN: "badge-neutral",
  };
  return <span className={`badge ${map[status] ?? "badge-neutral"}`}>{status}</span>;
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function NewModelPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [services, setServices] = useState<ServiceRead[]>([]);
  const [selectedServiceId, setSelectedServiceId] = useState("");
  const [slots, setSlots] = useState<ArtifactSlot[]>([
    { artifactType: "script", label: "Inference Script (.py)", accept: ".py", runtime: "python3.11", file: null, uploading: false, error: null },
    { artifactType: "requirements", label: "Requirements (.txt)", accept: ".txt", file: null, uploading: false, error: null },
    { artifactType: "weights", label: "Model Weights (.pt/.onnx/…)", accept: ".pt,.pth,.onnx,.h5,.bin,.safetensors", runtime: "pytorch", file: null, uploading: false, error: null },
  ]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load services
  useEffect(() => {
    apiFetch<{ items: ServiceRead[] }>("/services").then((r) => setServices(r.items)).catch(() => {});
  }, []);

  // Poll scan status in step 2
  useEffect(() => {
    if (step !== 2) {
      if (pollRef.current) clearInterval(pollRef.current);
      return;
    }
    const uploadedSlots = slots.filter((s) => s.uploaded);
    if (!uploadedSlots.length) return;

    const allDone = () =>
      uploadedSlots.every((s) =>
        s.uploaded && ["APPROVED", "REJECTED"].includes(s.uploaded.status)
      );

    if (allDone()) return;

    pollRef.current = setInterval(async () => {
      const updated = await Promise.all(
        slots.map(async (s) => {
          if (!s.uploaded || ["APPROVED", "REJECTED"].includes(s.uploaded.status)) return s;
          try {
            const fresh = await getArtifact(s.uploaded.id);
            return { ...s, uploaded: fresh };
          } catch {
            return s;
          }
        })
      );
      setSlots(updated);
      const done = updated.every(
        (s) => !s.uploaded || ["APPROVED", "REJECTED"].includes(s.uploaded.status)
      );
      if (done && pollRef.current) clearInterval(pollRef.current);
    }, 3000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [step]);

  const handleFileChange = (idx: number, file: File | null) => {
    setSlots((prev) => prev.map((s, i) => (i === idx ? { ...s, file, error: null } : s)));
  };

  const handleUploadAll = async () => {
    const toUpload = slots.filter((s) => s.file);
    if (!toUpload.length) return;

    const updated = [...slots];
    for (let i = 0; i < updated.length; i++) {
      if (!updated[i].file) continue;
      updated[i] = { ...updated[i], uploading: true, error: null };
    }
    setSlots([...updated]);

    for (let i = 0; i < slots.length; i++) {
      const slot = slots[i];
      if (!slot.file) continue;
      try {
        const result = await uploadArtifact(
          selectedServiceId,
          slot.artifactType,
          slot.runtime ?? null,
          slot.file,
        );
        updated[i] = { ...updated[i], uploaded: result, uploading: false };
        setSlots([...updated]);
      } catch (e: unknown) {
        updated[i] = {
          ...updated[i],
          uploading: false,
          error: e instanceof Error ? e.message : "Upload failed",
        };
        setSlots([...updated]);
      }
    }
    setStep(2);
  };

  const canProceedToUpload = selectedServiceId.length > 0;
  const canUpload = slots.some((s) => s.file !== null);
  const allScanned = slots
    .filter((s) => s.uploaded)
    .every((s) => s.uploaded && ["APPROVED", "REJECTED"].includes(s.uploaded.status));
  const anyRejected = slots.some((s) => s.uploaded?.status === "REJECTED");

  return (
    <div className="page-container" style={{ maxWidth: 720 }}>
      <h1 className="page-title">모델 아티팩트 업로드</h1>

      {/* Step indicator */}
      <div className="stepper" style={{ display: "flex", gap: 8, marginBottom: 32 }}>
        {STEPS.map((label, i) => (
          <div
            key={label}
            style={{
              flex: 1,
              padding: "8px 4px",
              textAlign: "center",
              borderRadius: 6,
              fontSize: 13,
              fontWeight: i === step ? 700 : 400,
              background: i === step ? "var(--color-primary)" : i < step ? "var(--color-success-light)" : "var(--color-surface)",
              color: i === step ? "#fff" : undefined,
              opacity: i > step ? 0.5 : 1,
            }}
          >
            {i + 1}. {label}
          </div>
        ))}
      </div>

      {/* Step 0: Select service */}
      {step === 0 && (
        <div className="card">
          <h2 className="card-title">서비스 선택</h2>
          <select
            className="form-control"
            value={selectedServiceId}
            onChange={(e) => setSelectedServiceId(e.target.value)}
          >
            <option value="">-- 서비스를 선택하세요 --</option>
            {services.map((svc) => (
              <option key={svc.id} value={svc.id}>
                {svc.display_name || svc.name}
              </option>
            ))}
          </select>
          <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
            <button
              className="btn btn-primary"
              disabled={!canProceedToUpload}
              onClick={() => setStep(1)}
            >
              다음
            </button>
          </div>
        </div>
      )}

      {/* Step 1: Upload artifacts */}
      {step === 1 && (
        <div>
          {slots.map((slot, idx) => (
            <div key={slot.artifactType} className="card" style={{ marginBottom: 16 }}>
              <h3 style={{ marginBottom: 8 }}>{slot.label}</h3>
              <div
                style={{
                  border: "2px dashed var(--color-border)",
                  borderRadius: 8,
                  padding: 24,
                  textAlign: "center",
                  cursor: "pointer",
                  background: slot.file ? "var(--color-success-light)" : undefined,
                }}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const f = e.dataTransfer.files[0];
                  if (f) handleFileChange(idx, f);
                }}
                onClick={() => document.getElementById(`file-input-${idx}`)?.click()}
              >
                <input
                  id={`file-input-${idx}`}
                  type="file"
                  accept={slot.accept}
                  style={{ display: "none" }}
                  onChange={(e) => handleFileChange(idx, e.target.files?.[0] ?? null)}
                />
                {slot.file ? (
                  <span>✅ {slot.file.name} ({(slot.file.size / 1024).toFixed(1)} KB)</span>
                ) : (
                  <span style={{ color: "var(--color-text-secondary)" }}>
                    파일을 드래그하거나 클릭하여 선택 ({slot.accept})
                  </span>
                )}
              </div>
              {slot.error && (
                <p style={{ color: "var(--color-error)", marginTop: 8, fontSize: 13 }}>
                  {slot.error}
                </p>
              )}
            </div>
          ))}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button className="btn btn-ghost" onClick={() => setStep(0)}>이전</button>
            <button
              className="btn btn-primary"
              disabled={!canUpload || slots.some((s) => s.uploading)}
              onClick={handleUploadAll}
            >
              {slots.some((s) => s.uploading) ? "업로드 중…" : "업로드 및 스캔 시작"}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Scan status */}
      {step === 2 && (
        <div>
          <div className="card">
            <h2 className="card-title">보안 스캔 결과</h2>
            {slots.filter((s) => s.uploaded).map((slot) => (
              <div key={slot.artifactType} style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <strong>{slot.label}</strong>
                  <StatusBadge status={slot.uploaded!.status} />
                </div>
                {slot.uploaded!.security_scans.length > 0 ? (
                  <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: "left", padding: "4px 8px" }}>Scanner</th>
                        <th style={{ textAlign: "left", padding: "4px 8px" }}>Status</th>
                        <th style={{ textAlign: "left", padding: "4px 8px" }}>Severity</th>
                        <th style={{ textAlign: "left", padding: "4px 8px" }}>Findings</th>
                      </tr>
                    </thead>
                    <tbody>
                      {slot.uploaded!.security_scans.map((scan) => (
                        <tr key={scan.id} style={{ borderTop: "1px solid var(--color-border)" }}>
                          <td style={{ padding: "4px 8px" }}>{scan.scanner}</td>
                          <td style={{ padding: "4px 8px" }}><StatusBadge status={scan.status} /></td>
                          <td style={{ padding: "4px 8px" }}>{scan.severity ?? "-"}</td>
                          <td style={{ padding: "4px 8px" }}>{scan.findings?.length ?? 0}건</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                    {["APPROVED", "REJECTED"].includes(slot.uploaded!.status)
                      ? "스캔 항목 없음"
                      : "스캔 진행 중…"}
                  </p>
                )}
              </div>
            ))}
            {!allScanned && (
              <p style={{ color: "var(--color-text-secondary)", fontSize: 13 }}>
                ⏳ 스캔이 완료될 때까지 기다려 주세요…
              </p>
            )}
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
            <button className="btn btn-ghost" onClick={() => setStep(1)}>이전</button>
            <button
              className="btn btn-primary"
              disabled={!allScanned}
              onClick={() => setStep(3)}
            >
              다음
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Submit for review */}
      {step === 3 && (
        <div className="card">
          <h2 className="card-title">검토 요청</h2>
          {anyRejected ? (
            <div className="banner banner-error">
              일부 파일이 보안 검사에서 거부되었습니다. 파일을 수정한 후 다시 업로드하세요.
            </div>
          ) : (
            <div className="banner banner-success">
              모든 파일이 승인되었습니다. 관리자 검토를 기다리고 있습니다.
            </div>
          )}
          <ul style={{ marginTop: 12, fontSize: 14 }}>
            {slots.filter((s) => s.uploaded).map((s) => (
              <li key={s.artifactType} style={{ marginBottom: 4 }}>
                <strong>{s.label}</strong>: <StatusBadge status={s.uploaded!.status} />
              </li>
            ))}
          </ul>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 24 }}>
            <button className="btn btn-ghost" onClick={() => router.push("/expert/models")}>
              목록으로
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
