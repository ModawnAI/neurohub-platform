"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, DownloadSimple, File } from "phosphor-react";
import {
  getRequest,
  advanceRequest,
  listCases,
  listCaseFiles,
  getDownloadUrl,
  type RequestStatus,
  type CaseRead,
  type CaseFileRead,
} from "@/lib/api";
import { Timeline } from "@/components/timeline";

const TRANSITIONS: Record<string, string[]> = {
  CREATED: ["RECEIVING"],
  RECEIVING: ["STAGING"],
  STAGING: ["READY_TO_COMPUTE"],
  READY_TO_COMPUTE: ["COMPUTING"],
  COMPUTING: ["QC", "FAILED"],
  QC: ["REPORTING", "COMPUTING", "FAILED"],
  REPORTING: ["EXPERT_REVIEW", "FINAL"],
  EXPERT_REVIEW: ["FINAL", "REPORTING"],
};

const STATUS_LABELS: Record<string, string> = {
  CREATED: "생성됨", RECEIVING: "데이터 수신 중", STAGING: "검증 중",
  READY_TO_COMPUTE: "분석 대기", COMPUTING: "분석 중", QC: "품질 검증",
  REPORTING: "보고서 생성", EXPERT_REVIEW: "전문가 검토", FINAL: "완료",
  FAILED: "실패", CANCELLED: "취소됨",
};

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function AdminCaseFiles({ requestId, caseItem }: { requestId: string; caseItem: CaseRead }) {
  const [expanded, setExpanded] = useState(false);
  const { data: filesData, isLoading } = useQuery({
    queryKey: ["case-files", requestId, caseItem.id],
    queryFn: () => listCaseFiles(requestId, caseItem.id),
    enabled: expanded,
  });

  const handleDownload = async (file: CaseFileRead) => {
    try {
      const { download_url } = await getDownloadUrl(requestId, caseItem.id, file.id);
      window.open(download_url, "_blank");
    } catch {
      alert("다운로드에 실패했습니다.");
    }
  };

  const files = filesData?.items ?? [];

  return (
    <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
      <button
        onClick={() => setExpanded(!expanded)}
        style={{ background: "none", border: "none", cursor: "pointer", width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", fontSize: 14 }}
      >
        <span><strong>{caseItem.patient_ref}</strong> <span className="muted-text" style={{ fontSize: 12 }}>({caseItem.status})</span></span>
        <span style={{ fontSize: 12, color: "var(--primary)" }}>{expanded ? "접기" : "파일 보기"}</span>
      </button>
      {expanded && (
        <div style={{ paddingLeft: 16, marginTop: 8 }}>
          {isLoading ? <span className="spinner" /> : files.length === 0 ? (
            <p className="muted-text" style={{ fontSize: 13 }}>파일 없음</p>
          ) : (
            <div className="stack-sm">
              {files.map((file) => (
                <div key={file.id} className="file-info-card">
                  <div className="file-info-card-icon"><File size={20} /></div>
                  <div className="file-info-card-body">
                    <p className="file-info-card-name">{file.filename}</p>
                    <p className="file-info-card-meta">{file.slot} &middot; {formatBytes(file.size_bytes)}</p>
                  </div>
                  {file.status === "COMPLETED" && (
                    <button className="btn btn-sm btn-secondary" onClick={() => handleDownload(file)} title="다운로드">
                      <DownloadSimple size={14} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: request, isLoading } = useQuery({
    queryKey: ["admin-request", id],
    queryFn: () => getRequest(id),
    enabled: !!id,
  });

  const { data: casesData } = useQuery({
    queryKey: ["request-cases", id],
    queryFn: () => listCases(id),
    enabled: !!id,
  });

  const transitionMut = useMutation({
    mutationFn: (targetStatus: string) => advanceRequest(id, targetStatus),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-request", id] });
    },
  });

  if (isLoading) return <div className="loading-center"><span className="spinner" /></div>;
  if (!request) return <div className="banner banner-warning">요청을 찾을 수 없습니다.</div>;

  const possibleTransitions = TRANSITIONS[request.status] || [];
  const serviceSnapshot = (request as any).service_snapshot;
  const cases: CaseRead[] = casesData?.items ?? [];

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/admin/requests")}>
        <ArrowLeft size={16} /> 요청 목록으로
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">요청 상세</h1>
          <p className="page-subtitle">#{id.slice(0, 8)}</p>
        </div>
        <span className={`status-chip status-${request.status.toLowerCase()}`}>
          {STATUS_LABELS[request.status] || request.status}
        </span>
      </div>

      <div className="detail-grid">
        <div className="stack-md">
          <div className="panel">
            <h2 className="panel-title-mb">요청 정보</h2>
            <div className="stack-md">
              <div><p className="detail-label">요청 ID</p><p className="detail-value" style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>{request.id}</p></div>
              <div><p className="detail-label">서비스</p><p className="detail-value">{serviceSnapshot?.display_name || "-"}</p></div>
              <div><p className="detail-label">케이스 수</p><p className="detail-value">{request.case_count}건</p></div>
              <div><p className="detail-label">우선순위</p><p className="detail-value">{request.priority}</p></div>
              <div><p className="detail-label">생성일</p><p className="detail-value">{new Date(request.created_at).toLocaleString("ko-KR")}</p></div>
              {request.updated_at && <div><p className="detail-label">최종 수정</p><p className="detail-value">{new Date(request.updated_at).toLocaleString("ko-KR")}</p></div>}
            </div>
          </div>

          {/* Case Files */}
          {cases.length > 0 && (
            <div className="panel">
              <h2 className="panel-title-mb">케이스 및 파일</h2>
              <div className="stack-sm">
                {cases.map((c) => (
                  <AdminCaseFiles key={c.id} requestId={id} caseItem={c} />
                ))}
              </div>
            </div>
          )}

          {possibleTransitions.length > 0 && (
            <div className="panel">
              <h2 className="panel-title-mb">상태 전이</h2>
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                {possibleTransitions.map((target) => (
                  <button
                    key={target}
                    className={`btn ${target === "FAILED" || target === "CANCELLED" ? "btn-danger" : "btn-primary"}`}
                    onClick={() => transitionMut.mutate(target)}
                    disabled={transitionMut.isPending}
                  >
                    → {STATUS_LABELS[target] || target}
                  </button>
                ))}
              </div>
              {transitionMut.isError && <p className="error-text" style={{ marginTop: 8 }}>{(transitionMut.error as Error).message}</p>}
            </div>
          )}
        </div>

        <div>
          <div className="panel">
            <h2 className="panel-title-mb">진행 상태</h2>
            <Timeline currentStatus={request.status as RequestStatus} createdAt={request.created_at} updatedAt={request.updated_at ?? undefined} />
          </div>
        </div>
      </div>
    </div>
  );
}
