"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAuditLogs, type AuditLogRead } from "@/lib/api";

export default function AdminAuditLogsPage() {
  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [page, setPage] = useState(0);
  const limit = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", action, entityType, page],
    queryFn: () =>
      listAuditLogs({
        action: action || undefined,
        entity_type: entityType || undefined,
        limit,
        offset: page * limit,
      }),
  });

  const logs = data?.items ?? [];
  const total = data?.total ?? 0;
  const hasMore = (page + 1) * limit < total;

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">감사 로그</h1>
          <p className="page-subtitle">시스템 내 모든 주요 활동 기록입니다</p>
        </div>
      </div>

      {/* Filters */}
      <div className="panel" style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
          <input
            className="input"
            placeholder="액션 필터 (예: CREATE)"
            value={action}
            onChange={(e) => { setAction(e.target.value); setPage(0); }}
            style={{ width: 200 }}
          />
          <input
            className="input"
            placeholder="엔티티 타입 (예: REQUEST)"
            value={entityType}
            onChange={(e) => { setEntityType(e.target.value); setPage(0); }}
            style={{ width: 200 }}
          />
          <span className="muted-text" style={{ fontSize: 12 }}>
            총 {total}건
          </span>
        </div>
      </div>

      {isLoading ? (
        <div className="loading-center"><span className="spinner" /></div>
      ) : (
        <div className="panel">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>시간</th>
                  <th>액션</th>
                  <th>엔티티</th>
                  <th>엔티티 ID</th>
                  <th>액터</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log: AuditLogRead) => (
                  <tr key={log.id}>
                    <td style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                      {new Date(log.created_at).toLocaleString("ko-KR")}
                    </td>
                    <td><span className="status-chip status-computing">{log.action}</span></td>
                    <td>{log.entity_type}</td>
                    <td className="mono-cell" style={{ fontSize: 12 }}>{log.entity_id.slice(0, 8)}</td>
                    <td className="mono-cell" style={{ fontSize: 12 }}>{log.actor_id.slice(0, 8)}</td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: 24, color: "var(--muted)" }}>
                      로그가 없습니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > limit && (
            <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 16 }}>
              <button className="btn btn-sm btn-secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
                이전
              </button>
              <span className="muted-text" style={{ fontSize: 13, lineHeight: "32px" }}>
                {page + 1} / {Math.ceil(total / limit)}
              </span>
              <button className="btn btn-sm btn-secondary" disabled={!hasMore} onClick={() => setPage(page + 1)}>
                다음
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
