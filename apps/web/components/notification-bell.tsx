"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, CheckCircle } from "phosphor-react";
import { useNotifications } from "@/lib/use-notifications";
import type { NotificationRead } from "@/lib/api";

export function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button className="notification-bell" onClick={() => setOpen(!open)}>
        <Bell size={20} weight={unreadCount > 0 ? "fill" : "regular"} />
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            width: 320,
            maxHeight: 400,
            overflowY: "auto",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-lg)",
            zIndex: 50,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>알림</span>
            {unreadCount > 0 && (
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => markAllRead()}
                style={{ fontSize: 11, padding: "4px 8px" }}
              >
                <CheckCircle size={12} /> 모두 읽음
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div style={{ padding: 24, textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
              알림이 없습니다
            </div>
          ) : (
            notifications.slice(0, 20).map((n: NotificationRead) => (
              <div
                key={n.id}
                onClick={() => { if (!n.is_read) markRead(n.id); }}
                style={{
                  padding: "10px 16px",
                  borderBottom: "1px solid var(--border)",
                  cursor: n.is_read ? "default" : "pointer",
                  background: n.is_read ? "transparent" : "var(--primary-subtle)",
                  fontSize: 13,
                }}
              >
                <p style={{ margin: 0, fontWeight: n.is_read ? 400 : 600 }}>{n.title}</p>
                {n.body && <p style={{ margin: "2px 0 0", color: "var(--muted)", fontSize: 12 }}>{n.body}</p>}
                <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: 11 }}>
                  {new Date(n.created_at).toLocaleString("ko-KR")}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
