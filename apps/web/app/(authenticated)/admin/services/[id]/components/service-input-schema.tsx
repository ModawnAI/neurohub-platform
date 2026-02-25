"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash, ArrowUp, ArrowDown } from "phosphor-react";
import { updateServiceDefinition, type ServiceRead } from "@/lib/api";
import type { InputField } from "@/components/dynamic-form/types";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

const FIELD_TYPES = ["text", "number", "select", "date", "radio", "checkbox", "textarea"] as const;

const EMPTY_FIELD: InputField = {
  key: "",
  type: "text",
  label: "",
  required: false,
};

interface Props {
  service: ServiceRead;
}

export function ServiceInputSchema({ service }: Props) {
  const { locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const existingFields: InputField[] = service.input_schema?.fields ?? [];
  const [fields, setFields] = useState<InputField[]>(existingFields);
  const [editIdx, setEditIdx] = useState<number | null>(null);

  const saveMut = useMutation({
    mutationFn: () =>
      updateServiceDefinition(service.id, {
        input_schema: { fields: fields as unknown as Array<Record<string, unknown>> },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      queryClient.invalidateQueries({ queryKey: ["service", service.id] });
      addToast("success", ko ? "입력 스키마 저장 완료" : "Input schema saved");
    },
    onError: () => addToast("error", ko ? "저장 실패" : "Save failed"),
  });

  const addField = () => {
    setFields([...fields, { ...EMPTY_FIELD, key: `field_${fields.length + 1}` }]);
    setEditIdx(fields.length);
  };

  const removeField = (idx: number) => {
    setFields(fields.filter((_, i) => i !== idx));
    setEditIdx(null);
  };

  const updateField = (idx: number, patch: Partial<InputField>) => {
    setFields(fields.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  };

  const moveField = (idx: number, dir: -1 | 1) => {
    const next = [...fields];
    const target = idx + dir;
    if (target < 0 || target >= next.length) return;
    const a = next[idx]!;
    const b = next[target]!;
    next[idx] = b;
    next[target] = a;
    setFields(next);
    setEditIdx(target);
  };

  const isDirty = JSON.stringify(fields) !== JSON.stringify(existingFields);

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 className="panel-title">{ko ? "입력 스키마" : "Input Schema"}</h3>
          <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
            {ko ? "환자 정보 및 입력 필드를 정의합니다" : "Define patient demographics and input fields"}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={addField}>
            <Plus size={14} /> {ko ? "필드 추가" : "Add Field"}
          </button>
          {isDirty && (
            <button className="btn btn-primary btn-sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
              {saveMut.isPending ? <span className="spinner" /> : ko ? "저장" : "Save"}
            </button>
          )}
        </div>
      </div>

      {fields.length === 0 ? (
        <p className="muted-text" style={{ fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          {ko ? "정의된 입력 필드가 없습니다. 필드를 추가하세요." : "No input fields defined. Add fields to get started."}
        </p>
      ) : (
        <div className="stack-sm">
          {fields.map((field, idx) => (
            <div
              key={idx}
              style={{
                border: `1px solid ${editIdx === idx ? "var(--primary)" : "var(--border)"}`,
                borderRadius: "var(--radius-sm)",
                padding: 12,
                background: editIdx === idx ? "var(--primary-subtle)" : "transparent",
                cursor: "pointer",
              }}
              onClick={() => setEditIdx(editIdx === idx ? null : idx)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span className="mono-cell" style={{ fontSize: 11, color: "var(--muted)" }}>{field.key || "—"}</span>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{field.label || (ko ? "라벨 없음" : "No label")}</span>
                  <span className="status-chip" style={{ fontSize: 10 }}>{field.type}</span>
                  {field.required && <span style={{ color: "var(--danger)", fontSize: 11, fontWeight: 600 }}>*</span>}
                </div>
                <div style={{ display: "flex", gap: 4 }} onClick={(e) => e.stopPropagation()}>
                  <button className="btn btn-secondary" style={{ padding: "2px 4px" }} onClick={() => moveField(idx, -1)} disabled={idx === 0}>
                    <ArrowUp size={12} />
                  </button>
                  <button className="btn btn-secondary" style={{ padding: "2px 4px" }} onClick={() => moveField(idx, 1)} disabled={idx === fields.length - 1}>
                    <ArrowDown size={12} />
                  </button>
                  <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={() => removeField(idx)}>
                    <Trash size={12} />
                  </button>
                </div>
              </div>

              {editIdx === idx && (
                <div className="stack-sm" style={{ marginTop: 12 }} onClick={(e) => e.stopPropagation()}>
                  <div className="form-grid">
                    <label className="field">
                      {ko ? "키 (영문)" : "Key"}
                      <input className="input" value={field.key} onChange={(e) => updateField(idx, { key: e.target.value.replace(/[^a-z0-9_]/g, "") })} placeholder="patient_age" />
                    </label>
                    <label className="field">
                      {ko ? "타입" : "Type"}
                      <select className="input" value={field.type} onChange={(e) => updateField(idx, { type: e.target.value as InputField["type"] })}>
                        {FIELD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </label>
                  </div>
                  <div className="form-grid">
                    <label className="field">
                      {ko ? "라벨 (한글)" : "Label (Korean)"}
                      <input className="input" value={field.label} onChange={(e) => updateField(idx, { label: e.target.value })} placeholder={ko ? "환자 나이" : "Patient Age"} />
                    </label>
                    <label className="field">
                      {ko ? "라벨 (영문)" : "Label (English)"}
                      <input className="input" value={field.label_en || ""} onChange={(e) => updateField(idx, { label_en: e.target.value || undefined })} placeholder="Patient Age" />
                    </label>
                  </div>
                  <div className="form-grid">
                    <label className="field">
                      {ko ? "플레이스홀더" : "Placeholder"}
                      <input className="input" value={field.placeholder || ""} onChange={(e) => updateField(idx, { placeholder: e.target.value || undefined })} />
                    </label>
                    <label className="field" style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 24 }}>
                      <input type="checkbox" checked={field.required ?? false} onChange={(e) => updateField(idx, { required: e.target.checked })} />
                      {ko ? "필수 입력" : "Required"}
                    </label>
                  </div>
                  {(field.type === "select" || field.type === "radio") && (
                    <label className="field">
                      {ko ? "옵션 (JSON)" : "Options (JSON)"}
                      <textarea
                        className="textarea"
                        rows={3}
                        value={JSON.stringify(field.options || [], null, 2)}
                        onChange={(e) => {
                          try { updateField(idx, { options: JSON.parse(e.target.value) }); } catch {}
                        }}
                        placeholder={`[{"value":"M","label":"남성"},{"value":"F","label":"여성"}]`}
                        style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}
                      />
                    </label>
                  )}
                  <label className="field">
                    {ko ? "도움말" : "Help Text"}
                    <input className="input" value={field.help_text || ""} onChange={(e) => updateField(idx, { help_text: e.target.value || undefined })} />
                  </label>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
