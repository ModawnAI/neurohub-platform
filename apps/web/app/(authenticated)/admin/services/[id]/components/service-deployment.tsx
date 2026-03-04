"use client";

import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CloudArrowUp, Trash, ArrowClockwise, DownloadSimple, File, UploadSimple, Package, CheckCircle, Warning } from "phosphor-react";
import {
  deployService,
  getDeploymentStatus,
  undeployService,
  presignPackageUpload,
  completePackageUpload,
  getPackageInfo,
  getPackageDownloadUrl,
  uploadFileToStorage,
  type ServiceRead,
  type PackageInfo,
} from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

interface Props {
  service: ServiceRead;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ServiceDeployment({ service }: Props) {
  const { t, locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Deploy state
  const [deployImage, setDeployImage] = useState("");
  const [memoryGb, setMemoryGb] = useState(1);
  const [cpus, setCpus] = useState(1);
  const [showDeploy, setShowDeploy] = useState(false);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  // Queries
  const { data: deployment, refetch: refetchDeploy, isLoading: deployLoading } = useQuery({
    queryKey: ["service-deployment", service.id],
    queryFn: () => getDeploymentStatus(service.id),
    enabled: !!service.id,
    retry: false,
    refetchInterval: 15000,
  });

  const { data: packageInfo, refetch: refetchPackage } = useQuery({
    queryKey: ["service-package", service.id],
    queryFn: () => getPackageInfo(service.id),
    enabled: !!service.id,
    retry: false,
  });

  // Mutations
  const deployMut = useMutation({
    mutationFn: () =>
      deployService(service.id, {
        container_image: deployImage || undefined,
        resource_requirements: { memory_gb: memoryGb, cpus },
      }),
    onSuccess: () => {
      refetchDeploy();
      setShowDeploy(false);
      setDeployImage("");
      addToast("success", ko ? "배포 완료" : "Deployed successfully");
    },
    onError: (err) => addToast("error", `${ko ? "배포 실패" : "Deploy failed"}: ${(err as Error).message}`),
  });

  const undeployMut = useMutation({
    mutationFn: () => undeployService(service.id),
    onSuccess: () => {
      refetchDeploy();
      addToast("success", ko ? "배포 해제 완료" : "Undeployed");
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  // Upload handler
  const handleUpload = useCallback(async (file: File) => {
    const allowed = [".zip", ".tar.gz", ".tgz", ".py", ".whl"];
    const isAllowed = allowed.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!isAllowed) {
      addToast("error", ko ? `허용된 파일: ${allowed.join(", ")}` : `Allowed: ${allowed.join(", ")}`);
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    try {
      // Step 1: Get presigned URL
      const presign = await presignPackageUpload(service.id, {
        file_name: file.name,
        content_type: file.type || "application/octet-stream",
        file_size: file.size,
      });

      // Step 2: Upload to storage
      await uploadFileToStorage(presign.presigned_url, file, (pct) => setUploadProgress(pct));

      // Step 3: Complete upload
      await completePackageUpload(service.id, {
        storage_path: presign.storage_path,
        file_name: file.name,
        file_size: file.size,
      });

      refetchPackage();
      addToast("success", ko ? `${file.name} 업로드 완료` : `${file.name} uploaded`);
    } catch (err) {
      addToast("error", `${ko ? "업로드 실패" : "Upload failed"}: ${(err as Error).message}`);
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  }, [service.id, ko, addToast, refetchPackage]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  }, [handleUpload]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = "";
  };

  const handleDownload = async () => {
    try {
      const { download_url } = await getPackageDownloadUrl(service.id);
      window.open(download_url, "_blank");
    } catch {
      addToast("error", ko ? "다운로드 실패" : "Download failed");
    }
  };

  const machineCount = deployment?.total ?? 0;

  return (
    <div className="stack-lg">
      {/* Package Upload Section */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <h3 className="panel-title" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Package size={18} /> {ko ? "서비스 패키지" : "Service Package"}
            </h3>
            <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
              {ko
                ? "AI 모델 코드, 스크립트, 또는 ZIP 패키지를 업로드합니다"
                : "Upload your AI model code, scripts, or ZIP package"}
            </p>
          </div>
        </div>

        {/* Current Package Info */}
        {packageInfo && (
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: 12,
            background: "var(--success-light)",
            borderRadius: "var(--radius-sm)",
            marginBottom: 16,
            border: "1px solid var(--success)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <CheckCircle size={18} weight="fill" style={{ color: "var(--success)" }} />
              <div>
                <p style={{ fontSize: 13, fontWeight: 600 }}>{packageInfo.file_name ?? "package"}</p>
                <p className="muted-text" style={{ fontSize: 11 }}>
                  {formatBytes(packageInfo.file_size ?? 0)} &middot; {new Date(packageInfo.uploaded_at ?? Date.now()).toLocaleString(ko ? "ko-KR" : "en-US")}
                </p>
              </div>
            </div>
            <button className="btn btn-secondary btn-sm" onClick={handleDownload}>
              <DownloadSimple size={14} /> {ko ? "다운로드" : "Download"}
            </button>
          </div>
        )}

        {/* Upload Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => !uploading && fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? "var(--primary)" : uploading ? "var(--warning)" : "var(--border)"}`,
            borderRadius: "var(--radius-md)",
            padding: uploading ? "16px 24px" : "32px 24px",
            textAlign: "center",
            cursor: uploading ? "default" : "pointer",
            background: dragOver ? "var(--primary-subtle)" : "transparent",
            transition: "all 0.15s",
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.tar.gz,.tgz,.py,.whl"
            onChange={handleFileSelect}
            style={{ display: "none" }}
          />

          {uploading ? (
            <div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginBottom: 8 }}>
                <span className="spinner" />
                <span style={{ fontSize: 13, fontWeight: 500 }}>{ko ? "업로드 중..." : "Uploading..."} {uploadProgress}%</span>
              </div>
              <div style={{ height: 4, background: "var(--surface-2)", borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${uploadProgress}%`, background: "var(--primary)", transition: "width 0.2s" }} />
              </div>
            </div>
          ) : (
            <>
              <UploadSimple size={32} weight="light" style={{ color: "var(--muted)", marginBottom: 8 }} />
              <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                {ko ? "파일을 드래그하거나 클릭하여 업로드" : "Drag & drop or click to upload"}
              </p>
              <p className="muted-text" style={{ fontSize: 11 }}>
                {ko
                  ? "지원 형식: .zip, .tar.gz, .py, .whl (AI 모델 코드 또는 패키지)"
                  : "Supported: .zip, .tar.gz, .py, .whl (AI model code or package)"}
              </p>
            </>
          )}
        </div>

        {/* Accepted file types guide */}
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
          {[
            { ext: ".zip", desc: ko ? "프로젝트 ZIP" : "Project ZIP" },
            { ext: ".tar.gz", desc: ko ? "압축 패키지" : "Compressed Package" },
            { ext: ".py", desc: ko ? "Python 스크립트" : "Python Script" },
            { ext: ".whl", desc: ko ? "Python Wheel" : "Python Wheel" },
          ].map(({ ext, desc }) => (
            <div key={ext} style={{ display: "flex", alignItems: "center", gap: 4, padding: "4px 8px", background: "var(--surface-2)", borderRadius: "var(--radius-sm)", fontSize: 11 }}>
              <File size={12} style={{ color: "var(--muted)" }} />
              <span className="mono-cell" style={{ fontSize: 10 }}>{ext}</span>
              <span className="muted-text">{desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Container Deployment Section */}
      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div>
            <h3 className="panel-title" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <CloudArrowUp size={18} /> {ko ? "컨테이너 배포" : "Container Deployment"}
            </h3>
            <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
              {ko ? "Fly.io에 서비스 컨테이너를 배포하고 관리합니다" : "Deploy and manage service containers on Fly.io"}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => refetchDeploy()} title={ko ? "새로고침" : "Refresh"}>
              <ArrowClockwise size={14} />
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowDeploy(!showDeploy)}>
              <CloudArrowUp size={16} /> {ko ? "배포" : "Deploy"}
            </button>
            {machineCount > 0 && (
              <button
                className="btn btn-danger btn-sm"
                onClick={() => { if (confirm(ko ? "모든 머신을 중지하시겠습니까?" : "Stop all machines?")) undeployMut.mutate(); }}
                disabled={undeployMut.isPending}
              >
                <Trash size={14} /> {ko ? "배포 해제" : "Undeploy"}
              </button>
            )}
          </div>
        </div>

        {/* Deploy Form */}
        {showDeploy && (
          <div className="stack-md" style={{ marginBottom: 16, padding: 16, background: "var(--primary-subtle)", borderRadius: "var(--radius-md)", border: "1px solid var(--primary-light)" }}>
            <label className="field">
              {ko ? "컨테이너 이미지" : "Container Image"}
              <input
                className="input"
                value={deployImage}
                onChange={(e) => setDeployImage(e.target.value)}
                placeholder={`registry.fly.io/neurohub-svc-${service.name}:${service.version_label}`}
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
              <span className="muted-text" style={{ fontSize: 11 }}>
                {ko ? "비어있으면 기본 레지스트리 태그 사용" : "Leave empty for default registry tag"}
              </span>
            </label>
            <div className="form-grid">
              <label className="field">
                {ko ? "메모리 (GB)" : "Memory (GB)"}
                <select className="input" value={memoryGb} onChange={(e) => setMemoryGb(Number(e.target.value))}>
                  <option value={0.5}>512 MB</option>
                  <option value={1}>1 GB</option>
                  <option value={2}>2 GB</option>
                  <option value={4}>4 GB</option>
                  <option value={8}>8 GB</option>
                  <option value={16}>16 GB</option>
                </select>
              </label>
              <label className="field">
                CPUs
                <select className="input" value={cpus} onChange={(e) => setCpus(Number(e.target.value))}>
                  <option value={1}>1 vCPU</option>
                  <option value={2}>2 vCPU</option>
                  <option value={4}>4 vCPU</option>
                  <option value={8}>8 vCPU</option>
                </select>
              </label>
            </div>
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => deployMut.mutate()} disabled={deployMut.isPending}>
                {deployMut.isPending ? <span className="spinner" /> : ko ? "배포 시작" : "Start Deploy"}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowDeploy(false)}>{ko ? "취소" : "Cancel"}</button>
            </div>
          </div>
        )}

        {/* Machine Status */}
        {deployLoading ? (
          <div className="loading-center" style={{ padding: 24 }}><span className="spinner" /></div>
        ) : machineCount > 0 ? (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <p className="detail-label">
                {ko ? "실행 중인 머신" : "Running Machines"}: <strong>{machineCount}</strong>
              </p>
              <span className="mono-cell" style={{ fontSize: 11 }}>{deployment?.app_name}</span>
            </div>
            <div className="table-wrap">
              <table className="table" style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th>{ko ? "머신 ID" : "Machine ID"}</th>
                    <th>{ko ? "상태" : "State"}</th>
                    <th>{ko ? "이미지" : "Image"}</th>
                  </tr>
                </thead>
                <tbody>
                  {(deployment?.machines ?? []).map((m) => (
                    <tr key={m.id}>
                      <td className="mono-cell">{m.id.slice(0, 14)}</td>
                      <td>
                        <span className={`status-chip ${m.state === "started" ? "status-computing" : m.state === "stopped" ? "status-cancelled" : "status-pending"}`}>
                          {m.state}
                        </span>
                      </td>
                      <td className="mono-cell" style={{ fontSize: 10 }}>{m.config?.image?.split("/").pop() || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: "center", padding: "24px 0" }}>
            <CloudArrowUp size={32} weight="light" style={{ color: "var(--muted)", marginBottom: 8 }} />
            <p className="muted-text" style={{ fontSize: 13 }}>
              {ko ? "배포된 컨테이너가 없습니다" : "No containers deployed"}
            </p>
            <p className="muted-text" style={{ fontSize: 12 }}>
              {ko ? "패키지를 업로드한 후 배포하세요" : "Upload a package, then deploy"}
            </p>
          </div>
        )}
      </div>

      {/* SDK Guide */}
      <div className="panel">
        <h3 className="panel-title" style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
          <Warning size={16} style={{ color: "var(--warning)" }} /> {ko ? "고급: SDK로 빌드 & 배포" : "Advanced: Build & Deploy with SDK"}
        </h3>
        <p className="muted-text" style={{ fontSize: 12, marginBottom: 12 }}>
          {ko
            ? "커스텀 컨테이너가 필요한 경우 SDK를 사용하여 로컬에서 빌드하고 배포할 수 있습니다."
            : "For custom containers, use the SDK to build and deploy locally."}
        </p>
        <pre style={{
          fontSize: 11,
          color: "var(--text-secondary)",
          whiteSpace: "pre-wrap",
          margin: 0,
          fontFamily: "var(--font-mono)",
          background: "var(--surface-2)",
          padding: 12,
          borderRadius: "var(--radius-sm)",
        }}>
{`# ${ko ? "SDK 설치 및 서비스 초기화" : "Install SDK and initialize service"}
pip install neurohub-sdk
neurohub init ${service.name}
cd ${service.name}

# ${ko ? "service.py에 AI 모델 코드 작성" : "Write your AI model code in service.py"}
# ${ko ? "예시:" : "Example:"}
from neurohub_sdk import BaseService, InputContext, OutputContext

class MyService(BaseService):
    async def predict(self, ctx: InputContext) -> OutputContext:
        # ${ko ? "여기에 AI 모델 코드를 작성하세요" : "Your AI model code here"}
        out = OutputContext()
        out.set("result", {"prediction": "..."})
        return out

# ${ko ? "빌드 및 배포" : "Build and deploy"}
neurohub build
neurohub deploy`}
        </pre>
      </div>
    </div>
  );
}
