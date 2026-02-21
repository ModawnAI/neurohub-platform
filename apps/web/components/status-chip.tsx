import type { RequestStatus } from "@/lib/api";

const labelMap: Record<RequestStatus, string> = {
  CREATED: "생성됨",
  RECEIVING: "수신 중",
  STAGING: "스테이징",
  READY_TO_COMPUTE: "실행 준비",
  COMPUTING: "분석 중",
  QC: "QC",
  REPORTING: "리포트 작성",
  EXPERT_REVIEW: "전문가 검토",
  FINAL: "최종 완료",
  FAILED: "실패",
  CANCELLED: "취소됨",
};

export function RequestStatusChip({ status }: { status: RequestStatus }) {
  const className = `status-chip status-${status.toLowerCase()}`;
  return <span className={className}>{labelMap[status]}</span>;
}
