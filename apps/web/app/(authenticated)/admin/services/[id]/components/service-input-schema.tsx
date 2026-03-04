"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash, ArrowUp, ArrowDown, PencilSimple } from "phosphor-react";
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
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 12 }}>
        <button className="btn btn-secondary btn-sm" onClick={addField}>
          <Plus size={14} /> {ko ? "필드 추가" : "Add Field"}
        </button>
        {isDirty && (
          <button className="btn btn-primary btn-sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? <span className="spinner" /> : ko ? "저장" : "Save"}
          </button>
        )}
      </div>

      {fields.length === 0 ? (
        <p className="muted-text" style={{ fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          {ko ? "정의된 입력 필드가 없습니다. 필드를 추가하세요." : "No input fields defined. Add fields to get started."}
        </p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 140 }}>{ko ? "키" : "Key"}</th>
                <th style={{ width: 90 }}>{ko ? "타입" : "Type"}</th>
                <th>{ko ? "라벨" : "Label"}</th>
                <th style={{ width: 50, textAlign: "center" }}>{ko ? "필수" : "Req"}</th>
                <th style={{ width: 80, textAlign: "center" }}>{ko ? "순서" : "Order"}</th>
                <th style={{ width: 80, textAlign: "center" }}>{ko ? "작업" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field, idx) => (
                <>
                  <tr key={`row-${idx}`} style={{ cursor: "pointer" }} onClick={() => setEditIdx(editIdx === idx ? null : idx)}>
                    <td className="mono-cell" style={{ fontSize: 12 }}>{field.key || "—"}</td>
                    <td><span className="status-chip" style={{ fontSize: 10 }}>{field.type}</span></td>
                    <td style={{ fontSize: 13 }}>{field.label || <span className="muted-text">{ko ? "라벨 없음" : "No label"}</span>}</td>
                    <td style={{ textAlign: "center" }}>{field.required ? <span style={{ color: "var(--danger)", fontWeight: 600 }}>*</span> : "—"}</td>
                    <td style={{ textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
                      <div style={{ display: "flex", gap: 2, justifyContent: "center" }}>
                        <button className="btn btn-secondary" style={{ padding: "2px 4px" }} onClick={() => moveField(idx, -1)} disabled={idx === 0}><ArrowUp size={12} /></button>
                        <button className="btn btn-secondary" style={{ padding: "2px 4px" }} onClick={() => moveField(idx, 1)} disabled={idx === fields.length - 1}><ArrowDown size={12} /></button>
                      </div>
                    </td>
                    <td style={{ textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
                      <div style={{ display: "flex", gap: 2, justifyContent: "center" }}>
                        <button className="btn btn-secondary" style={{ padding: "2px 4px" }} onClick={() => setEditIdx(editIdx === idx ? null : idx)}>
                          <PencilSimple size={12} />
                        </button>
                        <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={() => removeField(idx)}>
                          <Trash size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                  {editIdx === idx && (
                    <tr key={`detail-${idx}`} className="detail-row">
                      <td colSpan={6}>
                        <div className="stack-sm" onClick={(e) => e.stopPropagation()}>
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
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
