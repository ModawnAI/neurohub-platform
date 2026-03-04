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
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 12 }}>
        <button className="btn btn-secondary btn-sm" onClick={addField}>
          <Plus size={14} /> {ko ? "출력 추가" : "Add Output"}
        </button>
        {isDirty && (
          <button className="btn btn-primary btn-sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? <span className="spinner" /> : ko ? "저장" : "Save"}
          </button>
        )}
      </div>

      {fields.length === 0 ? (
        <p className="muted-text" style={{ fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          {ko ? "정의된 출력 필드가 없습니다." : "No output fields defined."}
        </p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>{ko ? "키" : "Key"}</th>
                <th style={{ width: 100 }}>{ko ? "타입" : "Type"}</th>
                <th>{ko ? "라벨" : "Label"}</th>
                <th style={{ width: 60, textAlign: "center" }}>{ko ? "작업" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field, idx) => (
                <tr key={idx}>
                  <td>
                    <input className="input" value={field.key} onChange={(e) => updateField(idx, { key: e.target.value.replace(/[^a-z0-9_]/g, "") })} placeholder="brain_map" style={{ fontSize: 12, fontFamily: "var(--font-mono)" }} />
                  </td>
                  <td>
                    <select className="input" value={field.type} onChange={(e) => updateField(idx, { type: e.target.value })} style={{ fontSize: 12 }}>
                      {OUTPUT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td>
                    <input className="input" value={field.label} onChange={(e) => updateField(idx, { label: e.target.value })} placeholder={ko ? "뇌 영상 지도" : "Brain Map"} style={{ fontSize: 12 }} />
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={() => removeField(idx)}>
                      <Trash size={12} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
