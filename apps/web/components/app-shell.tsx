"use client";

import clsx from "clsx";
import type { Route } from "next";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, ChartBar, ListChecks, PlusCircle } from "phosphor-react";
import type { ReactNode } from "react";

const navItems: Array<{ href: Route; label: string; icon: ReactNode }> = [
  { href: "/dashboard", label: "대시보드", icon: <ChartBar size={16} weight="bold" /> },
  { href: "/requests", label: "요청 관리", icon: <ListChecks size={16} weight="bold" /> },
  { href: "/new-request", label: "신규 요청", icon: <PlusCircle size={16} weight="bold" /> },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div>
      <header className="topbar-wrap">
        <div className="container topbar">
          <Link href="/" className="brand">
            <div className="brand-logo">
              <Brain size={20} weight="bold" />
            </div>
            <div>
              <h1 className="brand-title">NeuroHub</h1>
              <p className="brand-eyebrow">의료 AI 워크플로우 플랫폼</p>
            </div>
          </Link>
          <nav className="nav-row" aria-label="주요 메뉴">
            {navItems.map((item) => (
              <Link
                className={clsx("nav-link", pathname?.startsWith(item.href) && "nav-link-active")}
                key={item.href}
                href={item.href}
              >
                {item.icon}
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
