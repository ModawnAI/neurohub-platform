"use client";

import { Sidebar } from "@/components/sidebar";
import { useT } from "@/lib/i18n";
import { House, ListChecks, Users, Buildings, Cube, GearSix, ClockCounterClockwise, Key } from "phosphor-react";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const t = useT();

  const navItems = [
    { href: "/admin/dashboard", label: t("nav.dashboard"), icon: <House size={20} /> },
    { href: "/admin/requests", label: t("nav.requests"), icon: <ListChecks size={20} /> },
    { href: "/admin/users", label: t("nav.users"), icon: <Users size={20} /> },
    { href: "/admin/organizations", label: t("nav.organizations"), icon: <Buildings size={20} /> },
    { href: "/admin/services", label: t("nav.services"), icon: <Cube size={20} /> },
    { href: "/admin/api-keys", label: t("nav.apiKeys"), icon: <Key size={20} /> },
    { href: "/admin/audit-logs", label: t("nav.auditLogs"), icon: <ClockCounterClockwise size={20} /> },
    { href: "/admin/settings", label: t("nav.settings"), icon: <GearSix size={20} /> },
  ];

  return (
    <div className="app-layout">
      <Sidebar items={navItems} />
      <main className="main-content">
        <div className="main-content-inner">{children}</div>
      </main>
    </div>
  );
}
