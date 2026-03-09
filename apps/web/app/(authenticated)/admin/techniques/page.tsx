"use client";

import {
  type TechniqueModuleRead,
  createTechniqueModule,
  deprecateTechniqueModule,
  listTechniqueModules,
} from "@/lib/api";
import { type TranslationKey, useT } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Plus, X, Cube } from "phosphor-react";
import { useState } from "react";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { SkeletonCards } from "@/components/skeleton";

type T = (key: TranslationKey) => string;

const MODALITY_COLORS: Record<string, string> = {
  PET: "#ea580c",
  MRI: "#2563eb",
  EEG: "#16a34a",
  MEG: "#9333ea",
  fMRI: "#0891b2",
  SPECT: "#dc2626",
  PSG: "#ca8a04",
};

const MODALITIES = ["MRI", "PET", "EEG", "MEG", "fMRI", "SPECT", "PSG"];

function ModalityBadge({ modality }: { modality: string }) {
  const bg = MODALITY_COLORS[modality] ?? "var(--muted)";
  return (
    <span className="status-chip" style={{ backgroundColor: bg, color: "white", fontWeight: 600 }}>
      {modality}
    </span>
  );
}

function StatusChip({ status, t }: { status: string; t: T }) {
  const isActive = status === "ACTIVE";
  return (
    <span className={`status-chip ${isActive ? "status-final" : "status-cancelled"}`}>
      {isActive ? t("techniques.active") : t("techniques.deprecated")}
    </span>
  );
}

export default function TechniquesPage() {
  const t = useT();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [filterModality, setFilterModality] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [deprecatingId, setDeprecatingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["techniques", filterModality],
    queryFn: () => listTechniqueModules(filterModality ? { modality: filterModality } : undefined),
  });

  const deprecateMutation = useMutation({
    mutationFn: deprecateTechniqueModule,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["techniques"] }),
  });

  const techniques = data?.items ?? [];
  const modalities = [...new Set(techniques.map((t) => t.modality))].sort();

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("techniques.title")}</h1>
          <p className="page-subtitle">
            {t("common.total")} {data?.total ?? 0}
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={16} weight="bold" /> {t("techniques.addTechnique")}
        </button>
      </div>

      <div className="filter-tabs">
        <button
          type="button"
          className={`filter-tab ${!filterModality ? "active" : ""}`}
          onClick={() => setFilterModality("")}
        >
          {t("adminRequests.filterAll")}
        </button>
        {modalities.map((mod) => (
          <button
            type="button"
            key={mod}
            className={`filter-tab ${filterModality === mod ? "active" : ""}`}
            onClick={() => setFilterModality(mod)}
          >
            {mod}
          </button>
        ))}
      </div>

      {isLoading ? (
        <SkeletonCards count={6} />
      ) : techniques.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><Cube size={48} weight="light" /></div>
          <h3 className="empty-state-title">{t("techniques.noTechniques")}</h3>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: "16px",
          }}
        >
          {techniques.map((tech) => (
            <TechniqueCard
              key={tech.id}
              technique={tech}
              onDeprecate={() => setDeprecatingId(tech.id)}
              onClick={() => router.push(`/admin/techniques/${tech.id}`)}
              t={t}
            />
          ))}
        </div>
      )}

      {showCreate && <CreateTechniqueModal onClose={() => setShowCreate(false)} t={t} />}

      <ConfirmDialog
        open={!!deprecatingId}
        title={t("techniques.deprecate")}
        message={t("techniques.confirmDeprecate")}
        confirmLabel={t("techniques.deprecate")}
        cancelLabel={t("common.cancel")}
        variant="danger"
        loading={deprecateMutation.isPending}
        onConfirm={() => {
          if (deprecatingId) {
            deprecateMutation.mutate(deprecatingId, {
              onSuccess: () => setDeprecatingId(null),
            });
          }
        }}
        onCancel={() => setDeprecatingId(null)}
      />
    </div>
  );
}

