"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PencilSimple } from "phosphor-react";
import { updateService, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

interface Props {
  service: ServiceRead;
}

export function ServiceBasicInfo({ service }: Props) {
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const [editing, setEditing] = useState(false);
  const [displayName, setDisplayName] = useState(service.display_name);
  const [version, setVersion] = useState(String(service.version));
  const [department, setDepartment] = useState(service.department || "");
  const [description, setDescription] = useState(service.description || "");
  const [serviceType, setServiceType] = useState(service.service_type);
  const [requiresEvaluator, setRequiresEvaluator] = useState(service.requires_evaluator);

  const updateMut = useMutation({
    mutationFn: () =>
      updateService(service.id, {
        display_name: displayName,
        version,
        department: department || undefined,
        description: description || undefined,
        service_type: serviceType,
        requires_evaluator: requiresEvaluator,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      queryClient.invalidateQueries({ queryKey: ["service", service.id] });
      setEditing(false);
      addToast("success", t("toast.saveSuccess"));
    },
    onError: () => addToast("error", t("toast.saveError")),
  });

  const toggleMut = useMutation({
    mutationFn: () =>
      updateService(service.id, { status: service.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      queryClient.invalidateQueries({ queryKey: ["service", service.id] });
      addToast("success", t("toast.transitionSuccess"));
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  const openEdit = () => {
    setDisplayName(service.display_name);
    setVersion(String(service.version));
    setDepartment(service.department || "");
    setDescription(service.description || "");
    setServiceType(service.service_type);
    setRequiresEvaluator(service.requires_evaluator);
    setEditing(true);
  };

  if (editing) {
    return (
      <div className="panel">
        <h3 className="panel-title-mb">{t("serviceDetail.editInfo")}</h3>
        <div className="stack-md">
          <label className="field">
            {t("adminServices.displayName")}
            <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
          </label>
          <div className="form-grid">
            <label className="field">
              {t("adminServices.version")}
              <input className="input" value={version} onChange={(e) => setVersion(e.target.value)} />
            </label>
            <label className="field">
              {t("adminServices.department")}
              <input className="input" value={department} onChange={(e) => setDepartment(e.target.value)} />
            </label>
          </div>
          <label className="field">
            {t("serviceDetail.description")}
            <textarea className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </label>
          <div className="form-grid">
            <label className="field">
              {t("adminServices.serviceType")}
              <select className="input" value={serviceType} onChange={(e) => setServiceType(e.target.value)}>
                <option value="AUTOMATIC">{t("adminServices.automatic")}</option>
                <option value="HUMAN_IN_LOOP">{t("adminServices.humanInLoop")}</option>
              </select>
            </label>
            <label className="field" style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 24 }}>
              <input type="checkbox" checked={requiresEvaluator} onChange={(e) => setRequiresEvaluator(e.target.checked)} />
              {t("adminServices.requiresEvaluator")}
            </label>
          </div>
          {updateMut.isError && <p className="error-text">{(updateMut.error as Error).message}</p>}
          <div className="action-row">
            <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
              {updateMut.isPending ? <span className="spinner" /> : t("common.save")}
            </button>
            <button className="btn btn-secondary" onClick={() => setEditing(false)}>{t("common.cancel")}</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 className="panel-title">{t("serviceDetail.serviceInfo")}</h3>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={openEdit}>
            <PencilSimple size={14} /> {t("common.edit")}
          </button>
          <button
            className={`btn btn-sm ${service.status === "ACTIVE" ? "btn-danger" : "btn-primary"}`}
            onClick={() => toggleMut.mutate()}
            disabled={toggleMut.isPending}
          >
            {service.status === "ACTIVE" ? t("common.deactivate") : t("common.activate")}
          </button>
        </div>
      </div>
      <div className="detail-grid">
        <div>
          <p className="detail-label">{t("serviceDetail.internalName")}</p>
          <p className="detail-value mono-cell">{service.name}</p>
        </div>
        <div>
          <p className="detail-label">{t("serviceDetail.status")}</p>
          <p className="detail-value">
            <span className={`status-chip ${service.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>
              {service.status === "ACTIVE" ? t("common.active") : t("common.inactive")}
            </span>
          </p>
        </div>
        <div>
          <p className="detail-label">{t("adminServices.serviceType")}</p>
          <p className="detail-value">
            <span className={`status-chip ${service.service_type === "HUMAN_IN_LOOP" ? "status-pending" : "status-final"}`}>
              {service.service_type === "HUMAN_IN_LOOP" ? t("adminServices.humanInLoop") : t("adminServices.automatic")}
            </span>
          </p>
        </div>
        <div>
          <p className="detail-label">{t("adminServices.department")}</p>
          <p className="detail-value">{service.department || "—"}</p>
        </div>
        <div>
          <p className="detail-label">{t("serviceDetail.description")}</p>
          <p className="detail-value">{service.description || "—"}</p>
        </div>
        <div>
          <p className="detail-label">{t("serviceDetail.createdDate")}</p>
          <p className="detail-value">{new Date(service.created_at).toLocaleDateString(dateLocale)}</p>
        </div>
      </div>
    </div>
  );
}
