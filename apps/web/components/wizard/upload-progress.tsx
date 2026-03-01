"use client";

import { File as FileIcon, CheckCircle, XCircle, ArrowClockwise } from "phosphor-react";
import { useT } from "@/lib/i18n";

export interface UploadFileState {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "completed" | "error";
  fileId?: string;
  error?: string;
}

interface UploadProgressProps {
  files: UploadFileState[];
  onRemove?: (index: number) => void;
  onRetry?: (index: number) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadProgress({ files, onRemove, onRetry }: UploadProgressProps) {
  const t = useT();
  if (files.length === 0) return null;

  return (
    <div className="stack-md">
      {files.map((f, idx) => (
        <div key={`${f.file.name}-${idx}`} className="file-info-card">
          <div className="file-info-card-icon">
            {f.status === "completed" ? (
              <CheckCircle size={18} weight="fill" color="var(--success)" />
            ) : f.status === "error" ? (
              <XCircle size={18} weight="fill" color="var(--danger)" />
            ) : (
              <FileIcon size={18} />
            )}
          </div>
          <div className="file-info-card-body">
            <p className="file-info-card-name">{f.file.name}</p>
            <p className="file-info-card-meta">
              {formatBytes(f.file.size)}
              {f.status === "uploading" && ` — ${f.progress}%`}
              {f.status === "error" && f.error && ` — ${f.error}`}
            </p>
            {f.status === "uploading" && (
              <div className="upload-progress" style={{ marginTop: 6 }}>
                <div className="upload-progress-fill" style={{ width: `${f.progress}%` }} />
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 4, flexShrink: 0 }}>
            {onRetry && f.status === "error" && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => onRetry(idx)}
                title={t("common.retry" as any)}
              >
                <ArrowClockwise size={14} />
              </button>
            )}
            {onRemove && f.status !== "uploading" && (
              <button
                className="btn btn-danger btn-sm"
                onClick={() => onRemove(idx)}
              >
                <XCircle size={14} />
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