function TechniqueCard({
  technique,
  onDeprecate,
  onClick,
  t,
}: {
  technique: TechniqueModuleRead;
  onDeprecate: () => void;
  onClick: () => void;
  t: T;
}) {
  const gpu = (technique.resource_requirements as Record<string, unknown>)?.gpu;
  const memGb = (technique.resource_requirements as Record<string, unknown>)?.memory_gb;

  return (
    <div
      className="panel technique-card"
      style={{ display: "flex", flexDirection: "column", gap: "10px", cursor: "pointer" }}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter") onClick();
      }}
      role="button"
      tabIndex={0}
    >
      {/* Header: key + status */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <code style={{ fontSize: "14px", fontWeight: 700, color: "var(--text)" }}>
          {technique.key}
        </code>
        <StatusChip status={technique.status} t={t} />
      </div>

      {/* Titles */}
      <div>
        <p style={{ fontSize: "15px", fontWeight: 600, margin: 0 }}>{technique.title_ko}</p>
        <p className="muted-text" style={{ fontSize: "13px", marginTop: "2px" }}>
          {technique.title_en}
        </p>
      </div>

      {/* Modality + Category */}
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
        <ModalityBadge modality={technique.modality} />
        <span className="muted-text" style={{ fontSize: "12px" }}>
          {technique.category}
        </span>
      </div>

      {/* Docker image */}
      <div
        style={{
          padding: "6px 10px",
          background: "var(--surface-2)",
          borderRadius: "var(--radius-sm)",
          fontSize: "12px",
          fontFamily: "monospace",
        }}
      >
        {technique.docker_image}
      </div>

      {/* Resource info */}
      <div style={{ display: "flex", gap: "12px", fontSize: "12px", flexWrap: "wrap" }}>
        <span className="muted-text" style={{ fontWeight: 600 }}>
          v{technique.version}
        </span>
        {gpu !== undefined && (
          <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: gpu ? "var(--success)" : "var(--muted)",
                display: "inline-block",
              }}
            />
            <span className="muted-text">
              GPU: {gpu ? t("techniques.gpuRequired") : t("techniques.gpuNotRequired")}
            </span>
          </span>
        )}
        {memGb !== undefined && <span className="muted-text">{String(memGb)}GB RAM</span>}
      </div>

      {/* Deprecate action */}
      {technique.status === "ACTIVE" && (
        <div style={{ marginTop: "4px", display: "flex", justifyContent: "flex-end" }}>
          <button
            type="button"
            className="btn btn-danger btn-sm"
            onClick={(e) => {
              e.stopPropagation();
              onDeprecate();
            }}
          >
            {t("techniques.deprecate")}
          </button>
        </div>
      )}
    </div>
  );
}

/* ---------- Create Modal ---------- */

interface CreateForm {
  key: string;
  title_ko: string;
  title_en: string;
  modality: string;
  category: string;
  docker_image: string;
  version: string;
  description: string;
  qc_config: string;
  output_schema: string;
  resource_requirements: string;
}

const EMPTY_FORM: CreateForm = {
  key: "",
  title_ko: "",
  title_en: "",
  modality: "MRI",
  category: "",
  docker_image: "",
  version: "1.0.0",
  description: "",
  qc_config: "",
  output_schema: "",
  resource_requirements: "",
};

