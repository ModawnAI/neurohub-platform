"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CloudArrowUp, Trash, Spinner, ArrowClockwise } from "phosphor-react";
import { deployService, getDeploymentStatus, undeployService, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

interface Props {
  service: ServiceRead;
}

export function ServiceDeployment({ service }: Props) {
  const { t, locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [deployImage, setDeployImage] = useState("");
  const [memoryGb, setMemoryGb] = useState(1);
  const [cpus, setCpus] = useState(1);
  const [showDeploy, setShowDeploy] = useState(false);

  const { data: deployment, refetch: refetchDeploy, isLoading } = useQuery({
    queryKey: ["service-deployment", service.id],
    queryFn: () => getDeploymentStatus(service.id),
    enabled: !!service.id,
    retry: false,
    refetchInterval: 15000, // Auto-refresh every 15s
  });

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
    onError: (err) => addToast("error", ko ? `배포 실패: ${(err as Error).message}` : `Deploy failed: ${(err as Error).message}`),
  });

  const undeployMut = useMutation({
    mutationFn: () => undeployService(service.id),
    onSuccess: () => {
      refetchDeploy();
      addToast("success", ko ? "배포 해제 완료" : "Undeployed");
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  const machineCount = deployment?.total ?? 0;

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 className="panel-title">{ko ? "컨테이너 배포" : "Container Deployment"}</h3>
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
              {deployMut.isPending ? <Spinner size={14} className="spinner" /> : ko ? "배포 시작" : "Start Deploy"}
            </button>
            <button className="btn btn-secondary" onClick={() => setShowDeploy(false)}>{ko ? "취소" : "Cancel"}</button>
          </div>
        </div>
      )}

      {/* Machine Status */}
      {isLoading ? (
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
            {ko ? "SDK로 서비스를 빌드한 후 배포하세요" : "Build your service with the SDK, then deploy"}
          </p>
        </div>
      )}
    </div>
  );
}
