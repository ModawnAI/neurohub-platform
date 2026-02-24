"use client";

import { useCallback, useState } from "react";
import { ArrowLeft, ArrowRight } from "phosphor-react";
import { useT } from "@/lib/i18n";
import { FileDropZone } from "./file-drop-zone";
import { UploadProgress, type UploadFileState } from "./upload-progress";
import { initiateUpload, uploadFileToStorage, completeUpload } from "@/lib/api";
import type { WizardCaseInput } from "./types";

interface StepFileUploadProps {
  requestId: string | null;
  cases: WizardCaseInput[];
  caseIds: string[];
  uploadedFiles: Record<number, string[]>;
  onFilesUploaded: (caseIndex: number, fileIds: string[]) => void;
  onNext: () => void;
  onPrev: () => void;
}

export function StepFileUpload({
  requestId,
  cases,
  caseIds,
  uploadedFiles,
  onFilesUploaded,
  onNext,
  onPrev,
}: StepFileUploadProps) {
  const t = useT();
  const [activeCaseIndex, setActiveCaseIndex] = useState(0);
  const [fileStates, setFileStates] = useState<Record<number, UploadFileState[]>>({});

  const handleFiles = useCallback(
    async (caseIndex: number, files: File[]) => {
      if (!requestId || !caseIds[caseIndex]) return;

      const caseId = caseIds[caseIndex];
      const newStates: UploadFileState[] = files.map((f) => ({
        file: f,
        progress: 0,
        status: "pending" as const,
      }));

      setFileStates((prev) => ({
        ...prev,
        [caseIndex]: [...(prev[caseIndex] ?? []), ...newStates],
      }));

      const completedFileIds: string[] = [];

      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        if (!f) continue;
        const stateIdx = (fileStates[caseIndex]?.length ?? 0) + i;

        try {
          // Update status to uploading
          setFileStates((prev) => {
            const arr = [...(prev[caseIndex] ?? [])];
            if (arr[stateIdx]) arr[stateIdx] = { ...arr[stateIdx], status: "uploading" };
            return { ...prev, [caseIndex]: arr };
          });

          // 1. Get presigned URL
          const presign = await initiateUpload(requestId, caseId, {
            file_name: f.name,
            content_type: f.type || "application/octet-stream",
            slot_name: "primary",
            file_size: f.size,
          });

          // 2. Upload to storage
          await uploadFileToStorage(presign.presigned_url, f, (progress) => {
            setFileStates((prev) => {
              const arr = [...(prev[caseIndex] ?? [])];
              if (arr[stateIdx]) arr[stateIdx] = { ...arr[stateIdx], progress };
              return { ...prev, [caseIndex]: arr };
            });
          });

          // 3. Complete upload (compute SHA-256 checksum)
          const arrayBuf = await f.arrayBuffer();
          const hashBuf = await crypto.subtle.digest("SHA-256", arrayBuf);
          const hashArr = Array.from(new Uint8Array(hashBuf));
          const checksum = hashArr.map((b) => b.toString(16).padStart(2, "0")).join("");
          await completeUpload(requestId, caseId, presign.case_file_id, {
            checksum_sha256: checksum,
          });

          completedFileIds.push(presign.case_file_id);
          setFileStates((prev) => {
            const arr = [...(prev[caseIndex] ?? [])];
            if (arr[stateIdx])
              arr[stateIdx] = { ...arr[stateIdx], status: "completed", progress: 100, fileId: presign.case_file_id };
            return { ...prev, [caseIndex]: arr };
          });
        } catch (err: unknown) {
          const errorMsg = err instanceof Error ? err.message : t("wizard.uploadFailed");
          setFileStates((prev) => {
            const arr = [...(prev[caseIndex] ?? [])];
            if (arr[stateIdx])
              arr[stateIdx] = { ...arr[stateIdx], status: "error", error: errorMsg };
            return { ...prev, [caseIndex]: arr };
          });
        }
      }

      if (completedFileIds.length > 0) {
        onFilesUploaded(caseIndex, [...(uploadedFiles[caseIndex] ?? []), ...completedFileIds]);
      }
    },
    [requestId, caseIds, fileStates, uploadedFiles, onFilesUploaded, t],
  );

  const validCases = cases.filter((c) => c.patient_ref.trim());

  return (
    <div className="stack-lg">
      <p className="muted-text">{t("wizard.uploadFiles")}</p>

      {/* Case tabs */}
      <div className="filter-tabs">
        {validCases.map((c, i) => {
          const fileCount = uploadedFiles[i]?.length ?? 0;
          return (
            <button
              key={i}
              className={`filter-tab ${activeCaseIndex === i ? "active" : ""}`}
              onClick={() => setActiveCaseIndex(i)}
            >
              #{i + 1} {c.patient_ref.slice(0, 12)}
              {fileCount > 0 && ` (${fileCount})`}
            </button>
          );
        })}
      </div>

      {/* Upload area for active case */}
      <FileDropZone
        multiple
        onFiles={(files) => handleFiles(activeCaseIndex, files)}
        disabled={!requestId || !caseIds[activeCaseIndex]}
      />

      {/* File list */}
      <UploadProgress
        files={fileStates[activeCaseIndex] ?? []}
        onRemove={(idx) => {
          setFileStates((prev) => {
            const arr = [...(prev[activeCaseIndex] ?? [])];
            arr.splice(idx, 1);
            return { ...prev, [activeCaseIndex]: arr };
          });
        }}
      />

      {!requestId && (
        <div className="banner banner-warning">
          {t("wizard.warningCreateFirst")}
        </div>
      )}

      <div className="nav-buttons">
        <button className="btn btn-secondary" onClick={onPrev}>
          <ArrowLeft size={16} /> {t("common.prev")}
        </button>
        <button className="btn btn-primary" onClick={onNext}>
          {t("common.next")} <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
