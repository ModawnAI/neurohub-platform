"use client";

import { FileDropZone } from "@/components/wizard/file-drop-zone";
import { type UploadFileState, UploadProgress } from "@/components/wizard/upload-progress";
import { useCallback, useState } from "react";
import type { UploadSlot } from "./types";

interface DynamicUploadSlotsProps {
  slots: UploadSlot[];
  /** Per-slot uploaded file IDs */
  uploadedFiles: Record<string, string[]>;
  /** Called after files are staged (parent handles actual upload) */
  onFilesSelected: (slotKey: string, files: File[]) => void;
  /** Per-slot file upload states from parent */
  fileStates?: Record<string, UploadFileState[]>;
  disabled?: boolean;
}

/**
 * Renders upload zones per service-defined upload slot.
 * Shows required vs optional, accepted types, and help text.
 */
export function DynamicUploadSlots({
  slots,
  uploadedFiles,
  onFilesSelected,
  fileStates,
  disabled,
}: DynamicUploadSlotsProps) {
  const [activeSlot, setActiveSlot] = useState(slots[0]?.key ?? "");

  if (!slots.length) {
    return <p className="muted-text">이 서비스는 파일 업로드가 필요하지 않습니다.</p>;
  }

  const currentSlot = slots.find((s) => s.key === activeSlot) ?? slots[0];
  if (!currentSlot) return null;

  const acceptStr =
    currentSlot.accepted_extensions?.join(", ") ?? currentSlot.accepted_types?.join(", ") ?? "";

  return (
    <div className="stack-md">
      {/* Slot tabs */}
      {slots.length > 1 && (
        <div className="filter-tabs">
          {slots.map((slot) => {
            const count = uploadedFiles[slot.key]?.length ?? 0;
            return (
              <button
                key={slot.key}
                type="button"
                className={`filter-tab ${activeSlot === slot.key ? "active" : ""}`}
                onClick={() => setActiveSlot(slot.key)}
              >
                {slot.label}
                {slot.required && <span style={{ color: "var(--danger)" }}> *</span>}
                {count > 0 && ` (${count})`}
              </button>
            );
          })}
        </div>
      )}

      {/* Slot info */}
      <div style={{ fontSize: 13 }}>
        <strong>{currentSlot.label}</strong>
        {currentSlot.required && (
          <span style={{ color: "var(--danger)", marginLeft: 4 }}>(필수)</span>
        )}
        {!currentSlot.required && (
          <span style={{ color: "var(--muted)", marginLeft: 4 }}>(선택)</span>
        )}
        {currentSlot.description && (
          <p style={{ color: "var(--muted)", margin: "4px 0" }}>{currentSlot.description}</p>
        )}
        {acceptStr && <p style={{ color: "var(--muted)", fontSize: 12 }}>허용 형식: {acceptStr}</p>}
        {currentSlot.help_text && (
          <p style={{ color: "var(--muted)", fontSize: 12 }}>{currentSlot.help_text}</p>
        )}
        <p style={{ color: "var(--muted)", fontSize: 12 }}>
          파일 수: {currentSlot.min_files ?? 1} ~ {currentSlot.max_files ?? 500}
        </p>
      </div>

      {/* Drop zone */}
      <FileDropZone
        multiple
        accept={currentSlot.accepted_extensions?.join(",") || undefined}
        onFiles={(files) => onFilesSelected(currentSlot.key, files)}
        disabled={disabled}
      />

      {/* Progress */}
      {fileStates?.[currentSlot.key] && (
        <UploadProgress files={fileStates[currentSlot.key] ?? []} />
      )}
    </div>
  );
}
