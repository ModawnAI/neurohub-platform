"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch, listArtifacts, type ModelArtifactRead, type ServiceRead } from "@/lib/api";

interface GroupedArtifacts {
  service: ServiceRead;
  artifacts: ModelArtifactRead[];
}

function StatusChip({ status }: { status: string }) {
  const colors: Record<string, { bg: string; color: string }> = {
    APPROVED: { bg: "#d1fae5", color: "#065f46" },
    REJECTED: { bg: "#fee2e2", color: "#991b1b" },
    SCANNING: { bg: "#dbeafe", color: "#1e40af" },
    PENDING_SCAN: { bg: "#f3f4f6", color: "#374151" },
    FLAGGED: { bg: "#fef3c7", color: "#92400e" },
  };
  const style = colors[status] ?? { bg: "#f3f4f6", color: "#374151" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 10px",
        borderRadius: 12,
        fontSize: 12,
        fontWeight: 600,
        background: style.bg,
        color: style.color,
      }}
    >
      {status}
    </span>
  );
}

function BuildChip({ status }: { status: string | null }) {
  if (!status) return null;
  const colors: Record<string, { bg: string; color: string }> = {
    BUILT: { bg: "#d1fae5", color: "#065f46" },
    FAILED: { bg: "#fee2e2", color: "#991b1b" },
    BUILDING: { bg: "#dbeafe", color: "#1e40af" },
    PENDING: { bg: "#f3f4f6", color: "#374151" },
  };
  const style = colors[status] ?? { bg: "#f3f4f6", color: "#374151" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 12,
        fontSize: 11,
        background: style.bg,
        color: style.color,
        marginLeft: 6,
      }}
    >
      🐳 {status}
    </span>
  );
}

export default function ExpertModelsPage() {
  const [groups, setGroups] = useState<GroupedArtifacts[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { items: services } = await apiFetch<{ items: ServiceRead[] }>("/services");
        const grouped: GroupedArtifacts[] = [];
        for (const svc of services) {
          try {
            const { items } = await listArtifacts(svc.id);
            if (items.length > 0) {
              grouped.push({ service: svc, artifacts: items });
            }
          } catch {
            // skip services with no artifacts or access errors
          }
        }
        setGroups(grouped);
      } catch {
        // handle error
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="page-container">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <h1 className="page-title" style={{ margin: 0 }}>모델 아티팩트</h1>
        <Link href="/expert/models/new" className="btn btn-primary">
          + 새 아티팩트 업로드
        </Link>
      </div>

      {loading && <p>로딩 중…</p>}

      {!loading && groups.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: 40 }}>
          <p style={{ color: "var(--color-text-secondary)" }}>업로드된 아티팩트가 없습니다.</p>
          <Link href="/expert/models/new" className="btn btn-primary" style={{ marginTop: 16 }}>
            첫 아티팩트 업로드하기
          </Link>
        </div>
      )}

      {groups.map(({ service, artifacts }) => (
        <div key={service.id} style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>
            {service.display_name || service.name}
          </h2>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ background: "var(--color-surface-secondary)" }}>
                  <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600 }}>파일명</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600 }}>유형</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600 }}>크기</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600 }}>상태</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600 }}>런타임</th>
                  <th style={{ padding: "10px 16px", textAlign: "left", fontWeight: 600 }}>업로드일</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((a) => (
                  <tr key={a.id} style={{ borderTop: "1px solid var(--color-border)" }}>
                    <td style={{ padding: "10px 16px" }}>
                      <span title={a.id} style={{ fontFamily: "monospace", fontSize: 13 }}>
                        {a.file_name}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <code style={{ fontSize: 12 }}>{a.artifact_type}</code>
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      {a.file_size != null
                        ? a.file_size > 1024 * 1024
                          ? `${(a.file_size / 1024 / 1024).toFixed(1)} MB`
                          : `${(a.file_size / 1024).toFixed(1)} KB`
                        : "-"}
                    </td>
                    <td style={{ padding: "10px 16px" }}>
                      <StatusChip status={a.status} />
                      <BuildChip status={a.build_status} />
                    </td>
                    <td style={{ padding: "10px 16px" }}>{a.runtime ?? "-"}</td>
                    <td style={{ padding: "10px 16px", color: "var(--color-text-secondary)", fontSize: 12 }}>
                      {new Date(a.created_at).toLocaleDateString("ko-KR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
