"use client";

import { useState, useRef, useEffect } from "react";
import { Bell, CheckCircle } from "phosphor-react";
import { useNotifications } from "@/lib/use-notifications";
import { useT, useLocale } from "@/lib/i18n";
import type { NotificationRead } from "@/lib/api";

export function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const t = useT();
  const { locale } = useLocale();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const unreadLabel = unreadCount > 0
    ? t("notification.unreadCount").replace("{count}", String(unreadCount))
    : t("notification.title");

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className="sidebar-action-btn"
        onClick={() => setOpen(!open)}
        aria-label={unreadLabel}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Bell size={20} weight={unreadCount > 0 ? "fill" : "regular"} />
        {unreadCount > 0 && (
          <span className="notification-badge" aria-hidden="true">{unreadCount > 9 ? "9+" : unreadCount}</span>
        )}
      </button>

      {open && (
        <div
          role="menu"
          aria-label={t("notification.list")}
          style={{
            position: "absolute",
            bottom: "100%",
            left: 0,
            width: 320,
            maxHeight: 400,
            overflowY: "auto",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-lg)",
            zIndex: 50,
            marginBottom: 4,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>{t("notification.title")}</span>
            {unreadCount > 0 && (
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => markAllRead()}
                style={{ fontSize: 11, padding: "4px 8px" }}
                aria-label={t("notification.markAllReadLabel")}
              >
                <CheckCircle size={12} /> {t("notification.markAllRead")}
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div role="menuitem" style={{ padding: 24, textAlign: "center", color: "var(--muted)", fontSize: 13 }}>
              {t("notification.empty")}
            </div>
          ) : (
            notifications.slice(0, 20).map((n: NotificationRead) => (
              <div
                key={n.id}
                role="menuitem"
                tabIndex={0}
                onClick={() => { if (!n.is_read) markRead(n.id); }}
                onKeyDown={(e) => { if (e.key === "Enter" && !n.is_read) markRead(n.id); }}
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
                  {new Date(n.created_at).toLocaleString(locale === "ko" ? "ko-KR" : "en-US")}
                </p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
