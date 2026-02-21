"use client";

import { RequestStatusChip } from "@/components/status-chip";
import {
  type RequestRead,
  type RequestStatus,
  cancelRequest,
  confirmRequest,
  listRequests,
  submitRequest,
  transitionRequest,
} from "@/lib/api";
import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { CheckCircle, PaperPlaneTilt, XCircle, Tray, ArrowRight } from "phosphor-react";

type FilterStatus = "ALL" | RequestStatus;

const statusOptions: Array<{ value: FilterStatus; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "CREATED", label: "생성됨" },
  { value: "STAGING", label: "준비 중" },
  { value: "READY_TO_COMPUTE", label: "분석 대기" },
  { value: "COMPUTING", label: "분석 중" },
  { value: "QC", label: "품질 검증" },
  { value: "FINAL", label: "완료" },
  { value: "FAILED", label: "실패" },
  { value: "CANCELLED", label: "취소" },
];

const NEXT_STATUS: Partial<Record<RequestStatus, { target: RequestStatus; label: string }>> = {
  CREATED: { target: "RECEIVING", label: "수신 시작" },
  RECEIVING: { target: "STAGING", label: "준비 완료" },
};

function canAdvance(item: RequestRead) {
  return item.status in NEXT_STATUS;
}

function canConfirm(item: RequestRead) {
  return item.status === "STAGING";
}

function canSubmit(item: RequestRead) {
  return item.status === "READY_TO_COMPUTE";
}

function canCancel(item: RequestRead) {
  return ["CREATED", "RECEIVING", "STAGING", "READY_TO_COMPUTE"].includes(item.status);
}

export default function RequestsPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<FilterStatus>("ALL");
  const [selectedCancelId, setSelectedCancelId] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState("운영상 취소");

  const query = useQuery<{ items: RequestRead[]; total: number }, Error>({
    queryKey: ["requests"],
    queryFn: listRequests,
    refetchInterval: 15_000,
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["requests"] });
  };

  const confirmMutation = useMutation({
    mutationFn: confirmRequest,
    onSuccess: refresh,
  });

  const submitMutation = useMutation({
    mutationFn: submitRequest,
    onSuccess: refresh,
  });

  const cancelMutation = useMutation({
    mutationFn: ({ requestId, reason }: { requestId: string; reason: string }) =>
      cancelRequest(requestId, reason),
    onSuccess: async () => {
      setSelectedCancelId(null);
      await refresh();
    },
  });

  const advanceMutation = useMutation({
    mutationFn: ({ requestId, targetStatus }: { requestId: string; targetStatus: RequestStatus }) =>
      transitionRequest(requestId, targetStatus),
    onSuccess: refresh,
  });

  const filtered = useMemo(() => {
    const items = query.data?.items ?? [];
    if (filter === "ALL") {
      return items;
    }
    return items.filter((item) => item.status === filter);
  }, [query.data?.items, filter]);

  return (
    <div className="stack-lg">
      {/* 페이지 헤더 */}
      <div className="page-header">
        <div>
          <h2 className="page-title">요청 관리</h2>
          <p className="page-subtitle">요청 상태 전이와 실행 제출을 한 화면에서 관리합니다.</p>
        </div>
      </div>

      {/* 필터 탭 */}
      <div className="filter-tabs">
        {statusOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`filter-tab${filter === option.value ? " active" : ""}`}
            onClick={() => setFilter(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* 테이블 */}
      <section className="panel">
        {query.isLoading && <p className="muted-text">요청 목록을 불러오는 중입니다...</p>}
        {query.isError && <p className="error-text">{query.error.message}</p>}

        {!query.isLoading && !query.isError && filtered.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>요청 ID</th>
                  <th>상태</th>
                  <th>케이스 수</th>
                  <th>생성 시각</th>
                  <th>작업</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={item.id}>
                    <td className="mono-cell">{item.id.slice(0, 8)}</td>
                    <td>
                      <RequestStatusChip status={item.status} />
                    </td>
                    <td>{item.case_count}</td>
                    <td style={{ fontSize: 13, color: "var(--muted)" }}>
                      {new Date(item.created_at).toLocaleString("ko-KR")}
                    </td>
                    <td>
                      <div className="action-row">
                        {canAdvance(item) && (
                          <button
                            className="btn btn-secondary btn-sm"
                            type="button"
                            disabled={advanceMutation.isPending}
                            onClick={() => {
                              const next = NEXT_STATUS[item.status];
                              if (next) advanceMutation.mutate({ requestId: item.id, targetStatus: next.target });
                            }}
                          >
                            <ArrowRight size={14} weight="bold" />
                            {NEXT_STATUS[item.status]?.label ?? "진행"}
                          </button>
                        )}
                        <button
                          className="btn btn-secondary btn-sm"
                          type="button"
                          disabled={!canConfirm(item) || confirmMutation.isPending}
                          onClick={() => confirmMutation.mutate(item.id)}
                        >
                          <CheckCircle size={14} weight="bold" />
                          확정
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          type="button"
                          disabled={!canSubmit(item) || submitMutation.isPending}
                          onClick={() => submitMutation.mutate(item.id)}
                        >
                          <PaperPlaneTilt size={14} weight="bold" />
                          제출
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          type="button"
                          disabled={!canCancel(item) || cancelMutation.isPending}
                          onClick={() => {
                            setCancelReason("운영상 취소");
                            setSelectedCancelId(item.id);
                          }}
                        >
                          <XCircle size={14} weight="bold" />
                          취소
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!query.isLoading && !query.isError && filtered.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Tray size={40} weight="duotone" />
            </div>
            <p className="empty-state-text">조건에 맞는 요청이 없습니다.</p>
          </div>
        )}
      </section>

      {/* 취소 다이얼로그 */}
      <Dialog.Root
        open={Boolean(selectedCancelId)}
        onOpenChange={(open) => !open && setSelectedCancelId(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <Dialog.Title className="dialog-title">요청 취소</Dialog.Title>
            <Dialog.Description className="muted-text">
              취소 사유는 감사 로그에 기록됩니다.
            </Dialog.Description>

            <textarea
              className="textarea"
              rows={4}
              value={cancelReason}
              onChange={(event) => setCancelReason(event.target.value)}
              placeholder="취소 사유를 입력하세요"
            />

            <div className="action-row" style={{ justifyContent: "flex-end" }}>
              <Dialog.Close asChild>
                <button className="btn btn-secondary" type="button">
                  닫기
                </button>
              </Dialog.Close>
              <button
                className="btn btn-danger"
                type="button"
                disabled={!selectedCancelId || cancelMutation.isPending}
                onClick={() => {
                  if (!selectedCancelId) {
                    return;
                  }
                  cancelMutation.mutate({ requestId: selectedCancelId, reason: cancelReason });
                }}
              >
                <XCircle size={14} weight="bold" />
                취소 확정
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
