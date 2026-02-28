"use client";

import { useEffect, useRef, useState } from "react";

interface NiftiViewerProps {
  url: string;
  overlayUrl?: string;
  height?: number;
}

export function NiftiViewer({ url, overlayUrl, height = 400 }: NiftiViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nvRef = useRef<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      if (!canvasRef.current) return;

      try {
        const { Niivue } = await import("@niivue/niivue");
        if (cancelled) return;

        const nv = new Niivue({
          backColor: [0.15, 0.15, 0.15, 1],
          show3Dcrosshair: true,
          sliceType: 4, // multiplanar
        });

        nv.attachToCanvas(canvasRef.current);

        const volumes = [{ url, colormap: "gray", opacity: 1.0 }];
        if (overlayUrl) {
          volumes.push({ url: overlayUrl, colormap: "warm", opacity: 0.5 });
        }

        await nv.loadVolumes(volumes);
        nvRef.current = nv;
        setLoading(false);
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "NIfTI 뷰어를 로드할 수 없습니다");
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      if (nvRef.current && typeof (nvRef.current as Record<string, unknown>).dispose === "function") {
        (nvRef.current as { dispose: () => void }).dispose();
      }
    };
  }, [url, overlayUrl]);

  if (error) {
    return (
      <div
        style={{
          padding: 20,
          borderRadius: 8,
          backgroundColor: "var(--color-red-3, #fff1f0)",
          color: "var(--color-red-11, #cf1322)",
          fontSize: 13,
        }}
      >
        {error}
      </div>
    );
  }

  return (
    <div style={{ position: "relative", width: "100%", height }}>
      {loading && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "rgba(0,0,0,0.3)",
            borderRadius: 8,
            zIndex: 1,
          }}
        >
          <span className="spinner" />
        </div>
      )}
      <canvas
        ref={canvasRef}
        style={{
          width: "100%",
          height: "100%",
          borderRadius: 8,
          backgroundColor: "#1a1a1a",
        }}
      />
    </div>
  );
}
