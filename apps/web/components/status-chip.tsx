"use client";

import type { RequestStatus } from "@/lib/api";
import { useT } from "@/lib/i18n";

export function RequestStatusChip({ status }: { status: RequestStatus }) {
  const t = useT();
  const className = `status-chip status-${status.toLowerCase()}`;
  return <span className={className}>{t(`status.${status}` as `status.${RequestStatus}`)}</span>;
}