function CreateTechniqueModal({ onClose, t }: { onClose: () => void; t: T }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [form, setForm] = useState<CreateForm>(EMPTY_FORM);

  const [jsonErr, setJsonErr] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: () => {
      let qc: Record<string, unknown> | null = null;
      let outSchema: Record<string, unknown> | null = null;
      let resources: Record<string, unknown> | null = null;
      try {
        if (form.qc_config.trim()) qc = JSON.parse(form.qc_config);
        if (form.output_schema.trim()) outSchema = JSON.parse(form.output_schema);
        if (form.resource_requirements.trim()) resources = JSON.parse(form.resource_requirements);
      } catch {
        throw new Error("Invalid JSON");
      }
      return createTechniqueModule({
        key: form.key,
        title_ko: form.title_ko,
        title_en: form.title_en,
        modality: form.modality,
        category: form.category,
        docker_image: form.docker_image,
        version: form.version,
        description: form.description || null,
        qc_config: qc,
        output_schema: outSchema,
        resource_requirements: resources,
      });
    },
    onSuccess: (created) => {
      setJsonErr(null);
      queryClient.invalidateQueries({ queryKey: ["techniques"] });
      onClose();
      router.push(`/admin/techniques/${created.id}`);
    },
    onError: (err) => {
      if (err instanceof Error && err.message === "Invalid JSON") {
        setJsonErr("Invalid JSON");
      }
    },
  });

  const canSubmit =
    form.key &&
    form.title_ko &&
    form.title_en &&
    form.modality &&
    form.category &&
    form.docker_image;

  const set = (patch: Partial<CreateForm>) => setForm((f) => ({ ...f, ...patch }));

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: 600 }}>
        <div className="modal-header">
          <h2 className="modal-title">{t("techniques.create")}</h2>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose}>
            <X size={16} />
          </button>
        </div>
        <div style={{ padding: "0 24px 24px" }}>
          <div className="stack-md">
            <div className="form-grid">
              <label className="field">
                {t("techniques.key")}
                <input
                  className="input"
                  value={form.key}
                  onChange={(e) =>
                    set({ key: e.target.value.replace(/[^A-Za-z0-9_]/g, "").toUpperCase() })
                  }
                  placeholder={t("techniques.keyPlaceholder")}
                  style={{ fontFamily: "var(--font-mono)" }}
                />
              </label>
              <label className="field">
                {t("techniques.version")}
                <input
                  className="input"
                  value={form.version}
                  onChange={(e) => set({ version: e.target.value })}
                />
              </label>
            </div>
            <div className="form-grid">
              <label className="field">
                {t("techniques.titleKo")}
                <input
                  className="input"
                  value={form.title_ko}
                  onChange={(e) => set({ title_ko: e.target.value })}
                  placeholder={t("techniques.titleKoPlaceholder")}
                />
              </label>
              <label className="field">
                {t("techniques.titleEn")}
                <input
                  className="input"
                  value={form.title_en}
                  onChange={(e) => set({ title_en: e.target.value })}
                  placeholder={t("techniques.titleEnPlaceholder")}
                />
              </label>
            </div>
            <div className="form-grid">
              <label className="field">
                {t("techniques.modality")}
                <select
                  className="input"
                  value={form.modality}
                  onChange={(e) => set({ modality: e.target.value })}
                >
                  {MODALITIES.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                {t("techniques.category")}
                <input
                  className="input"
                  value={form.category}
                  onChange={(e) => set({ category: e.target.value })}
                  placeholder="Structural"
                />
              </label>
            </div>
            <label className="field">
              {t("techniques.dockerImage")}
              <input
                className="input"
                value={form.docker_image}
                onChange={(e) => set({ docker_image: e.target.value })}
                placeholder={t("techniques.dockerImagePlaceholder")}
                style={{ fontFamily: "var(--font-mono)" }}
              />
            </label>
            <label className="field">
              {t("techniques.description")}
              <textarea
                className="input"
                rows={2}
                value={form.description}
                onChange={(e) => set({ description: e.target.value })}
                placeholder={t("techniques.descriptionPlaceholder")}
              />
            </label>
            <label className="field">
              {t("techniques.resourceRequirements")} (JSON)
              <textarea
                className="input"
                rows={3}
                value={form.resource_requirements}
                onChange={(e) => {
                  set({ resource_requirements: e.target.value });
                  setJsonErr(null);
                }}
                placeholder='{"gpu": true, "memory_gb": 16, "cpu_cores": 4, "timeout_seconds": 3600}'
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
            </label>
            <label className="field">
              {t("techniques.qcConfig")} (JSON)
              <textarea
                className="input"
                rows={3}
                value={form.qc_config}
                onChange={(e) => {
                  set({ qc_config: e.target.value });
                  setJsonErr(null);
                }}
                placeholder="{}"
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
            </label>
            <label className="field">
              {t("techniques.outputSchema")} (JSON)
              <textarea
                className="input"
                rows={3}
                value={form.output_schema}
                onChange={(e) => {
                  set({ output_schema: e.target.value });
                  setJsonErr(null);
                }}
                placeholder="{}"
                style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
              />
            </label>
            {jsonErr && (
              <p style={{ color: "var(--danger)", fontSize: 12 }}>{jsonErr}</p>
            )}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              {t("common.cancel")}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!canSubmit || createMut.isPending}
              onClick={() => createMut.mutate()}
            >
              {createMut.isPending ? <span className="spinner" /> : t("techniques.create")}
            </button>
          </div>
          {createMut.isError && (
            <p style={{ color: "var(--danger)", fontSize: 13, marginTop: 8 }}>
              {t("techniques.createError")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
