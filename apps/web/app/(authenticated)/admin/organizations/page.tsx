"use client";

import { useQuery } from "@tanstack/react-query";
import { listOrganizations, type OrgRead } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  HOSPITAL: "병원",
  CLINIC: "의원",
  INDIVIDUAL: "개인",
};

export default function AdminOrganizationsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-orgs"], queryFn: listOrganizations });
  const orgs = data?.items ?? [];

  return (
    <div className="stack-lg">
      <div className="page-header">
        <div>
          <h1 className="page-title">기관 관리</h1>
          <p className="page-subtitle">등록된 기관 목록입니다</p>
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
                  <th>기관명</th>
                  <th>코드</th>
                  <th>유형</th>
                  <th>회원 수</th>
                  <th>상태</th>
                  <th>생성일</th>
                </tr>
              </thead>
              <tbody>
                {orgs.map((org: OrgRead) => (
                  <tr key={org.id}>
                    <td style={{ fontWeight: 600 }}>{org.name}</td>
                    <td className="mono-cell">{org.code}</td>
                    <td>{TYPE_LABELS[org.institution_type] || org.institution_type}</td>
                    <td>{org.member_count}명</td>
                    <td><span className={`status-chip ${org.status === "ACTIVE" ? "status-final" : "status-cancelled"}`}>{org.status === "ACTIVE" ? "활성" : "비활성"}</span></td>
                    <td>{org.created_at ? new Date(org.created_at).toLocaleDateString("ko-KR") : "-"}</td>
                  </tr>
                ))}
                {orgs.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>등록된 기관이 없습니다.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
