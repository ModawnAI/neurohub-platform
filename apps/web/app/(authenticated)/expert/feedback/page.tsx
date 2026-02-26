"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listEvaluations } from "@/lib/api";

interface EvaluationSummary {
  id: string;
  status: string;
  created_at: string;
  service_name?: string;
  run_id?: string;
}

export default function ExpertFeedbackPage() {
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listEvaluations({ status: "COMPLETED", limit: 50 })
      .then((data: any) => setEvaluations(data?.items ?? data ?? []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="page-title">피드백 제출</h1>
      <p className="page-subtitle" style={{ marginBottom: 24 }}>
        완료된 평가에 대해 전문가 피드백(정답 레이블, 출력 교정)을 제출하세요.
      </p>

      {loading && <p className="text-muted">불러오는 중...</p>}
      {!loading && evaluations.length === 0 && (
        <p className="text-muted">피드백 대기 중인 평가가 없습니다.</p>
      )}

      <div className="card-grid">
        {evaluations.map((ev) => (
          <div key={ev.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  평가 ID: {ev.id.slice(0, 8)}…
                </div>
                {ev.service_name && (
                  <div className="text-muted" style={{ fontSize: 13 }}>{ev.service_name}</div>
                )}
                <div className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                  {new Date(ev.created_at).toLocaleDateString("ko-KR")}
                </div>
              </div>
              <span className={`badge badge-${ev.status === "COMPLETED" ? "success" : "default"}`}>
                {ev.status}
              </span>
            </div>
            <div style={{ marginTop: 16 }}>
              <Link href={`/expert/feedback/${ev.id}`}>
                <button className="btn btn-primary btn-sm">피드백 제출 →</button>
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
