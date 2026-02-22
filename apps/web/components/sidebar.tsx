"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, SignOut } from "phosphor-react";
import { useAuth } from "@/lib/auth";
import { useT } from "@/lib/i18n";
import clsx from "clsx";
import { NotificationBell } from "@/components/notification-bell";
import { LanguageSwitcher } from "@/components/language-switcher";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

interface SidebarProps {
  items: NavItem[];
}

export function Sidebar({ items }: SidebarProps) {
  const pathname = usePathname();
  const { user, signOut } = useAuth();
  const t = useT();

  const initial = user?.displayName?.charAt(0) || user?.email?.charAt(0) || "U";
  const userTypeKey = user?.userType as "SERVICE_USER" | "EXPERT" | "ADMIN" | null;
  const roleLabel = userTypeKey ? t(`userType.${userTypeKey}`) : "";

  return (
    <aside className="sidebar" role="navigation" aria-label={t("sidebar.mainNav")}>
      <Link href="/" className="sidebar-brand" aria-label={t("sidebar.home")}>
        <div className="sidebar-brand-icon">
          <Brain size={20} weight="bold" />
        </div>
        <span className="sidebar-brand-text">NeuroHub</span>
      </Link>

      <nav className="sidebar-nav" aria-label={t("sidebar.pageNav")}>
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx("sidebar-link", pathname === item.href && "sidebar-link-active")}
            aria-current={pathname === item.href ? "page" : undefined}
          >
            <span className="sidebar-link-icon" aria-hidden="true">{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div className="sidebar-user">
        <div className="sidebar-user-profile">
          <div className="sidebar-user-avatar" aria-hidden="true">{initial.toUpperCase()}</div>
          <div className="sidebar-user-info">
            <p className="sidebar-user-name">{user?.displayName || user?.email || t("sidebar.user")}</p>
            {roleLabel && <p className="sidebar-user-role">{roleLabel}</p>}
          </div>
        </div>
        <div className="sidebar-user-actions">
          <LanguageSwitcher />
          <NotificationBell />
          <button
            className="sidebar-action-btn"
            onClick={() => signOut()}
            title={t("sidebar.logout")}
            aria-label={t("sidebar.logout")}
          >
            <SignOut size={18} />
          </button>
        </div>
      </div>
    </aside>
  );
}
