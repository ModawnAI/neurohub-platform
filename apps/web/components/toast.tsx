"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { X } from "phosphor-react";

/* ---------- Types ---------- */

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  exiting?: boolean;
}

interface ToastContextValue {
  toasts: Toast[];
  /** Shorthand: `toast("message", "success")` */
  toast: (message: string, type?: ToastType) => void;
  /** Original API kept for backward-compat: `addToast("success", "message")` */
  addToast: (type: ToastType, message: string) => void;
  removeToast: (id: string) => void;
}

/* ---------- Context ---------- */

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

/* ---------- Color map ---------- */

const TYPE_COLORS: Record<ToastType, { border: string; icon: string; bg: string }> = {
  success: { border: "#22c55e", icon: "#16a34a", bg: "#f0fdf4" },
  error: { border: "#ef4444", icon: "#dc2626", bg: "#fef2f2" },
  info: { border: "#3b82f6", icon: "#2563eb", bg: "#eff6ff" },
  warning: { border: "#f59e0b", icon: "#d97706", bg: "#fffbeb" },
};

/* ---------- Single Toast Item ---------- */

function ToastItem({
  toast,
  onClose,
}: {
  toast: Toast;
  onClose: (id: string) => void;
}) {
  const colors = TYPE_COLORS[toast.type];

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        padding: "12px 16px",
        borderRadius: 10,
        boxShadow: "0 6px 20px rgba(0,0,0,0.12)",
        background: colors.bg,
        borderLeft: `4px solid ${colors.border}`,
        minWidth: 280,
        maxWidth: 400,
        animation: toast.exiting
          ? "nh-toast-out 0.25s ease-in forwards"
          : "nh-toast-in 0.3s ease-out forwards",
        pointerEvents: "auto",
      }}
    >
      <span
        style={{
          flex: 1,
          fontSize: 14,
          fontWeight: 600,
          lineHeight: 1.45,
          color: "#1e293b",
          wordBreak: "break-word",
        }}
      >
        {toast.message}
      </span>
      <button
        type="button"
        onClick={() => onClose(toast.id)}
        aria-label="Close"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#94a3b8",
          flexShrink: 0,
        }}
      >
        <X size={16} weight="bold" />
      </button>
    </div>
  );
}

/* ---------- Provider ---------- */

const AUTO_DISMISS_MS = 3500;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      for (const timer of timersRef.current.values()) clearTimeout(timer);
    };
  }, []);

  const scheduleRemoval = useCallback((id: string) => {
    // Start exit animation, then remove from state
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)),
    );
    const exitTimer = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      timersRef.current.delete(id);
    }, 250); // matches animation duration
    timersRef.current.set(`${id}-exit`, exitTimer);
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string) => {
      const id = crypto.randomUUID();
      setToasts((prev) => [...prev, { id, type, message }]);

      const timer = setTimeout(() => scheduleRemoval(id), AUTO_DISMISS_MS);
      timersRef.current.set(id, timer);
    },
    [scheduleRemoval],
  );

  const toast = useCallback(
    (message: string, type: ToastType = "info") => {
      addToast(type, message);
    },
    [addToast],
  );

  const removeToast = useCallback(
    (id: string) => {
      // Clear auto-dismiss timer if manually closed
      const existing = timersRef.current.get(id);
      if (existing) {
        clearTimeout(existing);
        timersRef.current.delete(id);
      }
      scheduleRemoval(id);
    },
    [scheduleRemoval],
  );

  return (
    <ToastContext.Provider value={{ toasts, toast, addToast, removeToast }}>
      {children}

      {/* Keyframe injection (once) */}
      <style>{`
        @keyframes nh-toast-in {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
        @keyframes nh-toast-out {
          from { transform: translateX(0);    opacity: 1; }
          to   { transform: translateX(100%); opacity: 0; }
        }
      `}</style>

      {/* Container: fixed top-right, above modals */}
      <div
        aria-live="polite"
        style={{
          position: "fixed",
          top: 20,
          right: 20,
          zIndex: 2000,
          display: "flex",
          flexDirection: "column",
          gap: 10,
          pointerEvents: "none",
        }}
      >
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}
