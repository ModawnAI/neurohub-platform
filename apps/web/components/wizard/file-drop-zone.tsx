"use client";

import { useCallback, useRef, useState } from "react";
import { UploadSimple, WarningCircle } from "phosphor-react";
import { useT } from "@/lib/i18n";

const ALLOWED_EXTENSIONS = [".zip", ".dcm", ".nii", ".nii.gz", ".dicom", ".ima"];
const MAX_FILE_SIZE_MB = 500;

function getFileExtension(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".nii.gz")) return ".nii.gz";
  const idx = lower.lastIndexOf(".");
  return idx >= 0 ? lower.slice(idx) : "";
}

function validateFiles(
  files: File[],
  maxSizeMb: number,
): { valid: File[]; errors: string[] } {
  const valid: File[] = [];
  const errors: string[] = [];
  const maxBytes = maxSizeMb * 1024 * 1024;

  for (const file of files) {
    const ext = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      errors.push(`invalidType`);
      continue;
    }
    if (file.size > maxBytes) {
      errors.push(`fileTooLarge`);
      continue;
    }
    valid.push(file);
  }

  return { valid, errors: [...new Set(errors)] };
}

interface FileDropZoneProps {
  accept?: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  disabled?: boolean;
  maxSizeMb?: number;
}

export function FileDropZone({ accept, multiple, onFiles, disabled, maxSizeMb = MAX_FILE_SIZE_MB }: FileDropZoneProps) {
  const t = useT();
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const processFiles = useCallback(
    (files: File[]) => {
      const { valid, errors } = validateFiles(files, maxSizeMb);
      if (errors.length > 0) {
        const msgs = errors.map((e) => {
          if (e === "fileTooLarge") {
            return t("fileValidation.fileTooLarge" as any).replace("{max}", String(maxSizeMb));
          }
          return t(`fileValidation.${e}` as any);
        });
        setError(msgs.join(" "));
      } else {
        setError(null);
      }
      if (valid.length > 0) {
        onFiles(multiple ? valid : valid.slice(0, 1));
      }
    },
    [maxSizeMb, multiple, onFiles, t],
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setActive(true);
  }, [disabled]);

  const handleDragLeave = useCallback(() => {
    setActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setActive(false);
      if (disabled) return;
      const files = Array.from(e.dataTransfer.files);
      if (files.length) processFiles(files);
    },
    [disabled, processFiles],
  );

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) processFiles(files);
    e.target.value = "";
  };

  return (
    <div>
      <div
        className={`drop-zone ${active ? "drop-zone-active" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        style={disabled ? { opacity: 0.5, cursor: "not-allowed" } : undefined}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          style={{ display: "none" }}
        />
        <div className="drop-zone-icon">
          <UploadSimple size={32} />
        </div>
        <p style={{ margin: 0 }}>{t("fileValidation.dropPrompt" as any)}</p>
        <p style={{ margin: "4px 0 0", fontSize: 12 }}>{t("fileValidation.formatHint" as any)}</p>
      </div>
      {error && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, color: "var(--danger, #ef4444)", fontSize: 13 }}>
          <WarningCircle size={16} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
