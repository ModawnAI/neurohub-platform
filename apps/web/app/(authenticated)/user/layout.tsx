"use client";

import { Sidebar } from "@/components/sidebar";
import { House, ListChecks, PlusCircle, GearSix } from "phosphor-react";

const NAV_ITEMS = [
  { href: "/user/dashboard", label: "대시보드", icon: <House size={20} /> },
  { href: "/user/requests", label: "내 요청", icon: <ListChecks size={20} /> },
  { href: "/user/new-request", label: "새 요청", icon: <PlusCircle size={20} /> },
  { href: "/user/settings", label: "설정", icon: <GearSix size={20} /> },
];

export default function UserLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <Sidebar items={NAV_ITEMS} userTypeLabel="서비스 사용자" />
      <main className="main-content">
        <div className="main-content-inner">{children}</div>
      </main>
    </div>
  );
}
