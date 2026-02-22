"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import { getUsage, getAdminStats, type UsageEntry } from "@/lib/api";

function getMonthRange(monthsAgo = 0) {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - monthsAgo, 1);
  const end = new Date(now.getFullYear(), now.getMonth() - monthsAgo + 1, 0);
  return {
    start: start.toISOString().split("T")[0]!,
    end: end.toISOString().split("T")[0]!,
    label: start.toLocaleDateString("ko-KR", { year: "numeric", month: "long" }),
  };
}

export default function AdminSettingsPage() {
  const { user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(0);
  const monthRange = getMonthRange(selectedMonth);

  const { data: stats } = useQuery({
    queryKey: ["admin-stats"],
    queryFn: getAdminStats,
  });

  const { data: usageData, isLoading: usageLoading } = useQuery({
    queryKey: ["billing-usage", monthRange.start, monthRange.end],
    queryFn: () => getUsage(monthRange.start, monthRange.end),
  });

  const usageItems: UsageEntry[] = usageData?.items ?? [];

  return (
    <div className="stack-lg">
      <h1 className="page-title">시스템 설정</h1>

      <div className="panel">
        <h2 className="panel-title-mb">관리자 정보</h2>
        <div className="stack-md">
          <div>
            <p className="detail-label">이메일</p>
            <p className="detail-value">{user?.email || "-"}</p>
          </div>
          <div>
            <p className="detail-label">이름</p>
            <p className="detail-value">{user?.displayName || "-"}</p>
          </div>
          <div>
            <p className="detail-label">소속 기관</p>
            <p className="detail-value">{user?.institutionName || "-"}</p>
          </div>
        </div>
      </div>

      <div className="panel">
        <h2 className="panel-title-mb">시스템 정보</h2>
        <div className="stack-md">
          <div>
            <p className="detail-label">플랫폼</p>
            <p className="detail-value">NeuroHub {process.env.NEXT_PUBLIC_APP_VERSION || "v1.0"}</p>
          </div>
          <div>
            <p className="detail-label">환경</p>
            <p className="detail-value">{process.env.NEXT_PUBLIC_ENV || process.env.NODE_ENV || "development"}</p>
          </div>
          {stats && (
            <>
              <div>
                <p className="detail-label">총 요청 수</p>
                <p className="detail-value">{stats.total_requests}건</p>
              </div>
              <div>
                <p className="detail-label">활성 사용자</p>
                <p className="detail-value">{stats.active_users}명</p>
              </div>
              <div>
                <p className="detail-label">등록 서비스</p>
                <p className="detail-value">{stats.total_services}개</p>
              </div>
              <div>
                <p className="detail-label">등록 기관</p>
                <p className="detail-value">{stats.total_organizations}개</p>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 className="panel-title" style={{ margin: 0 }}>사용량</h2>
          <div style={{ display: "flex", gap: 8 }}>
            {[0, 1, 2].map((m) => {
              const mr = getMonthRange(m);
              return (
                <button
                  key={m}
                  className={`btn btn-sm ${selectedMonth === m ? "btn-primary" : "btn-secondary"}`}
                  onClick={() => setSelectedMonth(m)}
                >
                  {mr.label}
                </button>
              );
            })}
          </div>
        </div>

        {usageLoading ? (
          <div className="loading-center"><span className="spinner" /></div>
        ) : usageItems.length === 0 ? (
          <p className="muted-text">{monthRange.label} 사용 내역이 없습니다.</p>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>서비스</th>
                  <th>유형</th>
                  <th>건수</th>
                  <th>총액</th>
                </tr>
              </thead>
              <tbody>
                {usageItems.map((item, i) => (
                  <tr key={i}>
                    <td>{item.service_name}</td>
                    <td>{item.charge_type}</td>
                    <td>{item.count}건</td>
                    <td style={{ fontWeight: 600 }}>{item.total_amount.toLocaleString("ko-KR")}원</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
