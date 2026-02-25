"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash } from "phosphor-react";
import { updateServiceDefinition, type ServiceRead } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

const OUTPUT_TYPES = ["image", "pdf", "csv", "json", "html", "table", "chart"] as const;

interface OutputField {
  key: string;
  type: string;
  label: string;
  label_en?: string;
  description?: string;
}

interface Props {
  service: ServiceRead;
}

export function ServiceOutputSchema({ service }: Props) {
  const { locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const existingFields: OutputField[] = service.output_schema?.fields ?? [];
  const [fields, setFields] = useState<OutputField[]>(existingFields);

  const saveMut = useMutation({
    mutationFn: () =>
      updateServiceDefinition(service.id, {
        output_schema: { fields: fields as unknown as Array<Record<string, unknown>> },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      queryClient.invalidateQueries({ queryKey: ["service", service.id] });
      addToast("success", ko ? "출력 스키마 저장 완료" : "Output schema saved");
    },
    onError: () => addToast("error", ko ? "저장 실패" : "Save failed"),
  });

  const addField = () => {
    setFields([...fields, { key: `output_${fields.length + 1}`, type: "json", label: "" }]);
  };

  const removeField = (idx: number) => {
    setFields(fields.filter((_, i) => i !== idx));
  };

  const updateField = (idx: number, patch: Partial<OutputField>) => {
    setFields(fields.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  };

  const isDirty = JSON.stringify(fields) !== JSON.stringify(existingFields);

  return (
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 className="panel-title">{ko ? "출력 스키마" : "Output Schema"}</h3>
          <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
            {ko ? "AI 분석 결과로 생성될 출력 형식을 정의합니다" : "Define expected output fields from AI analysis"}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={addField}>
            <Plus size={14} /> {ko ? "출력 추가" : "Add Output"}
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
          {ko ? "정의된 출력 필드가 없습니다." : "No output fields defined."}
        </p>
      ) : (
        <div className="stack-sm">
          {fields.map((field, idx) => (
            <div key={idx} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: 12 }}>
              <div className="form-grid" style={{ gridTemplateColumns: "1fr 1fr 1fr auto" }}>
                <label className="field">
                  {ko ? "키" : "Key"}
                  <input className="input" value={field.key} onChange={(e) => updateField(idx, { key: e.target.value.replace(/[^a-z0-9_]/g, "") })} placeholder="brain_map" />
                </label>
                <label className="field">
                  {ko ? "타입" : "Type"}
                  <select className="input" value={field.type} onChange={(e) => updateField(idx, { type: e.target.value })}>
                    {OUTPUT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </label>
                <label className="field">
                  {ko ? "라벨" : "Label"}
                  <input className="input" value={field.label} onChange={(e) => updateField(idx, { label: e.target.value })} placeholder={ko ? "뇌 영상 지도" : "Brain Map"} />
                </label>
                <button className="btn btn-danger btn-sm" style={{ marginTop: 20 }} onClick={() => removeField(idx)}>
                  <Trash size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
