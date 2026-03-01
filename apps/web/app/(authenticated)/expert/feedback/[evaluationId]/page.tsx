"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getReviewDetail, submitFeedback } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

interface LabelAnnotation {
  region: string;
  label: string;
  confidence: number;
}

export default function FeedbackDetailPage() {
  const { t } = useTranslation();
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
    getReviewDetail(evaluationId)
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
        feedback_type: feedbackType as "label_correction" | "false_positive" | "false_negative" | "quality_score" | "annotation",
        quality_score: qualityScore,
        corrected_output: (corrected as Record<string, unknown> | undefined),
        label_annotations: annotations.filter((a) => a.region || a.label),
        comments: comments || undefined,
      });
      setSuccess(true);
      setTimeout(() => router.push("/expert/feedback"), 1500);
    } catch (e: any) {
      setError(e.message ?? t("expertFeedback.submitFailed"));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <p className="text-muted">{t("common.loading")}</p>;
  if (!evaluation) return <p className="text-muted">{t("expertFeedback.notFound")}</p>;

  return (
    <div>
      <h1 className="page-title">{t("expertFeedback.pageTitle")}</h1>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 24 }}>
        {/* Left: Original output */}
        <div className="card">
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>{t("expertFeedback.sectionOriginalOutput")}</h2>
          <div style={{ marginBottom: 8 }}>
            <span className="text-muted" style={{ fontSize: 12 }}>{t("expertFeedback.labelEvaluationId")}</span>{" "}
            <span style={{ fontSize: 12 }}>{evaluation.id}</span>
          </div>
          {evaluation.run_id && (
            <div style={{ marginBottom: 8 }}>
              <span className="text-muted" style={{ fontSize: 12 }}>Run ID:</span>{" "}
              <span style={{ fontSize: 12 }}>{evaluation.run_id}</span>
            </div>
          )}
          <div style={{ marginBottom: 8 }}>
            <span className="text-muted" style={{ fontSize: 12 }}>{t("expertFeedback.labelStatus")}</span>{" "}
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
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>{t("expertFeedback.sectionFeedbackForm")}</h2>

          {success && (
            <div className="banner banner-success" style={{ marginBottom: 16 }}>
              {t("expertFeedback.successMessage")}
            </div>
          )}
          {error && (
            <div className="banner banner-error" style={{ marginBottom: 16 }}>
              {error}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">{t("expertFeedback.labelFeedbackType")}</label>
            <select
              className="form-control"
              value={feedbackType}
              onChange={(e) => setFeedbackType(e.target.value)}
            >
              <option value="label_correction">{t("expertFeedback.optionLabelCorrection")}</option>
              <option value="false_positive">{t("expertFeedback.optionFalsePositive")}</option>
              <option value="false_negative">{t("expertFeedback.optionFalseNegative")}</option>
              <option value="quality_score">{t("expertFeedback.optionQualityScore")}</option>
              <option value="annotation">{t("expertFeedback.optionAnnotation")}</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">
              {t("expertFeedback.labelQualityScore").replace("{score}", qualityScore.toFixed(2))}
            </label>
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
              <span>0.0 ({t("expertFeedback.qualityLow")})</span>
              <span>1.0 ({t("expertFeedback.qualityHigh")})</span>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">{t("expertFeedback.labelCorrectedOutput")}</label>
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
            <label className="form-label">{t("expertFeedback.labelAnnotations")}</label>
            {annotations.map((ann, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 8, marginBottom: 8 }}>
                <input
                  className="form-control"
                  placeholder={t("expertFeedback.annotationRegionPlaceholder")}
                  value={ann.region}
                  onChange={(e) => updateAnnotation(i, "region", e.target.value)}
                />
                <input
                  className="form-control"
                  placeholder={t("expertFeedback.annotationLabelPlaceholder")}
                  value={ann.label}
                  onChange={(e) => updateAnnotation(i, "label", e.target.value)}
                />
                <input
                  className="form-control"
                  type="number"
                  min={0}
                  max={1}
                  step={0.1}
                  placeholder={t("expertFeedback.annotationConfidencePlaceholder")}
                  value={ann.confidence}
                  onChange={(e) => updateAnnotation(i, "confidence", Number(e.target.value))}
                  style={{ width: 80 }}
                />
              </div>
            ))}
            <button className="btn btn-ghost btn-sm" onClick={addAnnotation} type="button">
              {t("expertFeedback.addAnnotation")}
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">{t("expertFeedback.labelComments")}</label>
            <textarea
              className="form-control"
              rows={3}
              placeholder={t("expertFeedback.commentsPlaceholder")}
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
            {submitting ? t("expertFeedback.submitting") : t("expertFeedback.submit")}
          </button>
        </div>
      </div>
    </div>
  );
}
