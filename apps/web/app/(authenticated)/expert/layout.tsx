"use client";

import { Sidebar } from "@/components/sidebar";
import { useAuth } from "@/lib/auth";
import { House, ListChecks, GearSix } from "phosphor-react";

const NAV_ITEMS = [
  { href: "/expert/dashboard", label: "대시보드", icon: <House size={20} /> },
  { href: "/expert/reviews", label: "리뷰 대기", icon: <ListChecks size={20} /> },
  { href: "/expert/settings", label: "설정", icon: <GearSix size={20} /> },
];

export default function ExpertLayout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const isPending = user?.expertStatus === "PENDING_APPROVAL";

  return (
    <div className="app-layout">
      <Sidebar items={NAV_ITEMS} userTypeLabel="전문가 리뷰어" />
      <main className="main-content">
        <div className="main-content-inner">
          {isPending && (
            <div className="banner banner-warning" style={{ marginBottom: 20 }}>
              관리자 승인 대기 중입니다. 승인 후 리뷰 기능을 사용할 수 있습니다.
            </div>
          )}
          {children}
        </div>
      </main>
    </div>
  );
}
