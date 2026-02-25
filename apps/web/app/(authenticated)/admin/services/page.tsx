"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, PencilSimple, ArrowSquareOut, Cube } from "phosphor-react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import * as Dialog from "@radix-ui/react-dialog";
import { listServices, updateService, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

export default function AdminServicesPage() {
  const { t, locale } = useTranslation();
  const ko = locale === "ko";
  const dateLocale = ko ? "ko-KR" : "en-US";
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["services"], queryFn: listServices });
  const services = data?.items ?? [];

  // Edit dialog state
  const [editingService, setEditingService] = useState<ServiceRead | null>(null);
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editVersion, setEditVersion] = useState("");
  const [editDepartment, setEditDepartment] = useState("");

  function openEdit(svc: ServiceRead) {
    setEditingService(svc);
    setEditDisplayName(svc.display_name);
    setEditVersion(String(svc.version));
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
          <h1 className="page-title">{t("adminServices.title")}</h1>
          <p className="page-subtitle">{t("adminServices.subtitle")}</p>
        </div>
        <div className="page-header-actions">
          <Link href="/admin/services/new">
            <button className="btn btn-primary"><Plus size={16} /> {t("adminServices.registerService")}</button>
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : services.length === 0 ? (
        /* Empty state */
        <div className="panel" style={{ textAlign: "center", padding: "48px 24px" }}>
          <Cube size={48} weight="light" style={{ color: "var(--muted)", marginBottom: 12 }} />
          <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>
            {ko ? "등록된 서비스가 없습니다" : "No services registered"}
          </p>
          <p className="muted-text" style={{ fontSize: 13, marginBottom: 16 }}>
            {ko ? "새 AI 분석 서비스를 등록하여 시작하세요" : "Get started by registering a new AI analysis service"}
          </p>
          <Link href="/admin/services/new">
            <button className="btn btn-primary"><Plus size={16} /> {ko ? "첫 서비스 등록하기" : "Register First Service"}</button>
          </Link>
        </div>
      ) : (
        /* Service cards grid */
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 16 }}>
          {services.map((svc: ServiceRead) => (
            <div
              key={svc.id}
              className="panel"
              style={{ padding: 20, cursor: "pointer", transition: "box-shadow 0.15s", position: "relative" }}
              onClick={() => router.push(`/admin/services/${svc.id}`)}
            >
              {/* Status dot */}
              <div style={{ position: "absolute", top: 16, right: 16 }}>
                <span
                  className={`status-chip ${svc.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}
                  style={{ fontSize: 10, padding: "2px 8px" }}
                >
                  {svc.status === "ACTIVE" ? t("common.active") : t("common.inactive")}
                </span>
              </div>

              {/* Header */}
              <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 12 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: "var(--radius-md)",
                  background: "var(--primary-subtle)", display: "flex",
                  alignItems: "center", justifyContent: "center", flexShrink: 0,
                  color: "var(--primary)",
                }}>
                  <Cube size={20} />
                </div>
                <div style={{ minWidth: 0, paddingRight: 60 }}>
                  <p style={{ fontSize: 15, fontWeight: 600, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {svc.display_name}
                  </p>
                  <p className="mono-cell" style={{ fontSize: 11, color: "var(--muted)" }}>
                    {svc.name} v{svc.version}
                  </p>
                </div>
              </div>

              {/* Description */}
              {svc.description && (
                <p className="muted-text" style={{ fontSize: 12, marginBottom: 12, lineHeight: 1.4, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                  {svc.description}
                </p>
              )}

              {/* Meta row */}
              <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11, color: "var(--muted)", marginBottom: 12 }}>
                <span className={`status-chip ${svc.service_type === "HUMAN_IN_LOOP" ? "status-pending" : "status-final"}`} style={{ fontSize: 10, padding: "1px 6px" }}>
                  {svc.service_type === "HUMAN_IN_LOOP" ? (ko ? "전문가 검토" : "Expert Review") : (ko ? "자동" : "Auto")}
                </span>
                {svc.department && <span>{svc.department}</span>}
                <span>{new Date(svc.created_at).toLocaleDateString(dateLocale)}</span>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: 6, borderTop: "1px solid var(--border)", paddingTop: 12 }} onClick={(e) => e.stopPropagation()}>
                <button className="btn btn-sm btn-secondary" onClick={() => router.push(`/admin/services/${svc.id}`)}>
                  <ArrowSquareOut size={14} /> {ko ? "상세" : "Detail"}
                </button>
                <button className="btn btn-sm btn-secondary" onClick={() => openEdit(svc)}>
                  <PencilSimple size={14} /> {ko ? "편집" : "Edit"}
                </button>
                <button
                  className={`btn btn-sm ${svc.status === "ACTIVE" ? "btn-danger" : "btn-primary"}`}
                  onClick={() => toggleMut.mutate({ id: svc.id, status: svc.status })}
                  disabled={toggleMut.isPending}
                  style={{ marginLeft: "auto" }}
                >
                  {svc.status === "ACTIVE" ? t("common.deactivate") : t("common.activate")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog.Root open={!!editingService} onOpenChange={(open) => { if (!open) setEditingService(null); }}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <Dialog.Title className="dialog-title">{t("adminServices.editServiceTitle")}</Dialog.Title>
            <div className="stack-md">
              <label className="field">
                {t("adminServices.displayName")}
                <input className="input" value={editDisplayName} onChange={(e) => setEditDisplayName(e.target.value)} />
              </label>
              <div className="form-grid">
                <label className="field">
                  {t("adminServices.version")}
                  <input className="input" value={editVersion} onChange={(e) => setEditVersion(e.target.value)} />
                </label>
                <label className="field">
                  {t("adminServices.department")}
                  <input className="input" value={editDepartment} onChange={(e) => setEditDepartment(e.target.value)} />
                </label>
              </div>
              {updateMut.isError && <p className="error-text">{(updateMut.error as Error).message}</p>}
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <Dialog.Close asChild><button className="btn btn-secondary">{t("common.cancel")}</button></Dialog.Close>
                <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
                  {updateMut.isPending ? <span className="spinner" /> : t("common.save")}
                </button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
