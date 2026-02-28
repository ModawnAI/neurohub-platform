"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  createGroupStudy,
  listGroupStudies,
  type GroupAnalysisType,
  type GroupStudyBrief,
} from "@/lib/api";
import { listServices, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

const STATUS_STYLES: Record<string, { bg: string; color: string }> = {
  DRAFT: { bg: "var(--color-gray-3)", color: "var(--color-gray-11)" },
  RUNNING: { bg: "var(--color-blue-3)", color: "var(--color-blue-11)" },
  COMPLETED: { bg: "var(--color-green-3)", color: "var(--color-green-11)" },
  FAILED: { bg: "var(--color-red-3)", color: "var(--color-red-11)" },
};

const ANALYSIS_TYPES: GroupAnalysisType[] = [
  "COMPARISON",
  "CORRELATION",
  "REGRESSION",
  "LONGITUDINAL",
];

export default function GroupStudiesPage() {
  const { t, locale } = useTranslation();
  const [studies, setStudies] = useState<GroupStudyBrief[]>([]);
  const [services, setServices] = useState<ServiceRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    description: "",
    service_id: "",
    analysis_type: "COMPARISON" as GroupAnalysisType,
  });

  const analysisTypeLabels: Record<string, string> = {
    COMPARISON: t("groupStudy.comparison"),
    CORRELATION: t("groupStudy.correlation"),
    REGRESSION: t("groupStudy.regression"),
    LONGITUDINAL: t("groupStudy.longitudinal"),
  };

  useEffect(() => {
    Promise.all([listGroupStudies(), listServices()])
      .then(([s, svc]) => {
        setStudies(s);
        setServices(svc.items ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.service_id) {
      setError(t("groupStudy.selectRequest"));
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const study = await createGroupStudy({
        name: form.name,
        description: form.description || undefined,
        service_id: form.service_id,
        analysis_type: form.analysis_type,
      });
      setStudies((prev) => [{ ...study, member_count: 0 }, ...prev]);
      setShowDialog(false);
      setForm({ name: "", description: "", service_id: "", analysis_type: "COMPARISON" });
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("groupStudy.title")}</h1>
          <p className="page-subtitle">{t("groupStudy.subtitle")}</p>
        </div>
        <button onClick={() => setShowDialog(true)} className="btn btn-primary">
          + {t("groupStudy.newStudy")}
        </button>
      </div>

      {error && (
        <div style={{ padding: 12, borderRadius: 6, backgroundColor: "var(--color-red-3)", color: "var(--color-red-11)", fontSize: 13 }}>
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : studies.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-text">{t("groupStudy.noStudies")}</p>
          <p className="muted-text">{t("groupStudy.createFirst")}</p>
        </div>
      ) : (
        <div className="panel" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ backgroundColor: "var(--color-gray-2)", fontSize: 12, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                <th style={{ padding: "10px 16px", textAlign: "left" }}>{t("groupStudy.name")}</th>
                <th style={{ padding: "10px 16px", textAlign: "left" }}>{t("groupStudy.analysisType")}</th>
                <th style={{ padding: "10px 16px", textAlign: "left" }}>{t("groupStudy.status")}</th>
                <th style={{ padding: "10px 16px", textAlign: "left" }}>{t("groupStudy.members")}</th>
                <th style={{ padding: "10px 16px", textAlign: "left" }}>{t("groupStudy.createdDate")}</th>
                <th style={{ padding: "10px 16px" }} />
              </tr>
            </thead>
            <tbody>
              {studies.map((s) => {
                const style = STATUS_STYLES[s.status] ?? STATUS_STYLES.DRAFT;
                return (
                  <tr key={s.id} style={{ borderBottom: "1px solid var(--color-gray-4)" }}>
                    <td style={{ padding: "10px 16px", fontWeight: 600 }}>{s.name}</td>
                    <td style={{ padding: "10px 16px", color: "var(--color-gray-11)" }}>{analysisTypeLabels[s.analysis_type] ?? s.analysis_type}</td>
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{ padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600, backgroundColor: style?.bg, color: style?.color }}>
                        {s.status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--color-gray-11)" }}>{s.member_count}</td>
                    <td style={{ padding: "10px 16px", color: "var(--color-gray-9)" }}>
                      {new Date(s.created_at).toLocaleDateString(locale === "ko" ? "ko-KR" : "en-US")}
                    </td>
                    <td style={{ padding: "10px 16px", textAlign: "right" }}>
                      <Link href={`/user/group-studies/${s.id}`} style={{ color: "var(--primary)", fontSize: 12 }}>
                        {t("groupStudy.view")} &rarr;
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create dialog */}
      {showDialog && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div className="panel" style={{ width: "100%", maxWidth: 440 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>{t("groupStudy.newStudy")}</h2>
            <form onSubmit={handleCreate} className="stack-md">
              <label className="field">
                {t("groupStudy.name")} *
                <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </label>
              <label className="field">
                {t("groupStudy.description")}
                <textarea className="textarea" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </label>
              <label className="field">
                {t("groupStudy.service")} *
                <select className="input" required value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })}>
                  <option value="">--</option>
                  {services.map((svc) => (
                    <option key={svc.id} value={svc.id}>{svc.display_name || svc.name}</option>
                  ))}
                </select>
              </label>
              <label className="field">
                {t("groupStudy.analysisType")} *
                <select className="input" value={form.analysis_type} onChange={(e) => setForm({ ...form, analysis_type: e.target.value as GroupAnalysisType })}>
                  {ANALYSIS_TYPES.map((at) => (
                    <option key={at} value={at}>{analysisTypeLabels[at] ?? at}</option>
                  ))}
                </select>
              </label>
              {error && <p style={{ fontSize: 13, color: "var(--color-red-11)" }}>{error}</p>}
              <div className="action-row" style={{ justifyContent: "flex-end" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowDialog(false)}>{t("common.cancel")}</button>
                <button type="submit" className="btn btn-primary" disabled={creating}>
                  {creating ? <span className="spinner" /> : t("groupStudy.create")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
