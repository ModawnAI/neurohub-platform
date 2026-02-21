"use client";

import { useQuery } from "@tanstack/react-query";
import { listServices, type ServiceRead } from "@/lib/api";

export default function AdminServicesPage() {
  const { data, isLoading } = useQuery({ queryKey: ["services"], queryFn: listServices });
  const services = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">서비스 관리</h1>
          <p className="page-subtitle">등록된 AI 분석 서비스 목록입니다</p>
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
                  <th>서비스명</th>
                  <th>내부명</th>
                  <th>버전</th>
                  <th>부서</th>
                  <th>상태</th>
                  <th>생성일</th>
                </tr>
              </thead>
              <tbody>
                {services.map((svc: ServiceRead) => (
                  <tr key={svc.id}>
                    <td style={{ fontWeight: 600 }}>{svc.display_name}</td>
                    <td className="mono-cell">{svc.name}</td>
                    <td>v{svc.version}</td>
                    <td>{svc.department || "-"}</td>
                    <td><span className={`status-chip ${svc.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>{svc.status === "ACTIVE" ? "활성" : "비활성"}</span></td>
                    <td>{new Date(svc.created_at).toLocaleDateString("ko-KR")}</td>
                  </tr>
                ))}
                {services.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>등록된 서비스가 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
