"use client";

import { Sidebar } from "@/components/sidebar";
import { House, ListChecks, Users, Buildings, Cube, GearSix, ClockCounterClockwise, Key } from "phosphor-react";

const NAV_ITEMS = [
  { href: "/admin/dashboard", label: "대시보드", icon: <House size={20} /> },
  { href: "/admin/requests", label: "요청 관리", icon: <ListChecks size={20} /> },
  { href: "/admin/users", label: "사용자 관리", icon: <Users size={20} /> },
  { href: "/admin/organizations", label: "기관 관리", icon: <Buildings size={20} /> },
  { href: "/admin/services", label: "서비스 관리", icon: <Cube size={20} /> },
  { href: "/admin/api-keys", label: "API 키", icon: <Key size={20} /> },
  { href: "/admin/audit-logs", label: "감사 로그", icon: <ClockCounterClockwise size={20} /> },
  { href: "/admin/settings", label: "설정", icon: <GearSix size={20} /> },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-layout">
      <Sidebar items={NAV_ITEMS} userTypeLabel="관리자" />
      <main className="main-content">
        <div className="main-content-inner">{children}</div>
      </main>
    </div>
  );
}
