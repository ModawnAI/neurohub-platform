"use client";

import { useToast } from "@/components/toast";
import {
  type TechniqueModuleRead,
  deprecateTechniqueModule,
  getTechniqueModule,
  updateTechniqueModule,
} from "@/lib/api";
import { type TranslationKey, useT } from "@/lib/i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft } from "phosphor-react";
import { useState } from "react";
import { Breadcrumb } from "@/components/breadcrumb";
import { ConfirmDialog } from "@/components/confirm-dialog";

type T = (key: TranslationKey) => string;

const MODALITIES = ["MRI", "PET", "EEG", "MEG", "fMRI", "SPECT", "PSG"];

interface ResourceReq {
  gpu: boolean;
  memory_gb: number;
  cpu_cores: number;
  timeout_seconds: number;
}

function parseResources(raw: Record<string, unknown> | null | undefined): ResourceReq {
  return {
    gpu: Boolean(raw?.gpu),
    memory_gb: Number(raw?.memory_gb) || 0,
    cpu_cores: Number(raw?.cpu_cores) || 0,
    timeout_seconds: Number(raw?.timeout_seconds) || 0,
  };
}

export default function TechniqueDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const t = useT();
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const { data: technique, isLoading } = useQuery({
    queryKey: ["technique", id],
    queryFn: () => getTechniqueModule(id),
  });

  if (isLoading) {
    return (
      <div className="loading-center">
        <span className="spinner" />
      </div>
    );
  }

  if (!technique) {
    return <div className="banner banner-info">{t("serviceDetail.notFound")}</div>;
  }

  return (
    <div className="stack-lg">
      {/* Header */}
      <div>
        <Breadcrumb
          items={[
            { label: t("techniques.title"), href: "/admin/techniques" },
            { label: technique.key },
          ]}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
          <div>
            <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <code style={{ fontSize: "inherit" }}>{technique.key}</code>
              <span
                className={`status-chip ${technique.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}
              >
                {technique.status === "ACTIVE"
                  ? t("techniques.active")
                  : t("techniques.deprecated")}
              </span>
            </h1>
            <p className="page-subtitle">
              {technique.title_ko} — {technique.title_en}
            </p>
          </div>
        </div>
      </div>

      {/* Editable sections */}
      <BasicInfoPanel technique={technique} t={t} addToast={addToast} queryClient={queryClient} />
      <ResourcePanel technique={technique} t={t} addToast={addToast} queryClient={queryClient} />
      <JsonPanel
        technique={technique}
        field="qc_config"
        label={t("techniques.qcConfig")}
        t={t}
        addToast={addToast}
        queryClient={queryClient}
      />
      <JsonPanel
        technique={technique}
        field="output_schema"
        label={t("techniques.outputSchema")}
        t={t}
        addToast={addToast}
        queryClient={queryClient}
      />

      {/* Deprecate */}
      {technique.status === "ACTIVE" && (
        <DeprecateSection
          technique={technique}
          t={t}
          router={router}
          queryClient={queryClient}
          addToast={addToast}
        />
      )}
    </div>
  );
}

/* ---------- Basic Info Panel ---------- */

function BasicInfoPanel({
  technique,
  t,
  addToast,
  queryClient,
}: {
  technique: TechniqueModuleRead;
  t: T;
  addToast: (type: "success" | "error", msg: string) => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [form, setForm] = useState({
    title_ko: technique.title_ko,
    title_en: technique.title_en,
    modality: technique.modality,
    category: technique.category,
    description: technique.description ?? "",
    docker_image: technique.docker_image,
    version: technique.version,
  });

  const isDirty =
    form.title_ko !== technique.title_ko ||
    form.title_en !== technique.title_en ||
    form.modality !== technique.modality ||
    form.category !== technique.category ||
    form.description !== (technique.description ?? "") ||
    form.docker_image !== technique.docker_image ||
    form.version !== technique.version;

  const saveMut = useMutation({
    mutationFn: () =>
      updateTechniqueModule(technique.id, {
        title_ko: form.title_ko,
        title_en: form.title_en,
        modality: form.modality,
        category: form.category,
        description: form.description || null,
        docker_image: form.docker_image,
        version: form.version,
      } as Partial<TechniqueModuleRead>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["technique", technique.id] });
      queryClient.invalidateQueries({ queryKey: ["techniques"] });
      addToast("success", t("techniques.updateSuccess"));
    },
    onError: () => addToast("error", t("techniques.updateError")),
  });

  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));

  return (
    <div className="panel">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h3 className="panel-title">{t("serviceDetail.serviceInfo")}</h3>
        {isDirty && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending}
          >
            {saveMut.isPending ? <span className="spinner" /> : t("techniques.save")}
          </button>
        )}
      </div>

      <div className="stack-md">
        <div className="form-grid">
          <label className="field">
            {t("techniques.key")}
            <input
              className="input"
              value={technique.key}
              disabled
              style={{ fontFamily: "var(--font-mono)", opacity: 0.6 }}
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
            />
          </label>
          <label className="field">
            {t("techniques.titleEn")}
            <input
              className="input"
              value={form.title_en}
              onChange={(e) => set({ title_en: e.target.value })}
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
            />
          </label>
        </div>
        <label className="field">
          {t("techniques.dockerImage")}
          <input
            className="input"
            value={form.docker_image}
            onChange={(e) => set({ docker_image: e.target.value })}
            style={{ fontFamily: "var(--font-mono)" }}
          />
        </label>
        <label className="field">
          {t("techniques.description")}
          <textarea
            className="input"
            rows={3}
            value={form.description}
            onChange={(e) => set({ description: e.target.value })}
            placeholder={t("techniques.descriptionPlaceholder")}
          />
        </label>
      </div>
    </div>
  );
}

/* ---------- Resource Panel ---------- */

function ResourcePanel({
  technique,
  t,
  addToast,
  queryClient,
}: {
  technique: TechniqueModuleRead;
  t: T;
  addToast: (type: "success" | "error", msg: string) => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const initial = parseResources(technique.resource_requirements as Record<string, unknown> | null);
  const [res, setRes] = useState<ResourceReq>(initial);

  const isDirty = JSON.stringify(res) !== JSON.stringify(initial);

  const saveMut = useMutation({
    mutationFn: () =>
      updateTechniqueModule(technique.id, {
        resource_requirements: res as unknown as Record<string, unknown>,
      } as Partial<TechniqueModuleRead>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["technique", technique.id] });
      queryClient.invalidateQueries({ queryKey: ["techniques"] });
      addToast("success", t("techniques.updateSuccess"));
    },
    onError: () => addToast("error", t("techniques.updateError")),
  });

  const set = (patch: Partial<ResourceReq>) => setRes((r) => ({ ...r, ...patch }));

  return (
    <div className="panel">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h3 className="panel-title">{t("techniques.resourceRequirements")}</h3>
        {isDirty && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending}
          >
            {saveMut.isPending ? <span className="spinner" /> : t("techniques.save")}
          </button>
        )}
      </div>

      <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr 1fr" }}>
        <label className="field" style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={res.gpu}
            onChange={(e) => set({ gpu: e.target.checked })}
          />
          {t("techniques.gpu")}
        </label>
        <label className="field">
          {t("techniques.memoryGb")}
          <input
            className="input"
            type="number"
            min={0}
            step={1}
            value={res.memory_gb}
            onChange={(e) => set({ memory_gb: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          {t("techniques.cpuCores")}
          <input
            className="input"
            type="number"
            min={0}
            step={1}
            value={res.cpu_cores}
            onChange={(e) => set({ cpu_cores: Number(e.target.value) })}
          />
        </label>
        <label className="field">
          {t("techniques.timeoutSeconds")}
          <input
            className="input"
            type="number"
            min={0}
            step={60}
            value={res.timeout_seconds}
            onChange={(e) => set({ timeout_seconds: Number(e.target.value) })}
          />
        </label>
      </div>
    </div>
  );
}

/* ---------- JSON Panel (QC Config / Output Schema) ---------- */

function JsonPanel({
  technique,
  field,
  label,
  t,
  addToast,
  queryClient,
}: {
  technique: TechniqueModuleRead;
  field: "qc_config" | "output_schema";
  label: string;
  t: T;
  addToast: (type: "success" | "error", msg: string) => void;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const raw = technique[field] as Record<string, unknown> | null;
  const initial = raw ? JSON.stringify(raw, null, 2) : "";
  const [text, setText] = useState(initial);
  const [parseErr, setParseErr] = useState<string | null>(null);

  const isDirty = text !== initial;

  const saveMut = useMutation({
    mutationFn: () => {
      let parsed: Record<string, unknown> | null = null;
      if (text.trim()) {
        try {
          parsed = JSON.parse(text);
        } catch {
          throw new Error("Invalid JSON");
        }
      }
      return updateTechniqueModule(technique.id, {
        [field]: parsed,
      } as Partial<TechniqueModuleRead>);
    },
    onSuccess: () => {
      setParseErr(null);
      queryClient.invalidateQueries({ queryKey: ["technique", technique.id] });
      queryClient.invalidateQueries({ queryKey: ["techniques"] });
      addToast("success", t("techniques.updateSuccess"));
    },
    onError: (err) => {
      if (err instanceof Error && err.message === "Invalid JSON") {
        setParseErr("Invalid JSON");
      } else {
        addToast("error", t("techniques.updateError"));
      }
    },
  });

  return (
    <div className="panel">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h3 className="panel-title">{label}</h3>
        {isDirty && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending}
          >
            {saveMut.isPending ? <span className="spinner" /> : t("techniques.save")}
          </button>
        )}
      </div>

      <textarea
        className="input"
        rows={8}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          setParseErr(null);
        }}
        placeholder="{}"
        style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
      />
      {parseErr && <p style={{ color: "var(--danger)", fontSize: 12, marginTop: 4 }}>{parseErr}</p>}
    </div>
  );
}

/* ---------- Deprecate Section ---------- */

function DeprecateSection({
  technique,
  t,
  router,
  queryClient,
  addToast,
}: {
  technique: TechniqueModuleRead;
  t: T;
  router: ReturnType<typeof useRouter>;
  queryClient: ReturnType<typeof useQueryClient>;
  addToast: (type: "success" | "error", msg: string) => void;
}) {
  const [showConfirm, setShowConfirm] = useState(false);

  const deprecateMut = useMutation({
    mutationFn: () => deprecateTechniqueModule(technique.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["techniques"] });
      addToast("success", t("techniques.deprecateSuccess"));
      router.push("/admin/techniques");
    },
  });

  return (
    <div className="panel" style={{ borderColor: "var(--danger, #ef4444)" }}>
      <h3 className="panel-title" style={{ color: "var(--danger)" }}>
        {t("techniques.deprecate")}
      </h3>
      <p className="muted-text" style={{ fontSize: 13, margin: "8px 0 12px" }}>
        {t("techniques.confirmDeprecate")}
      </p>
      <button type="button" className="btn btn-danger" onClick={() => setShowConfirm(true)}>
        {t("techniques.deprecate")}
      </button>

      <ConfirmDialog
        open={showConfirm}
        title={t("techniques.deprecate")}
        message={t("techniques.confirmDeprecate")}
        confirmLabel={t("techniques.deprecate")}
        cancelLabel={t("common.cancel")}
        variant="danger"
        loading={deprecateMut.isPending}
        onConfirm={() => deprecateMut.mutate()}
        onCancel={() => setShowConfirm(false)}
      />
    </div>
  );
}
