"use client";

import { useState, useEffect, useCallback } from "react";
import {
  listDicomStudies,
  linkDicomStudy,
  createRequestFromDicom,
  listRequestsPage,
  listServices,
  type DicomStudyRead,
} from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { useT } from "@/lib/i18n";
import {
  X,
  Link as LinkIcon,
  PlusCircle,
  CheckCircle,
  Heartbeat,
  Calendar,
  Database,
  Broadcast,
} from "phosphor-react";

const STATUS_TABS = ["All", "RECEIVING", "RECEIVED", "LINKED", "FAILED"] as const;
type StatusTab = (typeof STATUS_TABS)[number];

const MODALITY_COLORS: Record<string, string> = {
  MR: "#2563eb",
  PT: "#ea580c",
  CT: "#6366f1",
  MG: "#d946ef",
  US: "#0891b2",
  NM: "#dc2626",
  XA: "#ca8a04",
  CR: "#059669",
};

function ModalityBadge({ modality }: { modality: string }) {
  const bg = MODALITY_COLORS[modality] ?? "var(--muted)";
  return (
    <span
      className="status-chip"
      style={{ backgroundColor: bg, color: "white", fontWeight: 700, fontSize: 11 }}
    >
      {modality}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    RECEIVING: { cls: "status-computing", label: "Receiving" },
    RECEIVED: { cls: "status-staging", label: "Received" },
    LINKED: { cls: "status-final", label: "Linked" },
    FAILED: { cls: "status-failed", label: "Failed" },
  };
  const info = map[status] ?? { cls: "", label: status };
  return <span className={`status-chip ${info.cls}`}>{info.label}</span>;
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="panel" style={{ padding: "16px 20px", display: "flex", alignItems: "center", gap: 14 }}>
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: "var(--radius-md)",
          background: `${color}14`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color,
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.1, color: "var(--text)" }}>{value}</div>
        <div className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>{label}</div>
      </div>
    </div>
  );
}

