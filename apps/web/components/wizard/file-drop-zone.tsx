"use client";

import { useCallback, useRef, useState } from "react";
import { UploadSimple } from "phosphor-react";

interface FileDropZoneProps {
  accept?: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

export function FileDropZone({ accept, multiple, onFiles, disabled }: FileDropZoneProps) {
  const [active, setActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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
      if (files.length) onFiles(multiple ? files : files.slice(0, 1));
    },
    [disabled, multiple, onFiles],
  );

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
    e.target.value = "";
  };

  return (
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
      <p style={{ margin: 0 }}>파일을 여기에 끌어다 놓거나 클릭하여 선택하세요</p>
      <p style={{ margin: "4px 0 0", fontSize: 12 }}>DICOM, NIfTI, ZIP 등</p>
    </div>
  );
}
