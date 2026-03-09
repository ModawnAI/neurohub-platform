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
      addToast("success", t("serviceDeployment.deploySuccess" as any));
    },
    onError: (err) => addToast("error", `${t("serviceDeployment.deployFailed" as any)}: ${(err as Error).message}`),
  });

  const undeployMut = useMutation({
    mutationFn: () => undeployService(service.id),
    onSuccess: () => {
      refetchDeploy();
      addToast("success", t("serviceDeployment.undeploySuccess" as any));
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  // Upload handler
  const handleUpload = useCallback(async (file: File) => {
    const allowed = [".zip", ".tar.gz", ".tgz", ".py", ".whl"];
    const isAllowed = allowed.some((ext) => file.name.toLowerCase().endsWith(ext));
    if (!isAllowed) {
      addToast("error", `${t("serviceDeployment.allowedFiles" as any)}: ${allowed.join(", ")}`);
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
      addToast("success", `${file.name} ${t("serviceDeployment.uploadComplete" as any)}`);
    } catch (err) {
      addToast("error", `${t("serviceDeployment.uploadFailed" as any)}: ${(err as Error).message}`);
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
      addToast("error", t("serviceDeployment.downloadFailed" as any));
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
              <Package size={18} /> {t("serviceDeployment.packageTitle" as any)}
            </h3>
            <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
              {t("serviceDeployment.packageSubtitle" as any)}
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
              <DownloadSimple size={14} /> {t("common.download" as any)}
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
                <span style={{ fontSize: 13, fontWeight: 500 }}>{t("serviceDeployment.uploading" as any)} {uploadProgress}%</span>
              </div>
              <div style={{ height: 4, background: "var(--surface-2)", borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: `${uploadProgress}%`, background: "var(--primary)", transition: "width 0.2s" }} />
              </div>
            </div>
          ) : (
            <>
              <UploadSimple size={32} weight="light" style={{ color: "var(--muted)", marginBottom: 8 }} />
              <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>
                {t("serviceDeployment.dragOrClick" as any)}
              </p>
              <p className="muted-text" style={{ fontSize: 11 }}>
                {t("serviceDeployment.supportedFormats" as any)}
              </p>
            </>
          )}
        </div>

        {/* Accepted file types guide */}
        <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
          {[
            { ext: ".zip", desc: t("serviceDeployment.projectZip" as any) },
            { ext: ".tar.gz", desc: t("serviceDeployment.compressedPackage" as any) },
            { ext: ".py", desc: "Python Script" },
            { ext: ".whl", desc: "Python Wheel" },
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
              <CloudArrowUp size={18} /> {t("serviceDeployment.containerDeployment" as any)}
            </h3>
            <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
              {t("serviceDeployment.containerSubtitle" as any)}
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => refetchDeploy()} title={t("serviceDeployment.refresh" as any)}>
              <ArrowClockwise size={14} />
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowDeploy(!showDeploy)}>
              <CloudArrowUp size={16} /> {t("serviceDeployment.deploy" as any)}
            </button>
            {machineCount > 0 && (
              <button
                className="btn btn-danger btn-sm"
                onClick={() => { if (confirm(t("confirmDialog.undeployTitle" as any))) undeployMut.mutate(); }}
                disabled={undeployMut.isPending}
              >
                <Trash size={14} /> {t("serviceDeployment.undeploy" as any)}
              </button>
            )}
          </div>
        </div>

        {/* Deploy Form */}
        {showDeploy && (
          <div className="stack-md" style={{ marginBottom: 16, padding: 16, background: "var(--primary-subtle)", borderRadius: "var(--radius-md)", border: "1px solid var(--primary-light)" }}>
            <label className="field">
              {t("serviceDeployment.containerImage" as any)}
              <input
                className="input"
                value={deployImage}
                onChange={(e) => setDeployImage(e.target.value)}
                placeholder={`registry.fly.io/neurohub-svc-${service.name}:${service.version_label}`}
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
              <span className="muted-text" style={{ fontSize: 11 }}>
                {t("serviceDeployment.defaultRegistryHint" as any)}
              </span>
            </label>
            <div className="form-grid">
              <label className="field">
                {t("serviceDeployment.memoryGb" as any)}
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
                {deployMut.isPending ? <span className="spinner" /> : t("serviceDeployment.startDeploy" as any)}
              </button>
              <button className="btn btn-secondary" onClick={() => setShowDeploy(false)}>{t("common.cancel")}</button>
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
                {t("serviceDeployment.runningMachines" as any)}: <strong>{machineCount}</strong>
              </p>
              <span className="mono-cell" style={{ fontSize: 11 }}>{deployment?.app_name}</span>
            </div>
            <div className="table-wrap">
              <table className="table" style={{ fontSize: 12 }}>
                <thead>
                  <tr>
                    <th>{t("serviceDeployment.machineId" as any)}</th>
                    <th>{t("serviceDeployment.machineState" as any)}</th>
                    <th>{t("serviceDeployment.machineImage" as any)}</th>
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
              {t("serviceDeployment.noContainers" as any)}
            </p>
            <p className="muted-text" style={{ fontSize: 12 }}>
              {t("serviceDeployment.uploadThenDeploy" as any)}
            </p>
          </div>
        )}
      </div>

      {/* SDK Guide */}
      <div className="panel">
        <h3 className="panel-title" style={{ marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
          <Warning size={16} style={{ color: "var(--warning)" }} /> {t("serviceDeployment.advancedSdk" as any)}
        </h3>
        <p className="muted-text" style={{ fontSize: 12, marginBottom: 12 }}>
          {t("serviceDeployment.advancedSdkDesc" as any)}
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
{`# ${t("serviceDeployment.sdkComment1" as any)}
pip install neurohub-sdk
neurohub init ${service.name}
cd ${service.name}

# ${t("serviceDeployment.sdkComment2" as any)}
# ${t("serviceDeployment.sdkComment3" as any)}
from neurohub_sdk import BaseService, InputContext, OutputContext

class MyService(BaseService):
    async def predict(self, ctx: InputContext) -> OutputContext:
        # ${t("serviceDeployment.sdkComment4" as any)}
        out = OutputContext()
        out.set("result", {"prediction": "..."})
        return out

# ${t("serviceDeployment.sdkComment5" as any)}
neurohub build
neurohub deploy`}
        </pre>
      </div>
    </div>
  );
}
