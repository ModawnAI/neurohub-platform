"use client";

import type { RequestStatus, TransitionRecord } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";
import clsx from "clsx";

const STATUS_ORDER: RequestStatus[] = [
  "CREATED",
  "RECEIVING",
  "STAGING",
  "READY_TO_COMPUTE",
  "COMPUTING",
  "QC",
  "REPORTING",
  "EXPERT_REVIEW",
  "FINAL",
];

const TERMINAL_STATUSES: RequestStatus[] = ["FAILED", "CANCELLED"];

interface TimelineProps {
  currentStatus: RequestStatus | string;
  createdAt?: string;
  updatedAt?: string | null;
  transitions?: TransitionRecord[];
}

function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(locale === "ko" ? "ko-KR" : "en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function Timeline({ currentStatus, createdAt, updatedAt, transitions }: TimelineProps) {
  const { t, locale } = useTranslation();

  // Build a lookup: status -> transition record
  const transitionMap = new Map<string, TransitionRecord>();
  if (transitions) {
    for (const t of transitions) {
      transitionMap.set(t.to_status, t);
    }
  }

  if (TERMINAL_STATUSES.includes(currentStatus as RequestStatus)) {
    const label = t(`timeline.${currentStatus as "FAILED" | "CANCELLED"}`);
    const transition = transitionMap.get(currentStatus);
    return (
      <div className="timeline">
        <div className="timeline-item">
          <div
            className={clsx("timeline-dot", currentStatus === "FAILED" ? "completed" : "pending")}
            style={{
              background: currentStatus === "FAILED" ? "var(--danger)" : "var(--muted)",
              borderColor: currentStatus === "FAILED" ? "var(--danger)" : "var(--muted)",
            }}
          />
          <p
            className="timeline-label"
            style={{ color: currentStatus === "FAILED" ? "var(--danger)" : "var(--muted)" }}
          >
            {label}
          </p>
          {(transition?.created_at || updatedAt) && (
            <p className="timeline-time">
              {formatDate(transition?.created_at || updatedAt!, locale)}
            </p>
          )}
          {transition?.note && (
            <p className="muted-text" style={{ fontSize: 12, marginTop: 2 }}>
              {transition.note}
            </p>
          )}
        </div>
      </div>
    );
  }

  const currentIdx = STATUS_ORDER.findIndex((s) => s === currentStatus);

  return (
    <div className="timeline">
      {STATUS_ORDER.map((status, idx) => {
        let state: "completed" | "current" | "pending";
        if (idx < currentIdx) state = "completed";
        else if (idx === currentIdx) state = "current";
        else state = "pending";

        const transition = transitionMap.get(status);
        const label = t(`timeline.${status}`);

        return (
          <div key={status} className="timeline-item">
            <div className={clsx("timeline-dot", state)} />
            <p className={clsx("timeline-label", state)}>{label}</p>
            {state === "completed" && transition?.created_at && (
              <p className="timeline-time">{formatDate(transition.created_at, locale)}</p>
            )}
            {state === "completed" && !transition?.created_at && idx === 0 && createdAt && (
              <p className="timeline-time">{formatDate(createdAt, locale)}</p>
            )}
            {state === "current" && (transition?.created_at || updatedAt) && (
              <p className="timeline-time">
                {formatDate(transition?.created_at || updatedAt!, locale)}
              </p>
            )}
            {transition?.actor_id && state !== "pending" && (
              <p className="muted-text" style={{ fontSize: 11, marginTop: 1 }}>
                {transition.actor_id.slice(0, 8)}
              </p>
            )}
            {transition?.note && state !== "pending" && (
              <p className="muted-text" style={{ fontSize: 11, marginTop: 1 }}>
                {transition.note}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
