"use client";

import { RequestStatusChip } from "@/components/status-chip";
import {
  type RequestRead,
  type RequestStatus,
  cancelRequest,
  confirmRequest,
  listRequests,
  submitRequest,
} from "@/lib/api";
import * as Dialog from "@radix-ui/react-dialog";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

type FilterStatus = "ALL" | RequestStatus;

const statusOptions: Array<{ value: FilterStatus; label: string }> = [
  { value: "ALL", label: "전체" },
  { value: "CREATED", label: "생성됨" },
  { value: "STAGING", label: "스테이징" },
  { value: "READY_TO_COMPUTE", label: "실행 준비" },
  { value: "COMPUTING", label: "분석 중" },
  { value: "QC", label: "QC" },
  { value: "FINAL", label: "최종 완료" },
  { value: "FAILED", label: "실패" },
  { value: "CANCELLED", label: "취소" },
];

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

  const filtered = useMemo(() => {
    const items = query.data?.items ?? [];
    if (filter === "ALL") {
      return items;
    }
    return items.filter((item) => item.status === filter);
  }, [query.data?.items, filter]);

  return (
    <section className="panel stack-md">
      <div className="panel-header-row">
        <div>
          <h2>요청 관리</h2>
          <p className="muted-text">요청 상태 전이와 실행 제출을 한 화면에서 관리합니다.</p>
        </div>
        <select
          className="select"
          value={filter}
          onChange={(event) => setFilter(event.target.value as FilterStatus)}
          aria-label="상태 필터"
        >
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {query.isLoading ? <p>요청 목록을 불러오는 중입니다...</p> : null}
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
                <th>작업</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td className="mono-cell">{item.id.slice(0, 8)}...</td>
                  <td>
                    <RequestStatusChip status={item.status} />
                  </td>
                  <td>{item.case_count}</td>
                  <td>{new Date(item.created_at).toLocaleString("ko-KR")}</td>
                  <td>
                    <div className="action-row">
                      <button
                        className="btn btn-secondary"
                        type="button"
                        disabled={!canConfirm(item) || confirmMutation.isPending}
                        onClick={() => confirmMutation.mutate(item.id)}
                      >
                        확정
                      </button>
                      <button
                        className="btn btn-primary"
                        type="button"
                        disabled={!canSubmit(item) || submitMutation.isPending}
                        onClick={() => submitMutation.mutate(item.id)}
                      >
                        제출
                      </button>
                      <button
                        className="btn btn-danger"
                        type="button"
                        disabled={!canCancel(item) || cancelMutation.isPending}
                        onClick={() => {
                          setCancelReason("운영상 취소");
                          setSelectedCancelId(item.id);
                        }}
                      >
                        취소
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {!filtered.length ? (
                <tr>
                  <td colSpan={5}>조건에 맞는 요청이 없습니다.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      ) : null}

      <Dialog.Root
        open={Boolean(selectedCancelId)}
        onOpenChange={(open) => !open && setSelectedCancelId(null)}
      >
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="dialog-content">
            <Dialog.Title>요청 취소</Dialog.Title>
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

            <div className="action-row">
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
                취소 확정
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </section>
  );
}
