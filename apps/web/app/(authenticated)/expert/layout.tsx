"use client";

import { Sidebar } from "@/components/sidebar";
import { useAuth } from "@/lib/auth";
import { useT } from "@/lib/i18n";
import { House, ListChecks, GearSix } from "phosphor-react";

export default function ExpertLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const t = useT();
  const isPending = user?.expertStatus === "PENDING_APPROVAL";

  const navItems = [
    { href: "/expert/dashboard", label: t("nav.dashboard"), icon: <House size={20} /> },
    { href: "/expert/reviews", label: t("nav.reviewQueue"), icon: <ListChecks size={20} /> },
    { href: "/expert/settings", label: t("nav.settings"), icon: <GearSix size={20} /> },
  ];

  return (
    <div className="app-layout">
      <Sidebar items={navItems} />
      <main className="main-content">
        <div className="main-content-inner">
          {isPending && (
            <div className="banner banner-warning" style={{ marginBottom: 20 }}>
              {t("expert.pendingApproval")}
            </div>
          )}
          {children}
        </div>
      </main>
    </div>
  );
}
