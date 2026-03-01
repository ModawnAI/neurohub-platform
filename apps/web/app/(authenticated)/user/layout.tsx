"use client";

import { Sidebar } from "@/components/sidebar";
import { useT } from "@/lib/i18n";
import { House, ListChecks, PlusCircle, Cube, GearSix, FileText, CreditCard, ChartBar, WifiHigh, ShoppingCart } from "phosphor-react";

export default function UserLayout({ children }: { children: React.ReactNode }) {
  const t = useT();

  const navItems = [
    { href: "/user/dashboard", label: t("nav.dashboard"), icon: <House size={20} /> },
    { href: "/user/services", label: t("nav.serviceCatalog"), icon: <Cube size={20} /> },
    { href: "/user/requests", label: t("nav.myRequests"), icon: <ListChecks size={20} /> },
    { href: "/user/reports", label: t("nav.reports"), icon: <FileText size={20} /> },
    { href: "/user/new-request", label: t("nav.newRequest"), icon: <PlusCircle size={20} /> },
    { href: "/user/group-studies", label: t("groupStudy.title"), icon: <ChartBar size={20} /> },
    { href: "/user/payment", label: t("nav.payment"), icon: <CreditCard size={20} /> },
    { href: "/user/marketplace", label: t("marketplace.browseMarketplace"), icon: <ShoppingCart size={20} /> },
    { href: "/user/dicom-worklist", label: t("nav.dicomWorklist"), icon: <WifiHigh size={20} /> },
    { href: "/user/settings", label: t("nav.settings"), icon: <GearSix size={20} /> },
  ];

  return (
    <div className="app-layout">
      <Sidebar items={navItems} />
      <main id="main-content" className="main-content">
        <div className="main-content-inner">{children}</div>
      </main>
    </div>
  );
}
