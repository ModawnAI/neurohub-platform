"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, PencilSimple } from "phosphor-react";
import * as Dialog from "@radix-ui/react-dialog";
import { listServices, createService, updateService, type ServiceRead } from "@/lib/api";
import { useZodForm } from "@/lib/use-zod-form";
import { serviceCreateSchema, type ServiceCreateValues } from "@/lib/schemas";

const INITIAL_CREATE: ServiceCreateValues = {
  name: "",
  display_name: "",
  version: "1.0",
  department: "",
  description: "",
};

export default function AdminServicesPage() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["services"], queryFn: listServices });
  const services = data?.items ?? [];

  const [showCreate, setShowCreate] = useState(false);
  const [editingService, setEditingService] = useState<ServiceRead | null>(null);

  // Create form
  const createForm = useZodForm(serviceCreateSchema, INITIAL_CREATE);

  const createMut = useMutation({
    mutationFn: () => {
      const data = createForm.validate();
      if (!data) throw new Error("입력값을 확인하세요");
      return createService({
        name: data.name,
        display_name: data.display_name,
        version: data.version,
        department: data.department || undefined,
        description: data.description || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      setShowCreate(false);
      createForm.reset();
    },
  });

  // Edit
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editVersion, setEditVersion] = useState("");
  const [editDepartment, setEditDepartment] = useState("");

  function openEdit(svc: ServiceRead) {
    setEditingService(svc);
    setEditDisplayName(svc.display_name);
    setEditVersion(svc.version);
    setEditDepartment(svc.department || "");
  }

  const updateMut = useMutation({
    mutationFn: () => {
      if (!editingService) throw new Error("No service");
      return updateService(editingService.id, {
        display_name: editDisplayName,
        version: editVersion,
        department: editDepartment || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      setEditingService(null);
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateService(id, { status: status === "ACTIVE" ? "INACTIVE" : "ACTIVE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["services"] }),
  });

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">서비스 관리</h1>
          <p className="page-subtitle">등록된 AI 분석 서비스 목록입니다</p>
        </div>
        <div className="page-header-actions">
          <Dialog.Root open={showCreate} onOpenChange={setShowCreate}>
            <Dialog.Trigger asChild>
              <button className="btn btn-primary"><Plus size={16} /> 서비스 등록</button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="dialog-overlay" />
              <Dialog.Content className="dialog-content">
                <Dialog.Title className="dialog-title">새 서비스 등록</Dialog.Title>
                <div className="stack-md">
                  <label className="field">
                    내부명 (영문/숫자)
                    <input className="input" value={createForm.values.name} onChange={(e) => createForm.setField("name", e.target.value)} placeholder="brain-mri-seg" />
                    {createForm.errors.name && <span className="error-text">{createForm.errors.name}</span>}
                  </label>
                  <label className="field">
                    표시 이름
                    <input className="input" value={createForm.values.display_name} onChange={(e) => createForm.setField("display_name", e.target.value)} placeholder="뇌 MRI 분할" />
                    {createForm.errors.display_name && <span className="error-text">{createForm.errors.display_name}</span>}
                  </label>
                  <div className="form-grid">
                    <label className="field">
                      버전
                      <input className="input" value={createForm.values.version} onChange={(e) => createForm.setField("version", e.target.value)} />
                    </label>
                    <label className="field">
                      부서 (선택)
                      <input className="input" value={createForm.values.department ?? ""} onChange={(e) => createForm.setField("department", e.target.value)} placeholder="신경과" />
                    </label>
                  </div>
                  <label className="field">
                    설명 (선택)
                    <textarea className="textarea" value={createForm.values.description ?? ""} onChange={(e) => createForm.setField("description", e.target.value)} rows={2} />
                  </label>
                  {createMut.isError && <p className="error-text">{(createMut.error as Error).message}</p>}
                  <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                    <Dialog.Close asChild><button className="btn btn-secondary">취소</button></Dialog.Close>
                    <button className="btn btn-primary" onClick={() => createMut.mutate()} disabled={createMut.isPending}>
                      {createMut.isPending ? <span className="spinner" /> : "등록"}
                    </button>
                  </div>
                </div>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : (
        <div className="panel">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>서비스명</th>
                  <th>내부명</th>
                  <th>버전</th>
                  <th>부서</th>
                  <th>상태</th>
                  <th>생성일</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc: ServiceRead) => (
                  <tr key={svc.id}>
                    <td style={{ fontWeight: 600 }}>{svc.display_name}</td>
                    <td className="mono-cell">{svc.name}</td>
                    <td>v{svc.version}</td>
                    <td>{svc.department || "-"}</td>
                    <td>
                      <span className={`status-chip ${svc.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>
                        {svc.status === "ACTIVE" ? "활성" : "비활성"}
                      </span>
                    </td>
                    <td>{new Date(svc.created_at).toLocaleDateString("ko-KR")}</td>
                    <td>
                      <div className="action-row">
                        <button className="btn btn-sm btn-secondary" onClick={() => openEdit(svc)}>
                          <PencilSimple size={14} />
                        </button>
                        <button
                          className={`btn btn-sm ${svc.status === "ACTIVE" ? "btn-danger" : "btn-primary"}`}
                          onClick={() => toggleMut.mutate({ id: svc.id, status: svc.status })}
                          disabled={toggleMut.isPending}
                        >
                          {svc.status === "ACTIVE" ? "비활성화" : "활성화"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {services.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
                      등록된 서비스가 없습니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog.Root open={!!editingService} onOpenChange={(open) => { if (!open) setEditingService(null); }}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <Dialog.Title className="dialog-title">서비스 수정</Dialog.Title>
            <div className="stack-md">
              <label className="field">
                표시 이름
                <input className="input" value={editDisplayName} onChange={(e) => setEditDisplayName(e.target.value)} />
              </label>
              <div className="form-grid">
                <label className="field">
                  버전
                  <input className="input" value={editVersion} onChange={(e) => setEditVersion(e.target.value)} />
                </label>
                <label className="field">
                  부서
                  <input className="input" value={editDepartment} onChange={(e) => setEditDepartment(e.target.value)} />
                </label>
              </div>
              {updateMut.isError && <p className="error-text">{(updateMut.error as Error).message}</p>}
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <Dialog.Close asChild><button className="btn btn-secondary">취소</button></Dialog.Close>
                <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
                  {updateMut.isPending ? <span className="spinner" /> : "저장"}
                </button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
