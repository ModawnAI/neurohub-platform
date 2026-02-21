"use client";

import {
  type PipelineRead,
  type ServiceRead,
  createRequest,
  listPipelines,
  listServices,
} from "@/lib/api";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

function defaultIdempotencyKey() {
  return `req_${new Date()
    .toISOString()
    .replace(/[-:.TZ]/g, "")
    .slice(0, 14)}`;
}

export default function NewRequestPage() {
  const router = useRouter();
  const [serviceId, setServiceId] = useState("");
  const [pipelineId, setPipelineId] = useState("");
  const [patientRef, setPatientRef] = useState("PT-2026-0001");
  const [priority, setPriority] = useState(5);
  const [idempotencyKey, setIdempotencyKey] = useState(defaultIdempotencyKey());

  const servicesQuery = useQuery<{ items: ServiceRead[] }, Error>({
    queryKey: ["services"],
    queryFn: listServices,
  });

  useEffect(() => {
    if (!serviceId && servicesQuery.data?.items.length) {
      const firstService = servicesQuery.data.items[0];
      if (firstService) {
        setServiceId(firstService.id);
      }
    }
  }, [servicesQuery.data?.items, serviceId]);

  const pipelinesQuery = useQuery<{ items: PipelineRead[] }, Error>({
    queryKey: ["pipelines", serviceId],
    queryFn: () => listPipelines(serviceId),
    enabled: Boolean(serviceId),
  });

  useEffect(() => {
    if (!pipelineId && pipelinesQuery.data?.items.length) {
      const defaultPipeline = pipelinesQuery.data.items.find((item) => item.is_default);
      const firstPipeline = pipelinesQuery.data.items[0];
      if (defaultPipeline?.id) {
        setPipelineId(defaultPipeline.id);
      } else if (firstPipeline) {
        setPipelineId(firstPipeline.id);
      }
    }
  }, [pipelinesQuery.data?.items, pipelineId]);

  const createMutation = useMutation({
    mutationFn: createRequest,
    onSuccess: () => {
      router.push("/requests");
    },
  });

  const disabled = useMemo(
    () => !serviceId || !pipelineId || !patientRef.trim() || createMutation.isPending,
    [serviceId, pipelineId, patientRef, createMutation.isPending],
  );

  const submit = () => {
    createMutation.mutate({
      service_id: serviceId,
      pipeline_id: pipelineId,
      priority,
      idempotency_key: idempotencyKey,
      cases: [{ patient_ref: patientRef.trim() }],
    });
  };

  return (
    <section className="panel stack-md">
      <div>
        <h2>신규 요청 생성</h2>
        <p className="muted-text">서비스와 파이프라인을 선택하고 첫 케이스를 등록합니다.</p>
      </div>

      {servicesQuery.isError ? <p className="error-text">{servicesQuery.error.message}</p> : null}
      {pipelinesQuery.isError ? <p className="error-text">{pipelinesQuery.error.message}</p> : null}
      {createMutation.isError ? <p className="error-text">{createMutation.error.message}</p> : null}

      <div className="form-grid">
        <label className="field">
          <span>서비스</span>
          <select
            className="select"
            value={serviceId}
            onChange={(event) => {
              setServiceId(event.target.value);
              setPipelineId("");
            }}
          >
            <option value="">선택하세요</option>
            {(servicesQuery.data?.items ?? []).map((service) => (
              <option key={service.id} value={service.id}>
                {service.display_name} ({service.version})
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>파이프라인</span>
          <select
            className="select"
            value={pipelineId}
            onChange={(event) => setPipelineId(event.target.value)}
            disabled={!serviceId}
          >
            <option value="">선택하세요</option>
            {(pipelinesQuery.data?.items ?? []).map((pipeline) => (
              <option key={pipeline.id} value={pipeline.id}>
                {pipeline.name} ({pipeline.version}){pipeline.is_default ? " [기본]" : ""}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>환자 참조 ID</span>
          <input
            className="input"
            value={patientRef}
            onChange={(event) => setPatientRef(event.target.value)}
            placeholder="PT-2026-0001"
          />
        </label>

        <label className="field">
          <span>우선순위 (1~10)</span>
          <input
            className="input"
            type="number"
            min={1}
            max={10}
            value={priority}
            onChange={(event) => setPriority(Number(event.target.value))}
          />
        </label>

        <label className="field field-wide">
          <span>Idempotency Key</span>
          <input
            className="input mono-field"
            value={idempotencyKey}
            onChange={(event) => setIdempotencyKey(event.target.value)}
          />
        </label>
      </div>

      <div className="action-row">
        <button
          className="btn btn-secondary"
          type="button"
          onClick={() => router.push("/requests")}
        >
          목록으로
        </button>
        <button className="btn btn-primary" type="button" disabled={disabled} onClick={submit}>
          {createMutation.isPending ? "생성 중..." : "요청 생성"}
        </button>
      </div>
    </section>
  );
}
