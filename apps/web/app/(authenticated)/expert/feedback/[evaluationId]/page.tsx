"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getEvaluation, submitFeedback } from "@/lib/api";

interface LabelAnnotation {
  region: string;
  label: string;
  confidence: number;
}

export default function FeedbackDetailPage() {
  const { evaluationId } = useParams<{ evaluationId: string }>();
  const router = useRouter();

  const [evaluation, setEvaluation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [feedbackType, setFeedbackType] = useState("label_correction");
  const [qualityScore, setQualityScore] = useState(0.8);
  const [correctedOutput, setCorrectedOutput] = useState("");
  const [comments, setComments] = useState("");
  const [annotations, setAnnotations] = useState<LabelAnnotation[]>([
    { region: "", label: "", confidence: 1.0 },
  ]);

  useEffect(() => {
    getEvaluation(evaluationId)
      .then(setEvaluation)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [evaluationId]);

  const addAnnotation = () =>
    setAnnotations((prev) => [...prev, { region: "", label: "", confidence: 1.0 }]);

  const updateAnnotation = (i: number, field: keyof LabelAnnotation, value: string | number) => {
    setAnnotations((prev) => prev.map((a, idx) => (idx === i ? { ...a, [field]: value } : a)));
  };

  const handleSubmit = async () => {
    if (!evaluation) return;
    setSubmitting(true);
    setError(null);
    try {
      let corrected: object | undefined;
      if (correctedOutput.trim()) {
        corrected = JSON.parse(correctedOutput);
      }
      await submitFeedback(evaluationId, {
        run_id: evaluation.run_id,
        feedback_type: feedbackType,
        quality_score: qualityScore,
        corrected_output: corrected,
        label_annotations: annotations.filter((a) => a.region || a.label),
        comments: comments || undefined,
      });
      setSuccess(true);
      setTimeout(() => router.push("/expert/feedback"), 1500);
    } catch (e: any) {
      setError(e.message ?? "제출 실패");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="text-muted">불러오는 중...</p>;
  if (!evaluation) return <p className="text-muted">평가를 찾을 수 없습니다.</p>;

  return (
    <div>
      <h1 className="page-title">피드백 제출</h1>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 24 }}>
        {/* Left: Original output */}
        <div className="card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>모델 원본 출력</h2>
          <div style={{ marginBottom: 8 }}>
            <span className="text-muted" style={{ fontSize: 12 }}>평가 ID:</span>{" "}
            <span style={{ fontSize: 12 }}>{evaluation.id}</span>
          </div>
          {evaluation.run_id && (
            <div style={{ marginBottom: 8 }}>
              <span className="text-muted" style={{ fontSize: 12 }}>Run ID:</span>{" "}
              <span style={{ fontSize: 12 }}>{evaluation.run_id}</span>
            </div>
          )}
          <div style={{ marginBottom: 8 }}>
            <span className="text-muted" style={{ fontSize: 12 }}>상태:</span>{" "}
            <span className="badge badge-success" style={{ fontSize: 11 }}>{evaluation.status}</span>
          </div>
          <pre
            style={{
              background: "var(--bg-subtle, #f5f5f5)",
              borderRadius: 6,
              padding: 12,
              fontSize: 11,
              overflow: "auto",
              maxHeight: 400,
              marginTop: 12,
            }}
          >
            {JSON.stringify(evaluation, null, 2)}
          </pre>
        </div>

        {/* Right: Feedback form */}
        <div className="card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>피드백 입력</h2>

          {success && (
            <div className="banner banner-success" style={{ marginBottom: 16 }}>
              피드백이 성공적으로 제출되었습니다!
            </div>
          )}
          {error && (
            <div className="banner banner-error" style={{ marginBottom: 16 }}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">피드백 유형</label>
            <select
              className="form-control"
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
            >
              <option value="label_correction">레이블 교정</option>
              <option value="false_positive">위양성</option>
              <option value="false_negative">위음성</option>
              <option value="quality_score">품질 점수</option>
              <option value="annotation">어노테이션</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">품질 점수: {qualityScore.toFixed(2)}</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={qualityScore}
              onChange={(e) => setQualityScore(Number(e.target.value))}
              style={{ width: "100%" }}
            />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-muted)" }}>
              <span>0.0 (낮음)</span>
              <span>1.0 (높음)</span>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">교정된 출력 (JSON)</label>
            <textarea
              className="form-control"
              rows={5}
              placeholder='{"result": "corrected value"}'
              value={correctedOutput}
              onChange={(e) => setCorrectedOutput(e.target.value)}
              style={{ fontFamily: "monospace", fontSize: 12 }}
            />
          </div>

          <div className="form-group">
            <label className="form-label">레이블 어노테이션</label>
            {annotations.map((ann, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 8, marginBottom: 8 }}>
                <input
                  className="form-control"
                  placeholder="영역 (예: hippocampus)"
                  value={ann.region}
                  onChange={(e) => updateAnnotation(i, "region", e.target.value)}
                />
                <input
                  className="form-control"
                  placeholder="레이블 (예: atrophy)"
                  value={ann.label}
                  onChange={(e) => updateAnnotation(i, "label", e.target.value)}
                />
                <input
                  className="form-control"
                  type="number"
                  min={0}
                  max={1}
                  step={0.1}
                  placeholder="신뢰도"
                  value={ann.confidence}
                  onChange={(e) => updateAnnotation(i, "confidence", Number(e.target.value))}
                  style={{ width: 80 }}
                />
              </div>
            ))}
            <button className="btn btn-ghost btn-sm" onClick={addAnnotation} type="button">
              + 어노테이션 추가
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">코멘트</label>
            <textarea
              className="form-control"
              rows={3}
              placeholder="추가 의견을 입력하세요"
              value={comments}
              onChange={(e) => setComments(e.target.value)}
            />
          </div>

          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitting || success}
            style={{ width: "100%" }}
          >
            {submitting ? "제출 중..." : "피드백 제출"}
          </button>
        </div>
      </div>
    </div>
  );
}
