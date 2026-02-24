"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, PencilSimple, ChartBar } from "phosphor-react";
import { useState } from "react";
import { listServices, updateService, listRequests, type ServiceRead, type RequestRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";
import { SkeletonCards } from "@/components/skeleton";
import { EmptyState } from "@/components/empty-state";

export default function ServiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { t, locale } = useTranslation();
  const dateLocale = locale === "ko" ? "ko-KR" : "en-US";
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const [editing, setEditing] = useState(false);
  const [editDisplayName, setEditDisplayName] = useState("");
  const [editVersion, setEditVersion] = useState("");
  const [editDepartment, setEditDepartment] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const { data: servicesData, isLoading } = useQuery({
    queryKey: ["services"],
    queryFn: listServices,
  });

  const { data: requestsData } = useQuery({
    queryKey: ["requests"],
    queryFn: listRequests,
  });

  const service = (servicesData?.items ?? []).find((s: ServiceRead) => s.id === id);
  const allRequests: RequestRead[] = requestsData?.items ?? [];

  // Usage stats
  const serviceRequests = allRequests.filter((r: any) => r.service_id === id || r.service_snapshot?.id === id);
  const totalRequests = serviceRequests.length;
  const completedRequests = serviceRequests.filter((r) => r.status === "FINAL").length;
  const failedRequests = serviceRequests.filter((r) => r.status === "FAILED").length;
  const inProgressRequests = serviceRequests.filter((r) => !["FINAL", "FAILED", "CANCELLED"].includes(r.status)).length;

  const updateMut = useMutation({
    mutationFn: () =>
      updateService(id, {
        display_name: editDisplayName,
        version: editVersion,
        department: editDepartment || undefined,
        description: editDescription || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      setEditing(false);
      addToast("success", t("toast.saveSuccess"));
    },
    onError: () => addToast("error", t("toast.saveError")),
  });

  const toggleMut = useMutation({
    mutationFn: () =>
      updateService(id, { status: service?.status === "ACTIVE" ? "INACTIVE" : "ACTIVE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      addToast("success", t("toast.transitionSuccess"));
    },
    onError: () => addToast("error", t("toast.genericError")),
  });

  const openEdit = () => {
    if (!service) return;
    setEditDisplayName(service.display_name);
    setEditVersion(service.version);
    setEditDepartment(service.department || "");
    setEditDescription((service as any).description || "");
    setEditing(true);
  };

  if (isLoading) return <SkeletonCards count={3} />;
  if (!service) {
    return (
      <EmptyState
        title={t("serviceDetail.notFound")}
        actionLabel={t("serviceDetail.backToList")}
        onAction={() => router.push("/admin/services")}
      />
    );
  }

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/admin/services")}>
        <ArrowLeft size={16} /> {t("serviceDetail.backToList")}
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">{service.display_name}</h1>
          <p className="page-subtitle">{service.name} v{service.version}</p>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-secondary" onClick={openEdit}>
            <PencilSimple size={16} /> {t("common.edit")}
          </button>
          <button
            className={`btn ${service.status === "ACTIVE" ? "btn-danger" : "btn-primary"}`}
            onClick={() => toggleMut.mutate()}
            disabled={toggleMut.isPending}
          >
            {service.status === "ACTIVE" ? t("common.deactivate") : t("common.activate")}
          </button>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="stats-grid" aria-label={t("serviceDetail.usageStats")}>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.totalRequests")}</p>
          <p className="stat-value">{totalRequests}</p>
        </div>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.completed")}</p>
          <p className="stat-value" style={{ color: "var(--success)" }}>{completedRequests}</p>
        </div>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.inProgress")}</p>
          <p className="stat-value" style={{ color: "var(--primary)" }}>{inProgressRequests}</p>
        </div>
        <div className="panel stat-card">
          <p className="detail-label">{t("serviceDetail.failed")}</p>
          <p className="stat-value" style={{ color: "var(--danger)" }}>{failedRequests}</p>
        </div>
      </div>

      {/* Service Info */}
      {editing ? (
        <div className="panel">
          <h3 className="panel-title-mb">{t("serviceDetail.editInfo")}</h3>
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
            <label className="field">
              {t("serviceDetail.description")}
              <textarea className="textarea" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} rows={3} />
            </label>
            {updateMut.isError && <p className="error-text">{(updateMut.error as Error).message}</p>}
            <div className="action-row">
              <button className="btn btn-primary" onClick={() => updateMut.mutate()} disabled={updateMut.isPending}>
                {updateMut.isPending ? <span className="spinner" /> : t("common.save")}
              </button>
              <button className="btn btn-secondary" onClick={() => setEditing(false)}>{t("common.cancel")}</button>
            </div>
          </div>
        </div>
      ) : (
        <div className="panel">
          <h3 className="panel-title-mb">{t("serviceDetail.serviceInfo")}</h3>
          <div className="stack-md">
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
              <p className="detail-label">{t("adminServices.department")}</p>
              <p className="detail-value">{service.department || "—"}</p>
            </div>
            <div>
              <p className="detail-label">{t("serviceDetail.createdDate")}</p>
              <p className="detail-value">{new Date(service.created_at).toLocaleDateString(dateLocale)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Requests */}
      <div className="panel">
        <h3 className="panel-title-mb">{t("serviceDetail.recentRequests")}</h3>
        {serviceRequests.length === 0 ? (
          <div className="empty-state" style={{ padding: "2rem 0" }}>
            <ChartBar size={32} weight="light" style={{ color: "var(--muted)" }} />
            <p className="muted-text">{t("serviceDetail.noRequests")}</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="table" aria-label={t("serviceDetail.recentRequests")}>
              <thead>
                <tr>
                  <th scope="col">{t("reports.tableId")}</th>
                  <th scope="col">{t("reports.tableStatus")}</th>
                  <th scope="col">{t("reports.tableCases")}</th>
                  <th scope="col">{t("reports.tableDate")}</th>
                </tr>
              </thead>
              <tbody>
                {serviceRequests.slice(0, 10).map((req) => (
                  <tr key={req.id}>
                    <td className="mono-cell">{req.id.slice(0, 8)}</td>
                    <td>
                      <span className={`status-chip status-${req.status.toLowerCase()}`}>
                        {t(`status.${req.status}`)}
                      </span>
                    </td>
                    <td>{req.case_count}{locale === "ko" ? "건" : ""}</td>
                    <td>{new Date(req.created_at).toLocaleDateString(dateLocale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
