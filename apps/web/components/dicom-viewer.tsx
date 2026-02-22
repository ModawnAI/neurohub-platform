"use client";

import { useState, useRef, useEffect } from "react";
import { Eye, X, ArrowsOut, MagnifyingGlassPlus, MagnifyingGlassMinus } from "phosphor-react";

interface DicomViewerProps {
  fileUrl: string;
  fileName: string;
  onClose?: () => void;
}

/**
 * DICOM file viewer component.
 *
 * For MVP, this provides:
 * - Image preview for standard image formats (JPEG, PNG used as thumbnails)
 * - Metadata display for DICOM files
 * - Download link for full DICOM viewing in external tools
 *
 * Full Cornerstone.js integration planned for Phase 2.
 */
export function DicomViewer({ fileUrl, fileName, onClose }: DicomViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);

  const isDicom = fileName.toLowerCase().endsWith(".dcm") || fileName.toLowerCase().endsWith(".dicom");
  const isImage = /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(fileName);

  return (
    <div className="dicom-viewer-overlay" role="dialog" aria-label="파일 뷰어">
      <div className="dicom-viewer-container" ref={containerRef}>
        <div className="dicom-viewer-header">
          <h3 className="dicom-viewer-title">{fileName}</h3>
          <div className="dicom-viewer-controls">
            <button
              onClick={() => setZoom((z) => Math.min(z + 0.25, 3))}
              className="dicom-viewer-btn"
              aria-label="확대"
              type="button"
            >
              <MagnifyingGlassPlus size={20} />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(z - 0.25, 0.5))}
              className="dicom-viewer-btn"
              aria-label="축소"
              type="button"
            >
              <MagnifyingGlassMinus size={20} />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="dicom-viewer-btn"
              aria-label="원본 크기"
              type="button"
            >
              <ArrowsOut size={20} />
            </button>
            {onClose && (
              <button onClick={onClose} className="dicom-viewer-btn dicom-viewer-close" aria-label="닫기" type="button">
                <X size={20} />
              </button>
            )}
          </div>
        </div>

        <div className="dicom-viewer-body">
          {isDicom ? (
            <div className="dicom-placeholder">
              <Eye size={64} weight="light" />
              <h4>DICOM 파일</h4>
              <p>DICOM 파일은 전문 뷰어에서 확인할 수 있습니다.</p>
              <a href={fileUrl} download={fileName} className="btn btn-primary">
                파일 다운로드
              </a>
              <div className="dicom-meta">
                <p>파일명: {fileName}</p>
                <p>형식: DICOM</p>
              </div>
            </div>
          ) : isImage ? (
            <div className="dicom-image-container" style={{ transform: `scale(${zoom})` }}>
              <img
                src={fileUrl}
                alt={fileName}
                onLoad={() => setLoading(false)}
                onError={() => setLoading(false)}
                className="dicom-image"
              />
              {loading && <div className="dicom-loading">로딩 중...</div>}
            </div>
          ) : (
            <div className="dicom-placeholder">
              <Eye size={64} weight="light" />
              <h4>미리보기 불가</h4>
              <p>이 파일 형식은 미리보기를 지원하지 않습니다.</p>
              <a href={fileUrl} download={fileName} className="btn btn-primary">
                파일 다운로드
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Button that opens the DICOM viewer for a file.
 */
export function DicomViewerButton({
  fileUrl,
  fileName,
}: {
  fileUrl: string;
  fileName: string;
}) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="btn btn-sm btn-secondary"
        aria-label={`${fileName} 미리보기`}
        type="button"
      >
        <Eye size={16} /> 보기
      </button>
      {isOpen && (
        <DicomViewer fileUrl={fileUrl} fileName={fileName} onClose={() => setIsOpen(false)} />
      )}
    </>
  );
}
