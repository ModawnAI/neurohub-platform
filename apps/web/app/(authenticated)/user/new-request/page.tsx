"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { ArrowLeft } from "phosphor-react";
import { listServices, listPipelines, createRequest, confirmRequest, submitRequest } from "@/lib/api";
import { useWizard } from "@/lib/use-wizard";
import { StepIndicator } from "@/components/wizard/step-indicator";
import { StepServiceSelect } from "@/components/wizard/step-service-select";
import { StepCaseInput } from "@/components/wizard/step-case-input";
import { StepFileUpload } from "@/components/wizard/step-file-upload";
import { StepReviewSubmit } from "@/components/wizard/step-review-submit";
import { EMPTY_DRAFT, type WizardDraft } from "@/components/wizard/types";

const STEPS = ["서비스 선택", "케이스 입력", "파일 업로드", "확인 및 제출"];
const DRAFT_KEY = "neurohub-new-request-draft";

export default function UserNewRequestPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [requestId, setRequestId] = useState<string | null>(null);
  const [caseIds, setCaseIds] = useState<string[]>([]);

  const { step, draft, setDraft, next, prev, goTo, clearDraft, hasSavedDraft, isLast } = useWizard<WizardDraft>({
    totalSteps: STEPS.length,
    draftKey: DRAFT_KEY,
    initialDraft: EMPTY_DRAFT,
    canAdvance: (s, d) => {
      if (s === 1) return !!d.service_id;
      if (s === 2) return d.cases.some((c) => c.patient_ref.trim());
      return true;
    },
  });

  const { data: servicesData } = useQuery({ queryKey: ["services"], queryFn: listServices });
  const services = servicesData?.items ?? [];
  const selectedService = services.find((s) => s.id === draft.service_id);

  const { data: pipelinesData } = useQuery({
    queryKey: ["pipelines", draft.service_id],
    queryFn: () => listPipelines(draft.service_id!),
    enabled: !!draft.service_id,
  });
  const defaultPipeline = pipelinesData?.items?.find((p) => p.is_default) || pipelinesData?.items?.[0];

  // Create the request when advancing to step 3 (file upload)
  const createMut = useMutation({
    mutationFn: async () => {
      if (requestId) return { id: requestId, caseIds };
      const validCases = draft.cases.filter((c) => c.patient_ref.trim());
      const result = await createRequest({
        service_id: draft.service_id!,
        pipeline_id: defaultPipeline!.id,
        priority: draft.priority,
        cases: validCases,
        idempotency_key: `web-${Date.now()}`,
      });
      return result;
    },
    onSuccess: (result: any) => {
      if (result.id && !requestId) {
        setRequestId(result.id);
        // Extract case IDs from the created request
        if (result.cases) {
          setCaseIds(result.cases.map((c: any) => c.id));
        }
      }
    },
    onError: (err: any) => setError(err?.message || "요청 생성에 실패했습니다."),
  });

  // Submit (confirm + submit) the request on final step
  const submitMut = useMutation({
    mutationFn: async () => {
      if (!requestId) throw new Error("요청이 생성되지 않았습니다.");
      await confirmRequest(requestId);
      return submitRequest(requestId);
    },
    onSuccess: () => {
      clearDraft();
      router.push("/user/requests");
    },
    onError: (err: any) => setError(err?.message || "요청 제출에 실패했습니다."),
  });

  const handleAdvanceToUpload = useCallback(async () => {
    setError("");
    if (!requestId) {
      createMut.mutate(undefined, { onSuccess: () => next() });
    } else {
      next();
    }
  }, [requestId, createMut, next]);

  const handleFilesUploaded = useCallback(
    (caseIndex: number, fileIds: string[]) => {
      setDraft({
        uploaded_files: { ...draft.uploaded_files, [caseIndex]: fileIds },
      });
    },
    [draft.uploaded_files, setDraft],
  );

  return (
    <div className="stack-lg">
      <button className="back-link" onClick={() => router.push("/user/requests")}>
        <ArrowLeft size={16} /> 돌아가기
      </button>

      <h1 className="page-title">새 요청 만들기</h1>

      {hasSavedDraft && step === 1 && (
        <div className="draft-banner">
          이전에 작성 중인 요청이 있습니다.
          <div className="draft-banner-actions">
            <button className="btn btn-sm btn-secondary" onClick={clearDraft}>
              삭제
            </button>
            <button className="btn btn-sm btn-primary" onClick={() => goTo(2)}>
              이어서 작성
            </button>
          </div>
        </div>
      )}

      <StepIndicator steps={STEPS} current={step} />

      {step === 1 && (
        <StepServiceSelect
          services={services}
          selectedId={draft.service_id}
          onSelect={(id) => {
            setDraft({ service_id: id });
            const pipeline = pipelinesData?.items?.find((p) => p.is_default) || pipelinesData?.items?.[0];
            if (pipeline) setDraft({ pipeline_id: pipeline.id });
          }}
          onNext={next}
        />
      )}

      {step === 2 && (
        <StepCaseInput
          cases={draft.cases}
          onChange={(cases) => setDraft({ cases })}
          onNext={handleAdvanceToUpload}
          onPrev={prev}
        />
      )}

      {step === 3 && (
        <StepFileUpload
          requestId={requestId}
          cases={draft.cases}
          caseIds={caseIds}
          uploadedFiles={draft.uploaded_files}
          onFilesUploaded={handleFilesUploaded}
          onNext={next}
          onPrev={prev}
        />
      )}

      {step === 4 && (
        <StepReviewSubmit
          service={selectedService}
          cases={draft.cases}
          uploadedFiles={draft.uploaded_files}
          onPrev={prev}
          onSubmit={() => submitMut.mutate()}
          isPending={submitMut.isPending}
          error={error}
        />
      )}
    </div>
  );
}