export default function DicomGatewayPage() {
  const t = useT();
  const [studies, setStudies] = useState<DicomStudyRead[]>([]);
  const [total, setTotal] = useState(0);
  const [activeTab, setActiveTab] = useState<StatusTab>("All");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [linkStudy, setLinkStudy] = useState<DicomStudyRead | null>(null);
  const [linkRequestId, setLinkRequestId] = useState("");
  const [linkLoading, setLinkLoading] = useState(false);

  const [createStudy, setCreateStudy] = useState<DicomStudyRead | null>(null);
  const [createServiceId, setCreateServiceId] = useState("");
  const [createLoading, setCreateLoading] = useState(false);

  const tabLabels: Record<StatusTab, string> = {
    All: t("dicom.tabAll"),
    RECEIVING: t("dicom.statusReceiving"),
    RECEIVED: t("dicom.statusReceived"),
    LINKED: t("dicom.statusLinked"),
    FAILED: t("dicom.statusFailed"),
  };

  const fetchStudies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = activeTab !== "All" ? { status: activeTab } : undefined;
      const data = await listDicomStudies(params);
      setStudies(data.items);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message || t("dicom.loadError"));
    } finally {
      setLoading(false);
    }
  }, [activeTab, t]);

  useEffect(() => {
    fetchStudies();
  }, [fetchStudies]);

  const handleLink = async () => {
    if (!linkStudy || !linkRequestId.trim()) return;
    setLinkLoading(true);
    try {
      await linkDicomStudy(linkStudy.study_instance_uid, linkRequestId.trim());
      setLinkStudy(null);
      setLinkRequestId("");
      await fetchStudies();
    } catch (e: any) {
      alert(`${t("dicom.linkFailed")} ${e.message || String(e)}`);
    } finally {
      setLinkLoading(false);
    }
  };

  const handleCreateRequest = async () => {
    if (!createStudy || !createServiceId.trim()) return;
    setCreateLoading(true);
    try {
      await createRequestFromDicom(createStudy.study_instance_uid, createServiceId.trim());
      setCreateStudy(null);
      setCreateServiceId("");
      await fetchStudies();
    } catch (e: any) {
      alert(`${t("dicom.createFailed")} ${e.message || String(e)}`);
    } finally {
      setCreateLoading(false);
    }
  };

  // Counts for stat cards
  const countByStatus = (s: string) => studies.filter((st) => st.status === s).length;

  const totalInstances = studies.reduce((acc, s) => acc + s.num_instances, 0);

  return (
    <div className="stack-lg">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("dicom.gatewayTitle")}</h1>
          <p className="page-subtitle">{t("dicom.gatewaySubtitle")}</p>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <StatCard icon={<Database size={20} weight="duotone" />} label={t("dicom.totalStudies")} value={total} color="#2563eb" />
        <StatCard icon={<Broadcast size={20} weight="duotone" />} label={t("dicom.statusReceiving")} value={countByStatus("RECEIVING")} color="#f59e0b" />
        <StatCard icon={<Heartbeat size={20} weight="duotone" />} label={t("dicom.statusReceived")} value={countByStatus("RECEIVED")} color="#8b5cf6" />
        <StatCard icon={<CheckCircle size={20} weight="duotone" />} label={t("dicom.statusLinked")} value={countByStatus("LINKED")} color="#10b981" />
      </div>

      {/* Status tabs */}
      <div className="filter-tabs">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab}
            className={`filter-tab ${activeTab === tab ? "active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tabLabels[tab]}
            {tab !== "All" && (
              <span style={{ marginLeft: 6, opacity: 0.6, fontSize: 11 }}>
                {countByStatus(tab)}
              </span>
            )}
          </button>
        ))}
      </div>

      {error && <div className="banner banner-warning">{error}</div>}

      {loading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : studies.length === 0 ? (
        <div className="banner banner-info">{t("dicom.noStudies")}</div>
      ) : (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t("dicom.patient")}</th>
                  <th>{t("dicom.modality")}</th>
                  <th>{t("dicom.studyDate")}</th>
                  <th style={{ textAlign: "center" }}>{t("dicom.series")}</th>
                  <th style={{ textAlign: "center" }}>{t("dicom.instances")}</th>
                  <th>{t("common.status")}</th>
                  <th>{t("dicom.sourceAet")}</th>
                  <th>{t("dicom.studyUid")}</th>
                  <th style={{ textAlign: "right" }}>{t("dicom.actions")}</th>
                </tr>
              </thead>
              <tbody>
                {studies.map((s) => (
                  <tr key={s.id}>
                    {/* Patient */}
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>
                        {s.patient_name && s.patient_name !== "UNKNOWN" ? s.patient_name : "—"}
                      </div>
                      {s.patient_id && s.patient_id !== "UNKNOWN" && (
                        <div className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
                          ID: {s.patient_id}
                        </div>
                      )}
                    </td>
                    {/* Modality */}
                    <td>
                      <ModalityBadge modality={s.modality || "—"} />
                    </td>
                    {/* Study Date */}
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <Calendar size={14} style={{ color: "var(--muted)", flexShrink: 0 }} />
                        <span>{s.study_date || "—"}</span>
                      </div>
                    </td>
                    {/* Series */}
                    <td style={{ textAlign: "center", fontWeight: 600 }}>{s.num_series}</td>
                    {/* Instances */}
                    <td style={{ textAlign: "center" }}>
                      <span style={{
                        background: "var(--surface-2, #f0f2f5)",
                        padding: "3px 10px",
                        borderRadius: "var(--radius-sm)",
                        fontWeight: 600,
                        fontSize: 13,
                        fontVariantNumeric: "tabular-nums",
                      }}>
                        {s.num_instances.toLocaleString()}
                      </span>
                    </td>
                    {/* Status */}
                    <td><StatusBadge status={s.status} /></td>
                    {/* Source AET */}
                    <td>
                      <code style={{ fontSize: 12, color: "var(--muted)", background: "var(--surface-2, #f0f2f5)", padding: "2px 6px", borderRadius: 4 }}>
                        {s.source_aet || "—"}
                      </code>
                    </td>
                    {/* Study UID */}
                    <td>
                      <code
                        style={{ fontSize: 11, color: "var(--muted)", cursor: "help" }}
                        title={s.study_instance_uid}
                      >
                        …{s.study_instance_uid.slice(-16)}
                      </code>
                    </td>
                    {/* Actions */}
                    <td>
                      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                        {s.status !== "LINKED" ? (
                          <>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => { setLinkStudy(s); setLinkRequestId(""); }}
                              title={t("dicom.link")}
                              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                            >
                              <LinkIcon size={14} />
                              {t("dicom.link")}
                            </button>
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => { setCreateStudy(s); setCreateServiceId(""); }}
                              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                            >
                              <PlusCircle size={14} />
                              {t("dicom.createRequest")}
                            </button>
                          </>
                        ) : (
                          <span
                            className="status-chip status-final"
                            style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 4 }}
                          >
                            <CheckCircle size={12} weight="fill" />
                            {t("dicom.linked")}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Table footer */}
          <div style={{
            padding: "10px 14px",
            borderTop: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 12,
            color: "var(--muted)",
          }}>
            <span>{total}개 스터디 · {totalInstances.toLocaleString()}개 인스턴스</span>
          </div>
        </div>
      )}

      {/* Link to Request Modal */}
      {linkStudy && (
        <LinkRequestModal
          study={linkStudy}
          requestId={linkRequestId}
          onRequestIdChange={setLinkRequestId}
          loading={linkLoading}
          onLink={handleLink}
          onClose={() => setLinkStudy(null)}
          t={t}
        />
      )}

      {/* Create Request Modal */}
      {createStudy && (
        <CreateRequestModal
          study={createStudy}
          serviceId={createServiceId}
          onServiceIdChange={setCreateServiceId}
          loading={createLoading}
          onCreate={handleCreateRequest}
          onClose={() => setCreateStudy(null)}
          t={t}
        />
      )}
    </div>
  );
}

function LinkRequestModal({
  study,
  requestId,
  onRequestIdChange,
  loading,
  onLink,
  onClose,
  t,
}: {
  study: DicomStudyRead;
  requestId: string;
  onRequestIdChange: (v: string) => void;
  loading: boolean;
  onLink: () => void;
  onClose: () => void;
  t: (key: string) => string;
}) {
  const { data: requestsData } = useQuery({
    queryKey: ["dicom-link-requests"],
    queryFn: () => listRequestsPage({ status: "RECEIVING", limit: 50 }),
  });
  const requests = requestsData?.items ?? [];

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <h2 className="modal-title">{t("dicom.linkModalTitle")}</h2>
          <button className="btn btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        <div style={{ padding: "0 24px 24px" }}>
          <div className="panel" style={{ padding: "12px 16px", marginBottom: 16, background: "var(--surface-2, #f8f9fb)" }}>
            <div className="muted-text" style={{ fontSize: 11, marginBottom: 4 }}>Study UID</div>
            <code style={{ fontSize: 12 }}>{study.study_instance_uid}</code>
          </div>
          <label className="detail-label" style={{ marginBottom: 6, display: "block" }}>{t("dicom.linkModalRequestId")}</label>
          {requests.length > 0 && (
            <select
              className="input"
              value={requestId}
              onChange={(e) => onRequestIdChange(e.target.value)}
              style={{ marginBottom: 8, width: "100%" }}
            >
              <option value="">{t("dicom.selectRequest")}</option>
              {requests.map((r) => (
                <option key={r.id} value={r.id}>
                  #{r.id.slice(0, 8)} — {r.status} ({r.case_count}{t("common.unitCount")})
                </option>
              ))}
            </select>
          )}
          <input
            className="input"
            type="text"
            value={requestId}
            onChange={(e) => onRequestIdChange(e.target.value)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            style={{ fontFamily: "monospace", marginBottom: 20, width: "100%" }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button className="btn btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
            <button className="btn btn-primary" onClick={onLink} disabled={loading || !requestId.trim()}>
              {loading ? t("dicom.linking") : t("dicom.link")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function CreateRequestModal({
  study,
  serviceId,
  onServiceIdChange,
  loading,
  onCreate,
  onClose,
  t,
}: {
  study: DicomStudyRead;
  serviceId: string;
  onServiceIdChange: (v: string) => void;
  loading: boolean;
  onCreate: () => void;
  onClose: () => void;
  t: (key: string) => string;
}) {
  const { data: servicesData } = useQuery({
    queryKey: ["dicom-services"],
    queryFn: () => listServices(),
  });
  const services = servicesData?.items ?? [];

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: 480 }}>
        <div className="modal-header">
          <h2 className="modal-title">{t("dicom.createModalTitle")}</h2>
          <button className="btn btn-secondary btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        <div style={{ padding: "0 24px 24px" }}>
          <div className="panel" style={{ padding: "12px 16px", marginBottom: 16, background: "var(--surface-2, #f8f9fb)" }}>
            <div style={{ display: "flex", gap: 16, fontSize: 13 }}>
              <div>
                <div className="muted-text" style={{ fontSize: 11 }}>{t("dicom.patient")}</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{study.patient_name || study.patient_id || "—"}</div>
              </div>
              <div>
                <div className="muted-text" style={{ fontSize: 11 }}>{t("dicom.modality")}</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{study.modality}</div>
              </div>
              <div>
                <div className="muted-text" style={{ fontSize: 11 }}>{t("dicom.instances")}</div>
                <div style={{ fontWeight: 600, marginTop: 2 }}>{study.num_instances.toLocaleString()}</div>
              </div>
            </div>
          </div>
          <label className="detail-label" style={{ marginBottom: 6, display: "block" }}>{t("dicom.serviceId")}</label>
          {services.length > 0 && (
            <select
              className="input"
              value={serviceId}
              onChange={(e) => onServiceIdChange(e.target.value)}
              style={{ marginBottom: 8, width: "100%" }}
            >
              <option value="">{t("dicom.selectService")}</option>
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.display_name} ({s.name})
                </option>
              ))}
            </select>
          )}
          <input
            className="input"
            type="text"
            value={serviceId}
            onChange={(e) => onServiceIdChange(e.target.value)}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            style={{ fontFamily: "monospace", marginBottom: 20, width: "100%" }}
          />
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <button className="btn btn-secondary" onClick={onClose}>{t("common.cancel")}</button>
            <button className="btn btn-primary" onClick={onCreate} disabled={loading || !serviceId.trim()}>
              {loading ? t("dicom.creating") : t("dicom.createRequest")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
