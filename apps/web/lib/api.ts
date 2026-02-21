import { supabase } from "@/lib/supabase";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

export type RequestStatus =
  | "CREATED"
  | "RECEIVING"
  | "STAGING"
  | "READY_TO_COMPUTE"
  | "COMPUTING"
  | "QC"
  | "REPORTING"
  | "EXPERT_REVIEW"
  | "FINAL"
  | "FAILED"
  | "CANCELLED";

export interface RequestRead {
  id: string;
  institution_id: string;
  service_id: string;
  pipeline_id: string;
  status: RequestStatus;
  priority: number;
  case_count: number;
  created_at: string;
  updated_at: string | null;
  cancel_reason: string | null;
}

export interface ServiceRead {
  id: string;
  institution_id: string;
  name: string;
  display_name: string;
  version: string;
  status: string;
  department: string | null;
  created_at: string;
}

export interface PipelineRead {
  id: string;
  service_id: string;
  name: string;
  version: string;
  is_default: boolean;
  created_at: string;
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window !== "undefined" && supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      return {
        Authorization: `Bearer ${session.access_token}`,
      };
    }
  }

  // Local fallback headers for fast development bootstrap.
  return {
    "X-User-Id": process.env.NEXT_PUBLIC_DEV_USER_ID ?? "11111111-1111-1111-1111-111111111111",
    "X-Username": process.env.NEXT_PUBLIC_DEV_USERNAME ?? "dev-user",
    "X-Institution-Id":
      process.env.NEXT_PUBLIC_DEV_INSTITUTION_ID ?? "00000000-0000-0000-0000-000000000001",
    "X-Roles": process.env.NEXT_PUBLIC_DEV_ROLES ?? "SYSTEM_ADMIN",
  };
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "";
    try {
      const body = (await response.json()) as { detail?: string | { message?: string } };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail?.message) {
        detail = body.detail.message;
      }
    } catch {
      detail = "";
    }

    const message = detail || `API ${response.status}: ${response.statusText}`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function listRequests() {
  return apiFetch<{ items: RequestRead[]; total: number }>("/requests");
}

export async function getRequest(requestId: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}`);
}

export async function createRequest(payload: {
  service_id: string;
  pipeline_id: string;
  priority: number;
  cases: Array<{ patient_ref: string; demographics?: Record<string, unknown> }>;
  idempotency_key?: string;
}) {
  return apiFetch<RequestRead>("/requests", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function transitionRequest(requestId: string, targetStatus: RequestStatus, note?: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/transition`, {
    method: "POST",
    body: JSON.stringify({ target_status: targetStatus, note }),
  });
}

export async function confirmRequest(requestId: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/confirm`, {
    method: "POST",
    body: JSON.stringify({ confirm_note: "웹에서 확인 완료" }),
  });
}

export async function submitRequest(requestId: string) {
  return apiFetch<{ request_id: string; status: RequestStatus; run_ids: string[] }>(
    `/requests/${requestId}/submit`,
    {
      method: "POST",
    },
  );
}

export async function cancelRequest(requestId: string, reason: string) {
  return apiFetch<RequestRead>(`/requests/${requestId}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function listServices() {
  return apiFetch<{ items: ServiceRead[] }>("/services");
}

export async function listPipelines(serviceId: string) {
  return apiFetch<{ items: PipelineRead[] }>(`/services/${serviceId}/pipelines`);
}
