"use client";

import { ActivityFeed } from "@/components/activity-feed";
import { MetricCard } from "@/components/metric-card";
import { StatusBar } from "@/components/status-bar";
import { RequestStatusChip } from "@/components/status-chip";
import { type RequestRead, listRequests } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Stack, Spinner, CheckCircle, XCircle, Tray } from "phosphor-react";

function countByStatus(items: RequestRead[], statuses: RequestRead["status"][]) {
  return items.filter((item) => statuses.includes(item.status)).length;
}

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "방금 전";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  const days = Math.floor(hours / 24);
  return `${days}일 전`;
}

export default function DashboardPage() {
  const query = useQuery<{ items: RequestRead[]; total: number }, Error>({
    queryKey: ["requests"],
    queryFn: listRequests,
    refetchInterval: 20_000,
  });

  const items = query.data?.items ?? [];
  const total = items.length;
  const active = countByStatus(items, [
    "CREATED",
    "RECEIVING",
    "STAGING",
    "READY_TO_COMPUTE",
    "COMPUTING",
    "QC",
    "REPORTING",
    "EXPERT_REVIEW",
  ]);
  const done = countByStatus(items, ["FINAL"]);
  const failed = countByStatus(items, ["FAILED", "CANCELLED"]);

  return (
    <div className="stack-lg">
      {/* Page header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">대시보드</h2>
          <p className="page-subtitle">실시간 요청 현황 및 활동 요약</p>
        </div>
        <div className="page-header-actions">
          <Link className="btn btn-primary" href="/new-request">
            신규 요청
          </Link>
          <Link className="btn btn-secondary" href="/requests">
            요청 관리
          </Link>
        </div>
      </div>

      {/* Metric cards */}
      <section className="panel-grid">
        <MetricCard
          icon={<Stack size={20} weight="bold" />}
          label="전체 요청"
          value={total}
          iconBg="#e2e8f0"
          iconColor="#334155"
        />
        <MetricCard
          icon={<Spinner size={20} weight="bold" />}
          label="진행 중"
          value={active}
          iconBg="#dbeafe"
          iconColor="#1d4ed8"
        />
        <MetricCard
          icon={<CheckCircle size={20} weight="bold" />}
          label="완료"
          value={done}
          iconBg="#dcfce7"
          iconColor="#166534"
        />
        <MetricCard
          icon={<XCircle size={20} weight="bold" />}
          label="실패/취소"
          value={failed}
          iconBg="#fee2e2"
          iconColor="#b91c1c"
        />
      </section>

      {/* Status distribution */}
      {items.length > 0 && (
        <section className="panel">
          <p style={{ margin: "0 0 12px", fontWeight: 700, fontSize: 14 }}>상태 분포</p>
          <StatusBar items={items} />
        </section>
      )}

      {/* Two-column: table + activity */}
      <div className="dashboard-columns">
        {/* Recent requests */}
        <section className="panel">
          <div className="panel-header-row" style={{ marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>최근 요청</h3>
            <Link className="btn btn-secondary btn-sm" href="/requests">
              전체 보기
            </Link>
          </div>

          {query.isLoading && <p className="muted-text">요청 데이터를 불러오는 중입니다...</p>}
          {query.isError && <p className="error-text">{query.error.message}</p>}

          {!query.isLoading && !query.isError && items.length > 0 && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>요청 ID</th>
                    <th>상태</th>
                    <th>케이스</th>
                    <th>생성</th>
                  </tr>
                </thead>
                <tbody>
                  {items.slice(0, 8).map((item) => (
                    <tr key={item.id}>
                      <td className="mono-cell">{item.id.slice(0, 8)}</td>
                      <td>
                        <RequestStatusChip status={item.status} />
                      </td>
                      <td>{item.case_count}</td>
                      <td style={{ color: "var(--muted)", fontSize: 13 }}>
                        {relativeTime(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!query.isLoading && !query.isError && items.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">
                <Tray size={40} weight="duotone" />
              </div>
              <p className="empty-state-text">
                요청 데이터가 없습니다.
                <br />
                <Link href="/new-request" style={{ color: "var(--primary)", fontWeight: 600 }}>
                  신규 요청을 생성해 주세요.
                </Link>
              </p>
            </div>
          )}
        </section>

        {/* Activity feed */}
        <section className="panel">
          <h3 style={{ margin: "0 0 8px", fontSize: 15, fontWeight: 700 }}>최근 활동</h3>
          {query.isLoading ? (
            <p className="muted-text">불러오는 중...</p>
          ) : (
            <ActivityFeed items={items} />
          )}
        </section>
      </div>
    </div>
  );
}
