"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash, PencilSimple } from "phosphor-react";
import { updateServiceDefinition, type ServiceRead } from "@/lib/api";
import type { UploadSlot } from "@/components/dynamic-form/types";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

const ACCEPTED_TYPES = ["DICOM", "NIfTI", "EEG", "EDF", "SET", "CSV", "PDF", "JSON", "ZIP", "PNG", "JPEG"];

const EMPTY_SLOT: UploadSlot = {
  key: "",
  label: "",
  required: true,
  accepted_types: ["DICOM"],
  min_files: 1,
  max_files: 500,
};

interface Props {
  service: ServiceRead;
}

export function ServiceUploadSlots({ service }: Props) {
  const { locale } = useTranslation();
  const ko = locale === "ko";
  const queryClient = useQueryClient();
  const { addToast } = useToast();

  const existingSlots: UploadSlot[] = service.upload_slots ?? [];
  const [slots, setSlots] = useState<UploadSlot[]>(existingSlots);
  const [editIdx, setEditIdx] = useState<number | null>(null);

  const saveMut = useMutation({
    mutationFn: () =>
      updateServiceDefinition(service.id, {
        upload_slots: slots as unknown as Array<Record<string, unknown>>,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
      queryClient.invalidateQueries({ queryKey: ["service", service.id] });
      addToast("success", ko ? "업로드 슬롯 저장 완료" : "Upload slots saved");
    },
    onError: () => addToast("error", ko ? "저장 실패" : "Save failed"),
  });

  const addSlot = () => {
    setSlots([...slots, { ...EMPTY_SLOT, key: `slot_${slots.length + 1}` }]);
    setEditIdx(slots.length);
  };

  const removeSlot = (idx: number) => {
    setSlots(slots.filter((_, i) => i !== idx));
    setEditIdx(null);
  };

  const updateSlot = (idx: number, patch: Partial<UploadSlot>) => {
    setSlots(slots.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };

  const toggleType = (idx: number, type: string) => {
    const current = slots[idx]?.accepted_types || [];
    const next = current.includes(type) ? current.filter((t) => t !== type) : [...current, type];
    updateSlot(idx, { accepted_types: next });
  };

  const isDirty = JSON.stringify(slots) !== JSON.stringify(existingSlots);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginBottom: 12 }}>
        <button className="btn btn-secondary btn-sm" onClick={addSlot}>
          <Plus size={14} /> {ko ? "슬롯 추가" : "Add Slot"}
        </button>
        {isDirty && (
          <button className="btn btn-primary btn-sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
            {saveMut.isPending ? <span className="spinner" /> : ko ? "저장" : "Save"}
          </button>
        )}
      </div>

      {slots.length === 0 ? (
        <p className="muted-text" style={{ fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          {ko ? "정의된 업로드 슬롯이 없습니다." : "No upload slots defined."}
        </p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 130 }}>{ko ? "키" : "Key"}</th>
                <th>{ko ? "라벨" : "Label"}</th>
                <th>{ko ? "허용 타입" : "Types"}</th>
                <th style={{ width: 90, textAlign: "center" }}>{ko ? "파일 수" : "Files"}</th>
                <th style={{ width: 50, textAlign: "center" }}>{ko ? "필수" : "Req"}</th>
                <th style={{ width: 80, textAlign: "center" }}>{ko ? "작업" : "Actions"}</th>
              </tr>
            </thead>
            <tbody>
              {slots.map((slot, idx) => (
                <>
                  <tr key={`row-${idx}`} style={{ cursor: "pointer" }} onClick={() => setEditIdx(editIdx === idx ? null : idx)}>
                    <td className="mono-cell" style={{ fontSize: 12 }}>{slot.key || "—"}</td>
                    <td style={{ fontSize: 13 }}>{slot.label || <span className="muted-text">{ko ? "라벨 없음" : "No label"}</span>}</td>
                    <td>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {(slot.accepted_types || []).map((t) => (
                          <span key={t} className="status-chip" style={{ fontSize: 10, padding: "1px 5px" }}>{t}</span>
                        ))}
                      </div>
                    </td>
                    <td style={{ textAlign: "center", fontSize: 12 }}>{slot.min_files ?? 1}–{slot.max_files ?? 500}</td>
                    <td style={{ textAlign: "center" }}>{slot.required ? <span style={{ color: "var(--danger)", fontWeight: 600 }}>*</span> : "—"}</td>
                    <td style={{ textAlign: "center" }} onClick={(e) => e.stopPropagation()}>
                      <div style={{ display: "flex", gap: 2, justifyContent: "center" }}>
                        <button className="btn btn-secondary" style={{ padding: "2px 4px" }} onClick={() => setEditIdx(editIdx === idx ? null : idx)}>
                          <PencilSimple size={12} />
                        </button>
                        <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={() => removeSlot(idx)}>
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
                              <input className="input" value={slot.key} onChange={(e) => updateSlot(idx, { key: e.target.value.replace(/[^a-z0-9_]/g, "") })} placeholder="mri_t1" />
                            </label>
                            <label className="field">
                              {ko ? "라벨" : "Label"}
                              <input className="input" value={slot.label} onChange={(e) => updateSlot(idx, { label: e.target.value })} placeholder={ko ? "MRI T1 영상" : "MRI T1 Image"} />
                            </label>
                          </div>
                          <div className="form-grid">
                            <label className="field">
                              {ko ? "최소 파일 수" : "Min Files"}
                              <input className="input" type="number" min={0} value={slot.min_files ?? 1} onChange={(e) => updateSlot(idx, { min_files: Number(e.target.value) })} />
                            </label>
                            <label className="field">
                              {ko ? "최대 파일 수" : "Max Files"}
                              <input className="input" type="number" min={1} value={slot.max_files ?? 500} onChange={(e) => updateSlot(idx, { max_files: Number(e.target.value) })} />
                            </label>
                          </div>
                          <div>
                            <p className="detail-label" style={{ marginBottom: 6 }}>{ko ? "허용 파일 타입" : "Accepted Types"}</p>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                              {ACCEPTED_TYPES.map((type) => (
                                <button
                                  key={type}
                                  className={`btn btn-sm ${(slot.accepted_types || []).includes(type) ? "btn-primary" : "btn-secondary"}`}
                                  style={{ fontSize: 11, padding: "3px 8px" }}
                                  onClick={() => toggleType(idx, type)}
                                >
                                  {type}
                                </button>
                              ))}
                            </div>
                          </div>
                          <div className="form-grid">
                            <label className="field" style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <input type="checkbox" checked={slot.required ?? true} onChange={(e) => updateSlot(idx, { required: e.target.checked })} />
                              {ko ? "필수" : "Required"}
                            </label>
                          </div>
                          <label className="field">
                            {ko ? "설명" : "Description"}
                            <input className="input" value={slot.description || ""} onChange={(e) => updateSlot(idx, { description: e.target.value || undefined })} />
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
