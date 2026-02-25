"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash } from "phosphor-react";
import { updateServiceDefinition, type ServiceRead } from "@/lib/api";
import type { UploadSlot } from "@/components/dynamic-form/types";
import { useTranslation } from "@/lib/i18n";
import { useToast } from "@/components/toast";

const ACCEPTED_TYPES = ["DICOM", "NIfTI", "EEG", "EDF", "SET", "CSV", "PDF", "ZIP", "PNG", "JPEG"];

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
    <div className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <h3 className="panel-title">{ko ? "업로드 슬롯" : "Upload Slots"}</h3>
          <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
            {ko ? "파일 업로드 슬롯을 정의합니다 (DICOM, NIfTI 등)" : "Define file upload slots (DICOM, NIfTI, etc.)"}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-secondary btn-sm" onClick={addSlot}>
            <Plus size={14} /> {ko ? "슬롯 추가" : "Add Slot"}
          </button>
          {isDirty && (
            <button className="btn btn-primary btn-sm" onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
              {saveMut.isPending ? <span className="spinner" /> : ko ? "저장" : "Save"}
            </button>
          )}
        </div>
      </div>

      {slots.length === 0 ? (
        <p className="muted-text" style={{ fontSize: 13, textAlign: "center", padding: "24px 0" }}>
          {ko ? "정의된 업로드 슬롯이 없습니다." : "No upload slots defined."}
        </p>
      ) : (
        <div className="stack-sm">
          {slots.map((slot, idx) => (
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
                  <span className="mono-cell" style={{ fontSize: 11, color: "var(--muted)" }}>{slot.key || "—"}</span>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{slot.label || (ko ? "라벨 없음" : "No label")}</span>
                  <span className="muted-text" style={{ fontSize: 11 }}>{(slot.accepted_types || []).join(", ")}</span>
                  {slot.required && <span style={{ color: "var(--danger)", fontSize: 11, fontWeight: 600 }}>*</span>}
                </div>
                <button className="btn btn-danger" style={{ padding: "2px 4px" }} onClick={(e) => { e.stopPropagation(); removeSlot(idx); }}>
                  <Trash size={12} />
                </button>
              </div>

              {editIdx === idx && (
                <div className="stack-sm" style={{ marginTop: 12 }} onClick={(e) => e.stopPropagation()}>
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
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
