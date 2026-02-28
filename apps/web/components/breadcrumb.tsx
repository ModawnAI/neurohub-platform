"use client";

import Link from "next/link";
import { CaretRight } from "phosphor-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className="breadcrumb">
      <ol style={{ display: "flex", alignItems: "center", gap: 6, listStyle: "none", margin: 0, padding: 0, fontSize: 13 }}>
        {items.map((item, idx) => (
          <li key={idx} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {idx > 0 && <CaretRight size={12} style={{ color: "var(--muted)" }} aria-hidden="true" />}
            {item.href ? (
              <Link href={item.href} style={{ color: "var(--primary)" }}>
                {item.label}
              </Link>
            ) : (
              <span style={{ color: "var(--muted)" }} aria-current="page">{item.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
