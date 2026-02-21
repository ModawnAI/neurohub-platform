"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, SignOut } from "phosphor-react";
import { useAuth } from "@/lib/auth";
import clsx from "clsx";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

interface SidebarProps {
  items: NavItem[];
  userTypeLabel: string;
}

const USER_TYPE_LABELS: Record<string, string> = {
  SERVICE_USER: "서비스 사용자",
  EXPERT: "전문가 리뷰어",
  ADMIN: "관리자",
};

export function Sidebar({ items, userTypeLabel }: SidebarProps) {
  const pathname = usePathname();
  const { user, signOut } = useAuth();

  const initial = user?.displayName?.charAt(0) || user?.email?.charAt(0) || "U";

  return (
    <aside className="sidebar">
      <Link href="/" className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Brain size={20} weight="bold" />
        </div>
        <span className="sidebar-brand-text">NeuroHub</span>
      </Link>

      <nav className="sidebar-nav">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx("sidebar-link", pathname === item.href && "sidebar-link-active")}
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-user-avatar">{initial.toUpperCase()}</div>
        <div className="sidebar-user-info">
          <p className="sidebar-user-name">{user?.displayName || user?.email || "사용자"}</p>
          <p className="sidebar-user-role">{userTypeLabel}</p>
        </div>
        <button
          className="sidebar-link"
          onClick={() => signOut()}
          style={{ width: "auto", padding: "6px" }}
          title="로그아웃"
        >
          <SignOut size={18} />
        </button>
      </div>
    </aside>
  );
}
