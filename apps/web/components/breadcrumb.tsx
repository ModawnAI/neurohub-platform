"use client";

import Link from "next/link";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        gap: 8,
        fontSize: 13,
        color: "var(--muted)",
        marginBottom: 4,
      }}
    >
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <span key={index} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {index > 0 && (
              <span aria-hidden="true" style={{ color: "var(--border-strong)" }}>
                ›
              </span>
            )}
            {isLast || !item.href ? (
              <span
                style={{
                  fontWeight: isLast ? 600 : 400,
                  color: isLast ? "var(--text)" : "var(--muted)",
                }}
                aria-current={isLast ? "page" : undefined}
              >
                {item.label}
              </span>
            ) : (
              <Link
                href={item.href}
                style={{
                  color: "var(--muted)",
                  textDecoration: "none",
                  transition: "color 0.15s",
                }}
                onMouseEnter={(e) => { (e.target as HTMLElement).style.color = "var(--primary)"; }}
                onMouseLeave={(e) => { (e.target as HTMLElement).style.color = "var(--muted)"; }}
              >
                {item.label}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
