"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** Tool identifiers used by cornerstone tools */
const TOOL_NAMES = {
  wwwc: "WindowLevelTool",
  zoom: "ZoomTool",
  pan: "PanTool",
  stackScroll: "StackScrollTool",
  length: "LengthTool",
  angle: "AngleTool",
} as const;

type ToolKey = keyof typeof TOOL_NAMES;

interface ToolButton {
  key: ToolKey;
  label: string;
  icon: string;
}

const TOOLBAR_BUTTONS: ToolButton[] = [
  { key: "wwwc", label: "밝기/대비", icon: "◐" },
  { key: "zoom", label: "확대/축소", icon: "🔍" },
  { key: "pan", label: "이동", icon: "✋" },
  { key: "stackScroll", label: "슬라이스 스크롤", icon: "☰" },
  { key: "length", label: "길이 측정", icon: "📏" },
  { key: "angle", label: "각도 측정", icon: "📐" },
];

interface CornerstoneViewerProps {
  /** Array of DICOM file URLs (presigned URLs from Supabase Storage) */
  imageUrls: string[];
  /** Called when user closes the viewer */
  onClose?: () => void;
}

export function CornerstoneViewer({ imageUrls, onClose }: CornerstoneViewerProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const [activeTool, setActiveTool] = useState<ToolKey>("wwwc");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentSlice, setCurrentSlice] = useState(0);
  const [totalSlices, setTotalSlices] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Store cornerstone references
  const csRef = useRef<{
    renderingEngine: unknown;
    toolGroup: unknown;
    viewportId: string;
    renderingEngineId: string;
  } | null>(null);

  // Initialize cornerstone
  useEffect(() => {
    if (!viewportRef.current || imageUrls.length === 0) return;

    let cancelled = false;

    async function init() {
      try {
        // Dynamic imports to avoid SSR issues
        const csCore = await import("@cornerstonejs/core");
        const csTools = await import("@cornerstonejs/tools");
        const csDicomLoader = await import("@cornerstonejs/dicom-image-loader");

        if (cancelled) return;

        // Initialize cornerstone
        await csCore.init();
        await csDicomLoader.init();

        // Register tools
        const {
          WindowLevelTool,
          ZoomTool,
          PanTool,
          StackScrollTool,
          LengthTool,
          AngleTool,
          ToolGroupManager,
        } = csTools;

        csTools.addTool(WindowLevelTool);
        csTools.addTool(ZoomTool);
        csTools.addTool(PanTool);
        csTools.addTool(StackScrollTool);
        csTools.addTool(LengthTool);
        csTools.addTool(AngleTool);

        // Create rendering engine
        const renderingEngineId = `engine-${Date.now()}`;
        const renderingEngine = new csCore.RenderingEngine(renderingEngineId);
        const viewportId = `viewport-${Date.now()}`;

        const viewportInput = {
          viewportId,
          type: csCore.Enums.ViewportType.STACK,
          element: viewportRef.current!,
        };

        renderingEngine.enableElement(viewportInput);

        // Create tool group
        const toolGroupId = `group-${Date.now()}`;
        const toolGroup = ToolGroupManager.createToolGroup(toolGroupId);

        if (toolGroup) {
          toolGroup.addViewport(viewportId, renderingEngineId);

          // Add all tools
          for (const name of Object.values(TOOL_NAMES)) {
            toolGroup.addTool(name);
          }

          // Set default active tool
          toolGroup.setToolActive(TOOL_NAMES.wwwc, {
            bindings: [{ mouseButton: csTools.Enums.MouseBindings.Primary }],
          });

          // Enable passive tools
          toolGroup.setToolActive(TOOL_NAMES.stackScroll, {
            bindings: [{ mouseButton: csTools.Enums.MouseBindings.Wheel }],
          });
        }

        // Load images
        const imageIds = imageUrls.map(
          (url) => `wadouri:${url}`
        );

        const viewport = renderingEngine.getViewport(viewportId);
        if (viewport && "setStack" in viewport) {
          await (viewport as { setStack: (ids: string[]) => Promise<void> }).setStack(imageIds);
          setTotalSlices(imageIds.length);
          setCurrentSlice(1);
        }

        csRef.current = {
          renderingEngine,
          toolGroup,
          viewportId,
          renderingEngineId,
        };

        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          console.error("Cornerstone initialization failed:", err);
          setError(
            err instanceof Error ? err.message : "DICOM 뷰어 초기화에 실패했습니다."
          );
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      cancelled = true;
      if (csRef.current?.renderingEngine) {
        try {
          (csRef.current.renderingEngine as { destroy: () => void }).destroy();
        } catch {
          // ignore cleanup errors
        }
      }
    };
  }, [imageUrls]);

  // Handle tool switching
  const handleToolChange = useCallback(
    async (toolKey: ToolKey) => {
      setActiveTool(toolKey);

      if (!csRef.current?.toolGroup) return;

      const csTools = await import("@cornerstonejs/tools");
      const tg = csRef.current.toolGroup as {
        setToolActive: (name: string, opts: unknown) => void;
        setToolPassive: (name: string) => void;
      };

      // Deactivate current non-scroll tools
      for (const [key, name] of Object.entries(TOOL_NAMES)) {
        if (key !== "stackScroll") {
          tg.setToolPassive(name);
        }
      }

      // Activate selected
      tg.setToolActive(TOOL_NAMES[toolKey], {
        bindings: [{ mouseButton: csTools.Enums.MouseBindings.Primary }],
      });
    },
    []
  );

  // Fullscreen toggle
  const toggleFullscreen = useCallback(() => {
    const container = viewportRef.current?.parentElement?.parentElement;
    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => setIsFullscreen(true));
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false));
    }
  }, []);

  // Listen for fullscreen changes
  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        background: "#000",
        color: "#fff",
        borderRadius: isFullscreen ? 0 : 8,
        overflow: "hidden",
      }}
    >
      {/* Toolbar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "8px 12px",
          background: "#1a1a1a",
          borderBottom: "1px solid #333",
          flexWrap: "wrap",
        }}
      >
        {TOOLBAR_BUTTONS.map((btn) => (
          <button
            key={btn.key}
            type="button"
            onClick={() => handleToolChange(btn.key)}
            title={btn.label}
            aria-label={btn.label}
            aria-pressed={activeTool === btn.key}
            style={{
              padding: "6px 10px",
              fontSize: 13,
              border: "1px solid",
              borderColor: activeTool === btn.key ? "#60a5fa" : "#555",
              borderRadius: 4,
              background: activeTool === btn.key ? "#1e3a5f" : "#2a2a2a",
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <span>{btn.icon}</span>
            <span>{btn.label}</span>
          </button>
        ))}

        <div style={{ flex: 1 }} />

        {totalSlices > 1 && (
          <span style={{ fontSize: 13, color: "#aaa", marginRight: 8 }}>
            슬라이스: {currentSlice} / {totalSlices}
          </span>
        )}

        <button
          type="button"
          onClick={toggleFullscreen}
          title={isFullscreen ? "전체화면 종료" : "전체화면"}
          aria-label={isFullscreen ? "전체화면 종료" : "전체화면"}
          style={{
            padding: "6px 10px",
            fontSize: 13,
            border: "1px solid #555",
            borderRadius: 4,
            background: "#2a2a2a",
            color: "#fff",
            cursor: "pointer",
          }}
        >
          {isFullscreen ? "⊡" : "⛶"} {isFullscreen ? "축소" : "전체화면"}
        </button>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            style={{
              padding: "6px 10px",
              fontSize: 13,
              border: "1px solid #555",
              borderRadius: 4,
              background: "#4a1a1a",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            ✕ 닫기
          </button>
        )}
      </div>

      {/* Viewport */}
      <div style={{ flex: 1, position: "relative", minHeight: 400 }}>
        {loading && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10,
              background: "rgba(0,0,0,0.7)",
            }}
          >
            <span style={{ fontSize: 16 }}>DICOM 이미지 로딩 중...</span>
          </div>
        )}
        {error && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10,
              background: "rgba(0,0,0,0.8)",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <span style={{ fontSize: 16, color: "#f87171" }}>⚠ {error}</span>
            <span style={{ fontSize: 13, color: "#aaa" }}>
              DICOM 파일을 불러올 수 없습니다.
            </span>
          </div>
        )}
        <div
          ref={viewportRef}
          style={{ width: "100%", height: "100%", background: "#000" }}
        />
      </div>
    </div>
  );
}
