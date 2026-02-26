"use client";

import { useEffect, useState } from "react";
import {
  getFeedbackStats,
  listServices,
  createTrainingJob,
  listTrainingJobs,
  getPerformanceMetrics,
} from "@/lib/api";

interface ServiceOption {
  id: string;
  name: string;
}

interface FeedbackStats {
  total_feedback: number;
  unused_feedback: number;
  high_quality_feedback: number;
  ready_for_training: boolean;
  threshold: number;
}

interface TrainingJob {
  id: string;
  status: string;
  trigger_type: string;
  feedback_count: number;
  started_at: string | null;
  completed_at: string | null;
  error_detail: string | null;
  created_at: string;
}

interface PerfDataPoint {
  metric_date: string;
  accuracy: number | null;
  sensitivity: number | null;
  specificity: number | null;
  auc_roc: number | null;
  total_runs: number | null;
  expert_approval_rate: number | null;
  evaluation_count: number | null;
}

const STATUS_COLORS: Record<string, string> = {
  COMPLETED: "success",
  FAILED: "danger",
  TRAINING: "info",
  PENDING: "default",
  PREPARING: "info",
  EVALUATING: "warning",
};

export default function PerformancePage() {
  const [services, setServices] = useState<ServiceOption[]>([]);
  const [selectedService, setSelectedService] = useState<string>("");
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [perfData, setPerfData] = useState<PerfDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [startingJob, setStartingJob] = useState(false);
  const [jobError, setJobError] = useState<string | null>(null);

  useEffect(() => {
    listServices()
      .then((data: any) => {
        const items = data?.items ?? data ?? [];
        setServices(items.map((s: any) => ({ id: s.id, name: s.name })));
        if (items.length > 0) setSelectedService(items[0].id);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (!selectedService) return;
    setLoading(true);
    Promise.all([
      getFeedbackStats(selectedService).catch(() => null),
      listTrainingJobs(selectedService).catch(() => []),
      getPerformanceMetrics(selectedService, 90).catch(() => ({ data_points: [] })),
    ])
      .then(([s, j, p]) => {
        setStats(s);
        setJobs(j as TrainingJob[]);
        setPerfData((p as any)?.data_points ?? []);
      })
      .finally(() => setLoading(false));
  }, [selectedService]);

  const handleStartTraining = async () => {
    if (!selectedService) return;
    setStartingJob(true);
    setJobError(null);
    try {
      await createTrainingJob(selectedService, { trigger_type: "manual" });
      // Refresh jobs
      const j = await listTrainingJobs(selectedService);
      setJobs(j as TrainingJob[]);
    } catch (e: any) {
      setJobError(e.message ?? "학습 시작 실패");
    } finally {
      setStartingJob(false);
    }
  };

  // Simple inline chart: accuracy over time
  const chartMax = 1.0;
  const chartHeight = 120;
  const chartWidth = perfData.length > 0 ? Math.max(400, perfData.length * 40) : 400;

  return (
    <div>
      <h1 className="page-title">모델 성능 & 학습 관리</h1>

      {/* Service selector */}
      <div className="form-group" style={{ maxWidth: 320, marginBottom: 24, marginTop: 16 }}>
        <label className="form-label">서비스 선택</label>
        <select
          className="form-control"
          value={selectedService}
          onChange={(e) => setSelectedService(e.target.value)}
        >
          {services.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {loading && <p className="text-muted">불러오는 중...</p>}

      {/* Stats cards */}
      {stats && (
        <div className="stats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16, marginBottom: 24 }}>
          <div className="card stat-card">
            <div className="stat-value">{stats.total_feedback}</div>
            <div className="stat-label">전체 피드백</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">{stats.unused_feedback}</div>
            <div className="stat-label">미사용 피드백</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">{stats.high_quality_feedback}</div>
            <div className="stat-label">고품질 피드백 (≥0.7)</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {stats.ready_for_training ? (
                <span className="badge badge-success">학습 준비됨</span>
              ) : (
                <span className="badge badge-default">
                  {stats.high_quality_feedback}/{stats.threshold}
                </span>
              )}
            </div>
            <div className="stat-label">학습 임계값</div>
          </div>
        </div>
      )}

      {/* Performance chart */}
      {perfData.length > 0 && (
        <div className="card" style={{ marginBottom: 24, overflowX: "auto" }}>
          <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>정확도 추이</h2>
          <svg width={chartWidth} height={chartHeight + 30} style={{ display: "block" }}>
            {/* Y axis lines */}
            {[0, 0.5, 1.0].map((v) => (
              <line
                key={v}
                x1={0}
                y1={chartHeight - v * chartHeight}
                x2={chartWidth}
                y2={chartHeight - v * chartHeight}
                stroke="#e5e7eb"
                strokeDasharray="4"
              />
            ))}
            {/* Accuracy line */}
            <polyline
              fill="none"
              stroke="#6366f1"
              strokeWidth={2}
              points={perfData
                .map((d, i) =>
                  d.accuracy != null
                    ? `${i * 40 + 20},${chartHeight - d.accuracy * chartHeight}`
                    : null
                )
                .filter(Boolean)
                .join(" ")}
            />
            {/* Dots */}
            {perfData.map((d, i) =>
              d.accuracy != null ? (
                <circle
                  key={i}
                  cx={i * 40 + 20}
                  cy={chartHeight - d.accuracy * chartHeight}
                  r={4}
                  fill="#6366f1"
                >
                  <title>{`${d.metric_date}: ${(d.accuracy * 100).toFixed(1)}%`}</title>
                </circle>
              ) : null
            )}
            {/* X axis labels */}
            {perfData.map((d, i) => (
              <text
                key={i}
                x={i * 40 + 20}
                y={chartHeight + 20}
                textAnchor="middle"
                fontSize={9}
                fill="#9ca3af"
              >
                {d.metric_date.slice(5)}
              </text>
            ))}
          </svg>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
            ● 정확도 (Accuracy)
          </div>
        </div>
      )}

      {/* Start training button */}
      <div style={{ marginBottom: 24 }}>
        {jobError && (
          <div className="banner banner-error" style={{ marginBottom: 12 }}>
            {jobError}
          </div>
        )}
        <button
          className="btn btn-primary"
          onClick={handleStartTraining}
          disabled={startingJob || !selectedService}
        >
          {startingJob ? "학습 시작 중..." : "🚀 학습 시작"}
        </button>
      </div>

      {/* Training jobs table */}
      <div className="card">
        <h2 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>학습 이력</h2>
        {jobs.length === 0 ? (
          <p className="text-muted">학습 이력이 없습니다.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>상태</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>트리거</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>피드백 수</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>시작</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>완료</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                  <td style={{ padding: "6px 8px" }}>
                    <span className={`badge badge-${STATUS_COLORS[j.status] ?? "default"}`}>
                      {j.status}
                    </span>
                  </td>
                  <td style={{ padding: "6px 8px" }}>{j.trigger_type}</td>
                  <td style={{ textAlign: "right", padding: "6px 8px" }}>{j.feedback_count}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {j.started_at ? new Date(j.started_at).toLocaleString("ko-KR") : "-"}
                  </td>
                  <td style={{ padding: "6px 8px" }}>
                    {j.completed_at ? new Date(j.completed_at).toLocaleString("ko-KR") : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
