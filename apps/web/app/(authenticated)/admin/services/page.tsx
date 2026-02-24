"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, PencilSimple, ArrowSquareOut } from "phosphor-react";
import { useRouter } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import { listServices, createService, updateService, type ServiceRead } from "@/lib/api";
import { useZodForm } from "@/lib/use-zod-form";
import { serviceCreateSchema, type ServiceCreateValues } from "@/lib/schemas";
import { useTranslation } from "@/lib/i18n";

const INITIAL_CREATE: ServiceCreateValues = {
  name: "",
  display_name: "",
  version: "1.0",
  department: "",
  description: "",
  service_type: "AUTOMATIC",
  requires_evaluator: false,
};

export default function AdminServicesPage() {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const router = useRouter();
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
      if (!data) throw new Error(t("common.validationError"));
      return createService({
        name: data.name,
        display_name: data.display_name,
        version: data.version,
        department: data.department || undefined,
        description: data.description || undefined,
        service_type: data.service_type,
        requires_evaluator: data.requires_evaluator,
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
          <Dialog.Root open={showCreate} onOpenChange={setShowCreate}>
            <Dialog.Trigger asChild>
              <button className="btn btn-primary"><Plus size={16} /> {t("adminServices.registerService")}</button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="dialog-overlay" />
              <Dialog.Content className="dialog-content">
                <Dialog.Title className="dialog-title">{t("adminServices.newServiceTitle")}</Dialog.Title>
                <div className="stack-md">
                  <label className="field">
                    {t("adminServices.internalName")}
                    <input className="input" value={createForm.values.name} onChange={(e) => createForm.setField("name", e.target.value)} placeholder={t("adminServices.internalNamePlaceholder")} />
                    {createForm.errors.name && <span className="error-text">{createForm.errors.name}</span>}
                  </label>
                  <label className="field">
                    {t("adminServices.displayName")}
                    <input className="input" value={createForm.values.display_name} onChange={(e) => createForm.setField("display_name", e.target.value)} placeholder={t("adminServices.displayNamePlaceholder")} />
                    {createForm.errors.display_name && <span className="error-text">{createForm.errors.display_name}</span>}
                  </label>
                  <div className="form-grid">
                    <label className="field">
                      {t("adminServices.version")}
                      <input className="input" value={createForm.values.version} onChange={(e) => createForm.setField("version", e.target.value)} />
                    </label>
                    <label className="field">
                      {t("adminServices.departmentOptional")}
                      <input className="input" value={createForm.values.department ?? ""} onChange={(e) => createForm.setField("department", e.target.value)} placeholder={t("adminServices.departmentPlaceholder")} />
                    </label>
                  </div>
                  <label className="field">
                    {t("adminServices.descriptionOptional")}
                    <textarea className="textarea" value={createForm.values.description ?? ""} onChange={(e) => createForm.setField("description", e.target.value)} rows={2} />
                  </label>
                  <div className="form-grid">
                    <label className="field">
                      {t("adminServices.serviceType")}
                      <select className="input" value={createForm.values.service_type} onChange={(e) => createForm.setField("service_type", e.target.value as "AUTOMATIC" | "HUMAN_IN_LOOP")}>
                        <option value="AUTOMATIC">{t("adminServices.automatic")}</option>
                        <option value="HUMAN_IN_LOOP">{t("adminServices.humanInLoop")}</option>
                      </select>
                    </label>
                    <label className="field" style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 24 }}>
                      <input type="checkbox" checked={createForm.values.requires_evaluator ?? false} onChange={(e) => createForm.setField("requires_evaluator", e.target.checked)} />
                      {t("adminServices.requiresEvaluator")}
                    </label>
                  </div>
                  {createMut.isError && <p className="error-text">{(createMut.error as Error).message}</p>}
                  <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                    <Dialog.Close asChild><button className="btn btn-secondary">{t("common.cancel")}</button></Dialog.Close>
                    <button className="btn btn-primary" onClick={() => createMut.mutate()} disabled={createMut.isPending}>
                      {createMut.isPending ? <span className="spinner" /> : t("common.register")}
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
                  <th>{t("adminServices.tableName")}</th>
                  <th>{t("adminServices.tableInternalName")}</th>
                  <th>{t("adminServices.tableVersion")}</th>
                  <th>{t("adminServices.tableDepartment")}</th>
                  <th>{t("adminServices.tableType")}</th>
                  <th>{t("adminServices.tableStatus")}</th>
                  <th>{t("adminServices.tableCreatedDate")}</th>
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
                      <span className={`status-chip ${svc.service_type === "HUMAN_IN_LOOP" ? "status-pending" : "status-final"}`}>
                        {svc.service_type === "HUMAN_IN_LOOP" ? t("adminServices.humanInLoop") : t("adminServices.automatic")}
                      </span>
                    </td>
                    <td>
                      <span className={`status-chip ${svc.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>
                        {svc.status === "ACTIVE" ? t("common.active") : t("common.inactive")}
                      </span>
                    </td>
                    <td>{new Date(svc.created_at).toLocaleDateString(dateLocale)}</td>
                    <td>
                      <div className="action-row">
                        <button className="btn btn-sm btn-secondary" onClick={() => router.push(`/admin/services/${svc.id}`)} aria-label={t("serviceDetail.usageStats")}>
                          <ArrowSquareOut size={14} />
                        </button>
                        <button className="btn btn-sm btn-secondary" onClick={() => openEdit(svc)}>
                          <PencilSimple size={14} />
                        </button>
                        <button
                          className={`btn btn-sm ${svc.status === "ACTIVE" ? "btn-danger" : "btn-primary"}`}
                          onClick={() => toggleMut.mutate({ id: svc.id, status: svc.status })}
                          disabled={toggleMut.isPending}
                        >
                          {svc.status === "ACTIVE" ? t("common.deactivate") : t("common.activate")}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {services.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
                      {t("adminServices.noServices")}
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
