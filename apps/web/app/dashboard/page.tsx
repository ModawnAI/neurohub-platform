"use client";

import { RequestStatusChip } from "@/components/status-chip";
import { type RequestRead, listRequests } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

function countByStatus(items: RequestRead[], statuses: RequestRead["status"][]) {
  return items.filter((item) => statuses.includes(item.status)).length;
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
      <section className="panel panel-grid">
        <article className="metric-card">
          <p className="metric-label">전체 요청</p>
          <p className="metric-value">{total}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">진행 중</p>
          <p className="metric-value">{active}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">완료</p>
          <p className="metric-value">{done}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">실패/취소</p>
          <p className="metric-value">{failed}</p>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header-row">
          <h3>최근 요청</h3>
          <Link className="btn btn-secondary" href="/requests">
            전체 보기
          </Link>
        </div>

        {query.isLoading ? <p>요청 데이터를 불러오는 중입니다...</p> : null}
        {query.isError ? <p className="error-text">{query.error.message}</p> : null}

        {!query.isLoading && !query.isError ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>요청 ID</th>
                  <th>상태</th>
                  <th>케이스 수</th>
                  <th>생성 시각</th>
                </tr>
              </thead>
              <tbody>
                {items.slice(0, 8).map((item) => (
                  <tr key={item.id}>
                    <td className="mono-cell">{item.id.slice(0, 8)}...</td>
                    <td>
                      <RequestStatusChip status={item.status} />
                    </td>
                    <td>{item.case_count}</td>
                    <td>{new Date(item.created_at).toLocaleString("ko-KR")}</td>
                  </tr>
                ))}
                {!items.length ? (
                  <tr>
                    <td colSpan={4}>요청 데이터가 없습니다. 신규 요청을 생성해 주세요.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
