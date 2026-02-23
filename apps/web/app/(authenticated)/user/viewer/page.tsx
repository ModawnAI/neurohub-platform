"use client";

import dynamic from "next/dynamic";
import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";

/** Lazy-load CornerstoneViewer — no SSR (requires browser APIs) */
const CornerstoneViewer = dynamic(
  () => import("@/components/cornerstone-viewer").then((m) => m.CornerstoneViewer),
  { ssr: false, loading: () => <ViewerSkeleton /> }
);

function ViewerSkeleton() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        minHeight: 500,
        background: "#000",
        color: "#aaa",
        fontSize: 16,
      }}
    >
      DICOM 뷰어 로딩 중...
    </div>
  );
}

function ViewerContent() {
  const params = useSearchParams();

  // Accept comma-separated urls param or individual url params
  const imageUrls = useMemo(() => {
    const urls = params.get("urls");
    if (urls) return urls.split(",").filter(Boolean);
    const single = params.get("url");
    if (single) return [single];
    return [];
  }, [params]);

  if (imageUrls.length === 0) {
    return (
      <div style={{ padding: 32, textAlign: "center" }}>
        <h2 style={{ fontSize: 20, marginBottom: 8 }}>DICOM 뷰어</h2>
        <p style={{ color: "#666" }}>
          표시할 DICOM 파일이 없습니다. 요청 상세 페이지에서 파일을 선택해주세요.
        </p>
      </div>
    );
  }

  return (
    <div style={{ height: "calc(100vh - 80px)" }}>
      <CornerstoneViewer
        imageUrls={imageUrls}
        onClose={() => window.history.back()}
      />
    </div>
  );
}

export default function ViewerPage() {
  return (
    <Suspense fallback={<ViewerSkeleton />}>
      <ViewerContent />
    </Suspense>
  );
}
