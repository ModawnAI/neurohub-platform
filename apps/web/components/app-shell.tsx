"use client";

import clsx from "clsx";
import type { Route } from "next";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems: Array<{ href: Route; label: string }> = [
  { href: "/dashboard", label: "대시보드" },
  { href: "/requests", label: "요청 관리" },
  { href: "/new-request", label: "신규 요청" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <header className="topbar-wrap">
        <div className="container topbar">
          <div>
            <p className="brand-eyebrow">의료 AI 워크플로우 오케스트레이션</p>
            <h1 className="brand-title">NeuroHub</h1>
          </div>
          <nav className="nav-row" aria-label="주요 메뉴">
            {navItems.map((item) => (
              <Link
                className={clsx("nav-link", pathname?.startsWith(item.href) && "nav-link-active")}
                key={item.href}
                href={item.href}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="container">{children}</main>
    </div>
  );
}
